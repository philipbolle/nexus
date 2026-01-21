#!/usr/bin/env python3
"""
PostgreSQL MCP Server for NEXUS Database

Provides read-only access to PostgreSQL database for schema inspection and queries.
"""

import asyncio
import asyncpg
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent

from config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PostgresMCP:
    """PostgreSQL MCP server implementation."""

    def __init__(self):
        self.server = Server("postgres-mcp")
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Initialize PostgreSQL connection pool."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=settings.dsn,
                min_size=1,
                max_size=5,
                command_timeout=30,
            )
            logger.info("PostgreSQL connection pool created")

    async def disconnect(self):
        """Close PostgreSQL connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("PostgreSQL connection pool closed")

    @asynccontextmanager
    async def connection(self):
        """Get a connection from the pool."""
        if not self.pool:
            raise RuntimeError("PostgreSQL not connected. Call connect() first.")
        async with self.pool.acquire() as conn:
            yield conn

    async def list_tables(self) -> List[str]:
        """List all tables in the database."""
        async with self.connection() as conn:
            rows = await conn.fetch("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            return [row['table_name'] for row in rows]

    async def describe_table(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema including columns, types, and constraints."""
        async with self.connection() as conn:
            # Get column information
            columns = await conn.fetch("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = $1
                ORDER BY ordinal_position
            """, table_name)

            # Get primary key information
            pk = await conn.fetch("""
                SELECT
                    kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = 'public'
                AND tc.table_name = $1
                AND tc.constraint_type = 'PRIMARY KEY'
            """, table_name)

            pk_columns = {row['column_name'] for row in pk}

            result = []
            for row in columns:
                result.append({
                    'column_name': row['column_name'],
                    'data_type': row['data_type'],
                    'is_nullable': row['is_nullable'],
                    'column_default': row['column_default'],
                    'is_primary_key': row['column_name'] in pk_columns
                })
            return result

    async def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query safely.
        Only allows SELECT queries for read-only access.
        """
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed for safety")

        async with self.connection() as conn:
            # Limit results to 1000 rows for safety
            limited_query = query.strip()
            if "LIMIT" not in query_upper:
                if ";" in limited_query:
                    limited_query = limited_query.replace(";", " LIMIT 1000;")
                else:
                    limited_query += " LIMIT 1000"

            params = params or []
            rows = await conn.fetch(limited_query, *params)
            return [dict(row) for row in rows]

    async def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get table statistics including row count and approximate size."""
        async with self.connection() as conn:
            # Get row count
            count_row = await conn.fetchrow(
                "SELECT COUNT(*) as row_count FROM public.{}".format(table_name)
            )
            row_count = count_row['row_count'] if count_row else 0

            # Get table size (approximate)
            size_row = await conn.fetchrow("""
                SELECT
                    pg_total_relation_size('public.' || $1) as total_size,
                    pg_relation_size('public.' || $1) as table_size,
                    pg_indexes_size('public.' || $1) as index_size
            """, table_name)

            return {
                'table_name': table_name,
                'row_count': row_count,
                'total_size_bytes': size_row['total_size'] if size_row else 0,
                'table_size_bytes': size_row['table_size'] if size_row else 0,
                'index_size_bytes': size_row['index_size'] if size_row else 0
            }

    async def search_schema(self, pattern: str) -> List[Dict[str, Any]]:
        """Search for tables and columns matching a pattern."""
        async with self.connection() as conn:
            results = await conn.fetch("""
                SELECT
                    t.table_name,
                    c.column_name,
                    c.data_type,
                    c.is_nullable
                FROM information_schema.tables t
                JOIN information_schema.columns c
                ON t.table_schema = c.table_schema
                AND t.table_name = c.table_name
                WHERE t.table_schema = 'public'
                AND (t.table_name ILIKE '%' || $1 || '%'
                     OR c.column_name ILIKE '%' || $1 || '%')
                ORDER BY t.table_name, c.ordinal_position
                LIMIT 100
            """, pattern)

            return [dict(row) for row in results]

    def create_tools(self) -> List[Tool]:
        """Create MCP tools for PostgreSQL operations."""
        return [
            Tool(
                name="list_tables",
                description="List all tables in the PostgreSQL database",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="describe_table",
                description="Get detailed schema information for a specific table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to describe"
                        }
                    },
                    "required": ["table_name"]
                }
            ),
            Tool(
                name="execute_query",
                description="Execute a SELECT query safely (read-only, limited to 1000 rows)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SELECT query to execute"
                        },
                        "params": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional query parameters"
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="get_table_stats",
                description="Get statistics for a table (row count, size)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table"
                        }
                    },
                    "required": ["table_name"]
                }
            ),
            Tool(
                name="search_schema",
                description="Search for tables and columns by name pattern",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Search pattern (case-insensitive)"
                        }
                    },
                    "required": ["pattern"]
                }
            )
        ]

    async def handle_list_tables(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle list_tables tool call."""
        tables = await self.list_tables()
        return [TextContent(
            type="text",
            text=f"Found {len(tables)} tables:\n" + "\n".join(f"- {table}" for table in tables)
        )]

    async def handle_describe_table(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle describe_table tool call."""
        table_name = arguments.get("table_name")
        if not table_name:
            raise ValueError("table_name is required")

        schema = await self.describe_table(table_name)
        if not schema:
            return [TextContent(type="text", text=f"Table '{table_name}' not found or has no columns")]

        lines = [f"Schema for table '{table_name}':"]
        for col in schema:
            pk = " (PK)" if col['is_primary_key'] else ""
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
            lines.append(f"- {col['column_name']}: {col['data_type']}{pk} {nullable}{default}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_execute_query(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle execute_query tool call."""
        query = arguments.get("query")
        if not query:
            raise ValueError("query is required")

        params = arguments.get("params", [])

        try:
            rows = await self.execute_query(query, params)
            if not rows:
                return [TextContent(type="text", text="Query returned no results")]

            # Format results as a simple table
            if len(rows) == 0:
                return [TextContent(type="text", text="Query returned 0 rows")]

            # Get column names from first row
            columns = list(rows[0].keys())
            header = " | ".join(columns)
            separator = "-" * len(header)

            lines = [f"Returned {len(rows)} rows:", separator, header, separator]
            for row in rows[:10]:  # Show first 10 rows
                line = " | ".join(str(row.get(col, "")) for col in columns)
                lines.append(line)

            if len(rows) > 10:
                lines.append(f"... and {len(rows) - 10} more rows")

            return [TextContent(type="text", text="\n".join(lines))]
        except ValueError as e:
            return [TextContent(type="text", text=f"Query error: {str(e)}")]
        except Exception as e:
            logger.exception("Query execution failed")
            return [TextContent(type="text", text=f"Database error: {str(e)}")]

    async def handle_get_table_stats(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_table_stats tool call."""
        table_name = arguments.get("table_name")
        if not table_name:
            raise ValueError("table_name is required")

        stats = await self.get_table_stats(table_name)
        text = f"Statistics for table '{table_name}':\n"
        text += f"- Row count: {stats['row_count']:,}\n"
        text += f"- Total size: {stats['total_size_bytes']:,} bytes ({stats['total_size_bytes'] / 1024 / 1024:.2f} MB)\n"
        text += f"- Table size: {stats['table_size_bytes']:,} bytes\n"
        text += f"- Index size: {stats['index_size_bytes']:,} bytes"

        return [TextContent(type="text", text=text)]

    async def handle_search_schema(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle search_schema tool call."""
        pattern = arguments.get("pattern")
        if not pattern:
            raise ValueError("pattern is required")

        results = await self.search_schema(pattern)
        if not results:
            return [TextContent(type="text", text=f"No tables or columns found matching '{pattern}'")]

        # Group by table
        grouped = {}
        for result in results:
            table = result['table_name']
            if table not in grouped:
                grouped[table] = []
            grouped[table].append(result)

        lines = [f"Found {len(results)} matches for '{pattern}':"]
        for table, columns in grouped.items():
            lines.append(f"\n{table}:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                lines.append(f"  - {col['column_name']}: {col['data_type']} ({nullable})")

        return [TextContent(type="text", text="\n".join(lines))]

    async def run(self):
        """Run the MCP server."""
        # Connect to database
        await self.connect()

        # Setup server
        @self.server.list_tools()
        async def handle_list_tools():
            return self.create_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]):
            logger.info(f"Tool call: {name} with args {arguments}")
            if name == "list_tables":
                return await self.handle_list_tables(arguments)
            elif name == "describe_table":
                return await self.handle_describe_table(arguments)
            elif name == "execute_query":
                return await self.handle_execute_query(arguments)
            elif name == "get_table_stats":
                return await self.handle_get_table_stats(arguments)
            elif name == "search_schema":
                return await self.handle_search_schema(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

        # Run server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="postgres-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main entry point."""
    server = PostgresMCP()
    try:
        await server.run()
    finally:
        await server.disconnect()


if __name__ == "__main__":
    asyncio.run(main())