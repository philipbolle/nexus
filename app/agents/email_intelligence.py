"""
NEXUS Email Intelligence Agent
Main orchestrator for intelligent email processing.

Migrated to Multi-Agent Framework with backward compatibility.
"""

import logging
import json
import re
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..database import db
from ..config import settings
from ..services.ai_providers import ai_request, TaskType
from ..services.email_client import (
    fetch_all_accounts, EmailMessage,
    archive_email, delete_email, mark_as_read
)
from ..services.email_learner import (
    should_auto_action, record_feedback,
    get_vip_senders, PREF_IMPORTANT, PREF_ARCHIVE, PREF_DELETE
)
from ..services.insight_engine import (
    generate_insights, get_recent_insights,
    mark_insight_seen, generate_daily_digest
)

# Import agent framework
from .base import BaseAgent, AgentType, AgentStatus
from .tools import ToolSystem, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

# Classification prompts (unchanged)
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


class EmailIntelligenceAgent(BaseAgent):
    """
    Email Intelligence Agent - Migrated to Multi-Agent Framework.

    Capabilities: email_processing, classification, extraction, summarization,
                  transaction_logging, alerting, scanning.
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "Email Intelligence Agent",
        description: str = "Processes emails intelligently using AI for classification, extraction, and automation.",
        system_prompt: str = "",
        capabilities: Optional[List[str]] = None,
        supervisor_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        if capabilities is None:
            capabilities = [
                "email_processing",
                "classification",
                "extraction",
                "summarization",
                "transaction_logging",
                "alerting",
                "scanning"
            ]

        if config is None:
            config = {
                "domain": "email",
                "max_emails_per_scan": 50,
                "default_since_days": 1,
                "importance_threshold_alert": 0.8,
                "importance_threshold_summarize": 0.7
            }

        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.DOMAIN,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities,
            supervisor_id=supervisor_id,
            config=config
        )

    async def _on_initialize(self) -> None:
        """Initialize email-specific resources and register tools."""
        logger.info(f"Initializing Email Intelligence Agent: {self.name}")

        # Register email-specific tools
        await self._register_email_tools()

        # Load any email-specific configuration
        await self._load_email_config()

    async def _on_cleanup(self) -> None:
        """Clean up email agent resources."""
        logger.info(f"Cleaning up Email Intelligence Agent: {self.name}")
        # Nothing specific to clean up

    async def _process_task(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process email-related tasks.

        Supported task types:
        - classify_email: Classify a single email
        - extract_data: Extract structured data from email
        - summarize_email: Summarize email content
        - process_email: Full email processing pipeline
        - scan_emails: Scan and process multiple emails
        - get_stats: Get email statistics
        """
        task_type = task.get("type", "unknown")

        try:
            if task_type == "classify_email":
                return await self._classify_email(task, context)
            elif task_type == "extract_data":
                return await self._extract_data(task, context)
            elif task_type == "summarize_email":
                return await self._summarize_email(task, context)
            elif task_type == "process_email":
                return await self._process_single_email(task, context)
            elif task_type == "scan_emails":
                return await self._scan_emails(task, context)
            elif task_type == "get_stats":
                return await self._get_email_stats(task, context)
            else:
                return {
                    "success": False,
                    "error": f"Unknown task type: {task_type}",
                    "supported_types": [
                        "classify_email", "extract_data", "summarize_email",
                        "process_email", "scan_emails", "get_stats"
                    ]
                }

        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_type": task_type
            }

    async def _register_email_tools(self) -> None:
        """Register email-specific tools."""
        # Tool: classify_email
        await self.register_tool(
            name="classify_email",
            display_name="Classify Email",
            description="Classify an email into categories (spam, promo, social, financial, work, personal, important)",
            input_schema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Email subject"},
                    "sender": {"type": "string", "description": "Sender email address"},
                    "body_preview": {"type": "string", "description": "Email body preview"},
                    "sender_name": {"type": "string", "description": "Sender name"}
                },
                "required": ["subject", "sender"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "classification": {"type": "string"},
                    "importance_score": {"type": "number"},
                    "confidence": {"type": "number"}
                }
            },
            function=self._tool_classify_email
        )

        # Tool: extract_email_data
        await self.register_tool(
            name="extract_email_data",
            display_name="Extract Email Data",
            description="Extract structured data (transactions, dates, people) from email content",
            input_schema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "sender": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["subject", "sender", "body"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "transaction": {"type": "object"},
                    "dates": {"type": "array"},
                    "action_items": {"type": "array"},
                    "people": {"type": "array"},
                    "companies": {"type": "array"},
                    "subscription": {"type": "object"}
                }
            },
            function=self._tool_extract_data
        )

        # Tool: summarize_email
        await self.register_tool(
            name="summarize_email",
            display_name="Summarize Email",
            description="Summarize email content in 1-2 sentences",
            input_schema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "sender_name": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["subject", "body"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "key_points": {"type": "array"}
                }
            },
            function=self._tool_summarize_email
        )

    async def _load_email_config(self) -> None:
        """Load email-specific configuration from database."""
        # Could load from database, but for now use defaults
        pass

    # ============ Task Processing Methods ============

    async def _classify_email(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Classify an email."""
        email_data = task.get("email", {})
        subject = email_data.get("subject", "")
        sender = email_data.get("sender", "")
        body_preview = email_data.get("body_preview", "")
        sender_name = email_data.get("sender_name", "")

        classify_prompt = f"Subject: {subject}\nFrom: {sender_name} <{sender}>\nPreview: {body_preview[:300]}"

        classify_result = await ai_request(
            prompt=classify_prompt,
            task_type="classification",
            system=CLASSIFY_SYSTEM
        )

        classification = classify_result["content"].strip().lower()
        importance = calculate_importance(classification, False, None)  # Simplified

        return {
            "success": True,
            "classification": classification,
            "importance_score": importance,
            "provider": classify_result["provider"],
            "latency_ms": classify_result.get("latency_ms", 0)
        }

    async def _extract_data(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract structured data from email."""
        email_data = task.get("email", {})
        subject = email_data.get("subject", "")
        sender = email_data.get("sender", "")
        body = email_data.get("body", "")

        extract_prompt = f"Email:\nSubject: {subject}\nFrom: {sender}\nBody:\n{body[:2000]}"

        extract_result = await ai_request(
            prompt=extract_prompt,
            task_type="extraction",
            system=EXTRACT_SYSTEM
        )

        extracted = {}
        try:
            json_match = re.search(r'\{.*\}', extract_result["content"], re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group())
        except:
            logger.warning(f"Failed to parse extraction")

        return {
            "success": True,
            "extracted_data": extracted,
            "provider": extract_result["provider"],
            "latency_ms": extract_result.get("latency_ms", 0)
        }

    async def _summarize_email(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Summarize email content."""
        email_data = task.get("email", {})
        subject = email_data.get("subject", "")
        sender_name = email_data.get("sender_name", "")
        body = email_data.get("body", "")

        summary_prompt = f"Subject: {subject}\nFrom: {sender_name}\nBody:\n{body[:1500]}"

        summary_result = await ai_request(
            prompt=summary_prompt,
            task_type="summarization",
            system=SUMMARIZE_SYSTEM
        )

        summary = summary_result["content"].strip()

        return {
            "success": True,
            "summary": summary,
            "provider": summary_result["provider"],
            "latency_ms": summary_result.get("latency_ms", 0)
        }

    async def _process_single_email(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process a single email through full pipeline."""
        # Delegate to original process_email function for compatibility
        email_obj = task.get("email_object")
        if not email_obj:
            return {
                "success": False,
                "error": "email_object required for processing"
            }

        # Import the original function to avoid circular imports
        from .email_intelligence import process_email
        result = await process_email(email_obj)
        return {
            "success": "error" not in result,
            "result": result
        }

    async def _scan_emails(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Scan and process multiple emails."""
        since_days = task.get("since_days", self.config.get("default_since_days", 1))
        limit = task.get("limit", self.config.get("max_emails_per_scan", 50))

        # Delegate to original scan_emails function
        from .email_intelligence import scan_emails
        results = await scan_emails(since_days=since_days, limit=limit)
        return {
            "success": True,
            "results": results
        }

    async def _get_email_stats(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get email processing statistics."""
        from .email_intelligence import get_email_stats
        stats = await get_email_stats()
        return {
            "success": True,
            "stats": stats
        }

    # ============ Tool Implementation Methods ============

    async def _tool_classify_email(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for classify_email."""
        result = await self._classify_email(
            {"email": kwargs},
            None
        )
        return result

    async def _tool_extract_data(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for extract_email_data."""
        result = await self._extract_data(
            {"email": kwargs},
            None
        )
        return result

    async def _tool_summarize_email(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for summarize_email."""
        result = await self._summarize_email(
            {"email": kwargs},
            None
        )
        return result


# ============ Original Functions (Backward Compatibility) ============

# Global agent instance for backward compatibility
_default_email_agent: Optional[EmailIntelligenceAgent] = None


async def get_default_email_agent() -> EmailIntelligenceAgent:
    """Get or create default email agent instance."""
    global _default_email_agent
    if _default_email_agent is None:
        _default_email_agent = EmailIntelligenceAgent()
        await _default_email_agent.initialize()
    return _default_email_agent


async def process_email(email: EmailMessage) -> Dict[str, Any]:
    """
    Process a single email through the intelligence pipeline.

    Returns processing result with classification, summary, extracted data, and action taken.
    """
    # Original implementation (unchanged except for delegation option)
    # For backward compatibility, keep original logic
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


# ============ Helper Functions (Unchanged) ============

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


# ============ Agent Registration Helper ============

async def register_email_agent() -> EmailIntelligenceAgent:
    """
    Register email agent with the agent registry.

    Call this during system startup to register the email agent.
    """
    from .registry import AgentRegistry

    agent = EmailIntelligenceAgent()
    await agent.initialize()

    registry = AgentRegistry()
    await registry.register_agent_instance(agent)

    logger.info(f"Email agent registered: {agent.name}")
    return agent