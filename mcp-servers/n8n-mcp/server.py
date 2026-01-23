#!/usr/bin/env python3
"""
n8n Workflow MCP Server for NEXUS

Provides access to n8n workflow automation through MCP tools.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent

from config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class N8nMCP:
    """n8n MCP server implementation."""

    def __init__(self):
        self.server = Server("n8n-mcp")
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self):
        """Initialize HTTP client."""
        if self.client is None:
            headers = {"User-Agent": "n8n-mcp/1.0.0"}
            if settings.n8n_api_key:
                headers["X-N8N-API-KEY"] = settings.n8n_api_key

            self.client = httpx.AsyncClient(
                base_url=settings.n8n_api_url,
                timeout=settings.request_timeout,
                headers=headers
            )
            logger.info(f"n8n HTTP client created for {settings.n8n_api_url}")

    async def disconnect(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("n8n HTTP client closed")

    async def _make_request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to n8n API."""
        if not self.client:
            raise RuntimeError("HTTP client not connected. Call connect() first.")

        try:
            response = await self.client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {method} {path}: {e.response.text}")
            raise ValueError(f"n8n API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Request failed for {method} {path}: {str(e)}")
            raise ValueError(f"Request failed: {str(e)}")

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows."""
        # n8n REST API endpoint for workflows
        data = await self._make_request("GET", "/api/v1/workflows")
        return data.get("data", [])

    async def get_workflow_details(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow details by ID."""
        data = await self._make_request("GET", f"/api/v1/workflows/{workflow_id}")
        return data

    async def trigger_workflow(self, workflow_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        """Trigger workflow execution."""
        # n8n webhook trigger endpoint
        # Note: This assumes webhook-triggered workflows
        # For API-triggered workflows, use the appropriate endpoint
        webhook_path = f"/webhook/{workflow_id}"
        data = await self._make_request("POST", webhook_path, json=payload or {})
        return data

    async def get_executions(self, workflow_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get workflow executions."""
        # n8n executions endpoint
        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id

        data = await self._make_request("GET", "/api/v1/executions", params=params)
        return data.get("data", [])

    async def get_system_status(self) -> Dict[str, Any]:
        """Get n8n system status."""
        # n8n health endpoint
        try:
            data = await self._make_request("GET", "/healthz")
            return {"status": "healthy", "details": data}
        except Exception:
            return {"status": "unreachable"}

    def create_tools(self) -> List[Tool]:
        """Create MCP tools for n8n operations."""
        return [
            Tool(
                name="list_workflows",
                description="List all n8n workflows",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_workflow_details",
                description="Get detailed information about a workflow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "Workflow ID or name"
                        }
                    },
                    "required": ["workflow_id"]
                }
            ),
            Tool(
                name="trigger_workflow",
                description="Trigger a workflow execution",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "Workflow ID or webhook path"
                        },
                        "payload": {
                            "type": "object",
                            "description": "Optional payload for workflow"
                        }
                    },
                    "required": ["workflow_id"]
                }
            ),
            Tool(
                name="get_executions",
                description="Get workflow executions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "Optional workflow ID to filter"
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of executions (default: 10)",
                            "default": 10
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_system_status",
                description="Get n8n system status",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]

    async def handle_list_workflows(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle list_workflows tool call."""
        workflows = await self.list_workflows()
        if not workflows:
            return [TextContent(type="text", text="No workflows found")]

        lines = [f"Found {len(workflows)} workflows:"]
        for wf in workflows[:20]:  # Limit to 20
            lines.append(f"\n- {wf.get('name', 'Unnamed')} (ID: {wf.get('id', 'N/A')})")
            lines.append(f"  Active: {wf.get('active', 'N/A')}")
            if 'nodes' in wf:
                lines.append(f"  Nodes: {len(wf['nodes'])}")

        if len(workflows) > 20:
            lines.append(f"\n... and {len(workflows) - 20} more workflows")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_get_workflow_details(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_workflow_details tool call."""
        workflow_id = arguments.get("workflow_id")
        if not workflow_id:
            raise ValueError("workflow_id is required")

        details = await self.get_workflow_details(workflow_id)
        lines = [f"Workflow: {details.get('name', 'Unnamed')}"]
        lines.append(f"ID: {details.get('id', 'N/A')}")
        lines.append(f"Active: {details.get('active', 'N/A')}")
        lines.append(f"Created: {details.get('createdAt', 'N/A')}")
        lines.append(f"Updated: {details.get('updatedAt', 'N/A')}")

        if 'nodes' in details:
            lines.append(f"\nNodes ({len(details['nodes'])}):")
            for node in details['nodes'][:10]:  # Show first 10 nodes
                lines.append(f"- {node.get('name', 'Unnamed')} ({node.get('type', 'N/A')})")
            if len(details['nodes']) > 10:
                lines.append(f"... and {len(details['nodes']) - 10} more nodes")

        if 'tags' in details and details['tags']:
            lines.append(f"\nTags: {', '.join(details['tags'])}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_trigger_workflow(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle trigger_workflow tool call."""
        workflow_id = arguments.get("workflow_id")
        payload = arguments.get("payload", {})

        if not workflow_id:
            raise ValueError("workflow_id is required")

        result = await self.trigger_workflow(workflow_id, payload)
        lines = [f"Workflow triggered: {workflow_id}"]
        lines.append(f"Execution ID: {result.get('executionId', 'N/A')}")
        lines.append(f"Status: {result.get('status', 'N/A')}")

        if 'data' in result:
            lines.append(f"Output data keys: {', '.join(result['data'].keys())}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_get_executions(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_executions tool call."""
        workflow_id = arguments.get("workflow_id")
        limit = arguments.get("limit", 10)

        executions = await self.get_executions(workflow_id, limit)
        if not executions:
            return [TextContent(type="text", text="No executions found")]

        lines = [f"Found {len(executions)} executions:"]
        for exec in executions[:limit]:
            lines.append(f"\n- Execution {exec.get('id', 'N/A')}:")
            lines.append(f"  Workflow: {exec.get('workflowName', 'N/A')}")
            lines.append(f"  Status: {exec.get('status', 'N/A')}")
            lines.append(f"  Started: {exec.get('startedAt', 'N/A')}")
            if 'stoppedAt' in exec:
                lines.append(f"  Stopped: {exec['stoppedAt']}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_get_system_status(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_system_status tool call."""
        status = await self.get_system_status()
        lines = ["n8n System Status:"]
        lines.append(f"Status: {status['status']}")

        if status['status'] == "healthy" and 'details' in status:
            details = status['details']
            lines.append(f"Version: {details.get('version', 'N/A')}")
            lines.append(f"Uptime: {details.get('uptime', 'N/A')}")
            if 'stats' in details:
                lines.append(f"Workflows: {details['stats'].get('workflows', 'N/A')}")
                lines.append(f"Executions: {details['stats'].get('executions', 'N/A')}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def run(self):
        """Run the MCP server."""
        # Connect to n8n
        await self.connect()

        # Setup server
        @self.server.list_tools()
        async def handle_list_tools():
            return self.create_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]):
            logger.info(f"Tool call: {name} with args {arguments}")
            if name == "list_workflows":
                return await self.handle_list_workflows(arguments)
            elif name == "get_workflow_details":
                return await self.handle_get_workflow_details(arguments)
            elif name == "trigger_workflow":
                return await self.handle_trigger_workflow(arguments)
            elif name == "get_executions":
                return await self.handle_get_executions(arguments)
            elif name == "get_system_status":
                return await self.handle_get_system_status(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

        # Run server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="n8n-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main entry point."""
    server = N8nMCP()
    try:
        await server.run()
    finally:
        await server.disconnect()


if __name__ == "__main__":
    asyncio.run(main())