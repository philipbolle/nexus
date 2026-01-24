"""
Test finance endpoints.
Tests expense logging, budget status, and debt progress endpoints.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
from fastapi import Depends

from app.main import app
from app.database import Database, get_db
from app.models.schemas import ExpenseCreate, ExpenseResponse


# Create test client with dependency override
def get_test_client(mock_db):
    """Create TestClient with overridden get_db dependency."""

    def override_get_db():
        return mock_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client


class TestFinanceAPI:
    """Test suite for finance API endpoints."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock database connection."""
        db = Mock()
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        db.execute = AsyncMock()
        db.fetch_val = AsyncMock(return_value=None)
        return db

    @pytest.fixture
    def sample_expense_data(self):
        """Sample expense data for testing."""
        return {
            "amount": 25.99,
            "category": "Food",
            "merchant": "Grocery Store",
            "description": "Weekly groceries",
            "transaction_date": "2026-01-23"
        }

    @pytest.fixture
    def sample_expense_response(self):
        """Sample expense response for testing."""
        expense_id = str(uuid.uuid4())
        return {
            "id": expense_id,
            "amount": 25.99,
            "category": "Food",
            "description": "Weekly groceries",
            "merchant": "Grocery Store",
            "transaction_date": "2026-01-23",
            "budget_remaining": 474.01,
            "message": "Logged $25.99 expense in Food"
        }

    @pytest.fixture
    def sample_budget_status(self):
        """Sample budget status response for testing."""
        return {
            "month": "2026-01",
            "total_budget": 1000.0,
            "total_spent": 525.99,
            "remaining": 474.01,
            "percent_used": 52.599,
            "categories": [
                {"category": "Food", "budget": 300.0, "spent": 175.0, "remaining": 125.0},
                {"category": "Transportation", "budget": 200.0, "spent": 150.0, "remaining": 50.0}
            ]
        }

    @pytest.fixture
    def sample_debt_progress(self):
        """Sample debt progress response for testing."""
        return {
            "total_original": 9700.0,
            "total_current": 8500.0,
            "total_paid": 1200.0,
            "percent_paid": 12.37,
            "debts": [
                {"name": "Credit Card", "original": 2500.0, "current": 2000.0, "paid": 500.0},
                {"name": "Student Loan", "original": 7200.0, "current": 6500.0, "paid": 700.0}
            ]
        }

    def test_log_expense_success(self, mock_database, sample_expense_data, sample_expense_response):
        """Test POST /finance/expense success."""
        # Mock database calls
        mock_database.fetch_one.side_effect = [
            {"id": str(uuid.uuid4())},  # Category lookup
            {"budget_remaining": 474.01}  # Budget remaining after insert
        ]
        mock_database.execute.return_value = None

        # Create client with dependency override
        test_client = get_test_client(mock_database)
        try:
            response = test_client.post("/finance/expense", json=sample_expense_data)

            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert float(data["amount"]) == sample_expense_data["amount"]
            assert data["category"] == sample_expense_data["category"]
            assert "budget_remaining" in data
            assert "message" in data
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_log_expense_missing_required_field(self, mock_database):
        """Test POST /finance/expense with missing required field."""
        invalid_expense = {
            "category": "Food"
            # Missing amount
        }

        # Create client with dependency override
        test_client = get_test_client(mock_database)
        try:
            response = test_client.post("/finance/expense", json=invalid_expense)

            # Should return 422 Unprocessable Entity for validation error
            assert response.status_code == 422
            data = response.json()
            # New error format uses 'error' field, not 'detail'
            assert "error" in data
            assert data["error"]["code"] == 422
            assert data["error"]["type"] == "validation_error"
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_log_expense_invalid_amount(self, mock_database):
        """Test POST /finance/expense with invalid amount."""
        invalid_expense = {
            "amount": -10.0,  # Negative amount
            "category": "Food"
        }

        # Create client with dependency override
        test_client = get_test_client(mock_database)
        try:
            response = test_client.post("/finance/expense", json=invalid_expense)

            # Should return 422 Unprocessable Entity for validation error
            assert response.status_code == 422
            data = response.json()
            # New error format uses 'error' field, not 'detail'
            assert "error" in data
            assert data["error"]["code"] == 422
            assert data["error"]["type"] == "validation_error"
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_get_budget_status_success(self, mock_database, sample_budget_status):
        """Test GET /finance/budget-status success."""
        # Mock database calls - router uses fetch_all only
        mock_database.fetch_all.return_value = [
            {"category": "Food", "budget": 300.0, "spent": 175.0},
            {"category": "Transportation", "budget": 200.0, "spent": 150.0}
        ]

        # Create client with dependency override
        test_client = get_test_client(mock_database)
        try:
            response = test_client.get("/finance/budget-status")

            assert response.status_code == 200
            data = response.json()
            assert "month" in data
            assert "total_budget" in data
            assert "total_spent" in data
            assert "remaining" in data
            assert "percent_used" in data
            assert "categories" in data
            assert len(data["categories"]) == 2
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_get_budget_status_with_month_param(self, mock_database):
        """Test GET /finance/budget-status (month parameter ignored)."""
        # Mock database calls - router uses fetch_all only
        mock_database.fetch_all.return_value = []

        # Create client with dependency override
        test_client = get_test_client(mock_database)
        try:
            # Month parameter is not supported by endpoint, will be ignored
            response = test_client.get("/finance/budget-status")

            assert response.status_code == 200
            data = response.json()
            # Month field should exist (current month)
            assert "month" in data
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_get_budget_status_no_data(self, mock_database):
        """Test GET /finance/budget-status when no data exists."""
        # Mock database calls - router uses fetch_all only
        mock_database.fetch_all.return_value = []

        # Create client with dependency override
        test_client = get_test_client(mock_database)
        try:
            response = test_client.get("/finance/budget-status")

            assert response.status_code == 200
            data = response.json()
            # Should return zeros for no data (Decimal fields returned as strings)
            assert float(data["total_budget"]) == 0.0
            assert float(data["total_spent"]) == 0.0
            assert float(data["remaining"]) == 0.0
            assert float(data["percent_used"]) == 0.0
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_get_debt_progress_success(self, mock_database, sample_debt_progress):
        """Test GET /finance/debt/progress success."""
        # Mock database calls - router uses fetch_all only
        mock_database.fetch_all.return_value = [
            {
                "name": "Credit Card",
                "creditor": "Bank",
                "original_amount": 2500.0,
                "current_balance": 2000.0,
                "minimum_payment": 50.0,
                "target_payoff_date": "2026-12-01",
                "total_paid": 500.0
            },
            {
                "name": "Student Loan",
                "creditor": "Federal",
                "original_amount": 7200.0,
                "current_balance": 6500.0,
                "minimum_payment": 100.0,
                "target_payoff_date": "2027-06-01",
                "total_paid": 700.0
            }
        ]

        # Create client with dependency override
        test_client = get_test_client(mock_database)
        try:
            response = test_client.get("/finance/debt/progress")

            assert response.status_code == 200
            data = response.json()
            assert "total_original" in data
            assert "total_current" in data
            assert "total_paid" in data
            assert "percent_paid" in data
            assert "debts" in data
            assert len(data["debts"]) == 2
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_get_debt_progress_with_include_inactive_param(self, mock_database):
        """Test GET /finance/debt/progress (include_inactive parameter ignored)."""
        # Mock database calls - router uses fetch_all only
        mock_database.fetch_all.return_value = []

        # Create client with dependency override
        test_client = get_test_client(mock_database)
        try:
            # include_inactive parameter is not supported by endpoint, will be ignored
            response = test_client.get("/finance/debt/progress")

            assert response.status_code == 200
            data = response.json()
            # Should return empty debts list
            assert data["debts"] == []
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_get_debt_progress_no_debts(self, mock_database):
        """Test GET /finance/debt/progress when no debts exist."""
        # Mock database calls - router uses fetch_all only
        mock_database.fetch_all.return_value = []

        # Create client with dependency override
        test_client = get_test_client(mock_database)
        try:
            response = test_client.get("/finance/debt/progress")

            assert response.status_code == 200
            data = response.json()
            # Should return zeros for no data (Decimal fields returned as strings)
            assert float(data["total_original"]) == 0.0
            assert float(data["total_current"]) == 0.0
            assert float(data["total_paid"]) == 0.0
            assert float(data["percent_paid"]) == 0.0
            assert data["debts"] == []
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()