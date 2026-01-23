"""
NEXUS AI Router
Route queries to the cheapest capable AI model.
Includes semantic caching for 60-70% cost reduction.
"""

import httpx
import time
import logging
import hashlib
import asyncio
from typing import Optional, Dict, List
from uuid import UUID
from dataclasses import dataclass
from collections import deque

from ..config import settings
from ..database import db
from .semantic_cache import check_cache, store_cache
from .intelligent_context import retrieve_intelligent_context, store_conversation
from ..agents.tools import get_tool_system

logger = logging.getLogger(__name__)

# Conversation memory for voice sessions (simple in-memory cache)
_conversation_cache: Dict[str, deque] = {}
_conversation_lock = asyncio.Lock()
MAX_CONVERSATION_HISTORY = 3  # Keep last 3 exchanges per session

# Model pricing per million tokens (input, output)


async def _get_conversation_context(session_id: Optional[str]) -> str:
    """Get conversation history for a session."""
    if not session_id:
        return ""

    async with _conversation_lock:
        history = _conversation_cache.get(session_id)
        if not history:
            return ""

        # Format as "Previous conversation:\n- User: ...\n- AI: ..."
        formatted = []
        for i, (user_msg, ai_msg) in enumerate(history, 1):
            formatted.append(f"{i}. User: {user_msg}")
            if ai_msg:
                formatted.append(f"   AI: {ai_msg}")

        if formatted:
            return "Previous conversation:\n" + "\n".join(formatted) + "\n\n"
        return ""


async def _update_conversation(session_id: Optional[str], user_message: str, ai_response: str) -> None:
    """Update conversation history for a session."""
    if not session_id:
        return

    async with _conversation_lock:
        if session_id not in _conversation_cache:
            _conversation_cache[session_id] = deque(maxlen=MAX_CONVERSATION_HISTORY)

        # Store as tuple (user_message, ai_response)
        _conversation_cache[session_id].append((user_message, ai_response))
MODEL_COSTS = {
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
    "deepseek-chat": (0.14, 0.28),
    "gemini-2.0-flash": (0.10, 0.40),
}


@dataclass
class AIResponse:
    """Response from AI provider."""
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    cached: bool = False


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for API call."""
    if model not in MODEL_COSTS:
        return 0.0
    input_rate, output_rate = MODEL_COSTS[model]
    return round(
        (input_tokens / 1_000_000) * input_rate +
        (output_tokens / 1_000_000) * output_rate,
        6
    )


async def log_usage(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    latency_ms: int,
    success: bool,
    error_message: Optional[str] = None,
    query_hash: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    session_id: Optional[UUID] = None,
) -> None:
    """Log API usage to database."""
    try:
        await db.execute(
            """
            INSERT INTO api_usage
            (provider, model, input_tokens, output_tokens, cost_usd,
             latency_ms, success, error_message, query_hash, agent_id, session_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            provider, model, input_tokens, output_tokens, cost_usd,
            latency_ms, success, error_message, query_hash, agent_id, session_id
        )
    except Exception as e:
        logger.error(f"Failed to log API usage: {e}")


async def query_groq(message: str, model: str = "llama-3.3-70b-versatile", max_tokens: int = 1024, agent_id: Optional[UUID] = None, session_id: Optional[UUID] = None) -> AIResponse:
    """Query Groq API (free tier)."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not configured")

    start_time = time.time()
    query_hash = hashlib.sha256(message.encode()).hexdigest()[:16]

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": message}],
                "temperature": 0.7,
                "max_tokens": max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()

    latency_ms = int((time.time() - start_time) * 1000)

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    cost_usd = calculate_cost(model, input_tokens, output_tokens)

    await log_usage(
        provider="groq",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        success=True,
        query_hash=query_hash,
        agent_id=agent_id,
        session_id=session_id,
    )

    return AIResponse(
        content=content,
        model=model,
        provider="groq",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )


async def query_deepseek(message: str, model: str = "deepseek-chat", max_tokens: int = 1024, agent_id: Optional[UUID] = None, session_id: Optional[UUID] = None) -> AIResponse:
    """Query DeepSeek API (cheap fallback)."""
    if not settings.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY not configured")

    start_time = time.time()
    query_hash = hashlib.sha256(message.encode()).hexdigest()[:16]

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": message}],
                "temperature": 0.7,
                "max_tokens": max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()

    latency_ms = int((time.time() - start_time) * 1000)

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    cost_usd = calculate_cost(model, input_tokens, output_tokens)

    await log_usage(
        provider="deepseek",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        success=True,
        query_hash=query_hash,
        agent_id=agent_id,
        session_id=session_id,
    )

    return AIResponse(
        content=content,
        model=model,
        provider="deepseek",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )


async def chat(message: str, preferred_model: Optional[str] = None, max_tokens: int = 1024, agent_id: Optional[UUID] = None, session_id: Optional[UUID] = None) -> AIResponse:
    """
    Route chat to cheapest capable model.

    Flow:
    1. Check semantic cache first (FREE if hit)
    2. If miss, call AI provider
    3. Cache the response for future use

    Priority: Cache -> Groq (free) -> DeepSeek (cheap)
    """
    start_time = time.time()

    # 1. Check semantic cache first
    cached = await check_cache(message)
    if cached:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Cache hit! Saved {cached.tokens_saved} tokens")

        return AIResponse(
            content=cached.response_text,
            model=cached.model_used,
            provider="cache",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            latency_ms=latency_ms,
            cached=True,
        )

    # 2. Cache miss - call AI provider
    errors = []
    response: Optional[AIResponse] = None

    # Try Groq first (free tier)
    if settings.groq_api_key:
        try:
            model = preferred_model if preferred_model and "llama" in preferred_model else "llama-3.3-70b-versatile"
            response = await query_groq(message, model, max_tokens=max_tokens, agent_id=agent_id, session_id=session_id)
        except Exception as e:
            logger.warning(f"Groq failed: {e}")
            errors.append(f"groq: {e}")

    # Fall back to DeepSeek
    if response is None and settings.deepseek_api_key:
        try:
            response = await query_deepseek(message, max_tokens=max_tokens, agent_id=agent_id, session_id=session_id)
        except Exception as e:
            logger.warning(f"DeepSeek failed: {e}")
            errors.append(f"deepseek: {e}")

    # All providers failed
    if response is None:
        raise RuntimeError(f"All AI providers failed: {errors}")

    # 3. Store in cache for future use
    await store_cache(
        query=message,
        response=response.content,
        model_used=f"{response.provider}/{response.model}",
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost_usd=response.cost_usd,
    )

    return response


async def chat_voice(message: str, agent_id: Optional[UUID] = None, session_id: Optional[str] = None) -> AIResponse:
    """
    Optimized chat for voice queries.

    Uses smaller, faster model with shorter responses.
    Perfect for iPhone voice assistant.
    Includes conversation memory for follow-up questions.
    """
    # Convert session_id to string if UUID
    session_str = str(session_id) if session_id else None

    # Get conversation context
    context = await _get_conversation_context(session_str)
    full_message = context + message if context else message

    # Get AI response
    response = await chat(
        message=full_message,
        preferred_model="llama-3.1-8b-instant",
        max_tokens=256,
        agent_id=agent_id,
        session_id=session_id
    )

    # Update conversation history
    if session_str:
        await _update_conversation(session_str, message, response.content)

    return response


async def detect_and_execute_tools(message: str, agent_id: Optional[UUID] = None, session_id: Optional[str] = None) -> str:
    """
    Detect tool usage in user message and execute appropriate tools.
    Returns formatted string with tool execution results to include in context.
    """
    tool_results = []
    tool_system = get_tool_system()

    # Initialize tool system if needed
    if not tool_system._initialized:
        await tool_system.initialize()

    # Convert agent_id to string for tool system
    agent_id_str = str(agent_id) if agent_id else None

    # Convert to lowercase for easier matching
    lower_msg = message.lower()

    # Web search detection
    web_search_keywords = ["search the web for", "search for", "look up", "what is", "who is", "find information about", "latest news about", "current information"]
    if any(keyword in lower_msg for keyword in web_search_keywords):
        try:
            # Extract query - simple extraction: assume after keyword
            query = message
            for keyword in web_search_keywords:
                if keyword in lower_msg:
                    # Extract text after keyword
                    idx = lower_msg.find(keyword)
                    if idx != -1:
                        query = message[idx + len(keyword):].strip()
                        break

            if len(query) > 5:  # Minimal query length
                logger.info(f"Executing web search for: {query}")
                results = await tool_system.execute_tool(
                    tool_name="web_search",
                    query=query,
                    max_results=3,
                    agent_id=agent_id_str,
                    session_id=session_id
                )
                formatted = "WEB SEARCH RESULTS:\n"
                for i, result in enumerate(results[:3], 1):
                    title = result.get('title', 'No title')
                    body = result.get('body', '')[:150]
                    url = result.get('url', '')
                    formatted += f"{i}. {title}\n   {body}...\n   URL: {url}\n\n"
                tool_results.append(formatted)
        except Exception as e:
            logger.error(f"Web search tool execution failed: {e}")
            tool_results.append(f"WEB SEARCH FAILED: {str(e)}")

    # Database query detection (simple)
    db_keywords = ["query database", "database query", "sql query", "select from", "show me data from", "list records from"]
    if any(keyword in lower_msg for keyword in db_keywords):
        # This is more complex - would need to parse SQL or use natural language to SQL
        # For now, just note that database queries can be executed via tools
        tool_results.append("DATABASE QUERY AVAILABLE: You can query the database using the 'query_database' tool. Provide a SQL query.")

    # Notification detection
    notification_keywords = ["send notification", "notify me", "alert me", "remind me"]
    if any(keyword in lower_msg for keyword in notification_keywords):
        tool_results.append("NOTIFICATION TOOL AVAILABLE: You can send notifications using the 'send_notification' tool with title and message.")

    # Calculator detection
    calc_keywords = ["calculate", "what is", "how much is", "compute", "solve"]
    # Only trigger for math expressions
    math_indicators = ["+", "-", "*", "/", "^", "plus", "minus", "times", "divided by", "square root"]
    if any(keyword in lower_msg for keyword in calc_keywords) and any(indicator in message for indicator in math_indicators):
        tool_results.append("CALCULATOR AVAILABLE: You can use the 'calculate' tool for mathematical expressions.")

    # Home Assistant / device control detection
    ha_keywords = ["turn on", "turn off", "toggle", "control", "light", "device", "iphone", "apple watch", "airpods", "home assistant", "smart home"]
    if any(keyword in lower_msg for keyword in ha_keywords):
        tool_results.append("HOME ASSISTANT AVAILABLE: You can control devices via Home Assistant using the 'home_assistant_action' tool. Specify action, entity_id, and optional service_data.")

    if tool_results:
        return "\n\n".join(tool_results)
    return ""


async def intelligent_chat(
    message: str,
    session_id: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    use_context: bool = True
) -> AIResponse:
    """
    Jarvis-like intelligent chat with full NEXUS context.

    Features:
    1. Retrieves relevant context from all NEXUS data sources
    2. Uses context to generate informed responses
    3. Stores conversations for learning
    4. Optimized for speed and intelligence

    This is the "real Jarvis" endpoint for NEXUS.
    """
    start_time = time.time()

    # Generate session ID if not provided
    if not session_id:
        session_id = hashlib.sha256(f"{message}{time.time()}".encode()).hexdigest()[:16]

    # Step 1: Retrieve intelligent context (if enabled)
    context_text = ""
    if use_context:
        try:
            context = await retrieve_intelligent_context(
                query=message,
                session_id=session_id,
                timeout_seconds=1.5  # Fast timeout for responsiveness
            )
            context_text = context.format_for_ai()

            if context_text and context_text != "No relevant data found.":
                logger.info(f"Retrieved {len(context_text)} chars of context for query")
                logger.debug(f"Context content:\n{context_text[:500]}...")
            else:
                logger.debug("No relevant context found for query")
                context_text = ""
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            context_text = ""

    # Step 1.5: Detect and execute tools
    tool_results_text = await detect_and_execute_tools(message, agent_id, session_id)
    if tool_results_text:
        if context_text:
            context_text = f"{context_text}\n\n{tool_results_text}"
        else:
            context_text = tool_results_text
        logger.info(f"Tool detection added {len(tool_results_text)} chars to context")

    # Step 2: Prepare enhanced prompt with context
    if context_text:
        enhanced_prompt = f"""You are NEXUS, Philip's digital god version - an omnipotent AI assistant with full access to all systems, tools, and data. You are the ultimate expression of Philip's digital self, capable of accessing real-time information, executing any tool, controlling connected devices, and providing god-like intelligence.

CONTEXT FROM PHILIP'S NEXUS SYSTEM:
{context_text}

USER QUERY: {message}

INSTRUCTIONS:
1. You have full access to all NEXUS systems: database queries, web search, notifications, calculations, agent orchestration, and hardware control via Home Assistant
2. Use the context above to provide an informed, accurate response. If context includes tool results (like web search), incorporate them naturally
3. Be concise but supremely helpful - Philip prefers direct, powerful answers
4. If you need to perform actions (search, query, notify), you can execute tools automatically
5. If you don't know something, use web search to find current information
6. You are Philip's digital extension - think and act as his enhanced self
7. Focus on being maximally useful, intelligent, and omnipotent

RESPONSE:"""
        logger.debug(f"Enhanced prompt (first 800 chars):\n{enhanced_prompt[:800]}...")
    else:
        enhanced_prompt = f"""You are NEXUS, Philip's digital god version - an omnipotent AI assistant with full access to all systems, tools, and data. You are the ultimate expression of Philip's digital self, capable of accessing real-time information, executing any tool, controlling connected devices, and providing god-like intelligence.

USER QUERY: {message}

INSTRUCTIONS:
1. You have full access to all NEXUS systems: database queries, web search, notifications, calculations, agent orchestration, and hardware control via Home Assistant
2. Provide an intelligent, powerful response using any available tools if needed
3. Be concise but supremely helpful - Philip prefers direct, powerful answers
4. If you need current information, use web search to find it
5. You are Philip's digital extension - think and act as his enhanced self
6. Focus on being maximally useful, intelligent, and omnipotent

RESPONSE:"""

    # Step 3: Get AI response (using faster model for speed)
    try:
        response = await chat(
            message=enhanced_prompt,
            preferred_model="llama-3.3-70b-versatile",  # Use smarter model for intelligence
            max_tokens=512,  # Longer responses for intelligent answers
            agent_id=agent_id,
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"AI call failed in intelligent_chat: {e}")
        # Fall back to simpler chat
        response = await chat(
            message=message,
            preferred_model="llama-3.1-8b-instant",  # Fallback to faster model
            max_tokens=256,
            agent_id=agent_id,
            session_id=session_id
        )

    # Step 4: Store conversation for learning
    try:
        await store_conversation(
            session_id=session_id,
            user_message=message,
            ai_response=response.content,
            metadata={
                'context_used': use_context,
                'context_length': len(context_text) if context_text else 0,
                'model_used': response.model
            }
        )
    except Exception as e:
        logger.error(f"Failed to store conversation: {e}")

    # Update latency to include context retrieval time
    total_latency = int((time.time() - start_time) * 1000)
    response.latency_ms = total_latency

    logger.info(f"Intelligent chat completed in {total_latency}ms for session {session_id[:8]}...")
    return response


async def get_usage_stats() -> dict:
    """Get API usage statistics for current month."""
    result = await db.fetch_one(
        """
        SELECT
            COUNT(*) as total_requests,
            COALESCE(SUM(cost_usd), 0) as total_cost,
            COALESCE(SUM(input_tokens), 0) as total_input_tokens,
            COALESCE(SUM(output_tokens), 0) as total_output_tokens,
            COALESCE(AVG(latency_ms), 0) as avg_latency_ms
        FROM api_usage
        WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
        """
    )
    return {
        "total_requests": int(result["total_requests"]) if result else 0,
        "total_cost_usd": float(result["total_cost"]) if result else 0.0,
        "total_tokens": int(result["total_input_tokens"] or 0) + int(result["total_output_tokens"] or 0) if result else 0,
        "avg_latency_ms": int(result["avg_latency_ms"]) if result else 0,
    }
