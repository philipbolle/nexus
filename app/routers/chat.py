"""
NEXUS Chat Endpoint
Natural language interface to NEXUS.
"""

from fastapi import APIRouter, HTTPException
import logging

from ..models.schemas import ChatRequest, ChatResponse
from ..services.ai import chat, AIResponse

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Send a message to NEXUS AI.

    Routes to cheapest capable model:
    1. Groq (free tier)
    2. DeepSeek (cheap fallback)
    """
    try:
        response: AIResponse = await chat(
            message=request.message,
            preferred_model=request.model
        )

        return ChatResponse(
            response=response.content,
            model_used=f"{response.provider}/{response.model}",
            tokens_used=response.input_tokens + response.output_tokens,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
            cached=response.cached
        )

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
