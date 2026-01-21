"""
NEXUS Email Learner
Learn user preferences from feedback to improve email handling.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..database import db

logger = logging.getLogger(__name__)


# Pattern types
PATTERN_SENDER = "sender"
PATTERN_SENDER_DOMAIN = "sender_domain"
PATTERN_SUBJECT_KEYWORD = "subject_keyword"
PATTERN_CATEGORY = "category"

# Preferences
PREF_IMPORTANT = "important"
PREF_ARCHIVE = "archive"
PREF_DELETE = "delete"
PREF_NEUTRAL = "neutral"


async def record_feedback(
    email_id: str,
    feedback: str,
    sender: str = None,
    subject: str = None,
    classification: str = None
) -> None:
    """
    Record user feedback and update preferences.

    Args:
        email_id: The processed email ID
        feedback: 'important', 'not_important', 'archive', 'delete', 'spam'
        sender: Email sender address
        subject: Email subject
        classification: AI classification
    """
    # Map feedback to preference
    pref_map = {
        "important": PREF_IMPORTANT,
        "not_important": PREF_ARCHIVE,
        "archive": PREF_ARCHIVE,
        "delete": PREF_DELETE,
        "spam": PREF_DELETE
    }
    preference = pref_map.get(feedback, PREF_NEUTRAL)

    # Update sender preference
    if sender:
        await update_preference(PATTERN_SENDER, sender.lower(), preference)

        # Also learn domain preference
        if "@" in sender:
            domain = sender.split("@")[1].lower()
            await update_preference(PATTERN_SENDER_DOMAIN, domain, preference, weight=0.5)

    # Learn from subject keywords (simple approach)
    if subject:
        keywords = extract_keywords(subject)
        for keyword in keywords:
            await update_preference(PATTERN_SUBJECT_KEYWORD, keyword, preference, weight=0.3)

    # Update category preference
    if classification:
        await update_preference(PATTERN_CATEGORY, classification, preference, weight=0.2)

    logger.info(f"Recorded feedback: {feedback} for email {email_id[:8]}...")


def extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from text."""
    import re
    # Remove common words and extract keywords
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'your', 'you', 'my', 'i', 'we', 'they', 'he', 'she', 'it', 'this',
        'that', 'these', 'those', 're', 'fwd', 'fw'
    }

    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    keywords = [w for w in words if w not in stop_words]

    # Return unique keywords, max 5
    return list(set(keywords))[:5]


async def update_preference(
    pattern_type: str,
    pattern_value: str,
    preference: str,
    weight: float = 1.0
) -> None:
    """Update or create a preference pattern."""
    # Check if pattern exists
    existing = await db.fetch_one(
        """
        SELECT id, preference, confidence, feedback_count
        FROM email_preferences
        WHERE pattern_type = $1 AND pattern_value = $2
        """,
        pattern_type, pattern_value
    )

    if existing:
        # Update existing - adjust confidence based on agreement
        old_pref = existing["preference"]
        old_conf = float(existing["confidence"])
        count = existing["feedback_count"]

        if old_pref == preference:
            # Same preference - increase confidence
            new_conf = min(0.99, old_conf + (1 - old_conf) * 0.2 * weight)
        else:
            # Different preference - decrease confidence or flip
            new_conf = old_conf - 0.3 * weight
            if new_conf < 0.3:
                # Flip to new preference
                preference = preference
                new_conf = 0.5

        await db.execute(
            """
            UPDATE email_preferences
            SET preference = $1, confidence = $2, feedback_count = $3,
                last_matched_at = NOW(), updated_at = NOW()
            WHERE id = $4
            """,
            preference, new_conf, count + 1, existing["id"]
        )
    else:
        # Create new pattern
        await db.execute(
            """
            INSERT INTO email_preferences (pattern_type, pattern_value, preference, confidence)
            VALUES ($1, $2, $3, $4)
            """,
            pattern_type, pattern_value, preference, 0.5 * weight
        )


async def get_sender_preference(sender: str) -> Optional[Dict[str, Any]]:
    """Get learned preference for a sender."""
    # Check exact sender
    result = await db.fetch_one(
        """
        SELECT preference, confidence
        FROM email_preferences
        WHERE pattern_type = $1 AND pattern_value = $2
        AND confidence >= 0.6
        """,
        PATTERN_SENDER, sender.lower()
    )

    if result:
        return {"preference": result["preference"], "confidence": float(result["confidence"])}

    # Check domain
    if "@" in sender:
        domain = sender.split("@")[1].lower()
        result = await db.fetch_one(
            """
            SELECT preference, confidence
            FROM email_preferences
            WHERE pattern_type = $1 AND pattern_value = $2
            AND confidence >= 0.7
            """,
            PATTERN_SENDER_DOMAIN, domain
        )
        if result:
            return {"preference": result["preference"], "confidence": float(result["confidence"])}

    return None


async def should_auto_action(
    sender: str,
    subject: str = None,
    classification: str = None
) -> Optional[str]:
    """
    Determine if an email should be auto-actioned based on learned preferences.

    Returns: 'archive', 'delete', 'important', or None
    """
    # Check sender preference (highest priority)
    sender_pref = await get_sender_preference(sender)
    if sender_pref and sender_pref["confidence"] >= 0.8:
        return sender_pref["preference"]

    # Check category preference
    if classification:
        cat_result = await db.fetch_one(
            """
            SELECT preference, confidence
            FROM email_preferences
            WHERE pattern_type = $1 AND pattern_value = $2
            AND confidence >= 0.75
            """,
            PATTERN_CATEGORY, classification
        )
        if cat_result:
            return cat_result["preference"]

    return None


async def get_vip_senders() -> List[str]:
    """Get list of VIP senders (marked important with high confidence)."""
    results = await db.fetch_all(
        """
        SELECT pattern_value
        FROM email_preferences
        WHERE pattern_type = $1
        AND preference = $2
        AND confidence >= 0.8
        ORDER BY confidence DESC
        """,
        PATTERN_SENDER, PREF_IMPORTANT
    )
    return [r["pattern_value"] for r in results]


async def get_blocked_senders() -> List[str]:
    """Get list of blocked senders (marked delete with high confidence)."""
    results = await db.fetch_all(
        """
        SELECT pattern_value
        FROM email_preferences
        WHERE pattern_type = $1
        AND preference = $2
        AND confidence >= 0.8
        ORDER BY confidence DESC
        """,
        PATTERN_SENDER, PREF_DELETE
    )
    return [r["pattern_value"] for r in results]


async def get_learning_stats() -> Dict[str, Any]:
    """Get statistics about learned preferences."""
    result = await db.fetch_one(
        """
        SELECT
            COUNT(*) as total_patterns,
            SUM(CASE WHEN preference = 'important' THEN 1 ELSE 0 END) as important_count,
            SUM(CASE WHEN preference = 'archive' THEN 1 ELSE 0 END) as archive_count,
            SUM(CASE WHEN preference = 'delete' THEN 1 ELSE 0 END) as delete_count,
            AVG(confidence) as avg_confidence,
            SUM(feedback_count) as total_feedback
        FROM email_preferences
        """
    )

    return {
        "total_patterns": result["total_patterns"] if result else 0,
        "important_senders": result["important_count"] if result else 0,
        "auto_archive_patterns": result["archive_count"] if result else 0,
        "auto_delete_patterns": result["delete_count"] if result else 0,
        "avg_confidence": float(result["avg_confidence"]) if result and result["avg_confidence"] else 0,
        "total_feedback": result["total_feedback"] if result else 0
    }
