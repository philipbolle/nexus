"""
NEXUS Self-Evolution System API Endpoints

Automated system improvement through performance analysis, bottleneck detection,
hypothesis generation, A/B testing, and code refactoring.
"""

from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging

from ..database import db, get_db, Database
from ..config import settings

# Import evolution components
from ..evolution.analyzer import PerformanceAnalyzer, MetricType
from ..evolution.hypothesis import HypothesisGenerator, HypothesisStatus, HypothesisType
from ..evolution.experiments import ExperimentManager, ExperimentType, RolloutStrategy
from ..evolution.refactor import CodeRefactor

router = APIRouter(tags=["evolution"])
logger = logging.getLogger(__name__)


# ============ Performance Analysis Endpoints ============

@router.post("/evolution/analyze/performance")
async def analyze_performance(
    days_back: int = 7,
    metric_types: Optional[List[str]] = None,
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """
    Trigger performance analysis for the system.

    Analyzes agent performance, API usage, system metrics, and cost data
    to identify bottlenecks and improvement opportunities.
    """
    try:
        performance_analyzer = PerformanceAnalyzer(database=db)

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        # Convert metric type strings to enums if provided
        metric_type_enums = None
        if metric_types:
            metric_type_enums = []
            for mt in metric_types:
                try:
                    metric_type_enums.append(MetricType(mt))
                except ValueError as e:
                    logger.debug(f"Ignoring invalid metric type '{mt}': {e}")
            if not metric_type_enums:
                metric_type_enums = None

        result = await performance_analyzer.analyze_period(
            start_date=start_date,
            end_date=end_date,
            metric_types=metric_type_enums
        )

        # Store analysis in evolution_analysis table (optional)
        # For now, just return the result

        return {
            "success": True,
            "period": result.get("period", {}),
            "bottlenecks_found": len(result.get("bottlenecks", [])),
            "recommendations": len(result.get("recommendations", [])),
            "trends": len(result.get("trends", []))
        }
    except Exception as e:
        logger.error(f"Performance analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Performance analysis failed: {str(e)}")


@router.get("/evolution/analysis/recent")
async def get_recent_analysis(
    limit: int = 10,
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get recent performance analysis results from evolution_analysis table.
    """
    try:
        query = """
            SELECT * FROM evolution_analysis
            ORDER BY created_at DESC
            LIMIT $1
        """
        analyses = await db.fetch_all(query, limit)

        return {
            "success": True,
            "analyses": analyses,
            "count": len(analyses)
        }
    except Exception as e:
        logger.error(f"Failed to fetch recent analyses: {e}", exc_info=True)
        # If table doesn't exist yet, return empty list
        return {
            "success": True,
            "analyses": [],
            "count": 0
        }


# ============ Hypothesis Generation Endpoints ============

@router.post("/evolution/hypotheses/generate")
async def generate_hypotheses(
    analysis_period_days: int = 7,
    max_hypotheses: int = 5,
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate improvement hypotheses based on recent performance analysis.
    """
    try:
        # Initialize analyzer and hypothesis generator
        performance_analyzer = PerformanceAnalyzer(database=db)
        hypothesis_generator = HypothesisGenerator(database=db, analyzer=performance_analyzer)

        hypotheses = await hypothesis_generator.generate_hypotheses(
            analysis_period_days=analysis_period_days,
            max_hypotheses=max_hypotheses
        )

        return {
            "success": True,
            "hypotheses": hypotheses,
            "count": len(hypotheses)
        }
    except Exception as e:
        logger.error(f"Hypothesis generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hypothesis generation failed: {str(e)}")


@router.get("/evolution/hypotheses")
async def get_hypotheses(
    status: Optional[str] = None,
    hypothesis_type: Optional[str] = None,
    limit: int = 20,
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get existing hypotheses with optional filtering.
    """
    try:
        performance_analyzer = PerformanceAnalyzer(database=db)
        hypothesis_generator = HypothesisGenerator(database=db, analyzer=performance_analyzer)

        # Convert string status to enum if provided
        status_enum = None
        if status:
            try:
                status_enum = HypothesisStatus(status)
            except ValueError as e:
                logger.debug(f"Ignoring invalid hypothesis status '{status}': {e}")

        # Convert string type to enum if provided
        type_enum = None
        if hypothesis_type:
            try:
                type_enum = HypothesisType(hypothesis_type)
            except ValueError as e:
                logger.debug(f"Ignoring invalid hypothesis type '{hypothesis_type}': {e}")

        hypotheses = await hypothesis_generator.get_hypotheses(
            status=status_enum,
            hypothesis_type=type_enum,
            limit=limit
        )

        return {
            "success": True,
            "hypotheses": hypotheses,
            "count": len(hypotheses)
        }
    except Exception as e:
        logger.error(f"Failed to fetch hypotheses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch hypotheses: {str(e)}")


# ============ Experiment Management Endpoints ============

@router.post("/evolution/experiments")
async def create_experiment(
    hypothesis_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    experiment_type: str = "agent_configuration",
    rollout_percentage: float = 10.0,
    duration_hours: int = 24,
    control_config: Optional[Dict[str, Any]] = None,
    treatment_config: Optional[Dict[str, Any]] = None,
    metrics: Optional[List[str]] = None,
    success_criteria: Optional[Dict[str, Any]] = None,
    rollout_strategy: str = "linear",
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a new A/B experiment to test a hypothesis.
    """
    try:
        experiment_manager = ExperimentManager(database=db)

        # Generate name if not provided
        if not name:
            name = f"Experiment for hypothesis {hypothesis_id[:8]}..."
        if not description:
            description = f"A/B test for hypothesis {hypothesis_id}"

        # Convert string enums to enum values
        try:
            experiment_type_enum = ExperimentType(experiment_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid experiment_type: {experiment_type}")

        try:
            rollout_strategy_enum = RolloutStrategy(rollout_strategy)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid rollout_strategy: {rollout_strategy}")

        # Convert duration_hours to max_duration_days (approximate)
        max_duration_days = max(1, duration_hours // 24)

        experiment = await experiment_manager.create_experiment(
            name=name,
            description=description,
            experiment_type=experiment_type_enum,
            hypothesis_id=hypothesis_id,
            control_config=control_config,
            treatment_config=treatment_config,
            metrics=metrics,
            success_criteria=success_criteria,
            rollout_strategy=rollout_strategy_enum,
            max_duration_days=max_duration_days,
            target_traffic_percentage=rollout_percentage
        )

        return {
            "success": True,
            "experiment": experiment
        }
    except Exception as e:
        logger.error(f"Experiment creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Experiment creation failed: {str(e)}")


# @router.get("/evolution/experiments")
# async def get_experiments(
#     status: Optional[str] = None,
#     limit: int = 20,
#     db: Database = Depends(get_db)
# ) -> Dict[str, Any]:
#     """
#     Get experiments with optional filtering.
#     """
#     try:
#         # Validate limit
#         if limit <= 0 or limit > 100:
#             limit = 20
#
#         # Build query with proper parameter numbering
#         base_query = "SELECT * FROM agent_experiments"
#         params = []
#
#         if status:
#             base_query += " WHERE status = $1"
#             params.append(status)
#             base_query += f" ORDER BY created_at DESC LIMIT {limit}"
#         else:
#             base_query += f" ORDER BY created_at DESC LIMIT {limit}"
#
#         logger.info(f"Query: {base_query}, params: {params}")
#         experiments = await db.fetch_all(base_query, *params)
#
#         return {
#             "success": True,
#             "experiments": experiments,
#             "count": len(experiments)
#         }
#     except Exception as e:
#         logger.error(f"Failed to fetch experiments: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Failed to fetch experiments: {str(e)}")


@router.post("/evolution/experiments/{experiment_id}/rollback")
async def rollback_experiment(
    experiment_id: str,
    reason: str = "manual_rollback",
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually rollback an experiment.
    """
    try:
        experiment_manager = ExperimentManager(database=db)

        result = await experiment_manager.rollback_experiment(
            experiment_id=experiment_id,
            reason=reason
        )

        return {
            "success": result.get("success", False),
            "message": result.get("message", "")
        }
    except Exception as e:
        logger.error(f"Experiment rollback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Experiment rollback failed: {str(e)}")


# ============ Code Refactoring Endpoints ============

@router.post("/evolution/refactor/code")
async def refactor_code(
    hypothesis_id: str,
    dry_run: bool = True,
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """
    Apply code refactoring based on a hypothesis.
    """
    try:
        code_refactor = CodeRefactor(database=db)

        # First, propose a refactoring based on the hypothesis
        proposal = await code_refactor.propose_refactor(
            hypothesis_id=hypothesis_id
        )

        refactor_id = proposal.get("id")
        if not refactor_id:
            raise HTTPException(status_code=500, detail="Failed to generate refactoring proposal")

        if dry_run:
            # Return the proposal without applying
            return {
                "success": True,
                "refactor_id": refactor_id,
                "proposal": proposal,
                "dry_run": True,
                "message": "Refactoring proposal created (dry run)"
            }
        else:
            # Validate and apply the refactoring
            validation = await code_refactor.validate_refactor(refactor_id)
            if not validation.get("validation_passed", False):
                raise HTTPException(status_code=400, detail=f"Refactoring validation failed: {validation.get('errors', [])}")

            # Apply the refactoring
            result = await code_refactor.apply_refactor(
                refactor_id=refactor_id,
                create_backup=True
            )

            return {
                "success": result.get("success", False),
                "refactor_id": refactor_id,
                "changes": result.get("application", {}).get("applied_changes", []),
                "dry_run": False,
                "message": result.get("application", {}).get("message", "")
            }
    except Exception as e:
        logger.error(f"Code refactoring failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Code refactoring failed: {str(e)}")


@router.get("/evolution/refactor/history")
async def get_refactor_history(
    limit: int = 20,
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get history of code refactoring operations.
    """
    try:
        # Query refactoring_proposals table
        query = """
            SELECT * FROM refactoring_proposals
            ORDER BY created_at DESC
            LIMIT $1
        """

        history = await db.fetch_all(query, limit)

        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Failed to fetch refactor history: {e}", exc_info=True)
        # If table doesn't exist yet, return empty list
        return {
            "success": True,
            "history": [],
            "count": 0
        }


# ============ System Evolution Status ============

@router.get("/evolution/status")
async def get_evolution_status(
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get overall status of the self-evolution system.
    """
    try:
        # Count hypotheses
        hypotheses_count = 0
        try:
            hypotheses_query = "SELECT COUNT(*) FROM evolution_hypotheses"
            hypotheses_result = await db.fetch_one(hypotheses_query)
            hypotheses_count = hypotheses_result["count"] if hypotheses_result else 0
        except Exception as e:
            logger.debug(f"Evolution hypotheses table may not exist yet: {e}")  # Table may not exist yet

        # Count experiments
        experiments_count = 0
        try:
            experiments_query = "SELECT COUNT(*) FROM agent_experiments"
            experiments_result = await db.fetch_one(experiments_query)
            experiments_count = experiments_result["count"] if experiments_result else 0
        except Exception as e:
            logger.debug(f"Agent experiments table may not exist yet: {e}")

        # Count refactoring proposals
        refactorings_count = 0
        try:
            refactorings_query = "SELECT COUNT(*) FROM refactoring_proposals"
            refactorings_result = await db.fetch_one(refactorings_query)
            refactorings_count = refactorings_result["count"] if refactorings_result else 0
        except Exception as e:
            logger.debug(f"Refactoring proposals table may not exist yet: {e}")

        # Get recent bottlenecks
        recent_bottlenecks = []
        try:
            bottlenecks_query = """
                SELECT * FROM bottleneck_patterns
                WHERE resolved = false
                ORDER BY last_detected DESC
                LIMIT 5
            """
            recent_bottlenecks = await db.fetch_all(bottlenecks_query)
        except Exception as e:
            logger.debug(f"Bottleneck patterns table may not exist yet: {e}")

        return {
            "success": True,
            "hypotheses_count": hypotheses_count,
            "experiments_count": experiments_count,
            "refactorings_count": refactorings_count,
            "recent_bottlenecks": recent_bottlenecks,
            "evolution_active": hypotheses_count > 0 or experiments_count > 0
        }
    except Exception as e:
        logger.error(f"Failed to get evolution status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get evolution status: {str(e)}")