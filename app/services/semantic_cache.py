"""
NEXUS Semantic Cache
Cache AI responses based on semantic similarity.
Reduces API costs by 60-70%.
"""

import logging
import hashlib
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..database import db
from .embeddings import get_embedding, cosine_similarity

logger = logging.getLogger(__name__)

# Similarity threshold - queries must be this similar to use cache
SIMILARITY_THRESHOLD = 0.92

# Cache TTL in hours
CACHE_TTL_HOURS = 168  # 1 week


@dataclass
class CachedResponse:
    """A cached AI response."""
    id: str
    response_text: str
    model_used: str
    tokens_saved: int
    similarity: float


async def check_cache(query: str) -> Optional[CachedResponse]:
    """
    Check if a similar query exists in cache.

    1. Generate embedding for query
    2. Search semantic_cache for similar embeddings
    3. Return cached response if similarity > threshold
    """
    try:
        # Generate embedding for incoming query
        query_embedding = get_embedding(query)

        # Get all non-expired cache entries with embeddings
        rows = await db.fetch_all(
            """
            SELECT id, query_text, query_embedding, response_text,
                   model_used, tokens_saved
            FROM semantic_cache
            WHERE query_embedding IS NOT NULL
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC
            LIMIT 100
            """
        )

        if not rows:
            logger.debug("Cache empty, no entries to check")
            return None

        # Find most similar entry
        best_match = None
        best_similarity = 0.0

        for row in rows:
            cached_embedding = row["query_embedding"]
            if not cached_embedding:
                continue

            similarity = cosine_similarity(query_embedding, cached_embedding)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = row

        # Check if best match exceeds threshold
        if best_match and best_similarity >= SIMILARITY_THRESHOLD:
            cache_id = str(best_match["id"])

            # Update hit count
            await db.execute(
                """
                UPDATE semantic_cache
                SET hit_count = hit_count + 1,
                    last_hit_at = NOW()
                WHERE id = $1
                """,
                best_match["id"]
            )

            logger.info(f"Cache HIT! Similarity: {best_similarity:.3f}")

            return CachedResponse(
                id=cache_id,
                response_text=best_match["response_text"],
                model_used=best_match["model_used"] or "cached",
                tokens_saved=best_match["tokens_saved"] or 0,
                similarity=best_similarity
            )

        logger.debug(f"Cache miss. Best similarity: {best_similarity:.3f}")
        return None

    except Exception as e:
        logger.error(f"Cache check failed: {e}")
        return None


async def store_cache(
    query: str,
    response: str,
    model_used: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0
) -> Optional[str]:
    """
    Store a query/response pair in the semantic cache.

    Returns cache entry ID if successful.
    """
    try:
        # Generate embedding
        query_embedding = get_embedding(query)

        # Create hash for deduplication
        query_hash = hashlib.sha256(query.encode()).hexdigest()

        # Calculate tokens saved (for future hits)
        tokens_saved = input_tokens + output_tokens

        # Set expiry
        expires_at = datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)

        # Insert into database
        result = await db.fetch_one(
            """
            INSERT INTO semantic_cache
            (query_text, query_hash, query_embedding, response_text,
             model_used, tokens_saved, cost_saved_usd, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (query_hash) DO UPDATE SET
                hit_count = semantic_cache.hit_count,
                updated_at = NOW()
            RETURNING id
            """,
            query,
            query_hash,
            query_embedding,
            response,
            model_used,
            tokens_saved,
            cost_usd,
            expires_at
        )

        if result:
            cache_id = str(result["id"])
            logger.info(f"Cached response: {cache_id[:8]}...")
            return cache_id

        return None

    except Exception as e:
        logger.error(f"Cache store failed: {e}")
        return None


async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    try:
        result = await db.fetch_one(
            """
            SELECT
                COUNT(*) as total_entries,
                COALESCE(SUM(hit_count), 0) as total_hits,
                COALESCE(SUM(tokens_saved * hit_count), 0) as total_tokens_saved,
                COALESCE(SUM(cost_saved_usd * hit_count), 0) as total_cost_saved
            FROM semantic_cache
            WHERE expires_at IS NULL OR expires_at > NOW()
            """
        )

        return {
            "total_entries": int(result["total_entries"]) if result else 0,
            "total_hits": int(result["total_hits"]) if result else 0,
            "total_tokens_saved": int(result["total_tokens_saved"]) if result else 0,
            "total_cost_saved_usd": float(result["total_cost_saved"]) if result else 0.0,
        }

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {}


async def cleanup_expired() -> int:
    """Remove expired cache entries. Returns count deleted."""
    try:
        result = await db.fetch_all(
            """
            DELETE FROM semantic_cache
            WHERE expires_at IS NOT NULL AND expires_at <= NOW()
            RETURNING id
            """
        )
        count = len(result)
        if count > 0:
            logger.info(f"Cleaned up {count} expired cache entries")
        return count

    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return 0
