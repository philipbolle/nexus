"""
NEXUS Autonomous Monitoring API Endpoints

Manual triggers for autonomous monitoring agents:
- Schema Guardian Agent: Database schema validation and repair
- Test Synchronizer Agent: Test-implementation synchronization
- Monitoring triggers: Scheduled and reactive monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional, List
import logging
import asyncio

from ..database import db
from ..config import settings
from ..agents.registry import registry
from ..agents.monitoring import performance_monitor

router = APIRouter(tags=["autonomous-monitoring"])
logger = logging.getLogger(__name__)


async def get_schema_guardian_agent():
    """Get the schema guardian agent from registry."""
    agent = await registry.get_agent_by_name("Schema Guardian Agent")
    if not agent:
        raise HTTPException(
            status_code=503,
            detail="Schema Guardian Agent not available. Agent may not be registered."
        )
    return agent


async def get_test_synchronizer_agent():
    """Get the test synchronizer agent from registry."""
    agent = await registry.get_agent_by_name("Test Synchronizer Agent")
    if not agent:
        raise HTTPException(
            status_code=503,
            detail="Test Synchronizer Agent not available. Agent may not be registered."
        )
    return agent


@router.post("/validate-schema", summary="Trigger schema validation")
async def trigger_schema_validation(
    background_tasks: BackgroundTasks,
    table_name: Optional[str] = None,
    check_jsonb: bool = True,
    check_types: bool = True,
    check_constraints: bool = False,
    run_full_pipeline: bool = False,
    agent = Depends(get_schema_guardian_agent)
) -> Dict[str, Any]:
    """
    Trigger schema validation using Schema Guardian Agent.

    This endpoint manually triggers the schema guardian agent to validate
    database schema for issues like JSONB codec problems, type mismatches,
    and constraint issues.

    Parameters:
    - table_name: Optional specific table to validate
    - check_jsonb: Whether to check JSONB columns and codecs
    - check_types: Whether to check PostgreSQL type mappings
    - check_constraints: Whether to check constraints and indexes
    - run_full_pipeline: If True, runs complete validation pipeline including codec checks

    Returns:
    - Validation results with issues found and recommendations
    """
    try:
        logger.info(f"Triggering schema validation (table: {table_name}, full_pipeline: {run_full_pipeline})")

        if run_full_pipeline:
            # Run complete validation pipeline
            results = await agent.run_validation_pipeline()
        else:
            # Run specific validation
            results = await agent.validate_database_schema(
                table_name=table_name,
                check_jsonb=check_jsonb,
                check_types=check_types,
                check_constraints=check_constraints
            )

        # Record monitoring event
        await performance_monitor.record_metric(
            agent_id=agent.agent_id,
            metric_type="validation_execution",
            value=1.0,
            tags={
                "validation_type": "schema",
                "table_name": table_name or "all",
                "full_pipeline": run_full_pipeline,
                "issues_found": len(results.get("issues", [])) if isinstance(results, dict) else 0
            }
        )

        return {
            "status": "success",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "results": results,
            "recommendation": "Review issues found and apply recommended fixes if safe."
        }

    except Exception as e:
        logger.error(f"Error triggering schema validation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger schema validation: {str(e)}"
        )


@router.post("/synchronize-tests", summary="Trigger test synchronization")
async def trigger_test_synchronization(
    background_tasks: BackgroundTasks,
    test_file: Optional[str] = None,
    source_file: Optional[str] = None,
    analyze_failures: bool = True,
    compare_implementation: bool = True,
    agent = Depends(get_test_synchronizer_agent)
) -> Dict[str, Any]:
    """
    Trigger test synchronization using Test Synchronizer Agent.

    This endpoint manually triggers the test synchronizer agent to analyze
    test failures, compare test expectations with implementations, and
    generate corrections for mismatches.

    Parameters:
    - test_file: Optional specific test file to analyze (e.g., "tests/unit/agents/test_sessions.py")
    - source_file: Optional source file to compare with (e.g., "app/agents/sessions.py")
    - analyze_failures: Whether to analyze test failure patterns
    - compare_implementation: Whether to compare test with implementation signatures

    Returns:
    - Synchronization results with mismatches found and recommended corrections
    """
    try:
        logger.info(f"Triggering test synchronization (test: {test_file}, source: {source_file})")

        # Run synchronization pipeline
        results = await agent.run_synchronization_pipeline(
            test_file=test_file,
            source_file=source_file
        )

        # Record monitoring event
        await performance_monitor.record_metric(
            agent_id=agent.agent_id,
            metric_type="validation_execution",
            value=1.0,
            tags={
                "validation_type": "test_synchronization",
                "test_file": test_file or "multiple",
                "source_file": source_file or "multiple",
                "mismatches_found": results.get("corrections_needed", 0)
            }
        )

        return {
            "status": "success",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "results": results,
            "recommendation": "Review mismatches and apply corrections if appropriate."
        }

    except Exception as e:
        logger.error(f"Error triggering test synchronization: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger test synchronization: {str(e)}"
        )


@router.get("/monitoring-status", summary="Get autonomous monitoring status")
async def get_monitoring_status() -> Dict[str, Any]:
    """
    Get status of autonomous monitoring agents and recent activities.

    Returns:
    - Status of registered monitoring agents
    - Recent validation results
    - System health for monitoring components
    """
    try:
        # Get monitoring agents
        schema_agent = await registry.get_agent_by_name("Schema Guardian Agent")
        test_agent = await registry.get_agent_by_name("Test Synchronizer Agent")

        # Get recent performance metrics for monitoring agents
        recent_validations = await performance_monitor.get_agent_performance(
            agent_id=schema_agent.agent_id if schema_agent else None,
            time_range_hours=24
        ) if schema_agent else {}

        # Get system health
        system_health = await performance_monitor.get_system_performance(time_range_hours=1)

        return {
            "timestamp": asyncio.get_event_loop().time(),
            "agents": {
                "schema_guardian": {
                    "registered": schema_agent is not None,
                    "agent_id": schema_agent.agent_id if schema_agent else None,
                    "status": schema_agent.status if schema_agent else "not_registered"
                },
                "test_synchronizer": {
                    "registered": test_agent is not None,
                    "agent_id": test_agent.agent_id if test_agent else None,
                    "status": test_agent.status if test_agent else "not_registered"
                }
            },
            "recent_activity": {
                "validations": (recent_validations.get("metrics") or [])[:5] if recent_validations else [],
                "active_alerts": len(system_health.get("active_alerts") or []),
                "system_status": system_health.get("overall_status", "unknown")
            },
            "recommendations": [
                "Run schema validation weekly to prevent JSONB codec issues",
                "Run test synchronization after code changes to maintain test integrity",
                "Monitor error rates for early detection of schema or test mismatches"
            ]
        }

    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "agents": {},
            "recent_activity": {},
            "recommendations": []
        }


@router.post("/trigger-reactive", summary="Trigger reactive monitoring (internal)")
async def trigger_reactive_monitoring(
    event_type: str,
    event_data: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Internal endpoint for reactive monitoring triggers.

    This endpoint is called by the monitoring system when specific events occur:
    - test_failures: When test suite fails (e.g., 64% failure rate)
    - jsonb_errors: When JSONB serialization errors are detected
    - schema_mismatch: When schema validation issues are found
    - performance_anomaly: When performance anomalies are detected

    Parameters:
    - event_type: Type of event that triggered monitoring
    - event_data: Event-specific data

    Returns:
    - Response indicating which agents were triggered and results
    """
    # This is a stub for reactive monitoring
    # In a full implementation, this would:
    # 1. Analyze event type and severity
    # 2. Determine which agents to trigger
    # 3. Execute appropriate validation pipelines
    # 4. Return results and recommendations

    logger.info(f"Reactive monitoring triggered: {event_type} - {event_data}")

    try:
        # Record monitoring metric
        await performance_monitor.record_metric(
            agent_id="autonomous_monitoring",
            metric_type="reactive_trigger",
            value=1.0,
            tags={
                "event_type": event_type,
                "severity": event_data.get("severity", "medium"),
                "source": event_data.get("source", "unknown")
            }
        )

        # Event type routing with severity thresholds
        if event_type == "test_failures":
            failure_rate = event_data.get("failure_rate", 0)
            severity = event_data.get("severity", "high" if failure_rate > 50 else "medium")

            if failure_rate > 50:  # 50% failure threshold
                # Trigger test synchronizer agent
                test_agent = await registry.get_agent_by_name("Test Synchronizer Agent")
                if test_agent:
                    background_tasks.add_task(
                        test_agent.run_synchronization_pipeline,
                        test_file=event_data.get("test_file")
                    )
                    return {
                        "status": "triggered",
                        "agent": "test_synchronizer",
                        "reason": f"High test failure rate: {failure_rate}%",
                        "severity": severity,
                        "action": "test_synchronization_triggered"
                    }

        elif event_type == "jsonb_errors":
            severity = event_data.get("severity", "high")
            error_count = event_data.get("error_count", 1)

            if error_count > 0:
                # Trigger schema guardian agent
                schema_agent = await registry.get_agent_by_name("Schema Guardian Agent")
                if schema_agent:
                    background_tasks.add_task(
                        schema_agent.run_validation_pipeline
                    )
                    return {
                        "status": "triggered",
                        "agent": "schema_guardian",
                        "reason": f"JSONB serialization errors detected (count: {error_count})",
                        "severity": severity,
                        "action": "schema_validation_triggered"
                    }

        elif event_type == "schema_mismatch":
            severity = event_data.get("severity", "medium")
            mismatch_count = event_data.get("mismatch_count", 0)

            if mismatch_count > 0:
                # Trigger schema guardian agent
                schema_agent = await registry.get_agent_by_name("Schema Guardian Agent")
                if schema_agent:
                    background_tasks.add_task(
                        schema_agent.validate_database_schema,
                        check_jsonb=True,
                        check_types=True,
                        check_constraints=False
                    )
                    return {
                        "status": "triggered",
                        "agent": "schema_guardian",
                        "reason": f"Schema mismatches detected (count: {mismatch_count})",
                        "severity": severity,
                        "action": "schema_validation_triggered"
                    }

        elif event_type == "performance_anomaly":
            severity = event_data.get("severity", "medium")
            metric = event_data.get("metric", "")
            value = event_data.get("value", 0)
            threshold = event_data.get("threshold", 0)

            if value > threshold:
                # Log anomaly for investigation
                logger.warning(f"Performance anomaly detected: {metric} = {value} > {threshold}")
                return {
                    "status": "logged",
                    "agent": "monitoring_system",
                    "reason": f"Performance anomaly: {metric} = {value} > {threshold}",
                    "severity": severity,
                    "action": "anomaly_logged"
                }

        elif event_type == "high_error_rate":
            severity = event_data.get("severity", "high")
            error_rate = event_data.get("error_rate", 0)
            service = event_data.get("service", "unknown")

            if error_rate > 10:  # 10% error rate threshold
                logger.error(f"High error rate detected for {service}: {error_rate}%")
                # Could trigger diagnostic agent in future
                return {
                    "status": "alerted",
                    "agent": "monitoring_system",
                    "reason": f"High error rate for {service}: {error_rate}%",
                    "severity": severity,
                    "action": "error_rate_alert"
                }

        # Default response for unhandled or low-severity events
        return {
            "status": "monitored",
            "message": f"Event '{event_type}' was logged but no immediate action required",
            "event_data": event_data,
            "severity": event_data.get("severity", "low")
        }

    except Exception as e:
        logger.error(f"Error in reactive monitoring: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to process reactive monitoring event: {str(e)}",
            "event_type": event_type,
            "error": str(e)
        }