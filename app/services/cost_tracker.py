"""
NEXUS Cost Optimization Tracker
Real-time tracking and analysis of AI API costs.
"""

import asyncio
import json
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from .config import config
from .database import db_service
from .cache_service import cache_service

logger = logging.getLogger(__name__)

@dataclass
class CostMetrics:
    """Cost metrics for a time period."""
    total_cost: float = 0.0
    total_tokens: int = 0
    cached_tokens: int = 0
    cache_hits: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0

class CostTracker:
    """Tracks and analyzes AI API costs in real-time."""
    
    def __init__(self):
        self.daily_budget = config.cost_optimization.daily_budget
        self.monthly_budget = config.cost_optimization.monthly_budget
        self.alert_threshold = config.cost_optimization.alert_threshold_percent
        
    async def initialize(self):
        """Initialize the cost tracker."""
        await db_service.initialize()
        await cache_service.initialize()
    
    async def close(self):
        """Close the cost tracker."""
        pass  # Database and cache services are closed separately
    
    # ===== Cost Tracking Methods =====
    
    async def track_api_call(
        self,
        provider_name: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        cache_hit: bool = False,
        latency_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        agent_id: Optional[uuid.UUID] = None,
        session_id: Optional[uuid.UUID] = None,
        query_hash: Optional[str] = None,
        request_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Track an API call and log it to the database."""
        # Calculate cost
        model_config = config.models.get(model_id)
        cost_usd = 0.0
        
        if model_config and success:
            input_cost = (input_tokens * model_config.input_cost_per_mtok) / 1_000_000
            output_cost = (output_tokens * model_config.output_cost_per_mtok) / 1_000_000
            cost_usd = input_cost + output_cost
        
        # Get provider ID (in a real system, we'd have provider IDs in the database)
        # For now, we'll use a placeholder
        provider_id = None
        model_uuid = None
        
        # Log to database
        usage_log = await db_service.log_api_usage(
            provider_id=provider_id,
            model_id=model_uuid,
            endpoint="chat/completions",  # Default
            request_type="chat",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            cache_hit=cache_hit,
            agent_id=agent_id,
            session_id=session_id,
            query_hash=query_hash,
            request_metadata=request_metadata
        )
        
        # Check for cost alerts
        await self._check_cost_alerts(provider_name, cost_usd)
        
        return {
            "cost_usd": cost_usd,
            "log_id": usage_log.get("id") if usage_log else None,
            "cache_hit": cache_hit,
            "tokens_saved": cached_tokens
        }
    
    async def _check_cost_alerts(self, provider_name: str, cost_usd: float):
        """Check if cost alerts should be triggered (background task)."""
        try:
            # Get today's cost for this provider
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # In a real implementation, we'd query the database for today's cost
            # and check against the provider's budget
            # For now, we'll just log the check
            pass
        except Exception as e:
            logger.error(f"Error checking cost alerts: {e}")
    
    # ===== Cost Analysis Methods =====
    
    async def get_daily_cost_breakdown(self, days: int = 7) -> Dict[str, Any]:
        """Get daily cost breakdown for the last N days."""
        db_costs = await db_service.get_daily_api_costs(days=days)
        
        # Transform data
        daily_data = {}
        for row in db_costs:
            date_str = row['date'].strftime('%Y-%m-%d')
            if date_str not in daily_data:
                daily_data[date_str] = {
                    "date": date_str,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "cached_tokens": 0,
                    "requests": 0,
                    "cache_hits": 0
                }
            
            daily_data[date_str]["total_cost"] += float(row['total_cost'] or 0)
            daily_data[date_str]["total_tokens"] += (row['total_input_tokens'] or 0) + (row['total_output_tokens'] or 0)
            daily_data[date_str]["cached_tokens"] += row['total_cached_tokens'] or 0
            daily_data[date_str]["requests"] += row['request_count'] or 0
            daily_data[date_str]["cache_hits"] += row['cache_hits'] or 0
        
        # Convert to list and sort by date
        result = list(daily_data.values())
        result.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            "days": days,
            "data": result,
            "summary": self._calculate_summary(result)
        }
    
    async def get_provider_cost_breakdown(self, days: int = 7) -> Dict[str, Any]:
        """Get cost breakdown by provider for the last N days."""
        db_costs = await db_service.get_daily_api_costs(days=days)
        
        provider_data = {}
        for row in db_costs:
            provider = row['provider_id'] or "unknown"
            if provider not in provider_data:
                provider_data[provider] = {
                    "provider": provider,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "requests": 0,
                    "cache_hits": 0
                }
            
            provider_data[provider]["total_cost"] += float(row['total_cost'] or 0)
            provider_data[provider]["total_tokens"] += (row['total_input_tokens'] or 0) + (row['total_output_tokens'] or 0)
            provider_data[provider]["requests"] += row['request_count'] or 0
            provider_data[provider]["cache_hits"] += row['cache_hits'] or 0
        
        # Convert to list and sort by cost
        result = list(provider_data.values())
        result.sort(key=lambda x: x['total_cost'], reverse=True)
        
        return {
            "days": days,
            "providers": result,
            "total_cost": sum(p['total_cost'] for p in result),
            "total_requests": sum(p['requests'] for p in result)
        }
    
    async def get_model_cost_breakdown(self, days: int = 7) -> Dict[str, Any]:
        """Get cost breakdown by model for the last N days."""
        # This would require a more complex query with model information
        # For now, return placeholder
        return {
            "days": days,
            "models": [],
            "message": "Model breakdown requires model_id in api_usage table"
        }
    
    def _calculate_summary(self, daily_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics from daily data."""
        if not daily_data:
            return {}
        
        total_cost = sum(day['total_cost'] for day in daily_data)
        total_tokens = sum(day['total_tokens'] for day in daily_data)
        total_requests = sum(day['requests'] for day in daily_data)
        total_cache_hits = sum(day['cache_hits'] for day in daily_data)
        
        avg_daily_cost = total_cost / len(daily_data) if daily_data else 0
        avg_cost_per_request = total_cost / total_requests if total_requests else 0
        avg_tokens_per_request = total_tokens / total_requests if total_requests else 0
        cache_hit_rate = total_cache_hits / total_requests if total_requests else 0
        
        # Project monthly cost
        avg_daily_cost_recent = daily_data[0]['total_cost'] if daily_data else 0
        projected_monthly = avg_daily_cost_recent * 30
        
        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "total_requests": total_requests,
            "total_cache_hits": total_cache_hits,
            "avg_daily_cost": avg_daily_cost,
            "avg_cost_per_request": avg_cost_per_request,
            "avg_tokens_per_request": avg_tokens_per_request,
            "cache_hit_rate": cache_hit_rate,
            "projected_monthly_cost": projected_monthly,
            "budget_status": self._check_budget_status(projected_monthly, avg_daily_cost_recent)
        }
    
    def _check_budget_status(self, projected_monthly: float, current_daily: float) -> Dict[str, Any]:
        """Check budget status and return alerts if needed."""
        daily_budget = config.cost_optimization.daily_budget
        monthly_budget = config.cost_optimization.monthly_budget
        alert_threshold = config.cost_optimization.alert_threshold_percent
        
        status = {
            "daily": {
                "budget": daily_budget,
                "current": current_daily,
                "percent_used": (current_daily / daily_budget * 100) if daily_budget > 0 else 0,
                "status": "ok"
            },
            "monthly": {
                "budget": monthly_budget,
                "projected": projected_monthly,
                "percent_projected": (projected_monthly / monthly_budget * 100) if monthly_budget > 0 else 0,
                "status": "ok"
            }
        }
        
        # Check for alerts
        if current_daily >= daily_budget * alert_threshold:
            status["daily"]["status"] = "warning"
        if current_daily >= daily_budget:
            status["daily"]["status"] = "exceeded"
        
        if projected_monthly >= monthly_budget * alert_threshold:
            status["monthly"]["status"] = "warning"
        if projected_monthly >= monthly_budget:
            status["monthly"]["status"] = "exceeded"
        
        return status
    
    # ===== Cache Performance Analysis =====
    
    async def get_cache_performance(self, days: int = 7) -> Dict[str, Any]:
        """Get cache performance metrics."""
        db_costs = await db_service.get_daily_api_costs(days=days)
        
        total_requests = 0
        total_cache_hits = 0
        total_cached_tokens = 0
        total_cost = 0.0
        
        for row in db_costs:
            total_requests += row['request_count'] or 0
            total_cache_hits += row['cache_hits'] or 0
            total_cached_tokens += row['total_cached_tokens'] or 0
            total_cost += float(row['total_cost'] or 0)
        
        cache_hit_rate = total_cache_hits / total_requests if total_requests else 0
        
        # Get cache statistics
        cache_stats = await cache_service.get_cache_stats()
        
        # Estimate cost savings
        # This is a rough estimate - in reality, we'd track cost_saved_usd in semantic_cache
        avg_cost_per_token = total_cost / (total_requests * 1000) if total_requests else 0.0001
        estimated_savings = total_cached_tokens * avg_cost_per_token
        
        return {
            "cache_hit_rate": cache_hit_rate,
            "total_requests": total_requests,
            "cache_hits": total_cache_hits,
            "cached_tokens": total_cached_tokens,
            "estimated_cost_savings_usd": estimated_savings,
            "cache_statistics": cache_stats
        }
    
    # ===== Budget Planning =====
    
    async def get_budget_recommendations(self) -> List[Dict[str, Any]]:
        """Get budget optimization recommendations."""
        recommendations = []
        
        # Get provider costs
        provider_breakdown = await self.get_provider_cost_breakdown(days=30)
        
        # Recommendation 1: Check for expensive providers
        for provider in provider_breakdown.get('providers', []):
            if provider['total_cost'] > 10:  # More than $10 in 30 days
                recommendations.append({
                    "type": "provider_cost",
                    "priority": "medium",
                    "title": f"High cost from provider {provider['provider']}",
                    "description": f"This provider cost ${provider['total_cost']:.2f} in the last 30 days.",
                    "suggestion": "Consider using cheaper alternatives or setting a budget limit."
                })
        
        # Recommendation 2: Check cache performance
        cache_perf = await self.get_cache_performance(days=30)
        if cache_perf['cache_hit_rate'] < 0.3:  # Less than 30% cache hit rate
            recommendations.append({
                "type": "cache_performance",
                "priority": "low",
                "title": "Low cache hit rate",
                "description": f"Cache hit rate is {cache_perf['cache_hit_rate']*100:.1f}%.",
                "suggestion": "Consider optimizing cache TTL or increasing semantic similarity threshold."
            })
        
        # Recommendation 3: Check daily spending patterns
        daily_costs = await self.get_daily_cost_breakdown(days=7)
        max_daily = max((day['total_cost'] for day in daily_costs['data']), default=0)
        
        if max_daily > config.cost_optimization.daily_budget:
            recommendations.append({
                "type": "budget_exceeded",
                "priority": "high",
                "title": "Daily budget exceeded",
                "description": f"Maximum daily cost was ${max_daily:.2f}, exceeding daily budget of ${config.cost_optimization.daily_budget:.2f}.",
                "suggestion": "Consider implementing spending limits or using cheaper models during peak usage."
            })
        
        return recommendations
    
    # ===== Reporting =====
    
    async def generate_cost_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate a comprehensive cost report."""
        daily_breakdown = await self.get_daily_cost_breakdown(days=days)
        provider_breakdown = await self.get_provider_cost_breakdown(days=days)
        cache_performance = await self.get_cache_performance(days=days)
        recommendations = await self.get_budget_recommendations()
        
        return {
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat(),
            "daily_breakdown": daily_breakdown,
            "provider_breakdown": provider_breakdown,
            "cache_performance": cache_performance,
            "recommendations": recommendations,
            "summary": {
                "total_cost": daily_breakdown['summary']['total_cost'],
                "avg_daily_cost": daily_breakdown['summary']['avg_daily_cost'],
                "cache_hit_rate": cache_performance['cache_hit_rate'],
                "estimated_savings": cache_performance['estimated_cost_savings_usd']
            }
        }

# Global cost tracker instance
cost_tracker = CostTracker()

async def initialize_cost_tracker():
    """Initialize the cost tracker."""
    await cost_tracker.initialize()

async def close_cost_tracker():
    """Close the cost tracker."""
    await cost_tracker.close()

if __name__ == "__main__":
    # Test the cost tracker
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    async def test():
        await initialize_cost_tracker()

        # Generate a sample report
        report = await cost_tracker.generate_cost_report(days=7)
        logger.info("Cost Report: %s", json.dumps(report, indent=2, default=str))

        await close_cost_tracker()

    asyncio.run(test())
