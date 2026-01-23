"""
NEXUS Intelligent Context Service
Retrieves relevant context from all NEXUS data sources for intelligent responses.

Functions as the "brain" of the Jarvis-like assistant, providing:
1. Query understanding and intent analysis
2. Multi-domain data retrieval (finance, email, agents, system, etc.)
3. Context assembly for AI responses
4. Conversation memory and learning
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from dataclasses import dataclass
import hashlib
from datetime import datetime, timedelta

from ..database import db
from .embeddings import get_embedding, cosine_similarity
from .semantic_cache import check_cache, store_cache
from .conversation_memory import get_conversation_memory_service

logger = logging.getLogger(__name__)

# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class QueryIntent:
    """Analyzed intent of a user query."""
    domains: List[str]  # ['finance', 'email', 'system', 'agents', 'memory', 'general']
    entities: List[str]  # Extracted entities like dates, amounts, names
    requires_data: bool  # Whether query needs database lookup
    is_personal: bool   # Whether query is about personal data
    is_operational: bool  # Whether query is about system operations
    time_frame: Optional[str]  # 'today', 'this_month', 'last_week', etc.


@dataclass
class RetrievedContext:
    """Context retrieved from various data sources."""
    finance_data: Optional[List[Dict]] = None
    email_data: Optional[List[Dict]] = None
    agent_data: Optional[List[Dict]] = None
    system_data: Optional[List[Dict]] = None
    database_data: Optional[List[Dict]] = None
    memory_data: Optional[List[Dict]] = None
    conversation_history: Optional[List[Dict]] = None
    usage_data: Optional[List[Dict]] = None
    errors: List[str] = None  # Any errors during retrieval

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def format_for_ai(self) -> str:
        """Format retrieved context for AI prompt."""
        sections = []

        if self.finance_data and len(self.finance_data) > 0:
            sections.append("FINANCE DATA:")
            for item in self.finance_data[:5]:  # Limit to 5 items
                sections.append(f"- {item.get('summary', str(item))}")

        if self.email_data and len(self.email_data) > 0:
            sections.append("EMAIL DATA:")
            for item in self.email_data[:5]:
                sections.append(f"- {item.get('summary', str(item))}")

        if self.agent_data and len(self.agent_data) > 0:
            sections.append("AGENT DATA:")
            for item in self.agent_data[:5]:
                sections.append(f"- {item.get('summary', str(item))}")

        if self.system_data and len(self.system_data) > 0:
            sections.append("SYSTEM DATA:")
            for item in self.system_data[:5]:
                sections.append(f"- {item.get('summary', str(item))}")

        if self.database_data and len(self.database_data) > 0:
            sections.append("DATABASE OVERVIEW:")
            for item in self.database_data[:5]:
                sections.append(f"- {item.get('summary', str(item))}")

        if self.conversation_history and len(self.conversation_history) > 0:
            sections.append("PREVIOUS CONVERSATION:")
            for msg in self.conversation_history[-3:]:  # Last 3 messages
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:100]
                sections.append(f"{role.upper()}: {content}...")

        if self.memory_data and len(self.memory_data) > 0:
            sections.append("RELEVANT PAST CONVERSATIONS:")
            for memory in self.memory_data[:3]:
                role = memory.get('role', 'unknown')
                content = memory.get('content', '')[:100]
                similarity = memory.get('similarity', 0)
                similarity_str = f" ({similarity:.0%} relevant)" if similarity > 0 else ""
                sections.append(f"{role.upper()}: {content}...{similarity_str}")

        if self.usage_data and len(self.usage_data) > 0:
            sections.append("USAGE STATISTICS:")
            for item in self.usage_data[:3]:
                sections.append(f"- {item.get('summary', str(item))}")

        if self.errors:
            sections.append("DATA RETRIEVAL ERRORS:")
            for error in self.errors[:3]:
                sections.append(f"- {error}")

        return "\n\n".join(sections) if sections else "No relevant data found."


# ============================================================================
# Domain-Specific Data Retrieval
# ============================================================================

async def retrieve_finance_data(query: str, intent: QueryIntent) -> List[Dict]:
    """Retrieve relevant finance data based on query intent."""
    try:
        # Check if query mentions specific finance topics
        finance_keywords = ['spent', 'spending', 'expense', 'budget', 'debt', 'money',
                          'cost', 'payment', 'transaction', 'category', 'merchant']

        if not any(keyword in query.lower() for keyword in finance_keywords):
            return []

        results = []

        # Get current month's spending summary
        month_spending = await db.fetch_all(
            """
            SELECT
                c.name as category,
                COALESCE(SUM(t.amount), 0) as spent,
                c.monthly_target as budget
            FROM fin_categories c
            LEFT JOIN fin_transactions t ON t.category_id = c.id
                AND t.transaction_type = 'expense'
                AND DATE_TRUNC('month', t.transaction_date) = DATE_TRUNC('month', CURRENT_DATE)
            WHERE c.is_active = true
            GROUP BY c.id, c.name, c.monthly_target
            ORDER BY spent DESC
            LIMIT 10
            """
        )

        for row in month_spending:
            budget = row.get('budget')
            spent = row.get('spent', 0)
            if spent > 0:  # Include any spending data
                if budget and budget > 0:
                    percent = (spent / budget) * 100
                    summary = f"{row['category']}: ${spent:.2f} spent of ${budget:.2f} budget ({percent:.1f}%)"
                else:
                    summary = f"{row['category']}: ${spent:.2f} spent (no budget set)"
                results.append({
                    'type': 'category_spending',
                    'category': row['category'],
                    'spent': float(spent),
                    'budget': float(budget) if budget else None,
                    'percent_used': float((spent / budget) * 100) if budget and budget > 0 else None,
                    'summary': summary
                })

        # Get recent transactions
        recent_tx = await db.fetch_all(
            """
            SELECT t.amount, t.transaction_date, t.merchant, t.description, c.name as category
            FROM fin_transactions t
            JOIN fin_categories c ON t.category_id = c.id
            WHERE t.transaction_type = 'expense'
            ORDER BY t.transaction_date DESC
            LIMIT 5
            """
        )

        for row in recent_tx:
            results.append({
                'type': 'recent_transaction',
                'date': row['transaction_date'].strftime('%Y-%m-%d'),
                'amount': float(row['amount']),
                'merchant': row['merchant'],
                'category': row['category'],
                'summary': f"${row['amount']:.2f} at {row['merchant']} ({row['category']}) on {row['transaction_date'].strftime('%m/%d')}"
            })

        # Get debt status
        debt_status = await db.fetch_all(
            """
            SELECT name, creditor, current_balance, original_amount
            FROM fin_debts
            WHERE is_active = true
            ORDER BY priority ASC
            LIMIT 5
            """
        )

        for row in debt_status:
            current = row.get('current_balance', 0)
            original = row.get('original_amount', 0)
            if original > 0:
                percent_paid = ((original - current) / original) * 100
                results.append({
                    'type': 'debt',
                    'name': row['name'],
                    'creditor': row['creditor'],
                    'current_balance': float(current),
                    'original_amount': float(original),
                    'percent_paid': float(percent_paid),
                    'summary': f"{row['name']}: ${current:.2f} remaining of ${original:.2f} original ({percent_paid:.1f}% paid)"
                })

        return results

    except Exception as e:
        logger.error(f"Finance data retrieval failed: {e}")
        return []


async def retrieve_email_data(query: str, intent: QueryIntent) -> List[Dict]:
    """Retrieve relevant email data based on query intent."""
    try:
        email_keywords = ['email', 'inbox', 'gmail', 'icloud', 'message', 'sender',
                         'unread', 'important', 'spam', 'promo']

        if not any(keyword in query.lower() for keyword in email_keywords):
            return []

        # Check if email tables exist
        try:
            # Try to get recent email insights
            recent_emails = await db.fetch_all(
                """
                SELECT from_address as sender, subject, category, received_at
                FROM emails
                ORDER BY received_at DESC
                LIMIT 5
                """
            )

            results = []
            for row in recent_emails:
                results.append({
                    'type': 'email',
                    'sender': row.get('sender', 'Unknown'),
                    'subject': row.get('subject', 'No subject'),
                    'category': row.get('category', 'unknown'),
                    'importance': 0,  # No importance_score column in emails table
                    'received': row.get('received_at'),
                    'summary': f"From {row.get('sender', 'Unknown')}: {row.get('subject', 'No subject')} ({row.get('category', 'unknown')})"
                })

            return results

        except Exception as table_error:
            # Email tables might not exist yet
            logger.debug(f"Email tables not accessible: {table_error}")
            return []

    except Exception as e:
        logger.error(f"Email data retrieval failed: {e}")
        return []


async def retrieve_agent_data(query: str, intent: QueryIntent) -> List[Dict]:
    """Retrieve relevant agent data based on query intent."""
    try:
        agent_keywords = ['agent', 'session', 'task', 'tool', 'performance',
                         'memory', 'learning', 'intelligence']

        if not any(keyword in query.lower() for keyword in agent_keywords):
            return []

        results = []

        # Get active agents
        active_agents = await db.fetch_all(
            """
            SELECT name, description, is_active, created_at
            FROM agents
            WHERE is_active = true
            ORDER BY created_at DESC
            LIMIT 5
            """
        )

        for row in active_agents:
            status = 'active' if row.get('is_active') else 'inactive'
            results.append({
                'type': 'agent',
                'name': row['name'],
                'description': row.get('description', ''),
                'status': status,
                'created': row['created_at'],
                'summary': f"Agent {row['name']}: {row.get('description', 'No description')} ({status})"
            })

        # Get recent agent sessions
        recent_sessions = await db.fetch_all(
            """
            SELECT s.id, s.status, s.started_at as created_at
            FROM sessions s
            ORDER BY s.started_at DESC
            LIMIT 5
            """
        )

        for row in recent_sessions:
            results.append({
                'type': 'session',
                'session_id': row['id'],
                'agent_name': 'unknown',  # No agent name in sessions table
                'status': row['status'],
                'created': row['created_at'],
                'summary': f"Session {str(row['id'])[:8]}... ({row['status']})"
            })

        return results

    except Exception as e:
        logger.error(f"Agent data retrieval failed: {e}")
        return []


async def retrieve_system_data(query: str, intent: QueryIntent) -> List[Dict]:
    """Retrieve relevant system data based on query intent."""
    try:
        system_keywords = ['system', 'status', 'health', 'docker', 'container',
                          'cpu', 'memory', 'disk', 'api', 'performance', 'error']

        if not any(keyword in query.lower() for keyword in system_keywords):
            return []

        results = []

        # Get system health status
        try:
            health_status = await db.fetch_all(
                """
                SELECT service_name, status, last_check, details
                FROM system_health
                ORDER BY last_check DESC
                LIMIT 5
                """
            )

            for row in health_status:
                results.append({
                    'type': 'health',
                    'service': row.get('service_name', 'unknown'),
                    'status': row.get('status', 'unknown'),
                    'last_check': row.get('last_check'),
                    'summary': f"{row.get('service_name', 'unknown')}: {row.get('status', 'unknown')}"
                })
        except Exception:
            pass  # Table might not exist

        # Get recent errors
        recent_errors = await db.fetch_all(
            """
            SELECT service, error_type, error_message, timestamp
            FROM error_logs
            WHERE error_type IN ('error', 'critical') OR resolved = false
            ORDER BY timestamp DESC
            LIMIT 5
            """
        )

        for row in recent_errors:
            results.append({
                'type': 'error',
                'service': row['service'],
                'severity': row.get('error_type', 'error'),
                'message': row['error_message'][:100],
                'timestamp': row['timestamp'],
                'summary': f"{row['service']} {row.get('error_type', 'error')}: {row['error_message'][:50]}..."
            })

        # Get API usage stats
        api_usage = await db.fetch_all(
            """
            SELECT provider, COUNT(*) as request_count, AVG(latency_ms) as avg_latency
            FROM api_usage
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY provider
            ORDER BY request_count DESC
            LIMIT 5
            """
        )

        for row in api_usage:
            results.append({
                'type': 'api_usage',
                'provider': row['provider'],
                'requests': row['request_count'],
                'avg_latency': float(row.get('avg_latency', 0)),
                'summary': f"{row['provider']}: {row['request_count']} requests, {row.get('avg_latency', 0):.0f}ms avg"
            })

        return results

    except Exception as e:
        logger.error(f"System data retrieval failed: {e}")
        return []


async def retrieve_database_data(query: str, intent: QueryIntent) -> List[Dict]:
    """Retrieve database overview information."""
    try:
        results = []

        # Get list of all tables
        all_tables = await db.fetch_all("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        total_tables = len(all_tables)

        # Check a few key tables for data existence
        key_tables = ['fin_categories', 'fin_transactions', 'fin_debts', 'agents', 'sessions',
                     'messages', 'api_usage', 'emails', 'system_health', 'error_logs']

        tables_with_data = []
        empty_tables = []

        for table in key_tables:
            try:
                # Try to count rows in the table
                # Using parameterized query is not possible for table names, but we validate against whitelist
                if table not in key_tables:
                    continue

                row_count = await db.fetch_one(f"SELECT COUNT(*) as cnt FROM {table}")
                if row_count and 'cnt' in row_count and row_count['cnt'] > 0:
                    tables_with_data.append(table)
                else:
                    empty_tables.append(table)
            except Exception:
                # Table might not exist or other error
                pass

        results.append({
            'type': 'database_overview',
            'total_tables': total_tables,
            'tables_with_data_sample': len(tables_with_data),
            'empty_tables_sample': len(empty_tables),
            'summary': f"Database: {total_tables} total tables, at least {len(tables_with_data)} tables with data (sampled)"
        })

        # Get some actual data from key tables (limited rows)
        print(f"[DEBUG-DB] Checking sample data. tables_with_data includes: {tables_with_data}")
        if 'fin_transactions' in tables_with_data:
            recent_tx = await db.fetch_all("""
                SELECT amount, merchant, transaction_date
                FROM fin_transactions
                ORDER BY transaction_date DESC
                LIMIT 3
            """)
            for row in recent_tx:
                try:
                    amount = row['amount'] if row['amount'] is not None else 0.0
                    merchant = row['merchant'] if row['merchant'] is not None else 'Unknown'
                    transaction_date = row['transaction_date']
                    date_str = transaction_date.strftime('%Y-%m-%d') if transaction_date else 'Unknown date'
                    results.append({
                        'type': 'sample_data',
                        'table': 'fin_transactions',
                        'data': f"${amount:.2f} at {merchant} on {date_str}",
                        'summary': f"Recent transaction: ${amount:.2f} at {merchant}"
                    })
                except Exception as e:
                    continue

        if 'agents' in tables_with_data:
            active_agents = await db.fetch_all("""
                SELECT name, description, is_active
                FROM agents
                WHERE is_active = true
                LIMIT 3
            """)
            for row in active_agents:
                try:
                    name = row['name'] if row['name'] is not None else 'Unknown'
                    description = row['description'] if row['description'] is not None else 'No description'
                    status = 'active' if row['is_active'] else 'inactive'
                    results.append({
                        'type': 'sample_data',
                        'table': 'agents',
                        'data': f"{name}: {description[:50]}... ({status})",
                        'summary': f"Active agent: {name} ({status})"
                    })
                except Exception as e:
                    continue

        return results
    except Exception as e:
        logger.error(f"Database data retrieval failed: {e}")
        return []


async def retrieve_conversation_history(session_id: Optional[str] = None, limit: int = 5) -> List[Dict]:
    """Retrieve recent conversation history."""
    try:
        if session_id:
            # Get messages for specific session
            messages = await db.fetch_all(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                session_id, limit
            )
        else:
            # Get most recent messages overall
            messages = await db.fetch_all(
                """
                SELECT role, content, created_at
                FROM messages
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit
            )

        # Format in chronological order
        messages.reverse()
        return [dict(msg) for msg in messages]

    except Exception as e:
        logger.error(f"Conversation history retrieval failed: {e}")
        return []


async def retrieve_memory_data(query: str, session_id: Optional[str] = None, limit: int = 5) -> List[Dict]:
    """Retrieve relevant past conversations from memory system."""
    try:
        memory_service = await get_conversation_memory_service()
        memories = await memory_service.retrieve_relevant_memories(
            query=query,
            session_id=session_id,
            limit=limit
        )

        if not memories:
            return []

        # Format memories for consistency with other retrieval functions
        formatted = []
        for memory in memories:
            metadata = memory.metadata or {}
            memory_session_id = metadata.get("session_id", "unknown")
            timestamp = metadata.get("timestamp", "")

            # Parse content which is "User: ...\nNEXUS: ..."
            content = memory.content
            # Extract user message (first line after "User: ")
            user_msg = ""
            ai_msg = ""
            if "\nNEXUS: " in content:
                user_part, ai_part = content.split("\nNEXUS: ", 1)
                user_msg = user_part.replace("User: ", "", 1)
                ai_msg = ai_part
            elif content.startswith("User: "):
                user_msg = content.replace("User: ", "", 1)

            formatted.append({
                "role": "user",
                "content": user_msg,
                "created_at": timestamp,
                "session_id": memory_session_id,
                "memory_id": memory.memory_id,
                "similarity": memory.similarity
            })

            if ai_msg:
                formatted.append({
                    "role": "assistant",
                    "content": ai_msg,
                    "created_at": timestamp,
                    "session_id": memory_session_id,
                    "memory_id": memory.memory_id,
                    "similarity": memory.similarity
                })

        return formatted

    except Exception as e:
        logger.error(f"Memory data retrieval failed: {e}")
        return []


# ============================================================================
# Main Context Retrieval Function
# ============================================================================

async def retrieve_intelligent_context(
    query: str,
    session_id: Optional[str] = None,
    timeout_seconds: float = 2.0
) -> RetrievedContext:
    """
    Retrieve relevant context from all NEXUS data sources.

    This is the core function that makes NEXUS intelligent by providing
    context-aware responses based on all available data.
    """
    start_time = time.time()
    errors = []

    # Simple intent analysis (in production, use AI for this)
    query_lower = query.lower()
    domains = []

    if any(word in query_lower for word in ['spent', 'budget', 'debt', 'money', 'expense', 'finance']):
        domains.append('finance')

    if any(word in query_lower for word in ['email', 'inbox', 'gmail', 'message', 'sender']):
        domains.append('email')

    if any(word in query_lower for word in ['agent', 'session', 'task', 'tool', 'memory']):
        domains.append('agents')

    if any(word in query_lower for word in ['system', 'status', 'health', 'error', 'docker', 'api']):
        domains.append('system')

    if any(word in query_lower for word in ['database', 'table', 'schema', 'what is in', 'what\'s in']):
        domains.append('database')

    # If no specific domain detected, check a few key ones
    if not domains:
        domains = ['finance', 'system', 'agents']  # Default domains to check

    logger.info(f"Query: '{query}' -> Detected domains: {domains}")

    # Create intent object
    intent = QueryIntent(
        domains=domains,
        entities=[],  # Would extract with NLP in production
        requires_data=len(domains) > 0,
        is_personal=any(word in query_lower for word in ['i', 'my', 'me', 'mine']),
        is_operational=any(word in query_lower for word in ['status', 'check', 'how', 'what']),
        time_frame=None
    )

    # Run data retrievals in parallel with timeout
    tasks = []
    finance_data = []
    email_data = []
    agent_data = []
    system_data = []
    database_data = []
    conversation_data = []
    memory_data = []

    try:
        # Run retrievals concurrently
        async with asyncio.timeout(timeout_seconds):
            if 'finance' in domains:
                tasks.append(retrieve_finance_data(query, intent))

            if 'email' in domains:
                tasks.append(retrieve_email_data(query, intent))

            if 'agents' in domains:
                tasks.append(retrieve_agent_data(query, intent))

            if 'system' in domains:
                tasks.append(retrieve_system_data(query, intent))

            if 'database' in domains:
                tasks.append(retrieve_database_data(query, intent))

            # Always retrieve conversation history
            tasks.append(retrieve_conversation_history(session_id))
            # Always retrieve relevant memories
            tasks.append(retrieve_memory_data(query, session_id))

            # Wait for all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            result_idx = 0
            if 'finance' in domains:
                finance_data = results[result_idx] if not isinstance(results[result_idx], Exception) else []
                if isinstance(results[result_idx], Exception):
                    errors.append(f"Finance retrieval: {results[result_idx]}")
                result_idx += 1

            if 'email' in domains:
                email_data = results[result_idx] if not isinstance(results[result_idx], Exception) else []
                if isinstance(results[result_idx], Exception):
                    errors.append(f"Email retrieval: {results[result_idx]}")
                result_idx += 1

            if 'agents' in domains:
                agent_data = results[result_idx] if not isinstance(results[result_idx], Exception) else []
                if isinstance(results[result_idx], Exception):
                    errors.append(f"Agent retrieval: {results[result_idx]}")
                result_idx += 1

            if 'system' in domains:
                system_data = results[result_idx] if not isinstance(results[result_idx], Exception) else []
                if isinstance(results[result_idx], Exception):
                    errors.append(f"System retrieval: {results[result_idx]}")
                result_idx += 1

            if 'database' in domains:
                database_data = results[result_idx] if not isinstance(results[result_idx], Exception) else []
                if isinstance(results[result_idx], Exception):
                    errors.append(f"Database retrieval: {results[result_idx]}")
                result_idx += 1

            # Conversation history is second to last, memory data is last
            # Ensure we have enough results (could be fewer due to timeout)
            if len(results) >= 2:
                conversation_data = results[-2] if not isinstance(results[-2], Exception) else []
                if isinstance(results[-2], Exception):
                    errors.append(f"Conversation retrieval: {results[-2]}")

                memory_data = results[-1] if not isinstance(results[-1], Exception) else []
                if isinstance(results[-1], Exception):
                    errors.append(f"Memory retrieval: {results[-1]}")
            elif len(results) == 1:
                # Only conversation history returned (memory retrieval timed out)
                conversation_data = results[-1] if not isinstance(results[-1], Exception) else []
                if isinstance(results[-1], Exception):
                    errors.append(f"Conversation retrieval: {results[-1]}")
                memory_data = []
            else:
                # No results (shouldn't happen)
                conversation_data = []
                memory_data = []

    except asyncio.TimeoutError:
        errors.append(f"Data retrieval timeout after {timeout_seconds} seconds")
    except Exception as e:
        errors.append(f"Context retrieval error: {e}")

    # Get usage statistics (quick query)
    usage_data = []
    try:
        usage_stats = await db.fetch_one(
            """
            SELECT
                COUNT(*) as total_requests,
                COALESCE(SUM(cost_usd), 0) as total_cost,
                COALESCE(AVG(latency_ms), 0) as avg_latency
            FROM api_usage
            WHERE created_at > NOW() - INTERVAL '24 hours'
            """
        )

        if usage_stats:
            usage_data.append({
                'type': 'usage_stats',
                'requests_24h': usage_stats['total_requests'],
                'cost_24h': float(usage_stats.get('total_cost', 0)),
                'avg_latency': float(usage_stats.get('avg_latency', 0)),
                'summary': f"{usage_stats['total_requests']} AI requests in last 24h, ${usage_stats.get('total_cost', 0):.4f} cost, {usage_stats.get('avg_latency', 0):.0f}ms avg latency"
            })
    except Exception as e:
        logger.debug(f"Usage stats retrieval failed: {e}")

    elapsed = time.time() - start_time
    logger.info(f"Context retrieval completed in {elapsed:.2f}s. Retrieved: "
                f"finance({len(finance_data)}), email({len(email_data)}), "
                f"agents({len(agent_data)}), system({len(system_data)}), "
                f"database({len(database_data)}), memory({len(memory_data)}), conversation({len(conversation_data)})")

    return RetrievedContext(
        finance_data=finance_data,
        email_data=email_data,
        agent_data=agent_data,
        system_data=system_data,
        database_data=database_data,
        memory_data=memory_data,
        conversation_history=conversation_data,
        usage_data=usage_data,
        errors=errors
    )


async def store_conversation(
    session_id: str,
    user_message: str,
    ai_response: str,
    metadata: Optional[Dict] = None
) -> bool:
    """
    Store a conversation exchange for future learning.

    Returns True if successful.
    """
    try:
        # First, ensure session exists
        session = await db.fetch_one(
            "SELECT id FROM sessions WHERE id = $1",
            session_id
        )

        if not session:
            # Create a new session for voice queries
            await db.execute(
                """
                INSERT INTO sessions (id, session_type, status, started_at, last_message_at)
                VALUES ($1, 'voice', 'completed', NOW(), NOW())
                """,
                session_id
            )

        # Store user message
        await db.execute(
            """
            INSERT INTO messages (session_id, role, content, created_at)
            VALUES ($1, 'user', $2, NOW())
            """,
            session_id, user_message
        )

        # Store AI response
        await db.execute(
            """
            INSERT INTO messages (session_id, role, content, created_at)
            VALUES ($1, 'assistant', $2, NOW())
            """,
            session_id, ai_response
        )

        logger.info(f"Stored conversation for session {session_id[:8]}...")
        return True

    except Exception as e:
        logger.error(f"Failed to store conversation: {e}")
        return False