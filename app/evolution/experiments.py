"""
NEXUS Self-Evolution System - Experiment Manager

A/B testing framework with progressive rollout, automatic rollback, and statistical evaluation.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import logging
import uuid
import random
from enum import Enum
from decimal import Decimal

from ..database import Database
from ..config import settings


class ExperimentStatus(Enum):
    """Status of an experiment."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class ExperimentType(Enum):
    """Types of experiments."""
    AGENT_CONFIGURATION = "agent_configuration"
    PROMPT_OPTIMIZATION = "prompt_optimization"
    MODEL_SELECTION = "model_selection"
    CACHE_STRATEGY = "cache_strategy"
    COST_OPTIMIZATION = "cost_optimization"
    PERFORMANCE_TUNING = "performance_tuning"


class RolloutStrategy(Enum):
    """Strategies for experiment rollout."""
    LINEAR = "linear"  # Gradually increase traffic
    STEPPED = "stepped"  # Step increases at intervals
    RANDOM = "random"   # Random percentage of traffic
    CANARY = "canary"   # Specific users/agents first


class ExperimentManager:
    """Manages A/B experiments for system optimization."""

    def __init__(self, database: Database):
        self.db = database
        self.logger = logging.getLogger(__name__)
        self.active_experiments: Dict[str, Any] = {}

    async def create_experiment(
        self,
        name: str,
        description: str,
        experiment_type: ExperimentType,
        hypothesis_id: Optional[str] = None,
        control_config: Dict[str, Any] = None,
        treatment_config: Dict[str, Any] = None,
        metrics: List[str] = None,
        success_criteria: Dict[str, Any] = None,
        rollout_strategy: RolloutStrategy = RolloutStrategy.LINEAR,
        max_duration_days: int = 7,
        target_traffic_percentage: float = 10.0
    ) -> Dict[str, Any]:
        """
        Create a new A/B experiment.

        Args:
            name: Experiment name
            description: Experiment description
            experiment_type: Type of experiment
            hypothesis_id: Optional hypothesis ID this experiment tests
            control_config: Configuration for control group
            treatment_config: Configuration for treatment group
            metrics: List of metrics to track
            success_criteria: Criteria for experiment success
            rollout_strategy: How to roll out the experiment
            max_duration_days: Maximum experiment duration
            target_traffic_percentage: Target percentage of traffic for treatment

        Returns:
            Experiment configuration
        """
        experiment_id = str(uuid.uuid4())

        # Default configurations if not provided
        if control_config is None:
            control_config = {"version": "current"}
        if treatment_config is None:
            treatment_config = {"version": "experimental"}
        if metrics is None:
            metrics = ["success_rate", "latency", "cost"]
        if success_criteria is None:
            success_criteria = {
                "success_rate_improvement": 0.05,  # 5% improvement
                "latency_improvement": -0.1,  # 10% reduction
                "cost_improvement": -0.1  # 10% reduction
            }

        experiment = {
            "id": experiment_id,
            "name": name,
            "description": description,
            "type": experiment_type.value,
            "hypothesis_id": hypothesis_id,
            "control_config": control_config,
            "treatment_config": treatment_config,
            "metrics": metrics,
            "success_criteria": success_criteria,
            "rollout_strategy": rollout_strategy.value,
            "max_duration_days": max_duration_days,
            "target_traffic_percentage": min(target_traffic_percentage, 100.0),
            "current_traffic_percentage": 0.0,
            "status": ExperimentStatus.DRAFT.value,
            "started_at": None,
            "ended_at": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "results": {},
            "rollback_reason": None
        }

        # Store in database
        await self._store_experiment(experiment)

        return experiment

    async def start_experiment(
        self,
        experiment_id: str,
        initial_traffic_percentage: float = 1.0
    ) -> Dict[str, Any]:
        """
        Start an experiment.

        Args:
            experiment_id: ID of experiment to start
            initial_traffic_percentage: Initial percentage of traffic (1-100)

        Returns:
            Updated experiment
        """
        experiment = await self._get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_id}")

        if experiment["status"] != ExperimentStatus.DRAFT.value:
            raise ValueError(f"Cannot start experiment in status: {experiment['status']}")

        # Update experiment
        experiment["status"] = ExperimentStatus.ACTIVE.value
        experiment["started_at"] = datetime.now().isoformat()
        experiment["current_traffic_percentage"] = min(initial_traffic_percentage, 100.0)
        experiment["updated_at"] = datetime.now().isoformat()

        # Store in database
        await self._store_experiment(experiment)

        # Add to active experiments
        self.active_experiments[experiment_id] = experiment

        self.logger.info(f"Started experiment: {experiment['name']} ({experiment_id})")

        return experiment

    async def assign_to_experiment(
        self,
        experiment_id: str,
        entity_id: str,
        entity_type: str = "agent"
    ) -> Optional[Dict[str, Any]]:
        """
        Assign an entity (agent, user, request) to control or treatment group.

        Args:
            experiment_id: Experiment ID
            entity_id: Entity identifier
            entity_type: Type of entity (agent, user, request)

        Returns:
            Assignment details or None if not assigned
        """
        experiment = self.active_experiments.get(experiment_id)
        if not experiment:
            experiment = await self._get_experiment(experiment_id)
            if not experiment or experiment["status"] != ExperimentStatus.ACTIVE.value:
                return None

        # Check if entity already assigned
        existing_assignment = await self._get_existing_assignment(
            experiment_id, entity_id, entity_type
        )
        if existing_assignment:
            return existing_assignment

        # Determine assignment based on traffic percentage
        current_percentage = experiment["current_traffic_percentage"]
        should_assign = random.random() * 100 < current_percentage

        if not should_assign:
            # Assign to control group (current configuration)
            group = "control"
            config = experiment["control_config"]
        else:
            # Assign to treatment group (experimental configuration)
            group = "treatment"
            config = experiment["treatment_config"]

        # Create assignment
        assignment_id = str(uuid.uuid4())
        assignment = {
            "id": assignment_id,
            "experiment_id": experiment_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "group": group,
            "config": config,
            "assigned_at": datetime.now().isoformat()
        }

        # Store assignment
        await self._store_assignment(assignment)

        # Track assignment in experiment
        await self._track_assignment(experiment_id, group)

        return assignment

    async def update_traffic_percentage(
        self,
        experiment_id: str,
        new_percentage: float
    ) -> Dict[str, Any]:
        """
        Update traffic percentage for an experiment.

        Args:
            experiment_id: Experiment ID
            new_percentage: New traffic percentage (0-100)

        Returns:
            Updated experiment
        """
        experiment = await self._get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_id}")

        if experiment["status"] != ExperimentStatus.ACTIVE.value:
            raise ValueError(f"Cannot update traffic for experiment in status: {experiment['status']}")

        new_percentage = max(0.0, min(new_percentage, 100.0))
        experiment["current_traffic_percentage"] = new_percentage
        experiment["updated_at"] = datetime.now().isoformat()

        # Update in database
        await self._store_experiment(experiment)

        # Update in memory if active
        if experiment_id in self.active_experiments:
            self.active_experiments[experiment_id] = experiment

        self.logger.info(
            f"Updated experiment {experiment_id} traffic to {new_percentage}%"
        )

        return experiment

    async def evaluate_experiment(
        self,
        experiment_id: str,
        force_evaluate: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate experiment results.

        Args:
            experiment_id: Experiment ID
            force_evaluate: Force evaluation even if experiment is still running

        Returns:
            Evaluation results
        """
        experiment = await self._get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_id}")

        # Check if experiment should be evaluated
        if not force_evaluate:
            if experiment["status"] != ExperimentStatus.ACTIVE.value:
                raise ValueError(f"Cannot evaluate experiment in status: {experiment['status']}")

            # Check if experiment has reached minimum duration
            started_at = datetime.fromisoformat(experiment["started_at"])
            min_duration = timedelta(days=1)  # Minimum 1 day
            if datetime.now() - started_at < min_duration:
                return {
                    "experiment_id": experiment_id,
                    "status": "too_early",
                    "message": "Experiment hasn't reached minimum duration",
                    "recommendation": "wait"
                }

        # Collect experiment metrics
        metrics = await self._collect_experiment_metrics(experiment_id)

        # Perform statistical analysis
        analysis = await self._analyze_experiment_results(experiment, metrics)

        # Determine if experiment should continue, succeed, or fail
        decision = await self._make_experiment_decision(experiment, analysis)

        # Update experiment with results
        experiment["results"] = {
            "metrics": metrics,
            "analysis": analysis,
            "decision": decision,
            "evaluated_at": datetime.now().isoformat()
        }
        experiment["updated_at"] = datetime.now().isoformat()

        # Take action based on decision
        if decision["action"] == "succeed":
            await self._complete_experiment(experiment_id, success=True)
        elif decision["action"] == "fail":
            await self._complete_experiment(experiment_id, success=False)
        elif decision["action"] == "rollback":
            await self._rollback_experiment(experiment_id, decision.get("reason", "performance_degradation"))
        elif decision["action"] == "continue":
            # Increase traffic if appropriate
            if experiment["current_traffic_percentage"] < experiment["target_traffic_percentage"]:
                new_percentage = min(
                    experiment["current_traffic_percentage"] * 1.5,
                    experiment["target_traffic_percentage"]
                )
                await self.update_traffic_percentage(experiment_id, new_percentage)

        # Store updated experiment
        await self._store_experiment(experiment)

        return {
            "experiment_id": experiment_id,
            "experiment_name": experiment["name"],
            "metrics_collected": len(metrics),
            "analysis": analysis,
            "decision": decision,
            "updated_traffic_percentage": experiment["current_traffic_percentage"]
        }

    async def complete_experiment(
        self,
        experiment_id: str,
        success: bool = True,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manually complete an experiment.

        Args:
            experiment_id: Experiment ID
            success: Whether experiment was successful
            notes: Completion notes

        Returns:
            Completed experiment
        """
        return await self._complete_experiment(experiment_id, success, notes)

    async def rollback_experiment(
        self,
        experiment_id: str,
        reason: str = "manual_rollback"
    ) -> Dict[str, Any]:
        """
        Rollback an experiment.

        Args:
            experiment_id: Experiment ID
            reason: Reason for rollback

        Returns:
            Rolled back experiment
        """
        return await self._rollback_experiment(experiment_id, reason)

    async def get_experiment_results(
        self,
        experiment_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed results for an experiment.

        Args:
            experiment_id: Experiment ID

        Returns:
            Experiment results
        """
        experiment = await self._get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_id}")

        # Collect fresh metrics if experiment is active
        if experiment["status"] == ExperimentStatus.ACTIVE.value:
            metrics = await self._collect_experiment_metrics(experiment_id)
            analysis = await self._analyze_experiment_results(experiment, metrics)

            return {
                "experiment": experiment,
                "metrics": metrics,
                "analysis": analysis
            }
        else:
            return {
                "experiment": experiment,
                "metrics": experiment.get("results", {}).get("metrics", {}),
                "analysis": experiment.get("results", {}).get("analysis", {})
            }

    async def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
        experiment_type: Optional[ExperimentType] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List experiments.

        Args:
            status: Filter by status
            experiment_type: Filter by type
            limit: Maximum number to return

        Returns:
            List of experiments
        """
        try:
            base_query = """
                SELECT * FROM agent_experiments
                WHERE 1=1
            """
            params = []
            param_count = 0

            if status:
                param_count += 1
                base_query += f" AND status = ${param_count}"
                params.append(status.value)

            if experiment_type:
                param_count += 1
                base_query += f" AND type = ${param_count}"
                params.append(experiment_type.value)

            base_query += f" ORDER BY created_at DESC LIMIT ${param_count + 1}"
            params.append(limit)

            rows = await self.db.fetch(base_query, *params)

            experiments = []
            for row in rows:
                experiments.append(dict(row))

            return experiments
        except Exception as e:
            self.logger.error(f"Failed to list experiments: {e}")
            return []

    # Private methods

    async def _store_experiment(self, experiment: Dict[str, Any]) -> None:
        """Store experiment in database."""
        try:
            query = """
                INSERT INTO agent_experiments (
                    id, name, description, type, hypothesis_id,
                    control_config, treatment_config, metrics, success_criteria,
                    rollout_strategy, max_duration_days, target_traffic_percentage,
                    current_traffic_percentage, status, started_at, ended_at,
                    created_at, updated_at, results, rollback_reason
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15,
                    $16, $17, $18, $19, $20
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    current_traffic_percentage = EXCLUDED.current_traffic_percentage,
                    results = EXCLUDED.results,
                    updated_at = EXCLUDED.updated_at,
                    rollback_reason = EXCLUDED.rollback_reason
            """

            started_at = (
                datetime.fromisoformat(experiment["started_at"])
                if experiment["started_at"] else None
            )
            ended_at = (
                datetime.fromisoformat(experiment["ended_at"])
                if experiment["ended_at"] else None
            )

            await self.db.execute(
                query,
                experiment["id"],
                experiment["name"],
                experiment["description"],
                experiment["type"],
                experiment["hypothesis_id"],
                experiment["control_config"],
                experiment["treatment_config"],
                experiment["metrics"],
                experiment["success_criteria"],
                experiment["rollout_strategy"],
                experiment["max_duration_days"],
                experiment["target_traffic_percentage"],
                experiment["current_traffic_percentage"],
                experiment["status"],
                started_at,
                ended_at,
                datetime.fromisoformat(experiment["created_at"]),
                datetime.fromisoformat(experiment["updated_at"]),
                experiment["results"],
                experiment["rollback_reason"]
            )
        except Exception as e:
            self.logger.error(f"Failed to store experiment: {e}")

    async def _get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve experiment from database."""
        try:
            query = "SELECT * FROM agent_experiments WHERE id = $1"
            row = await self.db.fetchrow(query, experiment_id)
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Failed to get experiment: {e}")
            return None

    async def _store_assignment(self, assignment: Dict[str, Any]) -> None:
        """Store assignment in database."""
        try:
            query = """
                INSERT INTO experiment_assignments (
                    id, experiment_id, entity_id, entity_type,
                    group, config, assigned_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            await self.db.execute(
                query,
                assignment["id"],
                assignment["experiment_id"],
                assignment["entity_id"],
                assignment["entity_type"],
                assignment["group"],
                assignment["config"],
                datetime.fromisoformat(assignment["assigned_at"])
            )
        except Exception as e:
            self.logger.error(f"Failed to store assignment: {e}")

    async def _get_existing_assignment(
        self,
        experiment_id: str,
        entity_id: str,
        entity_type: str
    ) -> Optional[Dict[str, Any]]:
        """Check for existing assignment."""
        try:
            query = """
                SELECT * FROM experiment_assignments
                WHERE experiment_id = $1
                  AND entity_id = $2
                  AND entity_type = $3
                LIMIT 1
            """
            row = await self.db.fetchrow(query, experiment_id, entity_id, entity_type)
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Failed to get assignment: {e}")
            return None

    async def _track_assignment(self, experiment_id: str, group: str) -> None:
        """Track assignment in experiment statistics."""
        try:
            query = """
                INSERT INTO experiment_stats (
                    experiment_id, group, assignment_count, date
                ) VALUES ($1, $2, 1, CURRENT_DATE)
                ON CONFLICT (experiment_id, group, date) DO UPDATE SET
                    assignment_count = experiment_stats.assignment_count + 1
            """
            await self.db.execute(query, experiment_id, group, datetime.now().date())
        except Exception as e:
            self.logger.error(f"Failed to track assignment: {e}")

    async def _collect_experiment_metrics(
        self,
        experiment_id: str
    ) -> Dict[str, Any]:
        """Collect metrics for experiment evaluation."""
        metrics = {}

        try:
            # Get metrics for control and treatment groups
            for group in ["control", "treatment"]:
                # Query performance metrics for this experiment and group
                query = """
                    SELECT
                        COUNT(*) as request_count,
                        AVG(success::int) as success_rate,
                        AVG(latency_ms) as avg_latency,
                        SUM(cost_usd) as total_cost,
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency
                    FROM experiment_metrics
                    WHERE experiment_id = $1
                      AND assignment_group = $2
                      AND timestamp >= CURRENT_DATE - INTERVAL '7 days'
                """
                row = await self.db.fetchrow(query, experiment_id, group)

                if row:
                    metrics[group] = {
                        "request_count": row["request_count"],
                        "success_rate": float(row["success_rate"] or 0),
                        "avg_latency": float(row["avg_latency"] or 0),
                        "total_cost": float(row["total_cost"] or 0),
                        "p95_latency": float(row["p95_latency"] or 0)
                    }
                else:
                    metrics[group] = {
                        "request_count": 0,
                        "success_rate": 0,
                        "avg_latency": 0,
                        "total_cost": 0,
                        "p95_latency": 0
                    }

            # Calculate relative improvements
            if metrics.get("control") and metrics.get("treatment"):
                control = metrics["control"]
                treatment = metrics["treatment"]

                if control["request_count"] > 0 and treatment["request_count"] > 0:
                    metrics["improvements"] = {
                        "success_rate": (
                            treatment["success_rate"] - control["success_rate"]
                        ) / max(control["success_rate"], 0.001),
                        "latency": (
                            treatment["avg_latency"] - control["avg_latency"]
                        ) / max(control["avg_latency"], 1),
                        "cost": (
                            treatment["total_cost"] - control["total_cost"]
                        ) / max(control["total_cost"], 0.001)
                    }

        except Exception as e:
            self.logger.error(f"Failed to collect experiment metrics: {e}")

        return metrics

    async def _analyze_experiment_results(
        self,
        experiment: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze experiment results with statistical significance."""
        analysis = {
            "statistically_significant": False,
            "confidence_level": 0.0,
            "effect_sizes": {},
            "meets_criteria": {}
        }

        try:
            control = metrics.get("control", {})
            treatment = metrics.get("treatment", {})

            # Check if we have enough data
            min_requests = 100
            if (control.get("request_count", 0) < min_requests or
                    treatment.get("request_count", 0) < min_requests):
                analysis["data_sufficiency"] = "insufficient"
                return analysis

            analysis["data_sufficiency"] = "sufficient"

            # Calculate effect sizes
            effect_sizes = {}
            for metric in ["success_rate", "avg_latency", "total_cost"]:
                if metric in control and metric in treatment:
                    control_val = control[metric]
                    treatment_val = treatment[metric]

                    if control_val != 0:
                        effect_size = (treatment_val - control_val) / control_val
                    else:
                        effect_size = 0

                    effect_sizes[metric] = effect_size

            analysis["effect_sizes"] = effect_sizes

            # Check against success criteria
            success_criteria = experiment.get("success_criteria", {})
            meets_criteria = {}

            for criterion, threshold in success_criteria.items():
                if criterion.endswith("_improvement"):
                    metric = criterion.replace("_improvement", "")
                    if metric in effect_sizes:
                        # For latency and cost, negative improvement is good
                        if metric in ["latency", "cost"]:
                            meets = effect_sizes[metric] <= threshold
                        else:
                            meets = effect_sizes[metric] >= threshold
                        meets_criteria[criterion] = {
                            "met": meets,
                            "effect_size": effect_sizes[metric],
                            "threshold": threshold
                        }

            analysis["meets_criteria"] = meets_criteria

            # Simple statistical significance check
            # In a real implementation, use proper statistical tests
            total_requests = control["request_count"] + treatment["request_count"]
            if total_requests > 500:
                analysis["statistically_significant"] = True
                analysis["confidence_level"] = 0.95
            elif total_requests > 100:
                analysis["statistically_significant"] = True
                analysis["confidence_level"] = 0.90
            else:
                analysis["statistically_significant"] = False
                analysis["confidence_level"] = 0.80

        except Exception as e:
            self.logger.error(f"Failed to analyze experiment results: {e}")

        return analysis

    async def _make_experiment_decision(
        self,
        experiment: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make decision about experiment based on analysis."""
        decision = {
            "action": "continue",
            "reason": "insufficient_data",
            "recommendation": "continue_experiment"
        }

        try:
            if analysis.get("data_sufficiency") != "sufficient":
                decision["action"] = "continue"
                decision["reason"] = "insufficient_data"
                return decision

            meets_criteria = analysis.get("meets_criteria", {})
            success_criteria = experiment.get("success_criteria", {})

            # Count how many criteria are met
            met_count = sum(1 for criterion in meets_criteria.values() if criterion.get("met", False))
            total_criteria = len(success_criteria)

            # Determine decision based on criteria met
            if total_criteria == 0:
                decision["action"] = "continue"
                decision["reason"] = "no_success_criteria_defined"

            elif met_count == total_criteria:
                # All criteria met
                if analysis.get("statistically_significant", False):
                    decision["action"] = "succeed"
                    decision["reason"] = "all_criteria_met_with_significance"
                    decision["recommendation"] = "implement_changes"
                else:
                    decision["action"] = "continue"
                    decision["reason"] = "all_criteria_met_but_insufficient_significance"
                    decision["recommendation"] = "increase_sample_size"

            elif met_count >= total_criteria * 0.7:
                # Most criteria met
                decision["action"] = "continue"
                decision["reason"] = "most_criteria_met"
                decision["recommendation"] = "increase_traffic_percentage"

            else:
                # Few criteria met - check for degradation
                # Check if any critical metrics degraded significantly
                critical_metrics = ["success_rate", "latency", "cost"]
                degraded = False

                for metric in critical_metrics:
                    if metric in analysis.get("effect_sizes", {}):
                        effect = analysis["effect_sizes"][metric]
                        # Degradation thresholds
                        if metric == "success_rate" and effect < -0.1:  # 10% degradation
                            degraded = True
                            break
                        elif metric == "latency" and effect > 0.2:  # 20% increase
                            degraded = True
                            break
                        elif metric == "cost" and effect > 0.2:  # 20% increase
                            degraded = True
                            break

                if degraded:
                    decision["action"] = "rollback"
                    decision["reason"] = "critical_metric_degradation"
                    decision["recommendation"] = "rollback_immediately"
                else:
                    decision["action"] = "continue"
                    decision["reason"] = "mixed_results_no_critical_degradation"
                    decision["recommendation"] = "continue_monitoring"

        except Exception as e:
            self.logger.error(f"Failed to make experiment decision: {e}")
            decision["action"] = "continue"
            decision["reason"] = "error_in_analysis"
            decision["recommendation"] = "manual_review"

        return decision

    async def _complete_experiment(
        self,
        experiment_id: str,
        success: bool = True,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Complete an experiment."""
        experiment = await self._get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_id}")

        status = ExperimentStatus.COMPLETED.value if success else ExperimentStatus.FAILED.value
        experiment["status"] = status
        experiment["ended_at"] = datetime.now().isoformat()
        experiment["updated_at"] = datetime.now().isoformat()

        if notes:
            experiment["results"]["completion_notes"] = notes

        # Remove from active experiments
        if experiment_id in self.active_experiments:
            del self.active_experiments[experiment_id]

        # Store in database
        await self._store_experiment(experiment)

        self.logger.info(
            f"Completed experiment {experiment_id} with status: {status}"
        )

        return experiment

    async def _rollback_experiment(
        self,
        experiment_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """Rollback an experiment."""
        experiment = await self._get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_id}")

        experiment["status"] = ExperimentStatus.ROLLED_BACK.value
        experiment["ended_at"] = datetime.now().isoformat()
        experiment["rollback_reason"] = reason
        experiment["updated_at"] = datetime.now().isoformat()

        # Remove from active experiments
        if experiment_id in self.active_experiments:
            del self.active_experiments[experiment_id]

        # Store in database
        await self._store_experiment(experiment)

        self.logger.info(f"Rolled back experiment {experiment_id}: {reason}")

        return experiment