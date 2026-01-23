"""
NEXUS Chat Endpoint
Natural language interface to NEXUS.
"""

from fastapi import APIRouter, HTTPException, Query
import logging
from typing import Optional, Dict, Any

from ..models.schemas import ChatRequest, ChatResponse
from ..services.ai import chat, chat_voice, intelligent_chat, AIResponse

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
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
) -> ChatResponse:
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


@router.post("/intelligent", response_model=ChatResponse)
async def intelligent_endpoint(
    request: ChatRequest,
    session_id: Optional[str] = Query(None, description="Session ID for conversation memory"),
    use_context: bool = Query(True, description="Whether to use intelligent context retrieval")
) -> ChatResponse:
    """
    Jarvis-like intelligent chat endpoint.

    Uses full NEXUS context from all data sources:
    - Finance data (expenses, debts, budgets)
    - Email data (recent emails, insights)
    - Agent data (active agents, sessions)
    - System data (health, errors, performance)
    - Conversation history
    - Usage statistics

    This is the "real Jarvis" endpoint - extremely intelligent,
    learns from every interaction, and provides context-aware responses.
    """
    try:
        response: AIResponse = await intelligent_chat(
            message=request.message,
            session_id=session_id,
            use_context=use_context
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
        logger.error(f"Intelligent chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
