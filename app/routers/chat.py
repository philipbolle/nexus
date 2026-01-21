"""
NEXUS Chat Endpoint
Natural language interface to NEXUS.
"""

from fastapi import APIRouter, HTTPException, Query
import logging
from typing import Optional

from ..models.schemas import ChatRequest, ChatResponse
from ..services.ai import chat, chat_voice, AIResponse

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


@router.post("/voice", response_model=ChatResponse)
async def voice_endpoint(
    request: ChatRequest,
    session_id: Optional[str] = Query(None, description="Optional session ID for conversation memory")
):
    """
    Voice-optimized chat endpoint.

    Uses faster, smaller model (llama-3.1-8b-instant) with shorter responses
    (max 256 tokens) for iPhone voice assistant.

    Perfect for "Hey NEXUS" demo.
    """
    try:
        response: AIResponse = await chat_voice(
            message=request.message,
            session_id=session_id
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
        logger.error(f"Voice chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
