"""
NEXUS Cost Optimization Database Service
Database operations for cost optimization tables.
"""

import asyncpg
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import hashlib
from .config import config

class DatabaseService:
    """Database service for cost optimization operations."""
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or config.database.connection_string
        self._pool = None
    
    async def initialize(self):
        """Initialize the database connection pool."""
        if not self._pool:
            async def init_connection(conn):
                """Initialize connection with JSONB codec."""
                await conn.set_type_codec(
                    'jsonb',
                    encoder=json.dumps,
                    decoder=json.loads,
                    schema='pg_catalog'
                )
                await conn.set_type_codec(
                    'json',
                    encoder=json.dumps,
                    decoder=json.loads,
                    schema='pg_catalog'
                )
            self._pool = await asyncpg.create_pool(
                dsn=self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=60,
                init=init_connection,
            )
    
    async def close(self):
        """Close the database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return results as dictionaries."""
        async with self._pool.acquire() as connection:
            results = await connection.fetch(query, *args)
            return [dict(record) for record in results]
    
    async def execute_insert(self, query: str, *args) -> Any:
        """Execute an INSERT query and return the inserted row."""
        async with self._pool.acquire() as connection:
            return await connection.fetchrow(query, *args)
    
    # ===== Semantic Cache Operations =====
    
    async def get_semantic_cache(self, query_hash: str, agent_id: Optional[uuid.UUID] = None) -> Optional[Dict[str, Any]]:
        """Get a cached response by query hash and optional agent_id."""
        if agent_id is None:
            query = """
                SELECT * FROM semantic_cache
                WHERE query_hash = $1
                AND agent_id IS NULL
                AND (expires_at IS NULL OR expires_at > NOW())
            """
            results = await self.execute_query(query, query_hash)
        else:
            query = """
                SELECT * FROM semantic_cache
                WHERE query_hash = $1
                AND agent_id = $2
                AND (expires_at IS NULL OR expires_at > NOW())
            """
            results = await self.execute_query(query, query_hash, agent_id)
        return results[0] if results else None
    
    async def update_semantic_cache_hit(self, cache_id: uuid.UUID):
        """Update hit count and last hit time for a cache entry."""
        query = """
            UPDATE semantic_cache 
            SET hit_count = hit_count + 1, last_hit_at = NOW()
            WHERE id = $1
        """
        await self.execute_query(query, cache_id)
    
    async def create_semantic_cache(
        self,
        query_text: str,
        response_text: str,
        model_used: str,
        query_embedding: Optional[List[float]] = None,
        response_metadata: Optional[Dict] = None,
        tokens_saved: int = 0,
        confidence_score: float = 0.9,
        ttl_hours: int = 168,
        agent_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Create a new semantic cache entry with optional agent_id."""
        # Include agent_id in query_hash to ensure uniqueness per agent
        if agent_id:
            query_hash = hashlib.sha256((query_text + str(agent_id)).encode()).hexdigest()
        else:
            query_hash = hashlib.sha256(query_text.encode()).hexdigest()

        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours) if ttl_hours else None

        query = """
            INSERT INTO semantic_cache (
                query_text, query_hash, query_embedding, response_text,
                response_metadata, model_used, tokens_saved, confidence_score,
                expires_at, agent_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
        """

        result = await self.execute_insert(
            query,
            query_text,
            query_hash,
            query_embedding,
            response_text,
            json.dumps(response_metadata) if response_metadata else None,
            model_used,
            tokens_saved,
            confidence_score,
            expires_at,
            agent_id
        )

        return dict(result) if result else None
    
    async def find_similar_semantic_cache(
        self,
        query_embedding: List[float],
        threshold: float = 0.85,
        limit: int = 5,
        agent_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """Find similar cache entries using vector similarity, optionally filtered by agent."""
        # Note: This requires the pgvector extension. We're using real[] for now.
        # In a real implementation with pgvector, we'd use vector similarity operators.
        # For now, we'll return empty list - this is a placeholder.
        # Future implementation should filter by agent_id if provided.
        return []
    
    # ===== Embedding Cache Operations =====
    
    async def get_embedding_cache(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached embedding by content hash."""
        query = """
            SELECT * FROM embedding_cache 
            WHERE content_hash = $1
        """
        results = await self.execute_query(query, content_hash)
        return results[0] if results else None
    
    async def create_embedding_cache(
        self,
        content: str,
        embedding: List[float],
        embedding_model: str,
        dimension: int
    ) -> Dict[str, Any]:
        """Create a new embedding cache entry."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        content_preview = content[:500]
        
        query = """
            INSERT INTO embedding_cache (
                content_hash, content_preview, embedding, 
                embedding_model, dimension
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (content_hash) 
            DO UPDATE SET 
                last_accessed_at = NOW(),
                access_count = embedding_cache.access_count + 1
            RETURNING *
        """
        
        result = await self.execute_insert(
            query,
            content_hash,
            content_preview,
            embedding,
            embedding_model,
            dimension
        )
        
        return dict(result) if result else None
    
    # ===== API Usage Tracking =====
    
    async def log_api_usage(
        self,
        provider_id: Optional[uuid.UUID] = None,
        model_id: Optional[uuid.UUID] = None,
        endpoint: Optional[str] = None,
        request_type: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        cost_usd: float = 0.0,
        latency_ms: Optional[int] = None,
        time_to_first_token_ms: Optional[int] = None,
        success: bool = True,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        cache_hit: bool = False,
        agent_id: Optional[uuid.UUID] = None,
        session_id: Optional[uuid.UUID] = None,
        query_hash: Optional[str] = None,
        request_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Log API usage to the database."""
        query = """
            INSERT INTO api_usage (
                provider_id, model_id, endpoint, request_type,
                input_tokens, output_tokens, cached_tokens, cost_usd,
                latency_ms, time_to_first_token_ms, success, error_code,
                error_message, cache_hit, agent_id, session_id, query_hash,
                request_metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            RETURNING *
        """
        
        result = await self.execute_insert(
            query,
            provider_id,
            model_id,
            endpoint,
            request_type,
            input_tokens,
            output_tokens,
            cached_tokens,
            cost_usd,
            latency_ms,
            time_to_first_token_ms,
            success,
            error_code,
            error_message,
            cache_hit,
            agent_id,
            session_id,
            query_hash,
            json.dumps(request_metadata) if request_metadata else None
        )
        
        return dict(result) if result else None
    
    async def get_daily_api_costs(
        self, 
        days: int = 7,
        provider_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get daily API costs for the last N days."""
        query = """
            SELECT 
                DATE(timestamp) as date,
                provider_id,
                SUM(cost_usd) as total_cost,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cached_tokens) as total_cached_tokens,
                COUNT(*) as request_count,
                SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
            FROM api_usage
            WHERE timestamp >= NOW() - INTERVAL '1 day' * $1
            {provider_filter}
            GROUP BY DATE(timestamp), provider_id
            ORDER BY date DESC
        """.format(
            provider_filter="AND provider_id = $2" if provider_id else ""
        )
        
        params = [days]
        if provider_id:
            params.append(provider_id)
        
        return await self.execute_query(query, *params)
    
    # ===== Cost Alert Operations =====
    
    async def check_cost_alerts(
        self,
        provider_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """Check if any cost alerts should be triggered."""
        # Get current month's spend
        query = """
            SELECT 
                provider_id,
                SUM(cost_usd) as current_month_spend
            FROM api_usage
            WHERE timestamp >= DATE_TRUNC('month', NOW())
            {provider_filter}
            GROUP BY provider_id
        """.format(
            provider_filter="AND provider_id = $1" if provider_id else ""
        )
        
        params = []
        if provider_id:
            params.append(provider_id)
        
        spends = await self.execute_query(query, *params)
        
        # Check against budgets (would compare with provider budgets here)
        # For now, just return the spend data
        return spends
    
    async def create_cost_alert(
        self,
        alert_type: str,
        threshold_usd: float,
        current_value_usd: float,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a new cost alert."""
        query = """
            INSERT INTO cost_alerts (
                alert_type, threshold_usd, current_value_usd, metadata
            ) VALUES ($1, $2, $3, $4)
            RETURNING *
        """
        
        result = await self.execute_insert(
            query,
            alert_type,
            threshold_usd,
            current_value_usd,
            json.dumps(metadata) if metadata else None
        )
        
        return dict(result) if result else None
    
    # ===== Batch Job Operations =====
    
    async def create_batch_job(
        self,
        name: str,
        provider_id: Optional[uuid.UUID] = None,
        model_id: Optional[uuid.UUID] = None,
        input_file_path: Optional[str] = None,
        estimated_cost_usd: float = 0.0,
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Create a new batch job."""
        query = """
            INSERT INTO batch_jobs (
                name, provider_id, model_id, input_file_path,
                estimated_cost_usd, expires_at, submitted_at
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
            RETURNING *
        """
        
        result = await self.execute_insert(
            query,
            name,
            provider_id,
            model_id,
            input_file_path,
            estimated_cost_usd,
            expires_at
        )
        
        return dict(result) if result else None
    
    async def update_batch_job(
        self,
        job_id: uuid.UUID,
        status: Optional[str] = None,
        completed_requests: Optional[int] = None,
        failed_requests: Optional[int] = None,
        output_file_path: Optional[str] = None,
        actual_cost_usd: Optional[float] = None
    ) -> Dict[str, Any]:
        """Update a batch job."""
        updates = []
        params = []
        
        if status:
            updates.append("status = $%d" % (len(params) + 1))
            params.append(status)
        
        if completed_requests is not None:
            updates.append("completed_requests = $%d" % (len(params) + 1))
            params.append(completed_requests)
        
        if failed_requests is not None:
            updates.append("failed_requests = $%d" % (len(params) + 1))
            params.append(failed_requests)
        
        if output_file_path:
            updates.append("output_file_path = $%d" % (len(params) + 1))
            params.append(output_file_path)
        
        if actual_cost_usd is not None:
            updates.append("actual_cost_usd = $%d" % (len(params) + 1))
            params.append(actual_cost_usd)
        
        if status == 'completed':
            updates.append("completed_at = NOW()")
        
        if not updates:
            return None
        
        params.append(job_id)
        
        query = """
            UPDATE batch_jobs 
            SET {updates}
            WHERE id = ${job_param}
            RETURNING *
        """.format(
            updates=", ".join(updates),
            job_param=len(params)
        )
        
        result = await self.execute_insert(query, *params)
        return dict(result) if result else None
    
    async def create_batch_job_item(
        self,
        batch_id: uuid.UUID,
        request_body: Dict[str, Any],
        custom_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a batch job item."""
        query = """
            INSERT INTO batch_job_items (
                batch_id, custom_id, request_body
            ) VALUES ($1, $2, $3)
            RETURNING *
        """
        
        result = await self.execute_insert(
            query,
            batch_id,
            custom_id,
            json.dumps(request_body)
        )
        
        return dict(result) if result else None
    
    async def update_batch_job_item(
        self,
        item_id: uuid.UUID,
        response_body: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a batch job item."""
        updates = []
        params = []
        
        if response_body is not None:
            updates.append("response_body = $%d" % (len(params) + 1))
            params.append(json.dumps(response_body))
        
        if status:
            updates.append("status = $%d" % (len(params) + 1))
            params.append(status)
        
        if error_message:
            updates.append("error_message = $%d" % (len(params) + 1))
            params.append(error_message)
        
        if not updates:
            return None
        
        params.append(item_id)
        
        query = """
            UPDATE batch_job_items 
            SET {updates}
            WHERE id = ${item_param}
            RETURNING *
        """.format(
            updates=", ".join(updates),
            item_param=len(params)
        )
        
        result = await self.execute_insert(query, *params)
        return dict(result) if result else None
    
    # ===== Utility Methods =====
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        semantic_cache_query = """
            SELECT 
                COUNT(*) as total_entries,
                SUM(hit_count) as total_hits,
                AVG(confidence_score) as avg_confidence,
                SUM(tokens_saved) as total_tokens_saved,
                SUM(cost_saved_usd) as total_cost_saved
            FROM semantic_cache
            WHERE expires_at IS NULL OR expires_at > NOW()
        """
        
        embedding_cache_query = """
            SELECT 
                COUNT(*) as total_entries,
                SUM(access_count) as total_accesses,
                AVG(dimension) as avg_dimension
            FROM embedding_cache
        """
        
        semantic_stats = await self.execute_query(semantic_cache_query)
        embedding_stats = await self.execute_query(embedding_cache_query)
        
        return {
            "semantic_cache": semantic_stats[0] if semantic_stats else {},
            "embedding_cache": embedding_stats[0] if embedding_stats else {}
        }
    
    async def cleanup_expired_cache(self) -> Tuple[int, int]:
        """Clean up expired cache entries."""
        semantic_query = """
            DELETE FROM semantic_cache 
            WHERE expires_at IS NOT NULL AND expires_at <= NOW()
            RETURNING id
        """
        
        embedding_query = """
            DELETE FROM embedding_cache 
            WHERE last_accessed_at <= NOW() - INTERVAL '30 days'
            RETURNING id
        """
        
        semantic_deleted = await self.execute_query(semantic_query)
        embedding_deleted = await self.execute_query(embedding_query)
        
        return len(semantic_deleted), len(embedding_deleted)

# Global database service instance
db_service = DatabaseService()

async def initialize_database():
    """Initialize the database service."""
    await db_service.initialize()

async def close_database():
    """Close the database service."""
    await db_service.close()

if __name__ == "__main__":
    # Test the database service
    async def test():
        await initialize_database()
        
        # Test cache statistics
        stats = await db_service.get_cache_statistics()
        print("Cache Statistics:", json.dumps(stats, indent=2, default=str))
        
        await close_database()
    
    asyncio.run(test())
