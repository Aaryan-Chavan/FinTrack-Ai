import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
import jwt
import requests

from config import Config
import auth
import services
import ai_assistant

# ==========================================
# 1. MONETARY PRECISION & VALIDATION TESTS
# ==========================================

def test_to_decimal_precision_and_rounding():
    assert services.to_decimal("100.555") == Decimal("100.56")
    assert services.to_decimal("100.554") == Decimal("100.55")
    assert services.to_decimal(50000) == Decimal("50000.00")
    assert services.to_decimal(None) == Decimal("0.00")
    assert services.to_decimal("") == Decimal("0.00")
    assert services.to_decimal("invalid") == Decimal("0.00")

def test_parse_non_negative_decimal():
    assert services.parse_non_negative_decimal("250.75") == Decimal("250.75")
    assert services.parse_non_negative_decimal(0) == Decimal("0.00")
    with pytest.raises(ValueError, match="cannot be negative"):
        services.parse_non_negative_decimal("-10.00", "Salary")
    with pytest.raises(ValueError, match="must be a valid number"):
        services.parse_non_negative_decimal("abc", "Salary")

# ==========================================
# 2. JWT AUTHENTICATION UNIT TESTS
# ==========================================

def test_jwt_generate_and_decode():
    token = auth.generate_token(42)
    decoded = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
    assert decoded["sub"] == "42"

def test_jwt_expired_token_rejected():
    from app import app
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)
    expired_token = jwt.encode({"exp": past, "iat": past, "sub": "42"}, Config.SECRET_KEY, algorithm="HS256")

    with app.test_client() as client:
        res = client.get("/api/v1/plan", headers={"Authorization": f"Bearer {expired_token}"})
        assert res.status_code == 401
        assert "expired" in res.get_json()["error"].lower()

def test_jwt_missing_and_malformed_tokens():
    from app import app
    with app.test_client() as client:
        res1 = client.get("/api/v1/plan")
        assert res1.status_code == 401

        res2 = client.get("/api/v1/plan", headers={"Authorization": "Bearer not.a.valid.jwt"})
        assert res2.status_code == 401

# ==========================================
# 3. FINANCIAL PLANNER UNIT TESTS
# ==========================================

@patch("services.get_profile")
def test_generate_plan_surplus_waterfall(mock_get_profile):
    mock_get_profile.return_value = {
        "user_id": 1,
        "take_home_salary": "100000.00",
        "essential_expenses": "40000.00",
        "debt_obligations": "15000.00"
    }
    plan = services.generate_plan(1)
    assert plan["status"] == "ok"
    assert plan["emergency_target"] == "10000.00"
    assert plan["short_term_target"] == "10000.00"
    assert plan["investments_target"] == "10000.00"
    assert plan["discretionary_allowance"] == "15000.00"

@patch("services.get_profile")
def test_generate_plan_deficit_detection(mock_get_profile):
    mock_get_profile.return_value = {
        "user_id": 1,
        "take_home_salary": "30000.00",
        "essential_expenses": "25000.00",
        "debt_obligations": "10000.00"
    }
    plan = services.generate_plan(1)
    assert plan["status"] == "deficit"
    assert plan["shortfall"] == "5000.00"
    assert plan["emergency_target"] == "0.00"

@patch("services.get_profile")
def test_generate_plan_tight_boundary_partial_buckets(mock_get_profile):
    mock_get_profile.return_value = {
        "user_id": 1,
        "take_home_salary": "50000.00",
        "essential_expenses": "40000.00",
        "debt_obligations": "2000.00"
    }
    # Remaining is 8000; 10% of 50000 is 5000
    plan = services.generate_plan(1)
    assert plan["status"] == "ok"
    assert plan["emergency_target"] == "5000.00"
    assert plan["short_term_target"] == "3000.00"
    assert plan["investments_target"] == "0.00"
    assert plan["discretionary_allowance"] == "0.00"

# ==========================================
# 4. MONTHLY CLOSURE & ALLOCATION UNIT TESTS
# ==========================================

def test_get_closure_invalid_month_format():
    with pytest.raises(ValueError, match="Invalid month format"):
        services.get_closure(1, "2026-13")
    with pytest.raises(ValueError, match="Invalid month format"):
        services.get_closure(1, "invalid")

@patch("services.get_db_connection")
def test_allocate_surplus_validation_and_limits(mock_db):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur

    # Case 1: Negative bucket value rejected before DB query
    ok, msg = services.allocate_surplus(1, 10, "-500", "1000", "500")
    assert ok is False
    assert "cannot be negative" in msg

    # Case 2: Exceeding confirmed surplus rejected
    mock_cur.fetchone.return_value = {"confirmed_surplus": Decimal("10000.00"), "is_closed": True}
    ok, msg = services.allocate_surplus(1, 10, "5000", "4000", "2000")
    assert ok is False
    assert "exceeds" in msg.lower()

    # Case 3: Valid allocation within confirmed surplus succeeds
    ok, msg = services.allocate_surplus(1, 10, "4000", "3000", "3000")
    assert ok is True
    assert "successfully" in msg.lower()

# ==========================================
# 5. GEMINI ASSISTANT MOCKED UNIT TESTS
# ==========================================

@patch("ai_assistant.requests.post")
@patch("services.get_analytics")
@patch("services.get_closure")
@patch("services.generate_plan")
@patch("services.get_profile")
def test_ai_assistant_success_and_rate_limit(mock_prof, mock_plan, mock_closure, mock_analytics, mock_post):
    Config.GEMINI_API_KEY = "test_valid_key_123"
    mock_prof.return_value = {"take_home_salary": "80000.00"}
    mock_plan.return_value = {"status": "ok", "emergency_target": "8000.00"}
    mock_closure.return_value = {"recorded_surplus": "30000.00", "is_closed": False}
    mock_analytics.return_value = {"income": "80000.00", "expense": "50000.00", "balance": "30000.00", "savings_rate": "37.50", "pie": []}

    # Mock 200 OK
    mock_resp_ok = MagicMock()
    mock_resp_ok.status_code = 200
    mock_resp_ok.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Your emergency target is ₹8,000.00."}]}}]
    }
    mock_post.return_value = mock_resp_ok

    res = ai_assistant.ask_assistant(1, "What is my emergency target?")
    assert "answer" in res
    assert "8,000.00" in res["answer"]

    # Mock 429 Rate Limit
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_post.return_value = mock_resp_429

    res_limit = ai_assistant.ask_assistant(1, "What is my emergency target?")
    assert "error" in res_limit
    assert "rate limit" in res_limit["error"].lower()
    assert "answer" not in res_limit


def _full_plan():
    return {
        "status": "ok",
        "take_home": "80000.00",
        "essentials": "32000.00",
        "debts": "8000.00",
        "obligations": "40000.00",
        "shortfall": "0.00",
        "emergency_target": "8000.00",
        "short_term_target": "8000.00",
        "investments_target": "8000.00",
        "discretionary_allowance": "16000.00",
    }


def _patch_records(mock_prof, mock_plan, mock_closure, mock_analytics, plan=None, closure=None, analytics=None):
    mock_prof.return_value = {
        "take_home_salary": "80000.00",
        "essential_expenses": "32000.00",
        "debt_obligations": "8000.00",
    }
    mock_plan.return_value = plan or _full_plan()
    mock_closure.return_value = closure or {
        "month": "2026-10",
        "recorded_income": "80000.00",
        "recorded_expense": "50000.00",
        "recorded_surplus": "30000.00",
        "confirmed_surplus": None,
        "is_closed": False,
        "allocation": None,
    }
    mock_analytics.return_value = analytics or {
        "income": "80000.00",
        "expense": "50000.00",
        "balance": "30000.00",
        "savings_rate": "37.50",
        "pie": [
            {"category": "Rent", "total": "22000.00"},
            {"category": "Groceries", "total": "8500.00"},
        ],
        "unusual_spending": [{"category": "Travel", "amount": "14000.00", "date": "2026-10-12"}],
        "recurring_expenses": [{"category": "Rent", "occurrences": 3, "total": "66000.00"}],
    }


@patch("ai_assistant.requests.post")
@patch("services.get_analytics")
@patch("services.get_closure")
@patch("services.generate_plan")
@patch("services.get_profile")
def test_ai_timeout_returns_grounded_plan_not_the_15s_error(
    mock_prof, mock_plan, mock_closure, mock_analytics, mock_post
):
    Config.GEMINI_API_KEY = "test_valid_key_123"
    _patch_records(mock_prof, mock_plan, mock_closure, mock_analytics)
    mock_post.side_effect = requests.exceptions.Timeout("timed out")

    res = ai_assistant.ask_assistant(1, "Generate a personalized budget plan based on my salary.")

    assert "error" not in res
    assert "15-second" not in res["answer"]
    assert "timeout" not in res["answer"].lower()
    assert "80,000.00" in res["answer"]
    assert "8,000.00" in res["answer"]
    assert "16,000.00" in res["answer"]
    assert mock_post.call_count == 1


@patch("ai_assistant.requests.post")
@patch("services.get_analytics")
@patch("services.get_closure")
@patch("services.generate_plan")
@patch("services.get_profile")
def test_ai_missing_key_never_calls_gemini(
    mock_prof, mock_plan, mock_closure, mock_analytics, mock_post
):
    Config.GEMINI_API_KEY = ""
    _patch_records(mock_prof, mock_plan, mock_closure, mock_analytics)

    res = ai_assistant.ask_assistant(1, "How should I allocate my monthly surplus?")

    assert "error" not in res
    assert "not closed" in res["answer"].lower()
    assert "8,000.00" in res["answer"]
    mock_post.assert_not_called()


@patch("ai_assistant.requests.post")
@patch("services.get_analytics")
@patch("services.get_closure")
@patch("services.generate_plan")
@patch("services.get_profile")
def test_ai_empty_candidates_and_thought_parts_do_not_crash(
    mock_prof, mock_plan, mock_closure, mock_analytics, mock_post
):
    Config.GEMINI_API_KEY = "test_valid_key_123"
    _patch_records(mock_prof, mock_plan, mock_closure, mock_analytics)

    empty = MagicMock()
    empty.status_code = 200
    empty.json.return_value = {"candidates": []}
    mock_post.return_value = empty
    res_empty = ai_assistant.ask_assistant(1, "Analyze my spending trends and suggest improvements.")
    assert "error" not in res_empty
    assert "37.50%" in res_empty["answer"]
    assert "Rent" in res_empty["answer"]
    assert "22,000.00" in res_empty["answer"]

    thought_only = MagicMock()
    thought_only.status_code = 200
    thought_only.json.return_value = {
        "candidates": [{"content": {"parts": [{"thought": True, "text": "hidden"}, {"text": "  "}]}}]
    }
    mock_post.return_value = thought_only
    res_thought = ai_assistant.ask_assistant(1, "Analyze my spending trends and suggest improvements.")
    assert "error" not in res_thought
    assert "hidden" not in res_thought["answer"]
    assert "Travel" in res_thought["answer"]


@patch("ai_assistant.requests.post")
@patch("services.get_analytics")
@patch("services.get_closure")
@patch("services.generate_plan")
@patch("services.get_profile")
def test_ai_404_advances_to_next_model_then_uses_that_answer(
    mock_prof, mock_plan, mock_closure, mock_analytics, mock_post
):
    Config.GEMINI_API_KEY = "test_valid_key_123"
    _patch_records(mock_prof, mock_plan, mock_closure, mock_analytics)

    missing = MagicMock()
    missing.status_code = 404
    missing.json.return_value = {"error": {"message": "models/gemini-2.5-flash-lite is not found"}}
    ok = MagicMock()
    ok.status_code = 200
    ok.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Discretionary allowance is ₹16,000.00."}]}}]
    }
    mock_post.side_effect = [missing, ok]

    res = ai_assistant.ask_assistant(1, "Generate a personalized budget plan based on my salary.")
    assert res["answer"] == "Discretionary allowance is ₹16,000.00."
    assert mock_post.call_count == 2
    called_models = [call.args[0] for call in mock_post.call_args_list]
    assert "gemini-2.5-flash-lite" in called_models[0]
    assert "gemini-2.0-flash" in called_models[1]


@patch("ai_assistant.requests.post")
@patch("services.get_analytics")
@patch("services.get_closure")
@patch("services.generate_plan")
@patch("services.get_profile")
def test_ai_deficit_plan_does_not_invent_a_surplus(
    mock_prof, mock_plan, mock_closure, mock_analytics, mock_post
):
    Config.GEMINI_API_KEY = "your_gemini_api_key_here"
    _patch_records(
        mock_prof,
        mock_plan,
        mock_closure,
        mock_analytics,
        plan={
            "status": "deficit",
            "take_home": "30000.00",
            "essentials": "25000.00",
            "debts": "10000.00",
            "obligations": "35000.00",
            "shortfall": "5000.00",
            "emergency_target": "0.00",
            "short_term_target": "0.00",
            "investments_target": "0.00",
            "discretionary_allowance": "0.00",
        },
    )

    res = ai_assistant.ask_assistant(1, "Generate a personalized budget plan based on my salary.")
    assert "error" not in res
    assert "5,000.00" in res["answer"]
    assert "Deficit" in res["answer"]
    assert "₹0.00" in res["answer"]
    mock_post.assert_not_called()


@patch("ai_assistant.requests.post")
@patch("services.get_analytics")
@patch("services.get_closure")
@patch("services.generate_plan")
@patch("services.get_profile")
def test_ai_closed_month_allocation_stays_inside_confirmed_surplus(
    mock_prof, mock_plan, mock_closure, mock_analytics, mock_post
):
    Config.GEMINI_API_KEY = ""
    _patch_records(
        mock_prof,
        mock_plan,
        mock_closure,
        mock_analytics,
        closure={
            "recorded_surplus": "30000.00",
            "confirmed_surplus": "15000.00",
            "is_closed": True,
            "allocation": {"emergency": "4000.00", "short_term": "0.00", "investments": "0.00"},
        },
    )

    res = ai_assistant.ask_assistant(1, "How should I allocate my monthly surplus?")
    assert "15,000.00" in res["answer"]
    assert "8,000.00" in res["answer"]
    # 15000 confirmed, targets 8000/8000/8000 → 8000 + 7000 + 0, remainder 0
    assert "7,000.00" in res["answer"]
    assert "4,000.00" in res["answer"]
    mock_post.assert_not_called()


@patch("ai_assistant.requests.post")
@patch("services.get_analytics")
@patch("services.get_closure")
@patch("services.generate_plan")
@patch("services.get_profile")
def test_ai_overloaded_and_bad_json_fall_back_once(
    mock_prof, mock_plan, mock_closure, mock_analytics, mock_post
):
    Config.GEMINI_API_KEY = "test_valid_key_123"
    _patch_records(mock_prof, mock_plan, mock_closure, mock_analytics)

    overloaded = MagicMock()
    overloaded.status_code = 503
    overloaded.json.return_value = {"error": {"message": "unavailable"}}
    mock_post.return_value = overloaded
    res = ai_assistant.ask_assistant(1, "What is my emergency target?")
    assert "error" not in res
    assert "8,000.00" in res["answer"]
    assert mock_post.call_count == 1

    bad = MagicMock()
    bad.status_code = 200
    bad.json.side_effect = ValueError("not json")
    mock_post.return_value = bad
    mock_post.side_effect = None
    res_bad = ai_assistant.ask_assistant(1, "What is my emergency target?")
    assert "error" not in res_bad
    assert "8,000.00" in res_bad["answer"]


def test_ai_empty_message_is_rejected_without_services():
    res = ai_assistant.ask_assistant(1, "   ")
    assert res == {"error": "Message is empty"}


def test_money_formatting_and_grounded_reply_ignore_unknown_numbers():
    text = ai_assistant.grounded_reply(
        "hello",
        {
            "plan": _full_plan(),
            "closure": {"is_closed": False, "recorded_surplus": "30000.00"},
            "analytics": {"income": "1.00", "expense": "0.00", "balance": "1.00", "savings_rate": "100.00", "pie": []},
        },
    )
    assert "80,000.00" in text
    assert "99,999" not in text