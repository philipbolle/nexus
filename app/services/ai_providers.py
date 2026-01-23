"""
NEXUS Multi-Provider AI Router
Routes tasks to optimal free AI provider based on task type and usage limits.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import date
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from ..config import settings
from ..database import db
from ..exceptions.manual_tasks import ConfigurationInterventionRequired

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of AI tasks."""
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    ANALYSIS = "analysis"
    PATTERNS = "patterns"
    QUICK = "quick"
    SIMPLE = "simple"


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""
    name: str
    url: str
    model: str
    daily_limit: int
    best_for: List[str]
    api_key_env: str


# Provider configurations
PROVIDERS = {
    "groq": ProviderConfig(
        name="groq",
        url="https://api.groq.com/openai/v1/chat/completions",
        model="llama-3.3-70b-versatile",
        daily_limit=1000,
        best_for=["classification", "extraction", "quick"],
        api_key_env="groq_api_key"
    ),
    "google": ProviderConfig(
        name="google",
        url="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        model="gemini-2.0-flash",
        daily_limit=1500,
        best_for=["analysis", "summarization", "patterns", "large_context"],
        api_key_env="google_ai_api_key"
    ),
    "openrouter": ProviderConfig(
        name="openrouter",
        url="https://openrouter.ai/api/v1/chat/completions",
        model="meta-llama/llama-3.2-3b-instruct:free",
        daily_limit=50,
        best_for=["backup", "simple"],
        api_key_env="openrouter_api_key"
    )
}


async def get_provider_usage(provider: str) -> int:
    """Get today's usage count for a provider."""
    result = await db.fetch_one(
        """
        SELECT request_count FROM ai_provider_usage
        WHERE provider = $1 AND date = CURRENT_DATE
        """,
        provider
    )
    return result["request_count"] if result else 0


async def increment_provider_usage(provider: str, tokens: int = 0, cost: float = 0.0) -> None:
    """Increment usage for a provider."""
    await db.execute(
        """
        INSERT INTO ai_provider_usage (provider, date, request_count, token_count, cost_usd)
        VALUES ($1, CURRENT_DATE, 1, $2, $3)
        ON CONFLICT (provider, date) DO UPDATE SET
            request_count = ai_provider_usage.request_count + 1,
            token_count = ai_provider_usage.token_count + $2,
            cost_usd = ai_provider_usage.cost_usd + $3
        """,
        provider, tokens, cost
    )


def get_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider."""
    config = PROVIDERS.get(provider)
    if not config:
        return None
    return getattr(settings, config.api_key_env, None)


async def select_provider(task_type: str) -> Optional[str]:
    """Select best available provider for a task type."""
    # Find providers that are good for this task
    suitable = []
    for name, config in PROVIDERS.items():
        if task_type in config.best_for:
            suitable.append((name, config))

    # Fall back to all providers if none specifically suitable
    if not suitable:
        suitable = list(PROVIDERS.items())

    # Check usage and availability
    for name, config in suitable:
        api_key = get_api_key(name)
        if not api_key:
            continue

        usage = await get_provider_usage(name)
        if usage < config.daily_limit * 0.9:  # 90% threshold
            return name

    # Try any available provider
    for name, config in PROVIDERS.items():
        api_key = get_api_key(name)
        if api_key:
            usage = await get_provider_usage(name)
            if usage < config.daily_limit:
                return name

    return None


async def call_groq(prompt: str, system: str = "", agent_id: Optional[UUID] = None, session_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Call Groq API."""
    api_key = settings.groq_api_key
    if not api_key:
        raise ConfigurationInterventionRequired(
            title="Configure Groq API Key",
            description="GROQ_API_KEY environment variable not configured. Add Groq API key to .env file for AI processing.",
            source_system="service:ai_providers",
            context={"provider": "groq", "missing_env_var": "GROQ_API_KEY"}
        )

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            PROVIDERS["groq"].url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": PROVIDERS["groq"].model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1024
            }
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("total_tokens", 0)

    await increment_provider_usage("groq", tokens)

    return {"content": content, "tokens": tokens, "provider": "groq"}


async def call_google(prompt: str, system: str = "", agent_id: Optional[UUID] = None, session_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Call Google Gemini API."""
    api_key = settings.google_ai_api_key
    if not api_key:
        raise ConfigurationInterventionRequired(
            title="Configure Google AI API Key",
            description="GOOGLE_AI_API_KEY environment variable not configured. Add Google AI API key to .env file for AI processing.",
            source_system="service:ai_providers",
            context={"provider": "google", "missing_env_var": "GOOGLE_AI_API_KEY"}
        )

    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{PROVIDERS['google'].url}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 1024
                }
            }
        )
        response.raise_for_status()
        data = response.json()

    content = data["candidates"][0]["content"]["parts"][0]["text"]
    tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)

    await increment_provider_usage("google", tokens)

    return {"content": content, "tokens": tokens, "provider": "google"}


async def call_openrouter(prompt: str, system: str = "", agent_id: Optional[UUID] = None, session_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Call OpenRouter API."""
    api_key = settings.openrouter_api_key
    if not api_key:
        raise ConfigurationInterventionRequired(
            title="Configure OpenRouter API Key",
            description="OPENROUTER_API_KEY environment variable not configured. Add OpenRouter API key to .env file for AI processing.",
            source_system="service:ai_providers",
            context={"provider": "openrouter", "missing_env_var": "OPENROUTER_API_KEY"}
        )

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            PROVIDERS["openrouter"].url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": PROVIDERS["openrouter"].model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 512
            }
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("total_tokens", 0)

    await increment_provider_usage("openrouter", tokens)

    return {"content": content, "tokens": tokens, "provider": "openrouter"}


async def ai_request(
    prompt: str,
    task_type: str = "quick",
    system: str = "",
    preferred_provider: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    session_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Make an AI request, automatically selecting the best provider.

    Args:
        prompt: The user prompt
        task_type: Type of task (classification, extraction, etc.)
        system: Optional system prompt
        preferred_provider: Force a specific provider
        agent_id: Optional agent ID for usage attribution
        session_id: Optional session ID for usage attribution

    Returns:
        Dict with content, tokens, and provider used
    """
    # Select provider
    provider = preferred_provider or await select_provider(task_type)

    if not provider:
        # Determine why no provider is available
        providers_with_keys = [p for p in PROVIDERS.keys() if get_api_key(p)]
        if not providers_with_keys:
            raise ConfigurationInterventionRequired(
                title="Configure AI Provider API Keys",
                description="No AI provider API keys configured. Add at least one API key (Groq, Google, or OpenRouter) to .env file for AI processing.",
                source_system="service:ai_providers",
                context={"available_providers": list(PROVIDERS.keys())}
            )
        else:
            # All configured providers are at daily limit
            raise ConfigurationInterventionRequired(
                title="AI Provider Daily Limits Reached",
                description="All configured AI providers have reached their daily free tier limits. Add additional API keys or wait until tomorrow.",
                source_system="service:ai_providers",
                context={
                    "configured_providers": providers_with_keys,
                    "daily_limits": {p: PROVIDERS[p].daily_limit for p in providers_with_keys}
                }
            )

    logger.info(f"Using {provider} for {task_type} task")

    # Call the appropriate provider
    try:
        if provider == "groq":
            return await call_groq(prompt, system, agent_id=agent_id, session_id=session_id)
        elif provider == "google":
            return await call_google(prompt, system, agent_id=agent_id, session_id=session_id)
        elif provider == "openrouter":
            return await call_openrouter(prompt, system, agent_id=agent_id, session_id=session_id)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    except Exception as e:
        logger.error(f"Provider {provider} failed: {e}")
        # Try fallback
        for fallback in ["groq", "google", "openrouter"]:
            if fallback != provider and get_api_key(fallback):
                try:
                    logger.info(f"Falling back to {fallback}")
                    if fallback == "groq":
                        return await call_groq(prompt, system, agent_id=agent_id, session_id=session_id)
                    elif fallback == "google":
                        return await call_google(prompt, system, agent_id=agent_id, session_id=session_id)
                    elif fallback == "openrouter":
                        return await call_openrouter(prompt, system, agent_id=agent_id, session_id=session_id)
                except Exception as e2:
                    logger.error(f"Fallback {fallback} also failed: {e2}")
                    continue
        raise RuntimeError(f"All providers failed. Original error: {e}")


async def get_provider_stats() -> Dict[str, Any]:
    """Get usage statistics for all providers."""
    results = await db.fetch_all(
        """
        SELECT provider, request_count, token_count, cost_usd
        FROM ai_provider_usage
        WHERE date = CURRENT_DATE
        """
    )

    stats = {}
    for row in results:
        provider = row["provider"]
        config = PROVIDERS.get(provider)
        stats[provider] = {
            "requests_today": row["request_count"],
            "tokens_today": row["token_count"],
            "cost_today": float(row["cost_usd"]),
            "daily_limit": config.daily_limit if config else 0,
            "usage_percent": round(row["request_count"] / config.daily_limit * 100, 1) if config else 0
        }

    # Add providers with no usage today
    for name, config in PROVIDERS.items():
        if name not in stats:
            stats[name] = {
                "requests_today": 0,
                "tokens_today": 0,
                "cost_today": 0.0,
                "daily_limit": config.daily_limit,
                "usage_percent": 0.0
            }

    return stats
