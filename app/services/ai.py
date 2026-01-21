"""
NEXUS AI Router
Route queries to the cheapest capable AI model.
Includes semantic caching for 60-70% cost reduction.
"""

import httpx
import time
import logging
import hashlib
from typing import Optional
from dataclasses import dataclass

from ..config import settings
from ..database import db
from .semantic_cache import check_cache, store_cache

logger = logging.getLogger(__name__)

# Model pricing per million tokens (input, output)
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
) -> None:
    """Log API usage to database."""
    try:
        await db.execute(
            """
            INSERT INTO api_usage
            (provider, model, input_tokens, output_tokens, cost_usd,
             latency_ms, success, error_message, query_hash)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            provider, model, input_tokens, output_tokens, cost_usd,
            latency_ms, success, error_message, query_hash
        )
    except Exception as e:
        logger.error(f"Failed to log API usage: {e}")


async def query_groq(message: str, model: str = "llama-3.3-70b-versatile") -> AIResponse:
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
                "max_tokens": 1024,
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


async def query_deepseek(message: str, model: str = "deepseek-chat") -> AIResponse:
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
                "max_tokens": 1024,
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


async def chat(message: str, preferred_model: Optional[str] = None) -> AIResponse:
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
            response = await query_groq(message, model)
        except Exception as e:
            logger.warning(f"Groq failed: {e}")
            errors.append(f"groq: {e}")

    # Fall back to DeepSeek
    if response is None and settings.deepseek_api_key:
        try:
            response = await query_deepseek(message)
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
