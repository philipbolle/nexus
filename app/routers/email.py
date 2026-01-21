"""
NEXUS Email API Endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import logging

from ..agents.email_intelligence import scan_emails, get_email_stats
from ..services.email_learner import (
    record_feedback, get_learning_stats,
    get_vip_senders, get_blocked_senders
)
from ..services.insight_engine import (
    generate_insights, get_recent_insights,
    mark_insight_seen, generate_daily_digest
)
from ..services.ai_providers import get_provider_stats
from ..database import db

router = APIRouter(prefix="/email", tags=["email"])
logger = logging.getLogger(__name__)


# Request/Response models
class ScanRequest(BaseModel):
    since_days: int = 1
    limit: int = 50


class FeedbackRequest(BaseModel):
    email_id: str
    feedback: str  # 'important', 'not_important', 'archive', 'delete', 'spam'


class PreferenceUpdate(BaseModel):
    sender: Optional[str] = None
    preference: str  # 'vip', 'block', 'normal'


# Endpoints

@router.post("/scan")
async def trigger_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    Trigger a full email scan.

    Processes emails from all accounts, classifies them,
    extracts data, and takes automatic actions based on learned preferences.
    """
    try:
        # Run scan in background for large scans
        if request.limit > 20:
            background_tasks.add_task(
                scan_emails,
                since_days=request.since_days,
                limit=request.limit
            )
            return {
                "status": "started",
                "message": f"Scanning last {request.since_days} days in background"
            }

        # Run immediately for small scans
        results = await scan_emails(
            since_days=request.since_days,
            limit=request.limit
        )
        return {"status": "completed", "results": results}

    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback on an email classification.

    This helps the system learn your preferences.
    Valid feedback: 'important', 'not_important', 'archive', 'delete', 'spam'
    """
    try:
        # Get email details
        email = await db.fetch_one(
            "SELECT sender, subject, classification FROM processed_emails WHERE id = $1",
            request.email_id
        )

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        await record_feedback(
            email_id=request.email_id,
            feedback=request.feedback,
            sender=email["sender"],
            subject=email["subject"],
            classification=email["classification"]
        )

        return {
            "status": "recorded",
            "message": f"Feedback '{request.feedback}' recorded for sender: {email['sender']}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feedback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_insights(limit: int = 10, unseen_only: bool = True):
    """
    Get cross-life insights from email analysis.

    These are patterns, trends, and actionable information
    discovered from your emails.
    """
    try:
        insights = await get_recent_insights(limit=limit, unseen_only=unseen_only)
        return {"insights": insights}
    except Exception as e:
        logger.error(f"Failed to get insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights/generate")
async def trigger_insight_generation(background_tasks: BackgroundTasks):
    """Generate new insights from recent data."""
    background_tasks.add_task(generate_insights)
    return {"status": "started", "message": "Generating insights in background"}


@router.post("/insights/{insight_id}/seen")
async def mark_seen(insight_id: str):
    """Mark an insight as seen."""
    success = await mark_insight_seen(insight_id)
    if success:
        return {"status": "marked_seen"}
    raise HTTPException(status_code=404, detail="Insight not found")


@router.get("/summary")
async def get_summary():
    """
    Get daily/weekly digest summary.

    Includes:
    - Emails processed today
    - Important emails
    - Transactions found
    - Recent insights
    """
    try:
        digest = await generate_daily_digest()
        return digest
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Get email processing statistics.

    Includes:
    - Classification breakdown
    - AI provider usage
    - Learning statistics
    """
    try:
        email_stats = await get_email_stats()
        provider_stats = await get_provider_stats()
        learning_stats = await get_learning_stats()

        return {
            "email_processing": email_stats,
            "ai_providers": provider_stats,
            "learning": learning_stats
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences")
async def get_preferences():
    """Get current email preferences (VIPs, blocked, etc.)."""
    try:
        vips = await get_vip_senders()
        blocked = await get_blocked_senders()
        learning = await get_learning_stats()

        return {
            "vip_senders": vips,
            "blocked_senders": blocked,
            "learning_stats": learning
        }
    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preferences")
async def update_preference(request: PreferenceUpdate):
    """
    Manually update email preferences.

    Set a sender as VIP, blocked, or normal.
    """
    try:
        if not request.sender:
            raise HTTPException(status_code=400, detail="Sender required")

        pref_map = {
            "vip": "important",
            "block": "delete",
            "normal": "neutral"
        }
        preference = pref_map.get(request.preference)
        if not preference:
            raise HTTPException(status_code=400, detail="Invalid preference")

        # Record as high-confidence preference
        await db.execute(
            """
            INSERT INTO email_preferences (pattern_type, pattern_value, preference, confidence)
            VALUES ('sender', $1, $2, 0.95)
            ON CONFLICT (pattern_type, pattern_value) DO UPDATE SET
                preference = $2,
                confidence = 0.95,
                updated_at = NOW()
            """,
            request.sender.lower(),
            preference
        )

        return {
            "status": "updated",
            "sender": request.sender,
            "preference": request.preference
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def get_recent_emails(limit: int = 20, classification: Optional[str] = None):
    """Get recently processed emails."""
    try:
        query = """
            SELECT id, account, sender, sender_name, subject, classification,
                   importance_score, summary, action_taken, received_at
            FROM processed_emails
            {where_clause}
            ORDER BY received_at DESC
            LIMIT $1
        """.format(
            where_clause=f"WHERE classification = '{classification}'" if classification else ""
        )

        results = await db.fetch_all(query, limit)

        return {
            "emails": [
                {
                    "id": str(r["id"]),
                    "account": r["account"],
                    "sender": r["sender"],
                    "sender_name": r["sender_name"],
                    "subject": r["subject"],
                    "classification": r["classification"],
                    "importance": float(r["importance_score"]) if r["importance_score"] else 0.5,
                    "summary": r["summary"],
                    "action": r["action_taken"],
                    "received_at": r["received_at"].isoformat() if r["received_at"] else None
                }
                for r in results
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get recent emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))
