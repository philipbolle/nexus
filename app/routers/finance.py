"""
NEXUS Finance Endpoints
Expense tracking, budget status, debt progress.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import uuid4
import logging

from ..database import db, get_db, Database
from ..models.schemas import (
    ExpenseCreate, ExpenseResponse,
    BudgetStatus, DebtProgress, DebtSummary
)

router = APIRouter(prefix="/finance", tags=["finance"])
logger = logging.getLogger(__name__)


async def get_or_create_category(db: Database, category_name: str) -> str:
    """Get category ID by name, or create if not exists."""
    # Try to find existing category
    result = await db.fetch_one(
        "SELECT id FROM fin_categories WHERE LOWER(name) = LOWER($1)",
        category_name
    )
    if result:
        return str(result["id"])

    # Create new category
    new_id = uuid4()
    await db.execute(
        """
        INSERT INTO fin_categories (id, name, category_type, is_active)
        VALUES ($1, $2, 'expense', true)
        """,
        new_id, category_name
    )
    return str(new_id)


@router.post("/expense", response_model=ExpenseResponse)
async def log_expense(expense: ExpenseCreate, database: Database = Depends(get_db)) -> ExpenseResponse:
    """
    Log an expense transaction.

    Returns the created expense with remaining budget info.
    """
    try:
        # Get or create category
        category_id = await get_or_create_category(database, expense.category)

        # Use today if no date provided
        tx_date = expense.transaction_date or date.today()
        tx_id = uuid4()

        # Insert transaction
        await database.execute(
            """
            INSERT INTO fin_transactions
            (id, transaction_date, amount, transaction_type, category_id,
             merchant, description, is_reviewed)
            VALUES ($1, $2, $3, 'expense', $4, $5, $6, true)
            """,
            tx_id,
            tx_date,
            float(expense.amount),
            category_id,
            expense.merchant,
            expense.description
        )

        # Calculate remaining budget for this category this month
        month_spent = await database.fetch_val(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM fin_transactions
            WHERE category_id = $1
            AND transaction_type = 'expense'
            AND DATE_TRUNC('month', transaction_date) = DATE_TRUNC('month', CURRENT_DATE)
            """,
            category_id
        )

        # Get category budget if exists
        category_budget = await database.fetch_val(
            "SELECT monthly_target FROM fin_categories WHERE id = $1",
            category_id
        )

        budget_remaining = None
        if category_budget:
            budget_remaining = Decimal(str(category_budget)) - Decimal(str(month_spent))

        return ExpenseResponse(
            id=tx_id,
            amount=expense.amount,
            category=expense.category,
            description=expense.description,
            merchant=expense.merchant,
            transaction_date=tx_date,
            budget_remaining=budget_remaining,
            message=f"Logged ${expense.amount} expense in {expense.category}"
        )

    except Exception as e:
        logger.error(f"Failed to log expense: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budget-status", response_model=BudgetStatus)
async def get_budget_status(database: Database = Depends(get_db)) -> BudgetStatus:
    """
    Get current month's budget status by category.
    """
    try:
        # Get spending by category for current month
        spending = await database.fetch_all(
            """
            SELECT
                c.name as category,
                c.monthly_target as budget,
                COALESCE(SUM(t.amount), 0) as spent
            FROM fin_categories c
            LEFT JOIN fin_transactions t ON t.category_id = c.id
                AND t.transaction_type = 'expense'
                AND DATE_TRUNC('month', t.transaction_date) = DATE_TRUNC('month', CURRENT_DATE)
            WHERE c.is_active = true
            GROUP BY c.id, c.name, c.monthly_target
            ORDER BY spent DESC
            """
        )

        # Calculate totals
        total_budget = sum(Decimal(str(row.get("budget") or 0)) for row in spending)
        total_spent = sum(Decimal(str(row.get("spent") or 0)) for row in spending)
        remaining = total_budget - total_spent if total_budget > 0 else Decimal(0)
        percent_used = float(total_spent / total_budget * 100) if total_budget > 0 else 0

        categories = []
        for row in spending:
            budget = Decimal(str(row.get("budget") or 0))
            spent = Decimal(str(row.get("spent") or 0))
            categories.append({
                "name": row["category"],
                "budget": float(budget),
                "spent": float(spent),
                "remaining": float(budget - spent) if budget > 0 else None,
                "percent_used": float(spent / budget * 100) if budget > 0 else None
            })

        return BudgetStatus(
            month=datetime.now().strftime("%B %Y"),
            total_budget=total_budget,
            total_spent=total_spent,
            remaining=remaining,
            percent_used=percent_used,
            categories=categories
        )

    except Exception as e:
        logger.error(f"Failed to get budget status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debt/progress", response_model=DebtSummary)
async def get_debt_progress(database: Database = Depends(get_db)) -> DebtSummary:
    """
    Get debt payoff progress.
    """
    try:
        debts = await database.fetch_all(
            """
            SELECT
                d.id,
                d.name,
                d.creditor,
                d.original_amount,
                d.current_balance,
                d.minimum_payment,
                d.target_payoff_date,
                COALESCE(SUM(p.amount), 0) as total_paid
            FROM fin_debts d
            LEFT JOIN fin_debt_payments p ON p.debt_id = d.id
            WHERE d.is_active = true
            GROUP BY d.id
            ORDER BY d.priority ASC
            """
        )

        debt_list = []
        total_original = Decimal(0)
        total_current = Decimal(0)
        total_paid = Decimal(0)

        for row in debts:
            original = Decimal(str(row["original_amount"]))
            current = Decimal(str(row["current_balance"]))
            paid = original - current

            total_original += original
            total_current += current
            total_paid += paid

            percent_paid = float(paid / original * 100) if original > 0 else 0

            debt_list.append(DebtProgress(
                debt_name=row["name"],
                creditor=row["creditor"],
                original_amount=original,
                current_balance=current,
                paid_amount=paid,
                percent_paid=percent_paid,
                monthly_payment=Decimal(str(row["minimum_payment"])) if row["minimum_payment"] else None,
                projected_payoff_date=row["target_payoff_date"]
            ))

        overall_percent = float(total_paid / total_original * 100) if total_original > 0 else 0

        return DebtSummary(
            total_original=total_original,
            total_current=total_current,
            total_paid=total_paid,
            percent_paid=overall_percent,
            debts=debt_list
        )

    except Exception as e:
        logger.error(f"Failed to get debt progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))
