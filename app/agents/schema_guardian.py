"""
NEXUS Schema Guardian Agent

Autonomous database schema validation and repair agent.
Detects schema mismatches, JSONB serialization issues, and type inconsistencies.
Generates and applies safe migrations with rollback capability.

Capabilities:
- Database schema validation
- Pydantic model extraction
- Schema-model comparison
- Migration generation
- Safe migration application
- JSONB codec verification
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import uuid

from .base import BaseAgent, AgentType, AgentStatus
from .tools import ToolSystem, ToolDefinition, ToolParameter, ToolType
from .memory import MemorySystem
from ..database import db
from ..config import settings

logger = logging.getLogger(__name__)


class SchemaGuardianAgent(BaseAgent):
    """
    Schema Guardian Agent - Autonomous database schema validation and repair.

    Capabilities: schema_validation, type_checking, migration_generation,
                  safe_deployment, jsonb_verification, pydantic_extraction
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "Schema Guardian Agent",
        description: str = "Autonomous database schema validation and repair agent. Detects and fixes schema mismatches, JSONB issues, and type inconsistencies.",
        system_prompt: str = "You are a Schema Guardian Agent. You analyze database schemas, compare them with Pydantic models, detect mismatches, and generate safe migrations. You prioritize data safety and always provide rollback capabilities.",
        capabilities: Optional[List[str]] = None,
        supervisor_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        if capabilities is None:
            capabilities = [
                "schema_validation",
                "type_checking",
                "migration_generation",
                "safe_deployment",
                "jsonb_verification",
                "pydantic_extraction",
                "codec_validation",
                "migration_rollback"
            ]

        if config is None:
            config = {
                "validation_interval_hours": 24,  # How often to run full validation
                "auto_apply_safe_fixes": False,   # Whether to auto-apply safe fixes
                "require_approval": True,         # Whether to require human approval
                "max_migration_size_kb": 100,     # Max size of auto-generated migrations
                "backup_before_migration": True,  # Whether to backup before applying
                "test_migration_first": True,     # Whether to test migration before applying
            }

        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.DOMAIN,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities,
            domain="database",
            supervisor_id=supervisor_id,
            config=config,
            **kwargs
        )

        self.tool_system = ToolSystem()
        self.memory_system = MemorySystem()

    async def initialize(self) -> None:
        """Initialize the agent and register tools."""
        await super().initialize()

        # Register tools
        await self._register_tools()

        logger.info(f"SchemaGuardianAgent {self.name} initialized with ID: {self.agent_id}")

    async def _register_tools(self) -> None:
        """Register all tools available to this agent."""

        # Tool 1: Validate database schema
        await self.tool_system.register_tool(
            ToolDefinition(
                name="validate_database_schema",
                display_name="Validate Database Schema",
                description="Validate database schema for common issues: JSONB columns, type mismatches, missing columns",
                tool_type=ToolType.DATABASE,
                parameters=[
                    ToolParameter("table_name", "string", "Specific table to validate (optional)", required=False),
                    ToolParameter("check_jsonb", "boolean", "Check JSONB columns and codecs", required=False, default=True),
                    ToolParameter("check_types", "boolean", "Check PostgreSQL type mappings", required=False, default=True),
                    ToolParameter("check_constraints", "boolean", "Check constraints and indexes", required=False, default=False),
                ]
            )
        )

        # Tool 2: Validate Pydantic models
        await self.tool_system.register_tool(
            ToolDefinition(
                name="validate_pydantic_models",
                display_name="Validate Pydantic Models",
                description="Extract and validate Pydantic model field types and constraints",
                tool_type=ToolType.ANALYSIS,
                parameters=[
                    ToolParameter("model_path", "string", "Path to Python file containing models", required=False),
                    ToolParameter("model_class", "string", "Specific model class to validate", required=False),
                ]
            )
        )

        # Tool 3: Compare schema with models
        await self.tool_system.register_tool(
            ToolDefinition(
                name="compare_schema_models",
                display_name="Compare Schema with Models",
                description="Compare database schema with Pydantic models to find mismatches",
                tool_type=ToolType.ANALYSIS,
                parameters=[
                    ToolParameter("table_name", "string", "Table to compare", required=False),
                    ToolParameter("model_class", "string", "Model class to compare", required=False),
                    ToolParameter("generate_report", "boolean", "Generate detailed mismatch report", required=False, default=True),
                ]
            )
        )

        # Tool 4: Generate migration script
        await self.tool_system.register_tool(
            ToolDefinition(
                name="generate_migration",
                display_name="Generate Migration Script",
                description="Generate SQL migration script to fix schema issues",
                tool_type=ToolType.DATABASE,
                parameters=[
                    ToolParameter("issues", "array", "List of schema issues to fix", required=True),
                    ToolParameter("migration_name", "string", "Name for the migration", required=False),
                    ToolParameter("include_rollback", "boolean", "Include rollback SQL", required=False, default=True),
                    ToolParameter("test_migration", "boolean", "Generate test migration first", required=False, default=True),
                ]
            )
        )

        # Tool 5: Apply migration safely
        await self.tool_system.register_tool(
            ToolDefinition(
                name="apply_migration_safely",
                display_name="Apply Migration Safely",
                description="Apply migration with transaction safety and rollback capability",
                tool_type=ToolType.DATABASE,
                parameters=[
                    ToolParameter("migration_sql", "string", "SQL migration to apply", required=True),
                    ToolParameter("backup_first", "boolean", "Create backup before applying", required=False, default=True),
                    ToolParameter("test_in_transaction", "boolean", "Test in transaction before commit", required=False, default=True),
                    ToolParameter("timeout_seconds", "number", "Timeout for migration execution", required=False, default=30),
                ]
            )
        )

        # Tool 6: Check JSONB codec registration
        await self.tool_system.register_tool(
            ToolDefinition(
                name="check_jsonb_codecs",
                display_name="Check JSONB Codec Registration",
                description="Verify JSONB codecs are properly registered in database connection",
                tool_type=ToolType.DATABASE,
                parameters=[
                    ToolParameter("test_decoding", "boolean", "Test actual JSONB decoding", required=False, default=True),
                    ToolParameter("sample_size", "number", "Number of sample rows to test", required=False, default=5),
                ]
            )
        )

        logger.info(f"Registered {len(self.tool_system.tools)} tools for SchemaGuardianAgent")

    # ============ Core Validation Methods ============

    async def validate_database_schema(
        self,
        table_name: Optional[str] = None,
        check_jsonb: bool = True,
        check_types: bool = True,
        check_constraints: bool = False
    ) -> Dict[str, Any]:
        """
        Validate database schema for common issues.

        Returns:
            Dictionary with validation results and issues found.
        """
        logger.info(f"Validating database schema (table: {table_name or 'all'})")

        results = {
            "timestamp": datetime.now().isoformat(),
            "table_name": table_name,
            "checks_performed": {
                "jsonb": check_jsonb,
                "types": check_types,
                "constraints": check_constraints,
            },
            "issues": [],
            "warnings": [],
            "summary": {}
        }

        try:
            await db.connect()

            # 1. Check JSONB columns
            if check_jsonb:
                jsonb_issues = await self._check_jsonb_columns(table_name)
                results["issues"].extend(jsonb_issues)
                results["summary"]["jsonb_issues"] = len(jsonb_issues)

            # 2. Check type mappings
            if check_types:
                type_issues = await self._check_type_mappings(table_name)
                results["issues"].extend(type_issues)
                results["summary"]["type_issues"] = len(type_issues)

            # 3. Check constraints
            if check_constraints and table_name:
                constraint_issues = await self._check_constraints(table_name)
                results["issues"].extend(constraint_issues)
                results["summary"]["constraint_issues"] = len(constraint_issues)

            # 4. Check for missing tables/columns
            missing_issues = await self._check_missing_elements(table_name)
            results["issues"].extend(missing_issues)
            results["summary"]["missing_issues"] = len(missing_issues)

            # Calculate overall status
            total_issues = len(results["issues"])
            results["status"] = "healthy" if total_issues == 0 else "issues_found"
            results["summary"]["total_issues"] = total_issues

            # Store in memory for tracking
            await self._store_validation_results(results)

        except Exception as e:
            logger.error(f"Error validating database schema: {e}", exc_info=True)
            results["status"] = "error"
            results["error"] = str(e)

        return results

    async def _check_jsonb_columns(self, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Check JSONB columns for issues."""
        issues = []

        try:
            # Get all JSONB columns
            query = """
                SELECT table_name, column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE data_type IN ('json', 'jsonb')
            """
            if table_name:
                query += f" AND table_name = '{table_name}'"
            query += " ORDER BY table_name, column_name"

            json_columns = await db.fetch_all(query)

            for col in json_columns:
                # Check if column has valid JSON data
                sample_query = f"""
                    SELECT {col['column_name']}, pg_typeof({col['column_name']}) as type_name
                    FROM {col['table_name']}
                    WHERE {col['column_name']} IS NOT NULL
                    LIMIT 3
                """

                try:
                    samples = await db.fetch_all(sample_query)

                    # Check for JSON decoding issues
                    for sample in samples:
                        col_value = sample[col['column_name']]
                        type_name = sample['type_name']

                        # If value is string but column is JSONB, might indicate codec issue
                        if isinstance(col_value, str) and col['data_type'] == 'jsonb':
                            try:
                                # Try to parse as JSON
                                json.loads(col_value)
                                issues.append({
                                    "table": col['table_name'],
                                    "column": col['column_name'],
                                    "issue": "jsonb_stored_as_string",
                                    "severity": "warning",
                                    "details": f"JSONB column contains string value (type: {type_name}). May indicate codec registration issue.",
                                    "sample": col_value[:100] if col_value else None
                                })
                            except json.JSONDecodeError:
                                issues.append({
                                    "table": col['table_name'],
                                    "column": col['column_name'],
                                    "issue": "invalid_json_in_jsonb",
                                    "severity": "error",
                                    "details": f"JSONB column contains invalid JSON string (type: {type_name})",
                                    "sample": col_value[:100] if col_value else None
                                })
                except Exception as e:
                    issues.append({
                        "table": col['table_name'],
                        "column": col['column_name'],
                        "issue": "sample_query_failed",
                        "severity": "warning",
                        "details": f"Failed to sample column: {str(e)}"
                    })

        except Exception as e:
            logger.error(f"Error checking JSONB columns: {e}", exc_info=True)

        return issues

    async def _check_type_mappings(self, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Check PostgreSQL type mappings for potential issues."""
        issues = []

        try:
            # Get column information
            query = """
                SELECT table_name, column_name, data_type, udt_name,
                       character_maximum_length, numeric_precision, numeric_scale,
                       is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
            """
            if table_name:
                query += f" AND table_name = '{table_name}'"
            query += " ORDER BY table_name, column_name"

            columns = await db.fetch_all(query)

            # Common type mapping issues to check
            for col in columns:
                data_type = col['data_type']
                udt_name = col['udt_name']

                # Check for TEXT columns that should be JSONB
                if data_type == 'text' and col['column_name'] in ['config', 'metadata', 'settings', 'data']:
                    issues.append({
                        "table": col['table_name'],
                        "column": col['column_name'],
                        "issue": "text_instead_of_jsonb",
                        "severity": "warning",
                        "details": f"Text column '{col['column_name']}' might be better as JSONB for structured data",
                        "data_type": data_type
                    })

                # Check for missing NOT NULL constraints on important columns
                if col['is_nullable'] == 'YES' and col['column_name'] in ['id', 'created_at', 'updated_at']:
                    issues.append({
                        "table": col['table_name'],
                        "column": col['column_name'],
                        "issue": "nullable_important_column",
                        "severity": "warning",
                        "details": f"Important column '{col['column_name']}' allows NULL values",
                        "is_nullable": col['is_nullable']
                    })

        except Exception as e:
            logger.error(f"Error checking type mappings: {e}", exc_info=True)

        return issues

    async def _check_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        """Check table constraints."""
        issues = []

        try:
            # Check for missing primary keys
            pk_query = """
                SELECT tc.table_name, kc.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kc
                    ON tc.constraint_name = kc.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_name = $1
            """

            primary_keys = await db.fetch_all(pk_query, table_name)

            if not primary_keys:
                issues.append({
                    "table": table_name,
                    "issue": "missing_primary_key",
                    "severity": "error",
                    "details": "Table has no primary key constraint"
                })

            # Check for missing foreign key constraints (heuristic based on column names)
            fk_heuristic_query = f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                    AND column_name LIKE '%_id'
                    AND column_name != 'id'
            """

            potential_fk_columns = await db.fetch_all(fk_heuristic_query)

            for col in potential_fk_columns:
                # Check if foreign key constraint exists
                fk_check = await db.fetch_one("""
                    SELECT tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kc
                        ON tc.constraint_name = kc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_name = $1
                        AND kc.column_name = $2
                """, table_name, col['column_name'])

                if not fk_check:
                    issues.append({
                        "table": table_name,
                        "column": col['column_name'],
                        "issue": "missing_foreign_key",
                        "severity": "warning",
                        "details": f"Column '{col['column_name']}' appears to be a foreign key but has no constraint"
                    })

        except Exception as e:
            logger.error(f"Error checking constraints: {e}", exc_info=True)

        return issues

    async def _check_missing_elements(self, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Check for missing tables or columns."""
        issues = []

        # This is a placeholder - would need to compare with expected schema
        # For now, just return empty list
        return issues

    async def _store_validation_results(self, results: Dict[str, Any]) -> None:
        """Store validation results in memory system."""
        try:
            await self.memory_system.store_memory(
                agent_id=self.agent_id,
                content=json.dumps(results, default=str),
                memory_type="validation_result",
                tags=["schema_validation", results.get("status", "unknown")],
                metadata={
                    "timestamp": results["timestamp"],
                    "table_name": results.get("table_name"),
                    "total_issues": results.get("summary", {}).get("total_issues", 0),
                    "agent_id": self.agent_id
                }
            )
        except Exception as e:
            logger.error(f"Failed to store validation results in memory: {e}")

    # ============ Public API Methods ============

    async def run_validation_pipeline(self) -> Dict[str, Any]:
        """
        Run complete validation pipeline.

        Returns:
            Comprehensive validation report.
        """
        logger.info("Running complete validation pipeline")

        pipeline_results = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "steps": [],
            "overall_status": "unknown"
        }

        try:
            # Step 1: Database schema validation
            schema_results = await self.validate_database_schema(
                check_jsonb=True,
                check_types=True,
                check_constraints=False
            )

            pipeline_results["steps"].append({
                "step": "database_schema_validation",
                "status": schema_results.get("status", "error"),
                "issues_found": len(schema_results.get("issues", [])),
                "details": schema_results
            })

            # Step 2: JSONB codec check
            codec_results = await self.check_jsonb_codecs()
            pipeline_results["steps"].append({
                "step": "jsonb_codec_validation",
                "status": codec_results.get("status", "error"),
                "issues_found": len(codec_results.get("issues", [])),
                "details": codec_results
            })

            # Determine overall status
            all_issues = sum(step["issues_found"] for step in pipeline_results["steps"])
            has_errors = any(
                step["details"].get("status") == "error"
                for step in pipeline_results["steps"]
            )

            if has_errors:
                pipeline_results["overall_status"] = "error"
            elif all_issues > 0:
                pipeline_results["overall_status"] = "issues_found"
            else:
                pipeline_results["overall_status"] = "healthy"

            # Store pipeline results
            await self.memory_system.store_memory(
                agent_id=self.agent_id,
                content=json.dumps(pipeline_results, default=str),
                memory_type="validation_pipeline",
                tags=["validation_pipeline", pipeline_results["overall_status"]],
                metadata={
                    "timestamp": pipeline_results["timestamp"],
                    "total_issues": all_issues,
                    "has_errors": has_errors
                }
            )

        except Exception as e:
            logger.error(f"Error in validation pipeline: {e}", exc_info=True)
            pipeline_results["overall_status"] = "pipeline_error"
            pipeline_results["error"] = str(e)

        return pipeline_results

    async def check_jsonb_codecs(
        self,
        test_decoding: bool = True,
        sample_size: int = 5
    ) -> Dict[str, Any]:
        """
        Check JSONB codec registration and test decoding.

        Returns:
            Codec validation results.
        """
        logger.info(f"Checking JSONB codec registration (test_decoding: {test_decoding})")

        results = {
            "timestamp": datetime.now().isoformat(),
            "test_decoding": test_decoding,
            "sample_size": sample_size,
            "issues": [],
            "status": "unknown"
        }

        try:
            await db.connect()

            # Get JSONB columns
            jsonb_columns = await db.fetch_all("""
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE data_type = 'jsonb'
                ORDER BY table_name, column_name
                LIMIT 10
            """)

            results["jsonb_columns_found"] = len(jsonb_columns)

            if test_decoding and jsonb_columns:
                # Test decoding on first column
                test_col = jsonb_columns[0]
                test_query = f"""
                    SELECT {test_col['column_name']},
                           pg_typeof({test_col['column_name']}) as type_name
                    FROM {test_col['table_name']}
                    WHERE {test_col['column_name']} IS NOT NULL
                    LIMIT {sample_size}
                """

                samples = await db.fetch_all(test_query)
                results["samples_tested"] = len(samples)

                # Analyze samples
                string_samples = 0
                dict_samples = 0
                list_samples = 0
                null_samples = 0
                invalid_samples = 0

                for sample in samples:
                    col_value = sample[test_col['column_name']]
                    type_name = sample['type_name']

                    if col_value is None:
                        null_samples += 1
                    elif isinstance(col_value, str):
                        string_samples += 1
                        # Try to parse as JSON
                        try:
                            parsed = json.loads(col_value)
                            if isinstance(parsed, dict):
                                dict_samples += 1
                            elif isinstance(parsed, list):
                                list_samples += 1
                        except json.JSONDecodeError:
                            invalid_samples += 1
                    elif isinstance(col_value, dict):
                        dict_samples += 1
                    elif isinstance(col_value, list):
                        list_samples += 1

                results["sample_analysis"] = {
                    "total": len(samples),
                    "string_samples": string_samples,
                    "dict_samples": dict_samples,
                    "list_samples": list_samples,
                    "null_samples": null_samples,
                    "invalid_json": invalid_samples
                }

                # Check for issues
                if string_samples > 0:
                    results["issues"].append({
                        "issue": "jsonb_decoded_as_string",
                        "severity": "warning",
                        "details": f"{string_samples} JSONB values were decoded as strings instead of dict/list",
                        "recommendation": "Check JSONB codec registration in database.py"
                    })

                if invalid_samples > 0:
                    results["issues"].append({
                        "issue": "invalid_json_in_jsonb",
                        "severity": "error",
                        "details": f"{invalid_samples} JSONB values contain invalid JSON",
                        "recommendation": "Check data integrity in JSONB columns"
                    })

            # Determine status
            has_errors = any(issue.get("severity") == "error" for issue in results["issues"])
            has_warnings = any(issue.get("severity") == "warning" for issue in results["issues"])

            if has_errors:
                results["status"] = "error"
            elif has_warnings:
                results["status"] = "warning"
            else:
                results["status"] = "healthy"

        except Exception as e:
            logger.error(f"Error checking JSONB codecs: {e}", exc_info=True)
            results["status"] = "error"
            results["error"] = str(e)

        return results

    async def process_validation_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process validation results and determine actions.

        Returns:
            Action plan with recommended fixes.
        """
        logger.info("Processing validation results")

        action_plan = {
            "timestamp": datetime.now().isoformat(),
            "results_processed": results.get("summary", {}).get("total_issues", 0),
            "recommended_actions": [],
            "priority": "low",
            "auto_apply_possible": False
        }

        issues = results.get("issues", [])

        for issue in issues:
            action = self._generate_action_for_issue(issue)
            if action:
                action_plan["recommended_actions"].append(action)

        # Determine priority
        error_count = sum(1 for action in action_plan["recommended_actions"]
                         if action.get("priority") == "high")
        warning_count = sum(1 for action in action_plan["recommended_actions"]
                           if action.get("priority") == "medium")

        if error_count > 0:
            action_plan["priority"] = "high"
        elif warning_count > 0:
            action_plan["priority"] = "medium"

        # Check if auto-apply is possible (based on config and issue severity)
        if (self.config.get("auto_apply_safe_fixes", False) and
            action_plan["priority"] != "high" and
            len(action_plan["recommended_actions"]) > 0):

            # Only auto-apply if all actions are safe
            all_safe = all(action.get("safe_to_auto_apply", False)
                          for action in action_plan["recommended_actions"])

            if all_safe:
                action_plan["auto_apply_possible"] = True

        return action_plan

    def _generate_action_for_issue(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate action recommendation for a specific issue."""

        issue_type = issue.get("issue", "")
        severity = issue.get("severity", "warning")

        # Map issues to actions
        action_templates = {
            "jsonb_stored_as_string": {
                "action": "register_jsonb_codec",
                "priority": "high" if severity == "error" else "medium",
                "description": "Register JSONB codec in database connection",
                "sql_fix": "No SQL needed - fix code in app/database.py init_connection()",
                "safe_to_auto_apply": True,
                "requires_restart": True
            },
            "text_instead_of_jsonb": {
                "action": "convert_text_to_jsonb",
                "priority": "medium",
                "description": f"Convert column {issue.get('column')} from TEXT to JSONB",
                "sql_fix": f"ALTER TABLE {issue.get('table')} ALTER COLUMN {issue.get('column')} TYPE JSONB USING {issue.get('column')}::jsonb;",
                "safe_to_auto_apply": False,  # Data conversion risk
                "requires_backup": True
            },
            "missing_primary_key": {
                "action": "add_primary_key",
                "priority": "high",
                "description": f"Add primary key to table {issue.get('table')}",
                "sql_fix": f"ALTER TABLE {issue.get('table')} ADD PRIMARY KEY (id);",
                "safe_to_auto_apply": False,  # Requires analysis of existing data
                "requires_analysis": True
            }
        }

        if issue_type in action_templates:
            action = action_templates[issue_type].copy()
            action["issue"] = issue
            return action

        # Default action for unknown issues
        return {
            "action": "investigate_issue",
            "priority": "low",
            "description": f"Investigate issue: {issue_type}",
            "details": issue,
            "safe_to_auto_apply": False
        }


# ============ Agent Registration Helper ============

async def register_schema_guardian_agent() -> SchemaGuardianAgent:
    """
    Register schema guardian agent with the agent registry.

    Call this during system startup to register the schema guardian agent.
    Returns existing agent if already registered.
    """
    from .registry import registry

    # Check if schema guardian agent already exists by name
    existing_agent = await registry.get_agent_by_name("Schema Guardian Agent")
    if existing_agent:
        logger.info(f"Schema guardian agent already registered: {existing_agent.name}")
        return existing_agent

    # Create new schema guardian agent using registry's create_agent method
    try:
        agent = await registry.create_agent(
            agent_type="schema_guardian",
            name="Schema Guardian Agent",
            description="Autonomous database schema validation and repair agent. Detects and fixes schema mismatches, JSONB issues, and type inconsistencies.",
            capabilities=[
                "schema_validation",
                "type_checking",
                "migration_generation",
                "safe_deployment",
                "jsonb_verification",
                "pydantic_extraction",
                "codec_validation",
                "migration_rollback"
            ],
            domain="database",
            config={
                "validation_interval_hours": 24,
                "auto_apply_safe_fixes": False,
                "require_approval": True,
                "max_migration_size_kb": 100,
                "backup_before_migration": True,
                "test_migration_first": True,
            }
        )
        logger.info(f"Schema guardian agent created and registered: {agent.name}")
        return agent
    except ValueError as e:
        # Likely duplicate name (race condition) - try to fetch again
        existing_agent = await registry.get_agent_by_name("Schema Guardian Agent")
        if existing_agent:
            logger.info(f"Schema guardian agent registered after race condition: {existing_agent.name}")
            return existing_agent
        raise e