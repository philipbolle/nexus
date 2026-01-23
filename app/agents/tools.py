"""
NEXUS Multi-Agent Framework - Tool System

Tool definition, validation, registration, and execution system.
Provides standardized way for agents to interact with external systems.
"""

import asyncio
import ast
import inspect
import logging
import json
from typing import Dict, Any, List, Optional, Callable, Type, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime

from ..database import db

# Optional web search import
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    DDGS = None

logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Types of tools available to agents."""
    DATABASE = "database"
    API = "api"
    FILE = "file"
    CALCULATION = "calculation"
    NOTIFICATION = "notification"
    AUTOMATION = "automation"
    ANALYSIS = "analysis"
    PYTHON_FUNCTION = "python_function"
    WEB_SEARCH = "web_search"
    HOME_AUTOMATION = "home_automation"
    OTHER = "other"


class ToolExecutionStatus(Enum):
    """Status of tool execution."""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    NEEDS_CONFIRMATION = "needs_confirmation"


@dataclass
class ToolParameter:
    """Parameter definition for a tool."""

    name: str
    type: str  # 'string', 'integer', 'number', 'boolean', 'array', 'object'
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None


@dataclass
class ToolDefinition:
    """Complete definition of a tool."""

    name: str
    display_name: str
    description: str
    tool_type: ToolType
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False
    timeout_seconds: int = 30
    max_retries: int = 3


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""

    def __init__(self, tool_name: str, error_message: str, details: Optional[Dict[str, Any]] = None):
        self.tool_name = tool_name
        self.error_message = error_message
        self.details = details or {}
        super().__init__(f"Tool '{tool_name}' failed: {error_message}")


class ToolSystem:
    """
    Central tool system for the NEXUS agent framework.

    Manages tool registration, validation, execution, and monitoring.
    Provides tool discovery and capability matching.
    """

    def __init__(self):
        """Initialize the tool system."""
        self.tools: Dict[str, ToolDefinition] = {}
        self.tool_implementations: Dict[str, Callable] = {}
        self.tool_execution_history: List[Dict[str, Any]] = []
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the tool system.

        Loads tools from database and registers built-in tools.
        """
        if self._initialized:
            return

        logger.info("Initializing tool system...")

        try:
            # Load tools from database
            await self._load_tools_from_db()

            # Register built-in tools
            await self._register_builtin_tools()

            self._initialized = True
            logger.info(f"Tool system initialized with {len(self.tools)} tools")

        except Exception as e:
            logger.error(f"Failed to initialize tool system: {e}")
            raise

    async def register_tool(
        self,
        definition: ToolDefinition,
        implementation: Callable
    ) -> None:
        """
        Register a new tool.

        Args:
            definition: Tool definition
            implementation: Async function implementing the tool

        Raises:
            ValueError: If tool already registered or invalid
        """
        if definition.name in self.tools:
            raise ValueError(f"Tool '{definition.name}' already registered")

        # Validate implementation
        if not asyncio.iscoroutinefunction(implementation):
            raise ValueError(f"Tool implementation must be async function")

        # Validate parameters match implementation signature
        await self._validate_tool_signature(definition, implementation)

        # Register tool
        self.tools[definition.name] = definition
        self.tool_implementations[definition.name] = implementation

        # Store in database
        await self._store_tool_in_db(definition)

        logger.debug(f"Registered tool: {definition.name}")

    async def execute_tool(
        self,
        tool_name: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **parameters
    ) -> Any:
        """
        Execute a tool with parameters.

        Args:
            tool_name: Name of registered tool
            agent_id: ID of agent executing the tool
            session_id: Session ID for context
            **parameters: Tool parameters

        Returns:
            Tool execution result

        Raises:
            ToolExecutionError: If execution fails
            ValueError: If tool not found or parameters invalid
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not registered")

        definition = self.tools[tool_name]
        implementation = self.tool_implementations[tool_name]

        # Validate parameters
        await self._validate_parameters(definition, parameters)

        # Create execution record
        execution_id = await self._create_execution_record(
            tool_name, agent_id, session_id, parameters
        )

        logger.info(f"Executing tool: {tool_name} for agent {agent_id or 'unknown'}")

        try:
            # Execute tool with timeout
            result = await asyncio.wait_for(
                self._execute_with_retry(implementation, parameters, definition.max_retries),
                timeout=definition.timeout_seconds
            )

            # Update execution record
            await self._update_execution_record(execution_id, ToolExecutionStatus.SUCCESS, result)

            # Log successful execution
            await self._log_tool_execution(
                tool_name, agent_id, session_id, parameters, result, True
            )

            return result

        except asyncio.TimeoutError:
            error_msg = f"Tool '{tool_name}' timed out after {definition.timeout_seconds}s"
            await self._update_execution_record(execution_id, ToolExecutionStatus.TIMEOUT, error_msg)
            await self._log_tool_execution(
                tool_name, agent_id, session_id, parameters, error_msg, False
            )
            raise ToolExecutionError(tool_name, error_msg)

        except Exception as e:
            error_msg = str(e)
            await self._update_execution_record(execution_id, ToolExecutionStatus.ERROR, error_msg)
            await self._log_tool_execution(
                tool_name, agent_id, session_id, parameters, error_msg, False
            )
            raise ToolExecutionError(tool_name, error_msg)

    async def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        Get tool definition by name.

        Args:
            tool_name: Tool name

        Returns:
            Tool definition or None if not found
        """
        return self.tools.get(tool_name)

    async def list_tools(
        self,
        tool_type: Optional[ToolType] = None,
        agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List available tools.

        Args:
            tool_type: Filter by tool type
            agent_id: Filter by agent availability

        Returns:
            List of tool information dictionaries
        """
        # If agent_id is provided, use existing logic (checks agent access)
        if agent_id:
            tools_info = []
            for name, definition in self.tools.items():
                if tool_type and definition.tool_type != tool_type:
                    continue

                # Check if agent has access to this tool
                has_access = await self._agent_has_tool_access(agent_id, name)
                if not has_access:
                    continue

                tools_info.append({
                    "name": name,
                    "display_name": definition.display_name,
                    "description": definition.description,
                    "tool_type": definition.tool_type,
                    "parameters": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "description": p.description,
                            "required": p.required,
                            "default": p.default
                        }
                        for p in definition.parameters
                    ],
                    "requires_confirmation": definition.requires_confirmation,
                    "timeout_seconds": definition.timeout_seconds
                })
            return tools_info

        # Otherwise, fetch full tool info from database for API consumption
        query = """
            SELECT id, name, display_name, description, tool_type, input_schema,
                   output_schema, requires_confirmation, is_enabled,
                   (SELECT COUNT(*) FROM tool_executions WHERE tool_id = agent_tools.id) as usage_count,
                   (SELECT AVG(execution_time_ms) FROM tool_executions WHERE tool_id = agent_tools.id) as avg_execution_ms,
                   created_at
            FROM agent_tools WHERE is_enabled = true
        """
        params = []

        if tool_type:
            query += " AND tool_type = $1"
            params.append(tool_type.value)

        query += " ORDER BY name"

        tools = await db.fetch_all(query, *params)

        import json
        tools_info = []
        for row in tools:
            input_schema = row["input_schema"]
            output_schema = row["output_schema"]

            # Parse JSON strings if needed
            if isinstance(input_schema, str):
                try:
                    input_schema = json.loads(input_schema)
                except json.JSONDecodeError:
                    input_schema = {}
            if isinstance(output_schema, str):
                try:
                    output_schema = json.loads(output_schema)
                except json.JSONDecodeError:
                    output_schema = None

            tools_info.append({
                "id": row["id"],
                "name": row["name"],
                "display_name": row["display_name"],
                "description": row["description"],
                "tool_type": ToolType(row["tool_type"]),
                "input_schema": input_schema,
                "output_schema": output_schema,
                "requires_confirmation": row["requires_confirmation"],
                "is_enabled": row["is_enabled"],
                "usage_count": row["usage_count"] or 0,
                "avg_execution_ms": int(row["avg_execution_ms"]) if row["avg_execution_ms"] else None,
                "created_at": row["created_at"]
            })

        return tools_info

    async def get_agent_tools(self, agent_id: str) -> List[str]:
        """
        Get tools available to a specific agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of tool names
        """
        tool_assignments = await db.fetch_all(
            """
            SELECT at.name FROM agent_tools at
            JOIN agent_tool_assignments ata ON at.id = ata.tool_id
            WHERE ata.agent_id = $1 AND ata.is_enabled = true
            """,
            agent_id
        )

        return [row["name"] for row in tool_assignments]

    async def assign_tool_to_agent(self, tool_name: str, agent_id: str) -> bool:
        """
        Assign a tool to an agent.

        Args:
            tool_name: Tool name
            agent_id: Agent ID

        Returns:
            True if successful
        """
        # Get tool ID
        tool_record = await db.fetch_one(
            "SELECT id FROM agent_tools WHERE name = $1",
            tool_name
        )

        if not tool_record:
            logger.error(f"Cannot assign tool '{tool_name}': not found in database")
            return False

        # Check if assignment already exists
        existing = await db.fetch_one(
            """
            SELECT id FROM agent_tool_assignments
            WHERE agent_id = $1 AND tool_id = $2
            """,
            agent_id, tool_record["id"]
        )

        if existing:
            logger.debug(f"Tool '{tool_name}' already assigned to agent {agent_id}")
            return True

        # Create assignment
        try:
            await db.execute(
                """
                INSERT INTO agent_tool_assignments (agent_id, tool_id, is_enabled)
                VALUES ($1, $2, true)
                """,
                agent_id, tool_record["id"]
            )
            logger.info(f"Assigned tool '{tool_name}' to agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to assign tool '{tool_name}' to agent {agent_id}: {e}")
            return False

    async def revoke_tool_from_agent(self, tool_name: str, agent_id: str) -> bool:
        """
        Revoke a tool from an agent.

        Args:
            tool_name: Tool name
            agent_id: Agent ID

        Returns:
            True if successful
        """
        # Get tool ID
        tool_record = await db.fetch_one(
            "SELECT id FROM agent_tools WHERE name = $1",
            tool_name
        )

        if not tool_record:
            logger.error(f"Cannot revoke tool '{tool_name}': not found in database")
            return False

        # Disable assignment
        try:
            await db.execute(
                """
                UPDATE agent_tool_assignments
                SET is_enabled = false
                WHERE agent_id = $1 AND tool_id = $2
                """,
                agent_id, tool_record["id"]
            )
            logger.info(f"Revoked tool '{tool_name}' from agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke tool '{tool_name}' from agent {agent_id}: {e}")
            return False

    async def get_tool_execution_history(
        self,
        tool_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get tool execution history.

        Args:
            tool_name: Filter by tool name
            agent_id: Filter by agent ID
            limit: Maximum number of records

        Returns:
            List of execution records
        """
        query = """
            SELECT te.*, at.name as tool_name, a.name as agent_name
            FROM tool_executions te
            LEFT JOIN agent_tools at ON te.tool_id = at.id
            LEFT JOIN agents a ON te.agent_id = a.id
            WHERE 1=1
        """
        params = []
        param_index = 1

        if tool_name:
            query += f" AND at.name = ${param_index}"
            params.append(tool_name)
            param_index += 1

        if agent_id:
            query += f" AND te.agent_id = ${param_index}"
            params.append(agent_id)
            param_index += 1

        query += " ORDER BY te.created_at DESC LIMIT $1"
        params.insert(0, limit)

        executions = await db.fetch_all(query, *params)

        return [
            {
                "id": row["id"],
                "tool_name": row["tool_name"],
                "agent_name": row["agent_name"],
                "status": row["status"],
                "execution_time_ms": row["execution_time_ms"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "input_params": row["input_params"],
                "output_result": row["output_result"],
                "error_message": row["error_message"]
            }
            for row in executions
        ]

    # ============ Internal Methods ============

    async def _load_tools_from_db(self) -> None:
        """Load tools from database."""
        try:
            tools = await db.fetch_all(
                """
                SELECT name, display_name, description, tool_type, input_schema,
                       output_schema, implementation_type, implementation_config,
                       requires_confirmation
                FROM agent_tools WHERE is_enabled = true
                """
            )

            logger.info(f"Found {len(tools)} tools in database")

            for tool_data in tools:
                try:
                    # Convert database record to ToolDefinition
                    definition = await self._convert_db_to_definition(tool_data)

                    # Check if we have an implementation
                    impl_config_raw = tool_data["implementation_config"]
                    impl_config = {}

                    if impl_config_raw is not None:
                        if isinstance(impl_config_raw, str):
                            try:
                                impl_config = json.loads(impl_config_raw)
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse implementation_config JSON for tool {tool_data.get('name', 'unknown')}")
                                impl_config = {}
                        elif isinstance(impl_config_raw, dict):
                            impl_config = impl_config_raw
                        # else: leave as empty dict for other types

                    implementation = await self._load_implementation(
                        tool_data["implementation_type"], impl_config
                    )

                    if implementation:
                        self.tools[definition.name] = definition
                        self.tool_implementations[definition.name] = implementation
                        logger.debug(f"Loaded tool from DB: {definition.name}")

                except Exception as e:
                    logger.error(f"Failed to load tool {tool_data.get('name', 'unknown')}: {e}")

        except Exception as e:
            logger.error(f"Failed to load tools from database: {e}")
            # Continue without tools from DB

    async def _convert_db_to_definition(self, tool_data: Dict[str, Any]) -> ToolDefinition:
        """Convert database record to ToolDefinition."""
        # Handle input_schema which might be string, dict, or None
        input_schema_raw = tool_data["input_schema"]
        input_schema = {}

        if input_schema_raw is not None:
            if isinstance(input_schema_raw, str):
                try:
                    input_schema = json.loads(input_schema_raw)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse input_schema JSON for tool {tool_data.get('name', 'unknown')}")
                    input_schema = {}
            elif isinstance(input_schema_raw, dict):
                input_schema = input_schema_raw
            else:
                logger.warning(f"Unexpected input_schema type {type(input_schema_raw)} for tool {tool_data.get('name', 'unknown')}")
                input_schema = {}

        # Handle output_schema similarly
        output_schema_raw = tool_data["output_schema"]
        output_schema = None

        if output_schema_raw is not None:
            if isinstance(output_schema_raw, str):
                try:
                    output_schema = json.loads(output_schema_raw)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse output_schema JSON for tool {tool_data.get('name', 'unknown')}")
                    output_schema = None
            elif isinstance(output_schema_raw, dict):
                output_schema = output_schema_raw
            # else: leave as None for other types

        # Extract parameters from schema
        parameters = []
        if "properties" in input_schema:
            for param_name, param_schema in input_schema["properties"].items():
                param = ToolParameter(
                    name=param_name,
                    type=param_schema.get("type", "string"),
                    description=param_schema.get("description", ""),
                    required=param_name in input_schema.get("required", []),
                    default=param_schema.get("default"),
                    enum=param_schema.get("enum")
                )
                parameters.append(param)

        return ToolDefinition(
            name=tool_data["name"],
            display_name=tool_data["display_name"],
            description=tool_data["description"],
            tool_type=ToolType(tool_data["tool_type"]),
            parameters=parameters,
            returns=output_schema,
            requires_confirmation=tool_data["requires_confirmation"],
            timeout_seconds=30,
            max_retries=3
        )

    async def _load_implementation(
        self,
        implementation_type: str,
        implementation_config: Dict[str, Any]
    ) -> Optional[Callable]:
        """
        Load tool implementation based on type and config.

        Note: This is a simplified implementation.
        In production, you would dynamically import modules or use a plugin system.
        """
        # For now, return None - implementations must be registered at runtime
        return None

    async def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        # Database query tool
        db_query_tool = ToolDefinition(
            name="query_database",
            display_name="Query Database",
            description="Execute a SQL query on the NEXUS database",
            tool_type=ToolType.DATABASE,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="SQL query to execute",
                    required=True
                ),
                ToolParameter(
                    name="parameters",
                    type="array",
                    description="Query parameters (for parameterized queries)",
                    required=False,
                    default=[]
                )
            ],
            requires_confirmation=True,  # Sensitive operation
            timeout_seconds=60
        )

        # Notification tool
        notification_tool = ToolDefinition(
            name="send_notification",
            display_name="Send Notification",
            description="Send a notification via configured notification system",
            tool_type=ToolType.NOTIFICATION,
            parameters=[
                ToolParameter(
                    name="title",
                    type="string",
                    description="Notification title",
                    required=True
                ),
                ToolParameter(
                    name="message",
                    type="string",
                    description="Notification message",
                    required=True
                ),
                ToolParameter(
                    name="priority",
                    type="string",
                    description="Priority level (low, normal, high, urgent)",
                    required=False,
                    default="normal",
                    enum=["low", "normal", "high", "urgent"]
                )
            ]
        )

        # Calculator tool
        calculator_tool = ToolDefinition(
            name="calculate",
            display_name="Calculator",
            description="Perform mathematical calculations",
            tool_type=ToolType.CALCULATION,
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="Mathematical expression to evaluate",
                    required=True
                )
            ]
        )

        # Web search tool
        web_search_tool = ToolDefinition(
            name="web_search",
            display_name="Web Search",
            description="Search the web for current information using DuckDuckGo",
            tool_type=ToolType.WEB_SEARCH,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results to return (1-10)",
                    required=False,
                    default=5,
                    min=1,
                    max=10
                )
            ],
            timeout_seconds=15
        )

        # Home Assistant automation tool
        home_assistant_tool = ToolDefinition(
            name="home_assistant_action",
            display_name="Home Assistant Action",
            description="Control Home Assistant devices and services (iPhone, Apple Watch, AirPods, lights, etc.)",
            tool_type=ToolType.HOME_AUTOMATION,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform: call_service, get_state, toggle",
                    required=True,
                    enum=["call_service", "get_state", "toggle"]
                ),
                ToolParameter(
                    name="entity_id",
                    type="string",
                    description="Home Assistant entity ID (e.g., light.living_room, device_tracker.iphone)",
                    required=True
                ),
                ToolParameter(
                    name="service_data",
                    type="object",
                    description="Additional service data (for call_service)",
                    required=False,
                    default={}
                )
            ],
            timeout_seconds=10
        )

        # Register built-in implementations
        builtin_tools = [
            (db_query_tool, self._execute_database_query),
            (notification_tool, self._send_notification),
            (calculator_tool, self._calculate_expression),
            (web_search_tool, self._web_search),
            (home_assistant_tool, self._home_assistant_action),
        ]

        for definition, implementation in builtin_tools:
            try:
                await self.register_tool(definition, implementation)
            except Exception as e:
                logger.error(f"Failed to register built-in tool {definition.name}: {e}")

    async def _validate_tool_signature(
        self,
        definition: ToolDefinition,
        implementation: Callable
    ) -> None:
        """Validate that tool implementation matches definition."""
        sig = inspect.signature(implementation)

        # Check parameter names
        param_names = set(sig.parameters.keys())
        defined_params = {p.name for p in definition.parameters}

        # Implementation can have additional parameters (like agent_id, session_id)
        # but must have all defined parameters
        if not defined_params.issubset(param_names):
            missing = defined_params - param_names
            raise ValueError(
                f"Tool implementation missing parameters: {missing}"
            )

    async def _validate_parameters(
        self,
        definition: ToolDefinition,
        parameters: Dict[str, Any]
    ) -> None:
        """Validate tool parameters against definition."""
        defined_params = {p.name: p for p in definition.parameters}

        for param_name, param_def in defined_params.items():
            if param_name not in parameters:
                if param_def.required:
                    raise ValueError(f"Missing required parameter: {param_name}")
                # Optional parameter with default
                continue

            value = parameters[param_name]

            # Type checking (simplified)
            if param_def.type == "string" and not isinstance(value, str):
                raise ValueError(f"Parameter '{param_name}' must be string")
            elif param_def.type == "integer" and not isinstance(value, int):
                raise ValueError(f"Parameter '{param_name}' must be integer")
            elif param_def.type == "number" and not isinstance(value, (int, float)):
                raise ValueError(f"Parameter '{param_name}' must be number")
            elif param_def.type == "boolean" and not isinstance(value, bool):
                raise ValueError(f"Parameter '{param_name}' must be boolean")

            # Enum validation
            if param_def.enum and value not in param_def.enum:
                raise ValueError(
                    f"Parameter '{param_name}' must be one of {param_def.enum}"
                )

            # Range validation
            if param_def.min is not None and value < param_def.min:
                raise ValueError(
                    f"Parameter '{param_name}' must be >= {param_def.min}"
                )
            if param_def.max is not None and value > param_def.max:
                raise ValueError(
                    f"Parameter '{param_name}' must be <= {param_def.max}"
                )

        # Check for extra parameters
        extra_params = set(parameters.keys()) - set(defined_params.keys())
        if extra_params:
            logger.warning(f"Extra parameters provided to tool '{definition.name}': {extra_params}")

    async def _execute_with_retry(
        self,
        implementation: Callable,
        parameters: Dict[str, Any],
        max_retries: int
    ) -> Any:
        """Execute tool with retry logic."""
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.debug(f"Retry attempt {attempt} for tool execution")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

                return await implementation(**parameters)

            except Exception as e:
                last_error = e
                if attempt == max_retries:
                    break
                logger.warning(f"Tool execution failed (attempt {attempt + 1}): {e}")

        raise last_error

    async def _create_execution_record(
        self,
        tool_name: str,
        agent_id: Optional[str],
        session_id: Optional[str],
        parameters: Dict[str, Any]
    ) -> str:
        """Create tool execution record in database."""
        execution_id = str(uuid.uuid4())

        # Get tool ID
        tool_record = await db.fetch_one(
            "SELECT id FROM agent_tools WHERE name = $1",
            tool_name
        )

        if not tool_record:
            logger.error(f"Tool '{tool_name}' not found in database")
            return execution_id

        await db.execute(
            """
            INSERT INTO tool_executions
            (id, session_id, agent_id, tool_id, input_params, status)
            VALUES ($1, $2, $3, $4, $5, 'executing')
            """,
            execution_id,
            session_id,
            agent_id,
            tool_record["id"],
            json.dumps(parameters)
        )

        return execution_id

    async def _update_execution_record(
        self,
        execution_id: str,
        status: ToolExecutionStatus,
        result: Any
    ) -> None:
        """Update tool execution record with result."""
        end_time = datetime.now()

        # Calculate execution time
        execution = await db.fetch_one(
            "SELECT created_at FROM tool_executions WHERE id = $1",
            execution_id
        )

        execution_time_ms = 0
        if execution and execution["created_at"]:
            start_time = execution["created_at"]
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Update record
        await db.execute(
            """
            UPDATE tool_executions SET
                status = $2,
                output_result = $3,
                execution_time_ms = $4,
                updated_at = NOW()
            WHERE id = $1
            """,
            execution_id,
            status.value,
            json.dumps(result) if result is not None else None,
            execution_time_ms
        )

    async def _log_tool_execution(
        self,
        tool_name: str,
        agent_id: Optional[str],
        session_id: Optional[str],
        parameters: Dict[str, Any],
        result: Any,
        success: bool
    ) -> None:
        """Log tool execution for analytics."""
        # Store in memory history (limited)
        self.tool_execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "agent_id": agent_id,
            "session_id": session_id,
            "success": success,
            "parameters": parameters,
            "result": result if success else str(result)
        })

        # Keep history limited
        if len(self.tool_execution_history) > 1000:
            self.tool_execution_history = self.tool_execution_history[-500:]

    async def _store_tool_in_db(self, definition: ToolDefinition) -> None:
        """Store tool definition in database."""
        # Build input schema
        properties = {}
        required = []

        for param in definition.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }

            if param.default is not None:
                properties[param.name]["default"] = param.default

            if param.enum:
                properties[param.name]["enum"] = param.enum

            if param.min is not None:
                properties[param.name]["minimum"] = param.min

            if param.max is not None:
                properties[param.name]["maximum"] = param.max

            if param.required:
                required.append(param.name)

        input_schema = {
            "type": "object",
            "properties": properties,
            "required": required
        }

        # Check if tool exists
        existing = await db.fetch_one(
            "SELECT id FROM agent_tools WHERE name = $1",
            definition.name
        )

        if existing:
            # Update existing tool
            await db.execute(
                """
                UPDATE agent_tools SET
                    display_name = $2,
                    description = $3,
                    tool_type = $4,
                    input_schema = $5,
                    output_schema = $6,
                    requires_confirmation = $7,
                    updated_at = NOW()
                WHERE id = $1
                """,
                existing["id"],
                definition.display_name,
                definition.description,
                definition.tool_type.value,
                json.dumps(input_schema),
                json.dumps(definition.returns) if definition.returns else None,
                definition.requires_confirmation
            )
        else:
            # Create new tool
            await db.execute(
                """
                INSERT INTO agent_tools
                (name, display_name, description, tool_type, input_schema,
                 output_schema, implementation_type, implementation_config,
                 requires_confirmation)
                VALUES ($1, $2, $3, $4, $5, $6, 'python_function', '{}', $7)
                """,
                definition.name,
                definition.display_name,
                definition.description,
                definition.tool_type.value,
                json.dumps(input_schema),
                json.dumps(definition.returns) if definition.returns else None,
                definition.requires_confirmation
            )

    async def _agent_has_tool_access(self, agent_id: str, tool_name: str) -> bool:
        """Check if agent has access to a tool."""
        result = await db.fetch_one(
            """
            SELECT ata.id FROM agent_tool_assignments ata
            JOIN agent_tools at ON ata.tool_id = at.id
            WHERE ata.agent_id = $1 AND at.name = $2 AND ata.is_enabled = true
            """,
            agent_id, tool_name
        )

        return result is not None

    # ============ Built-in Tool Implementations ============

    async def _execute_database_query(self, query: str, parameters: List[Any] = None) -> List[Dict[str, Any]]:
        """Execute a database query."""
        if not parameters:
            parameters = []

        # Basic security check (prevent destructive operations)
        query_lower = query.lower().strip()
        destructive_keywords = ["drop ", "delete ", "truncate ", "update ", "insert "]

        if any(keyword in query_lower for keyword in destructive_keywords):
            # For destructive operations, require additional validation
            # In production, implement proper authorization
            raise ToolExecutionError(
                "query_database",
                "Destructive database operations require special authorization"
            )

        try:
            if query_lower.startswith("select"):
                results = await db.fetch_all(query, *parameters)
                return [dict(row) for row in results]
            else:
                # For non-SELECT queries, execute and return status
                status = await db.execute(query, *parameters)
                return [{"status": status}]
        except Exception as e:
            raise ToolExecutionError("query_database", f"Database error: {e}")

    async def _send_notification(
        self,
        title: str,
        message: str,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Send a notification."""
        # TODO: Integrate with actual notification system (ntfy, email, etc.)
        logger.info(f"Notification [{priority}]: {title} - {message}")

        return {
            "status": "sent",
            "title": title,
            "message": message,
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        }

    async def _calculate_expression(self, expression: str) -> Dict[str, Any]:
        """Calculate a mathematical expression."""
        # Safe calculator using ast.parse with restricted operations
        # This implementation safely evaluates mathematical expressions

        # Safe expression validation
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            raise ToolExecutionError(
                "calculate",
                "Expression contains invalid characters"
            )

        try:
            # Safe evaluation using ast.parse and restricted operations
            import ast
            import operator

            # Define safe operations
            safe_operators = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.USub: operator.neg,
                ast.UAdd: operator.pos,
            }

            def safe_eval(node):
                if isinstance(node, ast.BinOp):
                    left = safe_eval(node.left)
                    right = safe_eval(node.right)
                    op_type = type(node.op)
                    if op_type not in safe_operators:
                        raise ValueError(f"Unsafe operator: {op_type}")
                    return safe_operators[op_type](left, right)
                elif isinstance(node, ast.UnaryOp):
                    operand = safe_eval(node.operand)
                    op_type = type(node.op)
                    if op_type not in safe_operators:
                        raise ValueError(f"Unsafe operator: {op_type}")
                    return safe_operators[op_type](operand)
                elif isinstance(node, ast.Num):  # Python 3.7 compatibility
                    return node.n
                elif isinstance(node, ast.Constant):  # Python 3.8+
                    return node.value
                else:
                    raise ValueError(f"Unsafe AST node: {type(node)}")

            # Parse the expression
            tree = ast.parse(expression, mode='eval')
            result = safe_eval(tree.body)

            return {
                "expression": expression,
                "result": result,
                "type": type(result).__name__
            }
        except Exception as e:
            raise ToolExecutionError("calculate", f"Calculation error: {e}")

    async def _web_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web using DuckDuckGo."""
        if not DDGS_AVAILABLE:
            raise ToolExecutionError(
                "web_search",
                "DuckDuckGo Search library not installed. Install with: pip install duckduckgo-search"
            )

        try:
            # Use synchronous DDGS in a thread pool to avoid blocking
            import asyncio
            from concurrent.futures import ThreadPoolExecutor

            def sync_search():
                results = []
                with DDGS() as ddgs:
                    for result in ddgs.text(query, max_results=max_results):
                        results.append({
                            "title": result.get("title", ""),
                            "body": result.get("body", ""),
                            "url": result.get("href", ""),
                            "rank": len(results) + 1
                        })
                return results

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                results = await loop.run_in_executor(pool, sync_search)

            if not results:
                return [{"message": "No results found for query", "query": query}]

            return results

        except Exception as e:
            raise ToolExecutionError("web_search", f"Search failed: {str(e)}")

    async def _home_assistant_action(self, action: str, entity_id: str, service_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a Home Assistant action (stub - needs configuration)."""
        logger.info(f"Home Assistant action requested: {action} on {entity_id} with data {service_data}")

        # Placeholder implementation
        # In production, this would call Home Assistant API with authentication
        # Example: POST to http://localhost:8123/api/services/{domain}/{service}

        return {
            "status": "success",
            "message": "Home Assistant tool is configured but not fully implemented. Needs HA access token and configuration.",
            "action": action,
            "entity_id": entity_id,
            "service_data": service_data or {},
            "timestamp": datetime.now().isoformat()
        }

    async def register_tool_from_api(
        self,
        name: str,
        display_name: str,
        description: str,
        tool_type: ToolType,
        input_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None,
        requires_confirmation: bool = False
    ) -> Dict[str, Any]:
        """
        Register a new tool from API parameters.

        This method provides the interface expected by the API router.
        Creates a tool definition and stores it in the database without
        an implementation (tool will need implementation registered separately).

        Args:
            name: Unique tool name
            display_name: Human-readable name
            description: Tool description
            tool_type: Type of tool
            input_schema: JSON Schema for inputs
            output_schema: JSON Schema for outputs (optional)
            requires_confirmation: Whether tool requires human confirmation

        Returns:
            Dictionary with tool information matching ToolResponse schema
        """
        # Convert input_schema to parameters list
        parameters = []
        if "properties" in input_schema:
            for param_name, param_schema in input_schema["properties"].items():
                param = ToolParameter(
                    name=param_name,
                    type=param_schema.get("type", "string"),
                    description=param_schema.get("description", ""),
                    required=param_name in input_schema.get("required", []),
                    default=param_schema.get("default"),
                    enum=param_schema.get("enum")
                )
                parameters.append(param)

        # Create tool definition
        definition = ToolDefinition(
            name=name,
            display_name=display_name,
            description=description,
            tool_type=tool_type,
            parameters=parameters,
            returns=output_schema,
            requires_confirmation=requires_confirmation,
            timeout_seconds=30,
            max_retries=3
        )

        # Create a placeholder implementation that raises an error
        async def placeholder_implementation(**kwargs):
            raise ToolExecutionError(
                name,
                "Tool has no implementation registered. "
                "Register an implementation using the tool system's register_tool method."
            )

        # Register tool with placeholder implementation
        await self.register_tool(definition, placeholder_implementation)

        # Get tool record from database to return full response
        tool_record = await db.fetch_one(
            """
            SELECT id, name, display_name, description, tool_type, input_schema,
                   output_schema, requires_confirmation, is_enabled,
                   (SELECT COUNT(*) FROM tool_executions WHERE tool_id = agent_tools.id) as usage_count,
                   (SELECT AVG(execution_time_ms) FROM tool_executions WHERE tool_id = agent_tools.id) as avg_execution_ms,
                   created_at
            FROM agent_tools WHERE name = $1
            """,
            name
        )

        if not tool_record:
            raise ValueError(f"Tool '{name}' was not created successfully")

        return {
            "id": tool_record["id"],
            "name": tool_record["name"],
            "display_name": tool_record["display_name"],
            "description": tool_record["description"],
            "tool_type": ToolType(tool_record["tool_type"]),
            "input_schema": tool_record["input_schema"],
            "output_schema": tool_record["output_schema"],
            "requires_confirmation": tool_record["requires_confirmation"],
            "is_enabled": tool_record["is_enabled"],
            "usage_count": tool_record["usage_count"] or 0,
            "avg_execution_ms": int(tool_record["avg_execution_ms"]) if tool_record["avg_execution_ms"] else None,
            "created_at": tool_record["created_at"]
        }


# Global tool system instance
tool_system = ToolSystem()


async def get_tool_system() -> ToolSystem:
    """Dependency for FastAPI routes."""
    return tool_system