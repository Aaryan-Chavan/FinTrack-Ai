import datetime
from flask import Flask, render_template, request, jsonify, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from db import get_db_connection
import auth
import services
import ai_assistant

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# ==========================================
# GLOBAL JSON ERROR HANDLERS
# ==========================================

@app.errorhandler(400)
def bad_request_error(e):
    return jsonify({"error": "Bad request"}), 400

@app.errorhandler(401)
def unauthorized_error(e):
    return jsonify({"error": "Unauthorized"}), 401

@app.errorhandler(404)
def not_found_error(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Resource not found"}), 404
    return render_template("index.html"), 404

@app.errorhandler(405)
def method_not_allowed_error(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": "Internal server error"}), 500

@app.route('/')
def home():
    """Serves the main frontend SPA."""
    return render_template("index.html")

# ==========================================
# AUTHENTICATION
# ==========================================

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()
    full_name = str(data.get('full_name', '')).strip() # Extract full_name

    if not username or not password:
        return jsonify({"error": "Username and password cannot be empty"}), 400
    if len(username) > 50:
        return jsonify({"error": "Username cannot exceed 50 characters"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        hashed_pw = generate_password_hash(password)
        # Include full_name in the INSERT statement
        cur.execute(
            "INSERT INTO Users (username, password_hash, full_name) VALUES (%s, %s, %s)", 
            (username, hashed_pw, full_name if full_name else None)
        )
        conn.commit()
        user_id = cur.lastrowid

        token = auth.generate_token(user_id)
        return jsonify({
            "user_id": user_id, 
            "token": token, 
            "username": username,
            "full_name": full_name # Return it so the frontend can store it
        }), 201
    except Exception as e:
        if "Duplicate" in str(e) or "1062" in str(e):
            return jsonify({"error": "User already exists"}), 400
        return jsonify({"error": "Registration failed"}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()

    if not username or not password:
        return jsonify({"error": "Username and password cannot be empty"}), 400

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Fetch full_name alongside id and password details
        cur.execute("SELECT id, password_hash, password, full_name FROM Users WHERE username=%s", (username,))
        user = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if user:
        if user.get('password_hash') and check_password_hash(user['password_hash'], password):
            token = auth.generate_token(user['id'])
            return jsonify({
                "user_id": user['id'], 
                "token": token, 
                "username": username,
                "full_name": user.get('full_name') # Pass full_name to frontend
            })

        elif user.get('password') and user['password'] == password:
            hashed_pw = generate_password_hash(password)
            conn = get_db_connection()
            cur = conn.cursor()
            try:
                cur.execute("UPDATE Users SET password_hash=%s, password=NULL WHERE id=%s", (hashed_pw, user['id']))
                conn.commit()
            finally:
                cur.close()
                conn.close()

            token = auth.generate_token(user['id'])
            return jsonify({
                "user_id": user['id'], 
                "token": token, 
                "username": username,
                "full_name": user.get('full_name')
            })

    return jsonify({"error": "Invalid credentials"}), 401

# ==========================================
# TRANSACTIONS
# ==========================================

@app.route('/api/v1/transactions', methods=['POST'])
@auth.login_required
def add_transaction():
    data = request.get_json(silent=True) or {}
    category = str(data.get('category', '')).strip()
    tx_type = str(data.get('type', '')).strip().lower()
    tx_date = str(data.get('date', '')).strip()

    if not category:
        return jsonify({"error": "Category is required"}), 400
    if tx_type not in ('income', 'expense'):
        return jsonify({"error": "Transaction type must be 'income' or 'expense'"}), 400

    try:
        datetime.datetime.strptime(tx_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400

    try:
        amount = services.parse_non_negative_decimal(data.get('amount'), "Amount")
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO Transactions (user_id, category, amount, type, date)
            VALUES (%s, %s, %s, %s, %s)
        """, (g.user_id, category, amount, tx_type, tx_date))
        conn.commit()
    except Exception:
        return jsonify({"error": "Failed to add transaction"}), 500
    finally:
        cur.close()
        conn.close()

    if tx_type == 'income':
        services.sync_monthly_income(g.user_id, tx_date)

    return jsonify({"message": "Added"}), 201

@app.route('/api/v1/transactions', methods=['GET'])
@auth.login_required
def get_transactions():
    type_filter = request.args.get('type', '').strip().lower()
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        query = "SELECT * FROM Transactions WHERE user_id=%s"
        params = [g.user_id]

        if type_filter in ('income', 'expense'):
            query += " AND type=%s"
            params.append(type_filter)

        query += " ORDER BY date DESC, id DESC"
        cur.execute(query, params)
        rows = cur.fetchall() or []

        for r in rows:
            r['amount'] = str(services.to_decimal(r.get('amount')))
            if isinstance(r.get('date'), (datetime.date, datetime.datetime)):
                r['date'] = r['date'].strftime("%Y-%m-%d")
            if isinstance(r.get('created_at'), (datetime.date, datetime.datetime)):
                r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")

        return jsonify(rows)
    finally:
        cur.close()
        conn.close()

@app.route('/api/v1/transactions/<int:tx_id>', methods=['DELETE', 'PUT'])
@auth.login_required
def modify_transaction(tx_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, type, date FROM Transactions WHERE id=%s AND user_id=%s", (tx_id, g.user_id))
        existing = cur.fetchone()
        if not existing:
            return jsonify({"error": "Transaction not found or unauthorized"}), 404

        if request.method == 'DELETE':
            cur.execute("DELETE FROM Transactions WHERE id=%s AND user_id=%s", (tx_id, g.user_id))
            conn.commit()
            msg = "Deleted"
        else:
            data = request.get_json(silent=True) or {}
            try:
                amount = services.parse_non_negative_decimal(data.get('amount'), "Amount")
                if amount <= 0:
                    return jsonify({"error": "Amount must be greater than 0"}), 400
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

            cur.execute("UPDATE Transactions SET amount=%s WHERE id=%s AND user_id=%s", (amount, tx_id, g.user_id))
            conn.commit()
            msg = "Updated successfully"
    finally:
        cur.close()
        conn.close()

    if existing.get('type') == 'income':
        dt = existing.get('date')
        dt_str = dt.strftime("%Y-%m-%d") if isinstance(dt, (datetime.date, datetime.datetime)) else str(dt)
        services.sync_monthly_income(g.user_id, dt_str)

    return jsonify({"message": msg})

# ==========================================
# PLANNER & PROFILE
# ==========================================

@app.route('/api/v1/profile', methods=['GET', 'PUT'])
@auth.login_required
def handle_profile():
    if request.method == 'GET':
        return jsonify(services.get_profile(g.user_id))

    data = request.get_json(silent=True) or {}
    try:
        services.update_profile(
            g.user_id,
            data.get('take_home_salary', 0),
            data.get('essential_expenses', 0),
            data.get('debt_obligations', 0)
        )
        return jsonify({"message": "Profile updated successfully"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/v1/plan', methods=['GET'])
@auth.login_required
def get_plan():
    return jsonify(services.generate_plan(g.user_id))

# ==========================================
# MONTHLY CLOSURE & ALLOCATION
# ==========================================

@app.route('/api/v1/closure/<month>', methods=['GET'])
@auth.login_required
def get_monthly_closure(month):
    try:
        return jsonify(services.get_closure(g.user_id, month))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/v1/closure/<month>/confirm', methods=['POST'])
@auth.login_required
def confirm_monthly_closure(month):
    data = request.get_json(silent=True) or {}
    confirmed_surplus = data.get('confirmed_surplus')
    if confirmed_surplus is None or confirmed_surplus == '':
        return jsonify({"error": "Confirmed surplus is required"}), 400

    try:
        success = services.confirm_closure(g.user_id, month, confirmed_surplus)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if success:
        return jsonify({"message": "Month closed and surplus confirmed."})
    return jsonify({"error": "Failed to close month. It may already be closed."}), 400

@app.route('/api/v1/closure/<int:closure_id>/allocate', methods=['POST'])
@auth.login_required
def allocate_surplus(closure_id):
    data = request.get_json(silent=True) or {}
    success, msg = services.allocate_surplus(
        g.user_id,
        closure_id,
        data.get('emergency', 0),
        data.get('short_term', 0),
        data.get('investments', 0)
    )
    if success:
        return jsonify({"message": msg})
    return jsonify({"error": msg}), 400

# ==========================================
# DASHBOARD & ANALYTICS
# ==========================================

@app.route('/api/v1/analytics', methods=['GET'])
@auth.login_required
def get_analytics():
    return jsonify(services.get_analytics(g.user_id))

# ==========================================
# AI ASSISTANT
# ==========================================

@app.route('/api/v1/ai/chat', methods=['POST'])
@auth.login_required
def ai_chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get('message', '')).strip()
    if not message:
        return jsonify({"error": "Message is empty"}), 400

    result = ai_assistant.ask_assistant(g.user_id, message)
    if "error" in result:
        return jsonify(result), 503
    return jsonify(result)

# ==========================================
# FINANCIAL PRODUCTS
# ==========================================

@app.route('/api/v1/products', methods=['GET'])
@auth.login_required
def get_products():
    return jsonify(services.get_products(g.user_id))

if __name__ == "__main__":
    app.run(port=5000, debug=True)