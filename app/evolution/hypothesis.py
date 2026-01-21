"""
NEXUS Self-Evolution System - Hypothesis Generator

Generates improvement hypotheses based on performance analysis and bottlenecks.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
import uuid
from enum import Enum

from ..database import Database
from ..config import settings
from .analyzer import PerformanceAnalyzer, BottleneckSeverity


class HypothesisType(Enum):
    """Types of improvement hypotheses."""
    CODE_OPTIMIZATION = "code_optimization"
    PROMPT_IMPROVEMENT = "prompt_improvement"
    CONFIGURATION_TUNING = "configuration_tuning"
    ARCHITECTURE_CHANGE = "architecture_change"
    RESOURCE_ALLOCATION = "resource_allocation"
    COST_OPTIMIZATION = "cost_optimization"
    FEATURE_ADDITION = "feature_addition"


class HypothesisStatus(Enum):
    """Status of a hypothesis."""
    PROPOSED = "proposed"
    VALIDATED = "validated"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    TESTING = "testing"


class HypothesisGenerator:
    """Generates improvement hypotheses based on performance analysis."""

    def __init__(self, database: Database, analyzer: PerformanceAnalyzer):
        self.db = database
        self.analyzer = analyzer
        self.logger = logging.getLogger(__name__)

    async def generate_hypotheses(
        self,
        analysis_period_days: int = 7,
        max_hypotheses: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate improvement hypotheses based on recent performance analysis.

        Args:
            analysis_period_days: Number of days to analyze for hypothesis generation
            max_hypotheses: Maximum number of hypotheses to generate

        Returns:
            List of hypothesis dictionaries
        """
        # Analyze recent performance
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=analysis_period_days)

        analysis = await self.analyzer.analyze_period(start_date, end_date)

        hypotheses = []

        # Generate hypotheses from bottlenecks
        bottlenecks = analysis.get("bottlenecks", [])
        for bottleneck in bottlenecks[:max_hypotheses]:
            hypothesis = await self._generate_hypothesis_from_bottleneck(bottleneck, analysis)
            if hypothesis:
                hypotheses.append(hypothesis)

        # Generate hypotheses from trends
        trends = analysis.get("trends", [])
        for trend in trends:
            if len(hypotheses) >= max_hypotheses:
                break

            hypothesis = await self._generate_hypothesis_from_trend(trend, analysis)
            if hypothesis:
                hypotheses.append(hypothesis)

        # Generate cost optimization hypotheses
        cost_data = analysis.get("metrics", {}).get("cost", {})
        if cost_data.get("data_available", False):
            cost_hypotheses = await self._generate_cost_hypotheses(cost_data, analysis)
            hypotheses.extend(cost_hypotheses[:max_hypotheses - len(hypotheses)])

        # Store hypotheses in database
        for hypothesis in hypotheses:
            await self._store_hypothesis(hypothesis)

        return hypotheses

    async def _generate_hypothesis_from_bottleneck(
        self,
        bottleneck: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate hypothesis from a detected bottleneck."""
        metric = bottleneck.get("metric", "")
        severity = bottleneck.get("severity", "")
        value = bottleneck.get("value", 0)
        threshold = bottleneck.get("threshold", 0)

        # Map bottleneck types to hypothesis types
        hypothesis_type_map = {
            "success_rate": HypothesisType.PROMPT_IMPROVEMENT,
            "latency": HypothesisType.CODE_OPTIMIZATION,
            "cost": HypothesisType.COST_OPTIMIZATION,
            "error_rate": HypothesisType.CODE_OPTIMIZATION,
            "cost_concentration": HypothesisType.CONFIGURATION_TUNING,
            "cost_spike": HypothesisType.RESOURCE_ALLOCATION
        }

        hypothesis_type = hypothesis_type_map.get(metric, HypothesisType.CODE_OPTIMIZATION)

        # Generate hypothesis based on metric
        if metric == "success_rate":
            agent_name = bottleneck.get("agent_name", "unknown agent")
            return {
                "id": str(uuid.uuid4()),
                "type": hypothesis_type.value,
                "title": f"Improve success rate for {agent_name}",
                "description": f"Agent {agent_name} has success rate of {value:.2%}, below threshold of {threshold:.2%}. Hypothesis: Refine agent prompts or improve error handling.",
                "rationale": f"Low success rate indicates potential issues with agent logic, prompt quality, or error handling.",
                "expected_impact": "high" if severity == "high" or severity == "critical" else "medium",
                "implementation_complexity": "medium",
                "estimated_effort_hours": 4,
                "risk_level": "low",
                "metrics_to_monitor": ["success_rate", "error_rate", "latency"],
                "validation_criteria": f"Success rate improves to at least {threshold:.2%}",
                "status": HypothesisStatus.PROPOSED.value,
                "created_at": datetime.now().isoformat(),
                "related_bottleneck": bottleneck
            }

        elif metric == "latency":
            agent_or_endpoint = bottleneck.get("agent_name") or bottleneck.get("endpoint", "unknown")
            return {
                "id": str(uuid.uuid4()),
                "type": hypothesis_type.value,
                "title": f"Reduce latency for {agent_or_endpoint}",
                "description": f"{agent_or_endpoint} has average latency of {value:.0f}ms, exceeding threshold of {threshold:.0f}ms. Hypothesis: Optimize code, add caching, or parallelize operations.",
                "rationale": "High latency impacts user experience and system throughput.",
                "expected_impact": "medium",
                "implementation_complexity": "medium",
                "estimated_effort_hours": 8,
                "risk_level": "medium",
                "metrics_to_monitor": ["latency", "throughput", "error_rate"],
                "validation_criteria": f"Latency reduces below {threshold:.0f}ms",
                "status": HypothesisStatus.PROPOSED.value,
                "created_at": datetime.now().isoformat(),
                "related_bottleneck": bottleneck
            }

        elif metric == "cost":
            agent_name = bottleneck.get("agent_name", "unknown agent")
            return {
                "id": str(uuid.uuid4()),
                "type": hypothesis_type.value,
                "title": f"Reduce costs for {agent_name}",
                "description": f"Agent {agent_name} costs ${value:.2f} per day, exceeding threshold of ${threshold:.2f}. Hypothesis: Implement cost optimization strategies like caching, model switching, or request batching.",
                "rationale": "High costs may indicate inefficient resource usage or suboptimal model selection.",
                "expected_impact": "high",
                "implementation_complexity": "low",
                "estimated_effort_hours": 2,
                "risk_level": "low",
                "metrics_to_monitor": ["cost", "success_rate", "latency"],
                "validation_criteria": f"Daily cost reduces below ${threshold:.2f}",
                "status": HypothesisStatus.PROPOSED.value,
                "created_at": datetime.now().isoformat(),
                "related_bottleneck": bottleneck
            }

        elif metric == "cost_concentration":
            provider = bottleneck.get("provider", "unknown")
            percentage = bottleneck.get("percentage", 0)
            return {
                "id": str(uuid.uuid4()),
                "type": hypothesis_type.value,
                "title": f"Diversify from {provider} provider",
                "description": f"{provider} accounts for {percentage:.1%} of total API costs. Hypothesis: Distribute requests across multiple providers to reduce dependency and potentially lower costs.",
                "rationale": "Provider concentration creates dependency risk and may miss cost optimization opportunities.",
                "expected_impact": "medium",
                "implementation_complexity": "low",
                "estimated_effort_hours": 3,
                "risk_level": "low",
                "metrics_to_monitor": ["cost_by_provider", "success_rate", "latency"],
                "validation_criteria": f"No single provider accounts for more than 50% of costs",
                "status": HypothesisStatus.PROPOSED.value,
                "created_at": datetime.now().isoformat(),
                "related_bottleneck": bottleneck
            }

        return None

    async def _generate_hypothesis_from_trend(
        self,
        trend: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate hypothesis from performance trend."""
        direction = trend.get("direction", "")
        metric = trend.get("metric", "")

        if direction != "degrading":
            return None

        # Generate hypothesis for degrading trends
        if metric == "agent_performance":
            return {
                "id": str(uuid.uuid4()),
                "type": HypothesisType.CODE_OPTIMIZATION.value,
                "title": "Address degrading agent performance trend",
                "description": f"Overall agent performance is trending negatively. Hypothesis: Investigate root causes and implement improvements.",
                "rationale": "Sustained degradation indicates systemic issues requiring intervention.",
                "expected_impact": "high",
                "implementation_complexity": "high",
                "estimated_effort_hours": 16,
                "risk_level": "medium",
                "metrics_to_monitor": ["success_rate", "latency", "error_rate"],
                "validation_criteria": "Performance trend stabilizes or improves",
                "status": HypothesisStatus.PROPOSED.value,
                "created_at": datetime.now().isoformat(),
                "related_trend": trend
            }

        elif metric == "cost":
            return {
                "id": str(uuid.uuid4()),
                "type": HypothesisType.COST_OPTIMIZATION.value,
                "title": "Address increasing cost trend",
                "description": "System costs are trending upward. Hypothesis: Implement cost control measures and optimization strategies.",
                "rationale": "Unchecked cost increases may exceed budget constraints.",
                "expected_impact": "high",
                "implementation_complexity": "medium",
                "estimated_effort_hours": 8,
                "risk_level": "low",
                "metrics_to_monitor": ["daily_cost", "cost_by_provider", "request_volume"],
                "validation_criteria": "Cost trend stabilizes or reverses",
                "status": HypothesisStatus.PROPOSED.value,
                "created_at": datetime.now().isoformat(),
                "related_trend": trend
            }

        return None

    async def _generate_cost_hypotheses(
        self,
        cost_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate cost optimization hypotheses."""
        hypotheses = []

        total_cost = cost_data.get("total_cost_usd", 0)
        avg_daily_cost = cost_data.get("avg_daily_cost_usd", 0)

        # Generate hypothesis if costs are high
        if avg_daily_cost > 1.0:  # More than $1 per day
            hypotheses.append({
                "id": str(uuid.uuid4()),
                "type": HypothesisType.COST_OPTIMIZATION.value,
                "title": "Implement aggressive cost optimization",
                "description": f"Average daily cost of ${avg_daily_cost:.2f} exceeds threshold. Hypothesis: Implement semantic caching, request batching, and intelligent model routing.",
                "rationale": "High daily costs indicate significant optimization opportunities.",
                "expected_impact": "high",
                "implementation_complexity": "medium",
                "estimated_effort_hours": 12,
                "risk_level": "low",
                "metrics_to_monitor": ["daily_cost", "cache_hit_rate", "model_distribution"],
                "validation_criteria": "Daily cost reduces by at least 30%",
                "status": HypothesisStatus.PROPOSED.value,
                "created_at": datetime.now().isoformat()
            })

        # Check for provider distribution
        api_usage_data = analysis.get("metrics", {}).get("api_usage", {})
        if api_usage_data.get("data_available", False):
            providers = api_usage_data.get("providers", {})
            if len(providers) == 1:
                provider = list(providers.keys())[0]
                hypotheses.append({
                    "id": str(uuid.uuid4()),
                    "type": HypothesisType.CONFIGURATION_TUNING.value,
                    "title": f"Add backup provider to {provider}",
                    "description": f"All API requests go to {provider}. Hypothesis: Add fallback provider for redundancy and potential cost savings.",
                    "rationale": "Single provider creates dependency risk and misses competitive pricing.",
                    "expected_impact": "medium",
                    "implementation_complexity": "low",
                    "estimated_effort_hours": 4,
                    "risk_level": "low",
                    "metrics_to_monitor": ["provider_distribution", "success_rate", "cost"],
                    "validation_criteria": "At least 2 providers receive regular requests",
                    "status": HypothesisStatus.PROPOSED.value,
                    "created_at": datetime.now().isoformat()
                })

        return hypotheses

    async def _store_hypothesis(self, hypothesis: Dict[str, Any]) -> None:
        """Store hypothesis in database."""
        try:
            query = """
                INSERT INTO evolution_hypotheses (
                    id, type, title, description, rationale,
                    expected_impact, implementation_complexity, estimated_effort_hours,
                    risk_level, metrics_to_monitor, validation_criteria, status,
                    created_at, metadata
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9, $10, $11, $12,
                    $13, $14
                )
                ON CONFLICT (id) DO UPDATE SET
                    type = EXCLUDED.type,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
            """

            metadata = {
                "related_bottleneck": hypothesis.get("related_bottleneck"),
                "related_trend": hypothesis.get("related_trend")
            }

            await self.db.execute(
                query,
                hypothesis["id"],
                hypothesis["type"],
                hypothesis["title"],
                hypothesis["description"],
                hypothesis["rationale"],
                hypothesis["expected_impact"],
                hypothesis["implementation_complexity"],
                hypothesis["estimated_effort_hours"],
                hypothesis["risk_level"],
                hypothesis["metrics_to_monitor"],
                hypothesis["validation_criteria"],
                hypothesis["status"],
                datetime.fromisoformat(hypothesis["created_at"]),
                metadata
            )
        except Exception as e:
            self.logger.error(f"Failed to store hypothesis: {e}")

    async def get_hypotheses(
        self,
        status: Optional[HypothesisStatus] = None,
        hypothesis_type: Optional[HypothesisType] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve hypotheses from database."""
        try:
            base_query = """
                SELECT * FROM evolution_hypotheses
                WHERE 1=1
            """
            params = []
            param_count = 0

            if status:
                param_count += 1
                base_query += f" AND status = ${param_count}"
                params.append(status.value)

            if hypothesis_type:
                param_count += 1
                base_query += f" AND type = ${param_count}"
                params.append(hypothesis_type.value)

            base_query += f" ORDER BY created_at DESC LIMIT ${param_count + 1}"
            params.append(limit)

            rows = await self.db.fetch(base_query, *params)

            hypotheses = []
            for row in rows:
                hypotheses.append(dict(row))

            return hypotheses
        except Exception as e:
            self.logger.error(f"Failed to retrieve hypotheses: {e}")
            return []

    async def update_hypothesis_status(
        self,
        hypothesis_id: str,
        status: HypothesisStatus,
        notes: Optional[str] = None
    ) -> bool:
        """Update hypothesis status."""
        try:
            query = """
                UPDATE evolution_hypotheses
                SET status = $1,
                    updated_at = CURRENT_TIMESTAMP,
                    status_notes = COALESCE($2, status_notes)
                WHERE id = $3
            """
            await self.db.execute(query, status.value, notes, hypothesis_id)
            return True
        except Exception as e:
            self.logger.error(f"Failed to update hypothesis status: {e}")
            return False

    async def evaluate_hypothesis_feasibility(
        self,
        hypothesis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate feasibility of implementing a hypothesis."""
        complexity = hypothesis.get("implementation_complexity", "medium")
        effort_hours = hypothesis.get("estimated_effort_hours", 8)
        risk_level = hypothesis.get("risk_level", "medium")
        expected_impact = hypothesis.get("expected_impact", "medium")

        # Simple feasibility scoring
        feasibility_score = 0

        # Complexity scoring (lower is better)
        complexity_scores = {
            "low": 3,
            "medium": 2,
            "high": 1
        }

        # Effort scoring (lower is better)
        if effort_hours <= 4:
            effort_score = 3
        elif effort_hours <= 8:
            effort_score = 2
        else:
            effort_score = 1

        # Risk scoring (lower is better)
        risk_scores = {
            "low": 3,
            "medium": 2,
            "high": 1
        }

        # Impact scoring (higher is better)
        impact_scores = {
            "low": 1,
            "medium": 2,
            "high": 3
        }

        feasibility_score = (
            complexity_scores.get(complexity, 1) +
            effort_score +
            risk_scores.get(risk_level, 1) +
            impact_scores.get(expected_impact, 1)
        ) / 4

        # Determine feasibility category
        if feasibility_score >= 2.5:
            feasibility = "high"
        elif feasibility_score >= 2.0:
            feasibility = "medium"
        else:
            feasibility = "low"

        return {
            "feasibility_score": feasibility_score,
            "feasibility": feasibility,
            "complexity_score": complexity_scores.get(complexity, 1),
            "effort_score": effort_score,
            "risk_score": risk_scores.get(risk_level, 1),
            "impact_score": impact_scores.get(expected_impact, 1),
            "recommendation": "Implement" if feasibility == "high" else "Evaluate further"
        }

    async def prioritize_hypotheses(
        self,
        hypotheses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prioritize hypotheses based on feasibility and impact."""
        prioritized = []

        for hypothesis in hypotheses:
            feasibility = await self.evaluate_hypothesis_feasibility(hypothesis)
            impact = hypothesis.get("expected_impact", "medium")

            # Calculate priority score
            impact_scores = {"low": 1, "medium": 2, "high": 3}
            impact_score = impact_scores.get(impact, 1)

            priority_score = feasibility["feasibility_score"] * impact_score

            prioritized.append({
                **hypothesis,
                "feasibility_analysis": feasibility,
                "priority_score": priority_score
            })

        # Sort by priority score (descending)
        prioritized.sort(key=lambda x: x["priority_score"], reverse=True)

        return prioritized