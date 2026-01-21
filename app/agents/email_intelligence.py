"""
NEXUS Email Intelligence Agent
Main orchestrator for intelligent email processing.
"""

import logging
import json
import re
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..database import db
from ..config import settings
from ..services.ai_providers import ai_request
from ..services.email_client import (
    fetch_all_accounts, EmailMessage,
    archive_email, delete_email, mark_as_read
)
from ..services.email_learner import (
    should_auto_action, record_feedback,
    get_vip_senders, PREF_IMPORTANT, PREF_ARCHIVE, PREF_DELETE
)

logger = logging.getLogger(__name__)


# Classification prompts
CLASSIFY_SYSTEM = """You are an email classifier. Classify emails into exactly one category.
Categories:
- spam: Obvious junk, scams, phishing
- promo: Marketing, newsletters, promotions
- social: Social media notifications
- financial: Bank statements, bills, receipts, transactions
- work: Work-related emails
- personal: From friends/family, personal matters
- important: Urgent matters, security alerts, time-sensitive

Respond with ONLY the category name, nothing else."""

EXTRACT_SYSTEM = """You are a data extractor. Extract structured information from emails.
Return JSON with these fields (include only if found):
{
    "transaction": {"amount": "$X.XX", "merchant": "name", "type": "purchase|refund|payment"},
    "dates": [{"date": "YYYY-MM-DD", "context": "what it's for"}],
    "action_items": ["task 1", "task 2"],
    "people": [{"name": "Name", "email": "email@example.com"}],
    "companies": ["Company 1"],
    "subscription": {"name": "service", "amount": "$X.XX", "frequency": "monthly"}
}
Only include fields where data was actually found. Return valid JSON only."""

SUMMARIZE_SYSTEM = """Summarize this email in 1-2 sentences. Focus on:
- Who it's from
- What they want/need
- Any action required
Keep it brief and actionable."""


async def process_email(email: EmailMessage) -> Dict[str, Any]:
    """
    Process a single email through the intelligence pipeline.

    Returns processing result with classification, summary, extracted data, and action taken.
    """
    result = {
        "message_id": email.message_id,
        "account": email.account,
        "sender": email.sender,
        "subject": email.subject,
        "classification": None,
        "importance_score": 0.5,
        "summary": None,
        "extracted_data": {},
        "action_taken": None,
        "ai_provider": None
    }

    try:
        # Check if already processed
        existing = await db.fetch_one(
            "SELECT id FROM processed_emails WHERE message_id = $1",
            email.message_id
        )
        if existing:
            logger.debug(f"Email already processed: {email.message_id[:20]}...")
            return {"skipped": True, "reason": "already_processed"}

        # Check VIP senders first
        vip_senders = await get_vip_senders()
        is_vip = email.sender.lower() in [s.lower() for s in vip_senders]

        # Check for learned auto-action
        auto_action = await should_auto_action(email.sender, email.subject)

        # 1. Quick classification (Groq - fast)
        classify_prompt = f"Subject: {email.subject}\nFrom: {email.sender_name} <{email.sender}>\nPreview: {email.body_preview[:300]}"

        classify_result = await ai_request(
            prompt=classify_prompt,
            task_type="classification",
            system=CLASSIFY_SYSTEM
        )
        classification = classify_result["content"].strip().lower()
        result["classification"] = classification
        result["ai_provider"] = classify_result["provider"]

        # 2. Determine importance score
        importance = calculate_importance(classification, is_vip, email)
        result["importance_score"] = importance

        # 3. Handle based on classification and learned preferences
        if auto_action == PREF_DELETE or classification == "spam":
            # Auto-delete spam or learned delete
            await delete_email(email.account, email.message_id)
            result["action_taken"] = "deleted"
            logger.info(f"Auto-deleted: {email.subject[:50]}")

        elif auto_action == PREF_ARCHIVE or classification == "promo":
            # Auto-archive promos or learned archive
            await archive_email(email.account, email.message_id)
            result["action_taken"] = "archived"
            logger.info(f"Auto-archived: {email.subject[:50]}")

        else:
            # Process further for important/financial/personal emails

            # 4. Extract entities (Groq - fast)
            if classification in ["financial", "important", "work", "personal"]:
                extract_prompt = f"Email:\nSubject: {email.subject}\nFrom: {email.sender}\nBody:\n{email.body[:2000]}"

                extract_result = await ai_request(
                    prompt=extract_prompt,
                    task_type="extraction",
                    system=EXTRACT_SYSTEM
                )

                try:
                    # Parse JSON from response
                    json_match = re.search(r'\{.*\}', extract_result["content"], re.DOTALL)
                    if json_match:
                        extracted = json.loads(json_match.group())
                        result["extracted_data"] = extracted

                        # Store extracted entities
                        await store_extracted_entities(email.message_id, extracted)
                except:
                    logger.warning(f"Failed to parse extraction for {email.message_id[:20]}")

            # 5. Summarize important emails (Gemini - better quality)
            if importance >= 0.7 or classification in ["important", "financial"]:
                summary_prompt = f"Subject: {email.subject}\nFrom: {email.sender_name}\nBody:\n{email.body[:1500]}"

                summary_result = await ai_request(
                    prompt=summary_prompt,
                    task_type="summarization",
                    system=SUMMARIZE_SYSTEM
                )
                result["summary"] = summary_result["content"].strip()

            # 6. Send alert for high-priority emails
            if importance >= 0.8 or classification == "important":
                await send_alert(email, result)
                result["action_taken"] = "alerted"

            elif classification == "financial" and result.get("extracted_data", {}).get("transaction"):
                # Log financial transaction
                await log_transaction(email, result["extracted_data"]["transaction"])
                result["action_taken"] = "transaction_logged"

        # Store processed email
        await store_processed_email(email, result)

        return result

    except Exception as e:
        logger.error(f"Failed to process email {email.message_id[:20]}: {e}")
        return {"error": str(e), "message_id": email.message_id}


def calculate_importance(classification: str, is_vip: bool, email: EmailMessage) -> float:
    """Calculate importance score 0-1."""
    score = 0.5

    # Classification-based
    class_scores = {
        "important": 0.9,
        "financial": 0.75,
        "personal": 0.7,
        "work": 0.65,
        "social": 0.4,
        "promo": 0.2,
        "spam": 0.0
    }
    score = class_scores.get(classification, 0.5)

    # VIP boost
    if is_vip:
        score = min(1.0, score + 0.2)

    # Urgency keywords
    urgent_words = ["urgent", "immediately", "asap", "action required", "deadline", "expires"]
    subject_lower = email.subject.lower()
    if any(word in subject_lower for word in urgent_words):
        score = min(1.0, score + 0.15)

    return round(score, 2)


async def store_extracted_entities(email_id: str, extracted: Dict[str, Any]) -> None:
    """Store extracted entities in database."""
    # Transaction
    if "transaction" in extracted:
        tx = extracted["transaction"]
        await db.execute(
            """
            INSERT INTO extracted_entities (source_type, source_id, entity_type, entity_value, context)
            VALUES ('email', $1, 'transaction', $2, $3)
            """,
            email_id, tx.get("amount", ""), f"{tx.get('merchant', '')} - {tx.get('type', '')}"
        )

    # Dates
    for date_info in extracted.get("dates", []):
        await db.execute(
            """
            INSERT INTO extracted_entities (source_type, source_id, entity_type, entity_value, context)
            VALUES ('email', $1, 'date', $2, $3)
            """,
            email_id, date_info.get("date", ""), date_info.get("context", "")
        )

    # People
    for person in extracted.get("people", []):
        await db.execute(
            """
            INSERT INTO extracted_entities (source_type, source_id, entity_type, entity_value, context)
            VALUES ('email', $1, 'person', $2, $3)
            """,
            email_id, person.get("name", ""), person.get("email", "")
        )

    # Subscription
    if "subscription" in extracted:
        sub = extracted["subscription"]
        await db.execute(
            """
            INSERT INTO extracted_entities (source_type, source_id, entity_type, entity_value, context)
            VALUES ('email', $1, 'subscription', $2, $3)
            """,
            email_id, sub.get("amount", ""), f"{sub.get('name', '')} - {sub.get('frequency', '')}"
        )


async def store_processed_email(email: EmailMessage, result: Dict[str, Any]) -> None:
    """Store processed email in database."""
    await db.execute(
        """
        INSERT INTO processed_emails
        (message_id, account, sender, sender_name, recipient, subject, body_preview,
         received_at, classification, importance_score, summary, extracted_data,
         action_taken, ai_provider_used)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        ON CONFLICT (message_id) DO NOTHING
        """,
        email.message_id,
        email.account,
        email.sender,
        email.sender_name,
        email.recipient,
        email.subject,
        email.body_preview,
        email.received_at,
        result.get("classification"),
        result.get("importance_score", 0.5),
        result.get("summary"),
        json.dumps(result.get("extracted_data", {})),
        result.get("action_taken"),
        result.get("ai_provider")
    )


async def log_transaction(email: EmailMessage, transaction: Dict[str, Any]) -> None:
    """Log a financial transaction from email."""
    try:
        amount_str = transaction.get("amount", "0")
        # Parse amount
        amount = float(re.sub(r'[^\d.]', '', amount_str))
        merchant = transaction.get("merchant", "Unknown")
        tx_type = transaction.get("type", "purchase")

        # Get or create category
        category = await db.fetch_one(
            "SELECT id FROM fin_categories WHERE name = 'Uncategorized' LIMIT 1"
        )

        if category:
            await db.execute(
                """
                INSERT INTO fin_transactions
                (transaction_date, amount, transaction_type, category_id, merchant, description)
                VALUES (CURRENT_DATE, $1, 'expense', $2, $3, $4)
                """,
                amount,
                category["id"],
                merchant,
                f"Auto-extracted from email: {email.subject[:100]}"
            )
            logger.info(f"Logged transaction: ${amount} at {merchant}")

    except Exception as e:
        logger.error(f"Failed to log transaction: {e}")


async def send_alert(email: EmailMessage, result: Dict[str, Any]) -> None:
    """Send notification for important email."""
    if not settings.ntfy_topic:
        logger.warning("NTFY_TOPIC not configured, skipping alert")
        return

    try:
        classification = result.get("classification", "")

        # Determine priority
        if classification == "important" or "fraud" in email.subject.lower():
            priority = 5
        elif classification == "financial":
            priority = 4
        else:
            priority = 3

        title = f"📧 {email.sender_name}"
        message = f"{email.subject}\n\n{result.get('summary', email.body_preview[:200])}"

        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://ntfy.sh/{settings.ntfy_topic}",
                headers={
                    "Title": title,
                    "Priority": str(priority),
                    "Tags": f"email,{classification}"
                },
                content=message[:500]
            )

        logger.info(f"Sent alert for: {email.subject[:50]}")

    except Exception as e:
        logger.error(f"Failed to send alert: {e}")


async def scan_emails(since_days: int = 1, limit: int = 50) -> Dict[str, Any]:
    """
    Scan and process emails from all accounts.

    Returns summary of processing.
    """
    logger.info(f"Starting email scan (last {since_days} days, limit {limit})")

    # Fetch emails
    emails = await fetch_all_accounts(since_days=since_days, limit_per_account=limit // 2)

    if not emails:
        return {"status": "no_emails", "processed": 0}

    results = {
        "total_fetched": len(emails),
        "processed": 0,
        "skipped": 0,
        "errors": 0,
        "by_classification": {},
        "by_action": {},
        "transactions_found": 0
    }

    for email in emails:
        try:
            result = await process_email(email)

            if result.get("skipped"):
                results["skipped"] += 1
            elif result.get("error"):
                results["errors"] += 1
            else:
                results["processed"] += 1

                # Track classifications
                classification = result.get("classification", "unknown")
                results["by_classification"][classification] = results["by_classification"].get(classification, 0) + 1

                # Track actions
                action = result.get("action_taken", "none")
                results["by_action"][action] = results["by_action"].get(action, 0) + 1

                # Count transactions
                if result.get("extracted_data", {}).get("transaction"):
                    results["transactions_found"] += 1

        except Exception as e:
            logger.error(f"Error processing email: {e}")
            results["errors"] += 1

    logger.info(f"Email scan complete: {results['processed']} processed, {results['skipped']} skipped")

    return results


async def get_email_stats() -> Dict[str, Any]:
    """Get email processing statistics."""
    # Today's stats
    today = await db.fetch_one(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN classification = 'spam' THEN 1 ELSE 0 END) as spam,
            SUM(CASE WHEN classification = 'promo' THEN 1 ELSE 0 END) as promo,
            SUM(CASE WHEN classification = 'financial' THEN 1 ELSE 0 END) as financial,
            SUM(CASE WHEN classification = 'important' THEN 1 ELSE 0 END) as important,
            SUM(CASE WHEN classification = 'personal' THEN 1 ELSE 0 END) as personal,
            SUM(CASE WHEN action_taken = 'archived' THEN 1 ELSE 0 END) as archived,
            SUM(CASE WHEN action_taken = 'deleted' THEN 1 ELSE 0 END) as deleted
        FROM processed_emails
        WHERE created_at > CURRENT_DATE
        """
    )

    # All time stats
    all_time = await db.fetch_one(
        """
        SELECT COUNT(*) as total
        FROM processed_emails
        """
    )

    return {
        "today": dict(today) if today else {},
        "all_time_total": all_time["total"] if all_time else 0
    }
