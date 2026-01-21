"""
NEXUS Cost Optimization Cache Service
Semantic and embedding caching with Redis and PostgreSQL.
"""

import asyncio
import json
import hashlib
import pickle
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import redis.asyncio as redis
from .config import config
from .database import db_service

class CacheService:
    """Cache service for semantic and embedding caching."""
    
    def __init__(self):
        self.redis_client = None
        self.redis_config = config.redis
    
    async def initialize(self):
        """Initialize Redis connection."""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_config.connection_string,
                decode_responses=False  # We'll handle serialization ourselves
            )
        await db_service.initialize()
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    def _generate_query_hash(self, query_text: str, agent_id: Optional[UUID] = None) -> str:
        """Generate query hash that includes agent_id for uniqueness."""
        if agent_id:
            return hashlib.sha256((query_text + str(agent_id)).encode()).hexdigest()
        return hashlib.sha256(query_text.encode()).hexdigest()

    # ===== Semantic Cache Methods =====
    
    async def get_semantic_cache(self, query_text: str, agent_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response for a query, optionally scoped to an agent.
        First checks Redis, then falls back to PostgreSQL.
        """
        query_hash = self._generate_query_hash(query_text, agent_id)

        # Try Redis first
        if self.redis_client:
            redis_key = f"semantic:{agent_id}:{query_hash}" if agent_id else f"semantic:{query_hash}"
            cached = await self.redis_client.get(redis_key)
            if cached:
                try:
                    data = pickle.loads(cached)
                    # Update hit count in background
                    asyncio.create_task(self._update_semantic_cache_hit(data['id']))
                    return data
                except:
                    # Corrupted cache, delete it
                    await self.redis_client.delete(redis_key)

        # Fall back to PostgreSQL
        db_cache = await db_service.get_semantic_cache(query_hash, agent_id)
        if db_cache:
            # Store in Redis for faster access
            if self.redis_client:
                redis_key = f"semantic:{agent_id}:{query_hash}" if agent_id else f"semantic:{query_hash}"
                ttl = config.cost_optimization.cache_ttl_hours * 3600
                await self.redis_client.setex(
                    redis_key,
                    ttl,
                    pickle.dumps(db_cache)
                )
            return db_cache

        return None
    
    async def set_semantic_cache(
        self,
        query_text: str,
        response_text: str,
        model_used: str,
        query_embedding: Optional[List[float]] = None,
        response_metadata: Optional[Dict] = None,
        tokens_saved: int = 0,
        confidence_score: float = 0.9,
        agent_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Set semantic cache in both Redis and PostgreSQL, optionally scoped to an agent."""
        # Calculate cost savings
        model_config = config.models.get(model_used)
        cost_saved_usd = 0.0
        if model_config:
            cost_per_token = model_config.input_cost_per_mtok / 1_000_000
            cost_saved_usd = tokens_saved * cost_per_token

        # Store in PostgreSQL
        db_cache = await db_service.create_semantic_cache(
            query_text=query_text,
            response_text=response_text,
            model_used=model_used,
            query_embedding=query_embedding,
            response_metadata=response_metadata,
            tokens_saved=tokens_saved,
            confidence_score=confidence_score,
            ttl_hours=config.cost_optimization.cache_ttl_hours,
            agent_id=agent_id
        )

        if not db_cache:
            raise Exception("Failed to create semantic cache in database")

        # Add cost savings to cache entry
        db_cache['cost_saved_usd'] = cost_saved_usd

        # Store in Redis
        if self.redis_client:
            query_hash = self._generate_query_hash(query_text, agent_id)
            redis_key = f"semantic:{agent_id}:{query_hash}" if agent_id else f"semantic:{query_hash}"
            ttl = config.cost_optimization.cache_ttl_hours * 3600
            await self.redis_client.setex(
                redis_key,
                ttl,
                pickle.dumps(db_cache)
            )

        return db_cache
    
    async def _update_semantic_cache_hit(self, cache_id: str):
        """Update hit count for semantic cache (background task)."""
        try:
            await db_service.update_semantic_cache_hit(cache_id)
        except Exception as e:
            print(f"Error updating cache hit: {e}")
    
    async def find_similar_semantic_cache(
        self,
        query_embedding: List[float],
        threshold: float = None,
        limit: int = 5,
        agent_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar cache entries using vector similarity, optionally filtered by agent.
        Currently a placeholder until pgvector is installed.
        """
        if threshold is None:
            threshold = config.cost_optimization.semantic_similarity_threshold

        # TODO: Implement vector similarity search with pgvector
        # For now, delegate to database service (which also returns empty list)
        return await db_service.find_similar_semantic_cache(
            query_embedding=query_embedding,
            threshold=threshold,
            limit=limit,
            agent_id=agent_id
        )
    
    # ===== Embedding Cache Methods =====
    
    async def get_embedding(self, content: str) -> Optional[List[float]]:
        """
        Get cached embedding for content.
        Returns embedding if found, None otherwise.
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Try Redis first
        if self.redis_client:
            redis_key = f"embedding:{content_hash}"
            cached = await self.redis_client.get(redis_key)
            if cached:
                try:
                    embedding = pickle.loads(cached)
                    # Update access count in background
                    asyncio.create_task(self._update_embedding_cache_access(content_hash))
                    return embedding
                except:
                    await self.redis_client.delete(redis_key)
        
        # Fall back to PostgreSQL
        db_cache = await db_service.get_embedding_cache(content_hash)
        if db_cache and db_cache.get('embedding'):
            embedding = db_cache['embedding']
            
            # Store in Redis
            if self.redis_client:
                redis_key = f"embedding:{content_hash}"
                # Embeddings don't expire, but we set a long TTL
                await self.redis_client.setex(redis_key, 86400 * 30, pickle.dumps(embedding))
            
            return embedding
        
        return None
    
    async def set_embedding(
        self,
        content: str,
        embedding: List[float],
        embedding_model: str,
        dimension: int
    ) -> Dict[str, Any]:
        """Cache embedding in both Redis and PostgreSQL."""
        # Store in PostgreSQL
        db_cache = await db_service.create_embedding_cache(
            content=content,
            embedding=embedding,
            embedding_model=embedding_model,
            dimension=dimension
        )
        
        # Store in Redis
        if self.redis_client:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            redis_key = f"embedding:{content_hash}"
            # Embeddings don't expire, but we set a long TTL
            await self.redis_client.setex(redis_key, 86400 * 30, pickle.dumps(embedding))
        
        return db_cache
    
    async def _update_embedding_cache_access(self, content_hash: str):
        """Update access count for embedding cache (background task)."""
        # This is handled by the ON CONFLICT clause in the database
        pass
    
    # ===== Cache Statistics =====
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        # Get database statistics
        db_stats = await db_service.get_cache_statistics()
        
        # Get Redis statistics
        redis_stats = {}
        if self.redis_client:
            try:
                # Get keys by pattern
                semantic_keys = await self.redis_client.keys("semantic:*")
                embedding_keys = await self.redis_client.keys("embedding:*")
                
                redis_stats = {
                    "semantic_cache_keys": len(semantic_keys),
                    "embedding_cache_keys": len(embedding_keys),
                    "total_keys": len(semantic_keys) + len(embedding_keys)
                }
            except Exception as e:
                redis_stats = {"error": str(e)}
        
        return {
            "database": db_stats,
            "redis": redis_stats,
            "config": {
                "semantic_cache_enabled": config.cost_optimization.semantic_cache_enabled,
                "embedding_cache_enabled": config.cost_optimization.embedding_cache_enabled,
                "cache_ttl_hours": config.cost_optimization.cache_ttl_hours,
                "semantic_similarity_threshold": config.cost_optimization.semantic_similarity_threshold
            }
        }
    
    async def cleanup_expired_cache(self) -> Dict[str, Any]:
        """Clean up expired cache entries."""
        # Clean up PostgreSQL cache
        db_semantic_deleted, db_embedding_deleted = await db_service.cleanup_expired_cache()
        
        # Clean up Redis cache (we rely on TTL, but we can also scan for expired)
        redis_deleted = 0
        if self.redis_client:
            # Note: In production, we'd use SCAN for large datasets
            # For now, we'll let Redis TTL handle it
            pass
        
        return {
            "database": {
                "semantic_cache_deleted": db_semantic_deleted,
                "embedding_cache_deleted": db_embedding_deleted
            },
            "redis": {
                "deleted": redis_deleted
            }
        }
    
    # ===== Batch Cache Operations =====
    
    async def batch_get_semantic_cache(self, query_texts: List[str], agent_id: Optional[UUID] = None) -> Dict[str, Optional[Dict[str, Any]]]:
        """Batch get semantic cache for multiple queries, optionally scoped to an agent."""
        results = {}
        for query_text in query_texts:
            results[query_text] = await self.get_semantic_cache(query_text, agent_id)
        return results
    
    async def batch_set_semantic_cache(
        self,
        cache_entries: List[Dict[str, Any]],
        agent_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Batch set semantic cache entries, optionally scoped to an agent."""
        results = []
        for entry in cache_entries:
            try:
                # If agent_id parameter provided and entry doesn't have agent_id, add it
                entry_copy = entry.copy()
                if agent_id is not None and 'agent_id' not in entry_copy:
                    entry_copy['agent_id'] = agent_id
                result = await self.set_semantic_cache(**entry_copy)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e), "entry": entry})
        return results
    
    # ===== Cache Health Check =====
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on cache services."""
        health = {
            "redis": {"status": "unknown", "error": None},
            "database": {"status": "unknown", "error": None}
        }
        
        # Check Redis
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health["redis"]["status"] = "healthy"
            except Exception as e:
                health["redis"]["status"] = "unhealthy"
                health["redis"]["error"] = str(e)
        else:
            health["redis"]["status"] = "not_initialized"
        
        # Check Database
        try:
            # Try a simple query
            stats = await db_service.get_cache_statistics()
            health["database"]["status"] = "healthy"
        except Exception as e:
            health["database"]["status"] = "unhealthy"
            health["database"]["error"] = str(e)
        
        return health

# Global cache service instance
cache_service = CacheService()

async def initialize_cache():
    """Initialize the cache service."""
    await cache_service.initialize()

async def close_cache():
    """Close the cache service."""
    await cache_service.close()

if __name__ == "__main__":
    # Test the cache service
    async def test():
        await initialize_cache()
        
        # Test health check
        health = await cache_service.health_check()
        print("Cache Health Check:", json.dumps(health, indent=2))
        
        # Test cache stats
        stats = await cache_service.get_cache_stats()
        print("\nCache Statistics:", json.dumps(stats, indent=2, default=str))
        
        await close_cache()
    
    asyncio.run(test())
