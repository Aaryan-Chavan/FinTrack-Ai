import datetime
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from db import get_db_connection

MONTH_REGEX = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')

def to_decimal(val):
    """Safely converts a value to a Decimal rounded to 2 decimal places."""
    if val is None or val == '' or isinstance(val, bool):
        return Decimal('0.00')
    try:
        d = Decimal(str(val).strip())
        if d.is_nan() or d.is_infinite():
            return Decimal('0.00')
        return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0.00')

def parse_non_negative_decimal(val, field_name="Amount"):
    """Parses a numeric value and raises ValueError if invalid or negative."""
    if val is None or val == '' or isinstance(val, bool):
        raise ValueError(f"{field_name} is required.")
    try:
        d = Decimal(str(val).strip())
        if d.is_nan() or d.is_infinite():
            raise ValueError(f"{field_name} must be a valid number.")
        quantized = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if quantized < Decimal('0.00'):
            raise ValueError(f"{field_name} cannot be negative.")
        return quantized
    except (InvalidOperation, ValueError, TypeError) as e:
        if "cannot be negative" in str(e) or "is required" in str(e):
            raise
        raise ValueError(f"{field_name} must be a valid number.")

def sync_monthly_income(user_id, date_or_month=None):
    """
    Synchronizes the user's recorded monthly income with UserProfiles.take_home_salary
    so adding/editing/deleting income transactions automatically updates the planner.
    """
    if not date_or_month:
        month_str = datetime.date.today().strftime("%Y-%m")
    else:
        month_str = str(date_or_month)[:7]

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM Transactions
            WHERE user_id=%s AND type='income' AND DATE_FORMAT(date, '%Y-%m') = %s
        """, (user_id, month_str))
        row = cur.fetchone()
        month_income = to_decimal(row[0] if row else 0)

        cur.execute("""
            INSERT INTO UserProfiles (user_id, take_home_salary)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE take_home_salary=%s
        """, (user_id, month_income, month_income))
        conn.commit()
        return month_income
    finally:
        cur.close()
        conn.close()

def get_profile(user_id):
    """Gets or creates the user's financial profile."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM UserProfiles WHERE user_id = %s", (user_id,))
        prof = cur.fetchone()

        if not prof:
            cur.execute("INSERT INTO UserProfiles (user_id) VALUES (%s)", (user_id,))
            conn.commit()
            cur.execute("SELECT * FROM UserProfiles WHERE user_id = %s", (user_id,))
            prof = cur.fetchone()

        # If take_home_salary is 0, check if the user has recorded income this month
        if to_decimal(prof.get('take_home_salary')) == Decimal('0.00'):
            current_month = datetime.date.today().strftime("%Y-%m")
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0) as inc
                FROM Transactions
                WHERE user_id=%s AND type='income' AND DATE_FORMAT(date, '%Y-%m') = %s
            """, (user_id, current_month))
            tx_inc = to_decimal((cur.fetchone() or {}).get('inc'))
            if tx_inc > Decimal('0.00'):
                cur.execute(
                    "UPDATE UserProfiles SET take_home_salary=%s WHERE user_id=%s",
                    (tx_inc, user_id)
                )
                conn.commit()
                prof['take_home_salary'] = tx_inc

        for k, v in list(prof.items()):
            if isinstance(v, Decimal):
                prof[k] = str(to_decimal(v))
            elif isinstance(v, (datetime.datetime, datetime.date)):
                prof[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        return prof
    finally:
        cur.close()
        conn.close()

def update_profile(user_id, take_home, essentials, debts):
    """Validates and updates the user's salary and fixed obligations."""
    th = parse_non_negative_decimal(take_home, "Take-home salary")
    ess = parse_non_negative_decimal(essentials, "Essential expenses")
    dbt = parse_non_negative_decimal(debts, "Debt obligations")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO UserProfiles (user_id, take_home_salary, essential_expenses, debt_obligations)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                take_home_salary=VALUES(take_home_salary),
                essential_expenses=VALUES(essential_expenses),
                debt_obligations=VALUES(debt_obligations)
        """, (user_id, th, ess, dbt))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def generate_plan(user_id):
    """
    Personalized waterfall planner:
    Income -> Debts & Essentials -> Emergency (10%) -> Short-Term Goals (10%) -> Investments (10%) -> Discretionary.
    """
    prof = get_profile(user_id)
    take_home = to_decimal(prof.get('take_home_salary'))
    essentials = to_decimal(prof.get('essential_expenses'))
    debts = to_decimal(prof.get('debt_obligations'))

    obligations = essentials + debts
    remaining = take_home - obligations

    if remaining < Decimal('0.00'):
        return {
            "status": "deficit",
            "take_home": str(take_home),
            "essentials": str(essentials),
            "debts": str(debts),
            "obligations": str(obligations),
            "shortfall": str(abs(remaining)),
            "emergency_target": "0.00",
            "short_term_target": "0.00",
            "investments_target": "0.00",
            "discretionary_allowance": "0.00",
            "message": "Deficit: Your essential expenses and debt obligations exceed your take-home income."
        }

    ten_pct = (take_home * Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    emergency = min(remaining, ten_pct)
    remaining -= emergency

    short_term = min(remaining, ten_pct)
    remaining -= short_term

    investments = min(remaining, ten_pct)
    remaining -= investments

    discretionary = remaining.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        "status": "ok",
        "take_home": str(take_home),
        "essentials": str(essentials),
        "debts": str(debts),
        "obligations": str(obligations),
        "shortfall": "0.00",
        "emergency_target": str(emergency),
        "short_term_target": str(short_term),
        "investments_target": str(investments),
        "discretionary_allowance": str(discretionary)
    }

def get_closure(user_id, month):
    """Calculates recorded surplus vs confirmed bank surplus for a specific YYYY-MM."""
    if not month or not MONTH_REGEX.match(str(month)):
        raise ValueError("Invalid month format. Expected YYYY-MM.")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) as inc,
                   COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) as exp
            FROM Transactions
            WHERE user_id=%s AND DATE_FORMAT(date, '%Y-%m') = %s
        """, (user_id, month))
        tx = cur.fetchone() or {'inc': 0, 'exp': 0}

        rec_inc = to_decimal(tx.get('inc'))
        rec_exp = to_decimal(tx.get('exp'))
        rec_surplus = rec_inc - rec_exp

        cur.execute("SELECT * FROM MonthlyClosures WHERE user_id=%s AND month=%s", (user_id, month))
        closure = cur.fetchone()

        if not closure:
            cur.execute("""
                INSERT INTO MonthlyClosures (user_id, month, recorded_income, recorded_expense, recorded_surplus)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, month, rec_inc, rec_exp, rec_surplus))
            conn.commit()
            cur.execute("SELECT * FROM MonthlyClosures WHERE id=%s", (cur.lastrowid,))
            closure = cur.fetchone()
        elif not closure.get('is_closed'):
            cur.execute("""
                UPDATE MonthlyClosures
                SET recorded_income=%s, recorded_expense=%s, recorded_surplus=%s
                WHERE id=%s
            """, (rec_inc, rec_exp, rec_surplus, closure['id']))
            conn.commit()
            closure['recorded_income'] = rec_inc
            closure['recorded_expense'] = rec_exp
            closure['recorded_surplus'] = rec_surplus

        # Fetch existing allocation if present
        cur.execute("SELECT * FROM SurplusAllocations WHERE closure_id=%s AND user_id=%s", (closure['id'], user_id))
        alloc = cur.fetchone()
        if alloc:
            closure['allocation'] = {
                "emergency": str(to_decimal(alloc.get('emergency_allocation'))),
                "short_term": str(to_decimal(alloc.get('short_term_allocation'))),
                "investments": str(to_decimal(alloc.get('investments_allocation')))
            }
        else:
            closure['allocation'] = None

        for k, v in list(closure.items()):
            if isinstance(v, Decimal):
                closure[k] = str(to_decimal(v))
            elif isinstance(v, (datetime.datetime, datetime.date)):
                closure[k] = v.strftime("%Y-%m-%d %H:%M:%S")

        closure['is_closed'] = bool(closure.get('is_closed'))
        return closure
    finally:
        cur.close()
        conn.close()

def confirm_closure(user_id, month, confirmed_surplus):
    """Locks the month and records the user-confirmed actual bank surplus."""
    if not month or not MONTH_REGEX.match(str(month)):
        raise ValueError("Invalid month format. Expected YYYY-MM.")

    conf_val = parse_non_negative_decimal(confirmed_surplus, "Confirmed surplus")
    # Ensure closure record exists and is synced before locking
    get_closure(user_id, month)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE MonthlyClosures
            SET confirmed_surplus=%s, is_closed=TRUE, closed_at=NOW()
            WHERE user_id=%s AND month=%s AND is_closed=FALSE
        """, (conf_val, user_id, month))
        rows = cur.rowcount
        conn.commit()
        return rows > 0
    finally:
        cur.close()
        conn.close()

def allocate_surplus(user_id, closure_id, emergency, short_term, investments):
    """Saves the user's allocation choices after validating non-negativity and surplus limits."""
    try:
        emg = parse_non_negative_decimal(emergency if emergency != '' and emergency is not None else 0, "Emergency allocation")
        st = parse_non_negative_decimal(short_term if short_term != '' and short_term is not None else 0, "Short-term allocation")
        inv = parse_non_negative_decimal(investments if investments != '' and investments is not None else 0, "Investments allocation")
    except ValueError as e:
        return False, str(e)

    total_alloc = emg + st + inv
    if total_alloc <= Decimal('0.00'):
        return False, "Total allocation must be greater than zero."

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT confirmed_surplus, is_closed FROM MonthlyClosures WHERE id=%s AND user_id=%s",
            (closure_id, user_id)
        )
        closure = cur.fetchone()

        if not closure or not closure.get('is_closed'):
            return False, "Closure not found or month is not closed yet."

        confirmed = to_decimal(closure.get('confirmed_surplus'))
        if total_alloc > confirmed:
            return False, f"Total allocation (₹{total_alloc}) exceeds your confirmed available surplus (₹{confirmed})."

        cur.execute("""
            INSERT INTO SurplusAllocations (closure_id, user_id, emergency_allocation, short_term_allocation, investments_allocation)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                emergency_allocation=VALUES(emergency_allocation),
                short_term_allocation=VALUES(short_term_allocation),
                investments_allocation=VALUES(investments_allocation)
        """, (closure_id, user_id, emg, st, inv))
        conn.commit()
        return True, "Allocated successfully."
    finally:
        cur.close()
        conn.close()

def get_analytics(user_id):
    """Computes comprehensive deterministic financial analytics for the authenticated user."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT COALESCE(SUM(amount), 0) as inc FROM Transactions WHERE type='income' AND user_id=%s", (user_id,))
        inc = to_decimal((cur.fetchone() or {}).get('inc'))

        cur.execute("SELECT COALESCE(SUM(amount), 0) as exp FROM Transactions WHERE type='expense' AND user_id=%s", (user_id,))
        exp = to_decimal((cur.fetchone() or {}).get('exp'))

        balance = inc - exp
        if inc > Decimal('0.00'):
            savings_rate = ((balance / inc) * Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            savings_rate = Decimal('0.00')

        cur.execute("""
            SELECT category, SUM(amount) as total, COUNT(*) as tx_count
            FROM Transactions
            WHERE type='expense' AND user_id=%s
            GROUP BY category
            ORDER BY total DESC
        """, (user_id,))
        pie_rows = cur.fetchall() or []

        pie = []
        recurring_expenses = []
        for r in pie_rows:
            cat_total = to_decimal(r.get('total'))
            pie.append({"category": r['category'], "total": str(cat_total)})
            if int(r.get('tx_count', 0)) >= 2:
                recurring_expenses.append({"category": r['category'], "occurrences": int(r['tx_count']), "total": str(cat_total)})

        cur.execute("""
            SELECT DATE_FORMAT(date, '%Y-%m') as month, SUM(amount) as total
            FROM Transactions
            WHERE user_id=%s AND type='expense'
            GROUP BY month
            ORDER BY month ASC
            LIMIT 6
        """, (user_id,))
        bar_rows = cur.fetchall() or []
        bar = [{"month": b['month'], "total": str(to_decimal(b.get('total')))} for b in bar_rows]

        # Detect unusual spending (single expense > 2x average expense when at least 3 expenses exist)
        cur.execute("""
            SELECT category, amount, date
            FROM Transactions
            WHERE user_id=%s AND type='expense'
            ORDER BY amount DESC
        """, (user_id,))
        all_expenses = cur.fetchall() or []
        unusual_spending = []
        if len(all_expenses) >= 3:
            avg_exp = exp / Decimal(str(len(all_expenses)))
            threshold = (avg_exp * Decimal('2.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            for item in all_expenses:
                amt = to_decimal(item.get('amount'))
                if amt > threshold:
                    dt_val = item.get('date')
                    dt_str = dt_val.strftime("%Y-%m-%d") if isinstance(dt_val, (datetime.date, datetime.datetime)) else str(dt_val)
                    unusual_spending.append({
                        "category": item['category'],
                        "amount": str(amt),
                        "date": dt_str
                    })

        return {
            "income": str(inc),
            "expense": str(exp),
            "balance": str(balance),
            "savings_rate": str(savings_rate),
            "pie": pie,
            "bar": bar,
            "recurring_expenses": recurring_expenses,
            "unusual_spending": unusual_spending
        }
    finally:
        cur.close()
        conn.close()

def get_products(user_id=None):
    """Fetches financial products and personalizes affordability & estimated return based on current surplus."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        surplus = Decimal('0.00')
        if user_id is not None:
            current_month = datetime.date.today().strftime("%Y-%m")
            cur.execute("""
                SELECT COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) as inc,
                       COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) as exp
                FROM Transactions
                WHERE user_id=%s AND DATE_FORMAT(date, '%Y-%m') = %s
            """, (user_id, current_month))
            tx = cur.fetchone() or {'inc': 0, 'exp': 0}
            surplus = to_decimal(tx.get('inc')) - to_decimal(tx.get('exp'))

        cur.execute("SELECT * FROM FinancialProducts ORDER BY id ASC")
        prods = cur.fetchall() or []

        seen_names = set()
        personalized_prods = []
        for p in prods:
            name = p.get('name', '').strip()
            if name in seen_names:
                continue
            seen_names.add(name)

            rate = to_decimal(p.get('interest_rate_pct')) if p.get('interest_rate_pct') is not None else None
            min_inv = to_decimal(p.get('min_investment'))

            p['interest_rate_pct'] = str(rate) if rate is not None else None
            p['min_investment'] = str(min_inv)
            if isinstance(p.get('verified_date'), (datetime.date, datetime.datetime)):
                p['verified_date'] = p['verified_date'].strftime("%Y-%m-%d")

            is_affordable = surplus >= min_inv and surplus > Decimal('0.00')
            p['is_affordable'] = is_affordable
            p['user_surplus'] = str(surplus)

            # Calculate educational 1-year simple return estimate on min_investment (or 10% of surplus if affordable)
            invest_base = max(min_inv, (surplus * Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if is_affordable else min_inv
            if rate is not None:
                est_return = (invest_base * (rate / Decimal('100.00'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                p['estimated_1yr_return'] = str(est_return)
                p['estimate_principal'] = str(invest_base)
            else:
                p['estimated_1yr_return'] = None
                p['estimate_principal'] = str(invest_base)

            personalized_prods.append(p)

        personalized_prods.sort(key=lambda x: (not x['is_affordable'], to_decimal(x['min_investment'])))
        return personalized_prods
    finally:
        cur.close()
        conn.close()