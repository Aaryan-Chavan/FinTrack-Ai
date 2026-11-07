"""FinTrack assistant.

The previous client called gemini-2.5-flash with a single 15-second socket
timeout. That model spends the budget on hidden thinking, so the request
died before any tokens arrived and the UI showed:

    Google AI took too long to respond (15-second timeout reached).

This module keeps the same public contract — {"answer": str} or {"error": str} —
but it will not strand a budget, allocation, or spending question on that timer.

Order of operations:
1. Load only the caller's own profile, plan, closure, and analytics.
2. If a Gemini key is configured, ask ONE fast model with thinking disabled
   and a bounded read timeout. A 404/400 advances to the next model.
   HTTP 429 is returned as a rate-limit error (it is account-wide, not transient).
3. On timeout, overload, an empty payload, a transport error, or a missing key,
   answer from those same records. Figures are formatted, never invented.
"""

import datetime
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import requests

from config import Config
import services


# Fast models first. gemini-2.5-flash is last and only with thinking switched off;
# the old default (thinking on, 15s cap) is what users were hitting.
_MODEL_CHAIN = (
    ("gemini-2.5-flash-lite", True),
    ("gemini-2.0-flash", False),
    ("gemini-2.5-flash", True),
)

_CONNECT_TIMEOUT = 4
_READ_TIMEOUT = 12
_MAX_MESSAGE_CHARS = 4000
_PLACEHOLDER_KEYS = {"", "your_gemini_api_key_here"}

_RATE_LIMIT_ERROR = (
    "Google API rate limit reached (Max 5 queries/min). Please wait 60 seconds."
)


def ask_assistant(user_id, message):
    """Return {"answer": text} or {"error": text}. Never raises."""
    message = str(message or "").strip()
    if not message:
        return {"error": "Message is empty"}
    if len(message) > _MAX_MESSAGE_CHARS:
        message = message[:_MAX_MESSAGE_CHARS]

    try:
        context = _load_context(user_id)
    except Exception as exc:
        print(f"System Error: {exc}")
        return {"error": "An unexpected system error occurred."}

    key = str(getattr(Config, "GEMINI_API_KEY", "") or "").strip()
    if key in _PLACEHOLDER_KEYS:
        return {"answer": grounded_reply(message, context)}

    try:
        remote = _ask_gemini(key, message, context)
    except Exception as exc:
        print(f"System Error: {exc}")
        return {"answer": grounded_reply(message, context)}

    if remote.get("answer"):
        return {"answer": remote["answer"]}
    if remote.get("rate_limited"):
        return {"error": _RATE_LIMIT_ERROR}
    # Timeout, 5xx, empty candidates, unknown model: the records still answer.
    return {"answer": grounded_reply(message, context)}


def grounded_reply(message, context):
    """Deterministic answer. Uses only numbers present in ``context``."""
    ctx = context or {}
    question = str(message or "").lower()
    plan = ctx.get("plan") or {}
    closure = ctx.get("closure") or {}
    analytics = ctx.get("analytics") or {}

    plan_hit = any(
        word in question
        for word in (
            "budget",
            "plan",
            "salary",
            "take-home",
            "take home",
            "emergency",
            "discretionary",
            "obligation",
            "emi",
            "debt",
        )
    )
    alloc_hit = any(
        word in question
        for word in ("allocat", "surplus", "split", "distribute", "where should", "how should")
    )
    spend_hit = any(
        word in question
        for word in ("spend", "expense", "analys", "analyz", "trend", "saving", "categor")
    )

    if (
        "emergency" in question
        and "target" in question
        and not alloc_hit
        and not spend_hit
        and "budget" not in question
    ):
        return _emergency_only(plan)

    sections = []
    if plan_hit or not (alloc_hit or spend_hit):
        sections.append(_plan_section(plan))
    if alloc_hit:
        sections.append(_alloc_section(plan, closure))
    if spend_hit:
        sections.append(_spend_section(analytics))

    intro = (
        "Here is what your FinTrack records support. "
        "Every figure below is calculated from your profile, transactions, and closure."
    )
    return intro + "\n\n" + "\n\n".join(sections)


def _load_context(user_id):
    month = datetime.date.today().strftime("%Y-%m")
    profile = _safe(services.get_profile, user_id)
    plan = _safe(services.generate_plan, user_id)
    closure = _safe(services.get_closure, user_id, month)
    analytics = _safe(services.get_analytics, user_id)
    return {
        "month": month,
        "profile": _slim_profile(profile),
        "plan": plan if isinstance(plan, dict) else None,
        "closure": _slim_closure(closure),
        "analytics": _slim_analytics(analytics),
    }


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:
        name = getattr(fn, "__name__", "service")
        print(f"Context fetch failed in {name}: {exc}")
        return None


def _slim_profile(profile):
    if not isinstance(profile, dict):
        return None
    keys = ("take_home_salary", "essential_expenses", "debt_obligations")
    return {key: profile.get(key) for key in keys}


def _slim_closure(closure):
    if not isinstance(closure, dict):
        return None
    keys = (
        "month",
        "recorded_income",
        "recorded_expense",
        "recorded_surplus",
        "confirmed_surplus",
        "is_closed",
        "allocation",
    )
    return {key: closure.get(key) for key in keys}


def _slim_analytics(analytics):
    if not isinstance(analytics, dict):
        return None
    pie = analytics.get("pie") or []
    unusual = analytics.get("unusual_spending") or []
    recurring = analytics.get("recurring_expenses") or []
    bar = analytics.get("bar") or []
    return {
        "income": analytics.get("income"),
        "expense": analytics.get("expense"),
        "balance": analytics.get("balance"),
        "savings_rate": analytics.get("savings_rate"),
        "pie": pie[:5] if isinstance(pie, list) else [],
        "unusual_spending": unusual[:3] if isinstance(unusual, list) else [],
        "recurring_expenses": recurring[:5] if isinstance(recurring, list) else [],
        "bar": bar[:6] if isinstance(bar, list) else [],
    }


def _ask_gemini(api_key, message, context):
    """One attempt per model. Returns answer, rate_limited, or reason."""
    payload_with_thinking = _payload(message, context, thinking=True)
    payload_plain = _payload(message, context, thinking=False)
    last_reason = "unavailable"

    for model, allow_thinking in _MODEL_CHAIN:
        payload = payload_with_thinking if allow_thinking else payload_plain
        outcome = _post_model(api_key, model, payload)
        if outcome.get("retry_without_thinking") and allow_thinking:
            outcome = _post_model(api_key, model, payload_plain)

        if outcome.get("answer"):
            return outcome
        if outcome.get("rate_limited"):
            return outcome
        if outcome.get("advance"):
            last_reason = outcome.get("reason") or last_reason
            continue
        # Timeout, 5xx, network: do not walk the rest of the chain.
        return {"reason": outcome.get("reason") or last_reason}

    return {"reason": last_reason}


def _post_model(api_key, model, payload):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
    except requests.exceptions.Timeout:
        print(f"Gemini timeout on {model} after {_READ_TIMEOUT}s read.")
        return {"reason": "timeout"}
    except requests.exceptions.RequestException as exc:
        print(f"Gemini transport error on {model}: {exc}")
        return {"reason": "network"}

    status = response.status_code
    if status == 200:
        try:
            body = response.json()
        except ValueError:
            return {"reason": "bad-json", "advance": True}
        text = _extract_text(body)
        if text:
            print(f"AI response received from {model}.")
            return {"answer": text}
        return {"reason": "empty", "advance": True}

    if status == 429:
        print("Gemini rate limit.")
        return {"rate_limited": True}

    error_msg = _error_message(response)
    if status == 400 and "thinking" in error_msg.lower():
        return {"retry_without_thinking": True, "reason": error_msg}
    if status in (400, 404):
        print(f"Gemini model {model} rejected ({status}): {error_msg}")
        return {"advance": True, "reason": error_msg}
    if status in (500, 502, 503, 504):
        print(f"Gemini overloaded ({status}) on {model}.")
        return {"reason": "overloaded"}
    if status in (401, 403):
        print(f"Gemini auth error ({status}): {error_msg}")
        return {"reason": error_msg}

    print(f"Gemini error ({status}): {error_msg}")
    return {"advance": True, "reason": error_msg}


def _payload(message, context, thinking):
    system_instruction = (
        "You are the FinTrack assistant for one person in India. "
        "Use ONLY the JSON figures below. Never invent amounts, rates, or dates. "
        "If a figure is missing, say it is not in the records. "
        "Answer in concise plain text. Amounts in INR.\n\n"
        "USER DATA:\n"
        + json.dumps(context, default=str)
    )
    generation = {"temperature": 0.2, "maxOutputTokens": 512}
    if thinking:
        generation["thinkingConfig"] = {"thinkingBudget": 0}
    return {
        "contents": [{"role": "user", "parts": [{"text": message}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": generation,
    }


def _extract_text(data):
    if not isinstance(data, dict):
        return ""
    candidates = data.get("candidates") or []
    if not candidates or not isinstance(candidates, list):
        return ""
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = (content or {}).get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        return ""
    chunks = []
    for part in parts:
        if not isinstance(part, dict) or part.get("thought"):
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            chunks.append(text.strip())
    return "\n".join(chunks).strip()


def _error_message(response):
    try:
        body = response.json()
    except ValueError:
        return "Unknown API Error"
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
    return "Unknown API Error"


def _money(val):
    if val is None or val == "":
        quantized = Decimal("0.00")
    else:
        try:
            quantized = Decimal(str(val).strip())
            if quantized.is_nan() or quantized.is_infinite():
                quantized = Decimal("0.00")
        except (InvalidOperation, ValueError, TypeError):
            quantized = Decimal("0.00")
    sign = "-" if quantized < 0 else ""
    quantized = abs(quantized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole, frac = f"{quantized:.2f}".split(".")
    if len(whole) <= 3:
        grouped = whole
    else:
        head, tail = whole[:-3], whole[-3:]
        groups = [tail]
        while head:
            groups.append(head[-2:])
            head = head[:-2]
        grouped = ",".join(reversed(groups))
    return f"{sign}₹{grouped}.{frac}"


def _emergency_only(plan):
    if not isinstance(plan, dict) or plan.get("status") == "deficit":
        shortfall = _money(plan.get("shortfall") if isinstance(plan, dict) else None)
        return (
            f"There is no emergency-fund target this month. "
            f"Obligations exceed take-home by **{shortfall}**, "
            "so the emergency, short-term, and investment buckets stay at ₹0.00."
        )
    return (
        f"Your emergency-fund target is **{_money(plan.get('emergency_target'))}**. "
        f"That is 10% of take-home ({_money(plan.get('take_home'))}), "
        "capped by what remains after essentials and debt. "
        "No other figure was used."
    )


def _plan_section(plan):
    if not isinstance(plan, dict):
        return (
            "**Budget plan**\n"
            "No salary profile is on file yet. Enter take-home, essentials, and debt in Salary Planner."
        )
    if plan.get("status") == "deficit":
        return (
            "**Budget plan**\n"
            f"Deficit. Take-home {_money(plan.get('take_home'))} does not cover "
            f"essentials {_money(plan.get('essentials'))} plus debt {_money(plan.get('debts'))}. "
            f"The gap is **{_money(plan.get('shortfall'))}**.\n"
            "Emergency, short-term, and investment targets are ₹0.00 until obligations fit inside take-home. "
            "Do not allocate a surplus you do not have."
        )
    return (
        "**Budget plan**\n"
        f"- Take-home: {_money(plan.get('take_home'))}\n"
        f"- Essentials: {_money(plan.get('essentials'))}\n"
        f"- Debt / EMI: {_money(plan.get('debts'))}\n"
        f"- Obligations: {_money(plan.get('obligations'))}\n"
        f"- Emergency target (10% of take-home, or whatever remains): **{_money(plan.get('emergency_target'))}**\n"
        f"- Short-term goals (next 10%): **{_money(plan.get('short_term_target'))}**\n"
        f"- Investments (next 10%): **{_money(plan.get('investments_target'))}**\n"
        f"- Left for discretionary spending: **{_money(plan.get('discretionary_allowance'))}**"
    )


def _alloc_section(plan, closure):
    lines = ["**Surplus allocation**"]
    plan = plan if isinstance(plan, dict) else {}
    closure = closure if isinstance(closure, dict) else {}

    if plan.get("status") == "deficit":
        lines.append(
            f"No surplus to allocate. The planner shortfall is {_money(plan.get('shortfall'))}."
        )
        return "\n".join(lines)

    recorded = closure.get("recorded_surplus")
    if recorded is not None:
        lines.append(f"- Recorded surplus (income minus expense): {_money(recorded)}")

    if closure.get("is_closed") and closure.get("confirmed_surplus") is not None:
        confirmed = _to_decimal(closure.get("confirmed_surplus"))
        lines.append(f"- Confirmed bank surplus: **{_money(confirmed)}**")
        split = _split_confirmed(confirmed, plan)
        lines.append(
            "Suggested split of that confirmed amount, capped by the planner targets "
            "(not a new rate, and never above the confirmed surplus):"
        )
        lines.append(f"- Emergency: {_money(split['emergency'])}")
        lines.append(f"- Short-term: {_money(split['short_term'])}")
        lines.append(f"- Investments: {_money(split['investments'])}")
        lines.append(f"- Unassigned remainder: {_money(split['remainder'])}")
    else:
        lines.append("- This month is not closed, so there is no confirmed bank surplus to distribute yet.")
        lines.append(
            "- Close the month against your actual bank balance, then aim for the planner targets: "
            f"emergency {_money(plan.get('emergency_target'))}, "
            f"short-term {_money(plan.get('short_term_target'))}, "
            f"investments {_money(plan.get('investments_target'))}."
        )

    allocation = closure.get("allocation") if isinstance(closure.get("allocation"), dict) else None
    if allocation:
        lines.append(
            "- Already saved on this closure: "
            f"emergency {_money(allocation.get('emergency'))}, "
            f"short-term {_money(allocation.get('short_term'))}, "
            f"investments {_money(allocation.get('investments'))}."
        )
    return "\n".join(lines)


def _split_confirmed(confirmed, plan):
    remaining = confirmed if confirmed > 0 else Decimal("0.00")
    out = {}
    for src, dest in (
        ("emergency_target", "emergency"),
        ("short_term_target", "short_term"),
        ("investments_target", "investments"),
    ):
        cap = _to_decimal(plan.get(src))
        take = min(remaining, cap)
        out[dest] = take
        remaining -= take
    out["remainder"] = remaining
    return out


def _spend_section(analytics):
    analytics = analytics if isinstance(analytics, dict) else {}
    if not analytics:
        return "**Spending**\nNo expense analytics are on file yet. Add a few transactions first."

    lines = [
        "**Spending**",
        (
            f"- Income {_money(analytics.get('income'))}, "
            f"expenses {_money(analytics.get('expense'))}, "
            f"balance {_money(analytics.get('balance'))}."
        ),
        f"- Savings rate: **{analytics.get('savings_rate') or '0.00'}%** of recorded income.",
    ]
    pie = analytics.get("pie") or []
    if pie:
        top = pie[0] if isinstance(pie[0], dict) else {}
        lines.append(
            f"- Largest category: **{top.get('category') or 'Uncategorised'}** "
            f"at {_money(top.get('total'))}. Look here before the smaller categories."
        )
        rest = []
        for row in pie[1:5]:
            if isinstance(row, dict):
                rest.append(f"{row.get('category') or 'Uncategorised'} {_money(row.get('total'))}")
        if rest:
            lines.append("- Also recorded: " + ", ".join(rest) + ".")
    else:
        lines.append("- No expense categories are recorded yet.")

    unusual = analytics.get("unusual_spending") or []
    if unusual and isinstance(unusual[0], dict):
        item = unusual[0]
        lines.append(
            f"- Unusual: {item.get('category') or 'Uncategorised'} "
            f"{_money(item.get('amount'))} on {item.get('date') or 'an unknown date'} "
            "is above twice your average expense. Confirm it before it repeats."
        )

    recurring = analytics.get("recurring_expenses") or []
    if recurring and isinstance(recurring[0], dict):
        item = recurring[0]
        lines.append(
            f"- Recurring: {item.get('category') or 'Uncategorised'} appears "
            f"{item.get('occurrences')} times, totalling {_money(item.get('total'))}."
        )

    lines.append(
        "Keep discretionary spending inside the planner allowance. "
        "These notes use only the totals above."
    )
    return "\n".join(lines)


def _to_decimal(val):
    try:
        number = Decimal(str(val).strip())
        if number.is_nan() or number.is_infinite():
            return Decimal("0.00")
        return number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        return Decimal("0.00")