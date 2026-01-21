"""
NEXUS Insight Engine
Generate cross-life insights from emails and other data.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from ..database import db
from .ai_providers import ai_request

logger = logging.getLogger(__name__)


async def generate_insights() -> List[Dict[str, Any]]:
    """Generate insights from recent data."""
    insights = []

    # Subscription insights
    sub_insights = await analyze_subscriptions()
    insights.extend(sub_insights)

    # Spending insights
    spend_insights = await analyze_spending()
    insights.extend(spend_insights)

    # Upcoming events
    event_insights = await analyze_upcoming_events()
    insights.extend(event_insights)

    # Bill trends
    bill_insights = await analyze_bill_trends()
    insights.extend(bill_insights)

    # Store new insights
    for insight in insights:
        await store_insight(insight)

    return insights


async def analyze_subscriptions() -> List[Dict[str, Any]]:
    """Analyze subscription patterns from emails."""
    insights = []

    # Find recurring charges from extracted entities
    subscriptions = await db.fetch_all(
        """
        SELECT entity_value, context, COUNT(*) as count
        FROM extracted_entities
        WHERE entity_type = 'subscription'
        AND created_at > NOW() - INTERVAL '30 days'
        GROUP BY entity_value, context
        ORDER BY count DESC
        """
    )

    if subscriptions:
        total = sum(float(s.get("entity_value", 0) or 0) for s in subscriptions if s["entity_value"].replace(".", "").isdigit())
        if total > 0:
            insights.append({
                "type": "subscription_summary",
                "title": f"Monthly Subscriptions: ${total:.2f}",
                "description": f"You have {len(subscriptions)} active subscriptions totaling ${total:.2f}/month",
                "data": {"subscriptions": [dict(s) for s in subscriptions], "total": total},
                "importance": "medium"
            })

    return insights


async def analyze_spending() -> List[Dict[str, Any]]:
    """Analyze spending patterns from transactions."""
    insights = []

    # Get this week's spending by category
    weekly_spend = await db.fetch_all(
        """
        SELECT
            c.name as category,
            SUM(t.amount) as total
        FROM fin_transactions t
        JOIN fin_categories c ON t.category_id = c.id
        WHERE t.transaction_date >= CURRENT_DATE - INTERVAL '7 days'
        AND t.transaction_type = 'expense'
        GROUP BY c.name
        ORDER BY total DESC
        """
    )

    for spend in weekly_spend:
        category = spend["category"]
        total = float(spend["total"])

        # Check against budget
        budget = await db.fetch_one(
            """
            SELECT monthly_target
            FROM fin_categories
            WHERE name = $1
            """,
            category
        )

        if budget and budget["monthly_target"]:
            weekly_budget = float(budget["monthly_target"]) / 4
            if total > weekly_budget:
                over_percent = ((total - weekly_budget) / weekly_budget) * 100
                insights.append({
                    "type": "budget_warning",
                    "title": f"{category}: ${total:.0f} this week",
                    "description": f"You've spent ${total:.2f} on {category} this week, {over_percent:.0f}% over weekly budget",
                    "data": {"category": category, "spent": total, "budget": weekly_budget},
                    "importance": "high" if over_percent > 50 else "medium"
                })

    return insights


async def analyze_upcoming_events() -> List[Dict[str, Any]]:
    """Find upcoming events from extracted entities."""
    insights = []

    # Find dates mentioned in recent emails
    upcoming = await db.fetch_all(
        """
        SELECT entity_value, context, source_id
        FROM extracted_entities
        WHERE entity_type = 'date'
        AND created_at > NOW() - INTERVAL '7 days'
        ORDER BY entity_value
        """
    )

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    for event in upcoming:
        if event["entity_value"] and tomorrow in str(event["entity_value"]):
            insights.append({
                "type": "upcoming_event",
                "title": "Event Tomorrow",
                "description": event["context"][:200] if event["context"] else "You have something scheduled tomorrow",
                "data": {"date": event["entity_value"], "context": event["context"]},
                "importance": "high"
            })

    return insights


async def analyze_bill_trends() -> List[Dict[str, Any]]:
    """Analyze bill trends from financial emails."""
    insights = []

    # Find bills that increased
    bills = await db.fetch_all(
        """
        SELECT
            e1.context as company,
            e1.entity_value as current_amount,
            e2.entity_value as previous_amount
        FROM extracted_entities e1
        JOIN extracted_entities e2 ON e1.context = e2.context
        WHERE e1.entity_type = 'bill_amount'
        AND e2.entity_type = 'bill_amount'
        AND e1.created_at > e2.created_at
        AND e1.created_at > NOW() - INTERVAL '30 days'
        """
    )

    for bill in bills:
        try:
            current = float(bill["current_amount"].replace("$", "").replace(",", ""))
            previous = float(bill["previous_amount"].replace("$", "").replace(",", ""))
            if current > previous * 1.1:  # 10% increase
                increase_pct = ((current - previous) / previous) * 100
                insights.append({
                    "type": "bill_increase",
                    "title": f"{bill['company']} bill increased",
                    "description": f"Your {bill['company']} bill went from ${previous:.2f} to ${current:.2f} ({increase_pct:.0f}% increase)",
                    "data": {"company": bill["company"], "current": current, "previous": previous},
                    "importance": "medium"
                })
        except:
            continue

    return insights


async def store_insight(insight: Dict[str, Any]) -> Optional[str]:
    """Store an insight in the database."""
    try:
        # Check for duplicate
        existing = await db.fetch_one(
            """
            SELECT id FROM insights
            WHERE insight_type = $1 AND title = $2
            AND created_at > NOW() - INTERVAL '24 hours'
            """,
            insight["type"], insight["title"]
        )

        if existing:
            return str(existing["id"])

        result = await db.fetch_one(
            """
            INSERT INTO insights (insight_type, title, description, data, importance)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            insight["type"],
            insight["title"],
            insight["description"],
            json.dumps(insight.get("data", {})),
            insight.get("importance", "low")
        )

        return str(result["id"]) if result else None

    except Exception as e:
        logger.error(f"Failed to store insight: {e}")
        return None


async def get_recent_insights(limit: int = 10, unseen_only: bool = False) -> List[Dict[str, Any]]:
    """Get recent insights."""
    query = """
        SELECT id, insight_type, title, description, data, importance, seen, created_at
        FROM insights
        {where_clause}
        ORDER BY
            CASE importance
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                ELSE 3
            END,
            created_at DESC
        LIMIT $1
    """.format(where_clause="WHERE seen = false" if unseen_only else "")

    results = await db.fetch_all(query, limit)

    return [
        {
            "id": str(r["id"]),
            "type": r["insight_type"],
            "title": r["title"],
            "description": r["description"],
            "data": json.loads(r["data"]) if r["data"] else {},
            "importance": r["importance"],
            "seen": r["seen"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None
        }
        for r in results
    ]


async def mark_insight_seen(insight_id: str) -> bool:
    """Mark an insight as seen."""
    try:
        await db.execute(
            "UPDATE insights SET seen = true WHERE id = $1",
            insight_id
        )
        return True
    except Exception as e:
        logger.error(f"Failed to mark insight seen: {e}")
        return False


async def generate_daily_digest() -> Dict[str, Any]:
    """Generate a daily email digest summary."""

    # Get today's processed emails
    emails_today = await db.fetch_one(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN classification = 'important' THEN 1 ELSE 0 END) as important,
            SUM(CASE WHEN classification = 'financial' THEN 1 ELSE 0 END) as financial,
            SUM(CASE WHEN action_taken = 'archived' THEN 1 ELSE 0 END) as auto_archived
        FROM processed_emails
        WHERE created_at > CURRENT_DATE
        """
    )

    # Get recent insights
    insights = await get_recent_insights(limit=5, unseen_only=True)

    # Get transactions extracted today
    transactions = await db.fetch_all(
        """
        SELECT entity_value, context
        FROM extracted_entities
        WHERE entity_type = 'transaction'
        AND created_at > CURRENT_DATE
        ORDER BY created_at DESC
        LIMIT 5
        """
    )

    return {
        "date": datetime.now().strftime("%B %d, %Y"),
        "emails": {
            "total_processed": emails_today["total"] if emails_today else 0,
            "important": emails_today["important"] if emails_today else 0,
            "financial": emails_today["financial"] if emails_today else 0,
            "auto_archived": emails_today["auto_archived"] if emails_today else 0
        },
        "insights": insights,
        "transactions": [
            {"amount": t["entity_value"], "description": t["context"][:100]}
            for t in transactions
        ]
    }
