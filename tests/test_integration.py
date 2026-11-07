import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from app import app
import auth

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_headers():
    token = auth.generate_token(101)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# ==========================================
# WORKFLOW 1: AUTHENTICATION & ISOLATION
# ==========================================

@patch("app.get_db_connection")
def test_workflow_auth_register_and_login(mock_db, client):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    mock_cur.lastrowid = 101

    reg_res = client.post("/api/v1/auth/register", json={"username": "testuser", "password": "secretpassword"})
    assert reg_res.status_code == 201
    data = reg_res.get_json()
    assert "token" in data
    assert data["user_id"] == 101

# ==========================================
# WORKFLOW 2: TRANSACTIONS & INPUT VALIDATION
# ==========================================

@patch("services.sync_monthly_income")
@patch("app.get_db_connection")
def test_workflow_transactions_crud_and_validation(mock_db, mock_sync, client, auth_headers):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur

    # Valid income addition triggers sync_monthly_income
    res_ok = client.post("/api/v1/transactions", headers=auth_headers, json={
        "category": "Salary",
        "amount": "95000",
        "type": "income",
        "date": "2026-10-28"
    })
    assert res_ok.status_code == 201
    mock_sync.assert_called_once_with(101, "2026-10-28")

    # Negative amount rejected with 400
    res_neg = client.post("/api/v1/transactions", headers=auth_headers, json={
        "category": "Food",
        "amount": "-500",
        "type": "expense",
        "date": "2026-10-28"
    })
    assert res_neg.status_code == 400

    # Invalid transaction type rejected with 400
    res_type = client.post("/api/v1/transactions", headers=auth_headers, json={
        "category": "Food",
        "amount": "500",
        "type": "invalid_type",
        "date": "2026-10-28"
    })
    assert res_type.status_code == 400

    # Cross-user IDOR delete attempt rejected with 404
    mock_cur.fetchone.return_value = None
    res_idor = client.delete("/api/v1/transactions/999", headers=auth_headers)
    assert res_idor.status_code == 404

# ==========================================
# WORKFLOW 3 & 4: PLANNER, CLOSURE & ALLOCATION
# ==========================================

@patch("services.update_profile")
def test_workflow_profile_negative_rejected(mock_update, client, auth_headers):
    mock_update.side_effect = ValueError("Essential expenses cannot be negative.")
    res = client.put("/api/v1/profile", headers=auth_headers, json={
        "take_home_salary": "50000",
        "essential_expenses": "-1000",
        "debt_obligations": "0"
    })
    assert res.status_code == 400
    assert "cannot be negative" in res.get_json()["error"]

@patch("services.confirm_closure")
def test_workflow_closure_confirmation(mock_confirm, client, auth_headers):
    mock_confirm.return_value = True
    res = client.post("/api/v1/closure/2026-10/confirm", headers=auth_headers, json={
        "confirmed_surplus": "25000.00"
    })
    assert res.status_code == 200

# ==========================================
# WORKFLOW 5, 6 & 7: AI, PRODUCTS & ANALYTICS
# ==========================================

@patch("ai_assistant.ask_assistant")
def test_workflow_ai_chat_endpoint(mock_ask, client, auth_headers):
    mock_ask.return_value = {"answer": "Here is your budget summary."}
    res = client.post("/api/v1/ai/chat", headers=auth_headers, json={"message": "Summarize my budget"})
    assert res.status_code == 200
    assert res.get_json()["answer"] == "Here is your budget summary."

    # Empty message rejected with 400
    res_empty = client.post("/api/v1/ai/chat", headers=auth_headers, json={"message": "   "})
    assert res_empty.status_code == 400

@patch("services.get_db_connection")
def test_workflow_products_and_analytics(mock_db, client, auth_headers):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur

    # Mock DB responses for get_products
    mock_cur.fetchone.return_value = {"inc": Decimal("50000.00"), "exp": Decimal("20000.00")}
    mock_cur.fetchall.return_value = [{
        "id": 1,
        "category": "fd",
        "name": "SBI 1-Year Fixed Deposit",
        "interest_rate_pct": Decimal("6.80"),
        "risk_level": "Low",
        "liquidity": "Moderate",
        "min_investment": Decimal("1000.00"),
        "lock_in_period": "1 Year",
        "source_url": "https://sbi.co.in",
        "verified_date": datetime.date(2026, 1, 1)
    }]

    res_prod = client.get("/api/v1/products", headers=auth_headers)
    assert res_prod.status_code == 200
    prods = res_prod.get_json()
    assert len(prods) == 1
    assert prods[0]["is_affordable"] is True
    assert prods[0]["estimated_1yr_return"] == "204.00"  # 6.8% on 10% of 30,000 surplus (3,000)