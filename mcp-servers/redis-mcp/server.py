#!/usr/bin/env python3
"""
Redis MCP Server for NEXUS

Provides read-only access to Redis cache for inspection and monitoring.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import redis.asyncio as redis
from contextlib import asynccontextmanager

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent

from config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisMCP:
    """Redis MCP server implementation."""

    def __init__(self):
        self.server = Server("redis-mcp")
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Initialize Redis client."""
        if self.client is None:
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                max_connections=5
            )
            try:
                await self.client.ping()
                logger.info(f"Redis connected to {settings.redis_host}:{settings.redis_port}")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                raise

    async def disconnect(self):
        """Close Redis client."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Redis client closed")

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching pattern."""
        if not self.client:
            raise RuntimeError("Redis not connected. Call connect() first.")

        try:
            keys = await self.client.keys(pattern)
            return sorted(keys)[:100]  # Limit to 100 keys for safety
        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            raise ValueError(f"Redis error: {str(e)}")

    async def get_key_info(self, key: str) -> Dict[str, Any]:
        """Get information about a key."""
        if not self.client:
            raise RuntimeError("Redis not connected. Call connect() first.")

        try:
            key_type = await self.client.type(key)
            ttl = await self.client.ttl(key)
            memory = await self.client.memory_usage(key)

            info = {
                "key": key,
                "type": key_type,
                "ttl": ttl if ttl >= 0 else "no expiry",
                "memory_bytes": memory
            }

            # Get value based on type (limited size)
            if key_type == "string":
                value = await self.client.get(key)
                if value and len(value) > 1000:
                    info["value"] = value[:1000] + "...(truncated)"
                else:
                    info["value"] = value
            elif key_type == "hash":
                # Get first 5 fields
                fields = await self.client.hgetall(key)
                info["field_count"] = len(fields)
                info["sample_fields"] = dict(list(fields.items())[:5])
            elif key_type == "list":
                length = await self.client.llen(key)
                info["length"] = length
                if length > 0:
                    info["sample_items"] = await self.client.lrange(key, 0, 4)
            elif key_type == "set":
                members = await self.client.smembers(key)
                info["member_count"] = len(members)
                info["sample_members"] = list(members)[:5]
            elif key_type == "zset":
                count = await self.client.zcard(key)
                info["member_count"] = count
                if count > 0:
                    info["sample_members"] = await self.client.zrange(key, 0, 4, withscores=True)

            return info
        except Exception as e:
            logger.error(f"Failed to get key info for {key}: {e}")
            raise ValueError(f"Redis error: {str(e)}")

    async def get_memory_info(self) -> Dict[str, Any]:
        """Get Redis memory information."""
        if not self.client:
            raise RuntimeError("Redis not connected. Call connect() first.")

        try:
            info = await self.client.info("memory")
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                "used_memory_rss": info.get("used_memory_rss", 0),
                "used_memory_rss_human": info.get("used_memory_rss_human", "0B"),
                "maxmemory": info.get("maxmemory", 0),
                "maxmemory_human": info.get("maxmemory_human", "0B"),
                "maxmemory_policy": info.get("maxmemory_policy", "noeviction")
            }
        except Exception as e:
            logger.error(f"Failed to get memory info: {e}")
            raise ValueError(f"Redis error: {str(e)}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics."""
        if not self.client:
            raise RuntimeError("Redis not connected. Call connect() first.")

        try:
            info = await self.client.info()
            return {
                "total_commands_processed": info.get("total_commands_processed", 0),
                "total_connections_received": info.get("total_connections_received", 0),
                "connected_clients": info.get("connected_clients", 0),
                "blocked_clients": info.get("blocked_clients", 0),
                "used_cpu_sys": info.get("used_cpu_sys", 0),
                "used_cpu_user": info.get("used_cpu_user", 0),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1), 1)
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise ValueError(f"Redis error: {str(e)}")

    def create_tools(self) -> List[Tool]:
        """Create MCP tools for Redis operations."""
        return [
            Tool(
                name="list_keys",
                description="List Redis keys matching a pattern (limited to 100 keys)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Key pattern (default: *)",
                            "default": "*"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_key_info",
                description="Get detailed information about a Redis key",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Redis key name"
                        }
                    },
                    "required": ["key"]
                }
            ),
            Tool(
                name="get_memory_info",
                description="Get Redis memory usage information",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_stats",
                description="Get Redis performance statistics",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]

    async def handle_list_keys(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle list_keys tool call."""
        pattern = arguments.get("pattern", "*")
        keys = await self.list_keys(pattern)

        if not keys:
            return [TextContent(type="text", text=f"No keys found matching pattern '{pattern}'")]

        lines = [f"Found {len(keys)} keys matching '{pattern}':"]
        for key in keys[:50]:  # Show first 50 keys
            lines.append(f"- {key}")

        if len(keys) > 50:
            lines.append(f"... and {len(keys) - 50} more keys")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_get_key_info(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_key_info tool call."""
        key = arguments.get("key")
        if not key:
            raise ValueError("key is required")

        info = await self.get_key_info(key)
        lines = [f"Information for key '{key}':"]
        lines.append(f"Type: {info['type']}")
        lines.append(f"TTL: {info['ttl']}")
        lines.append(f"Memory: {info['memory_bytes']:,} bytes")

        if 'value' in info:
            lines.append(f"Value: {info['value']}")
        elif 'field_count' in info:
            lines.append(f"Field count: {info['field_count']}")
            if 'sample_fields' in info:
                lines.append("Sample fields:")
                for k, v in info['sample_fields'].items():
                    lines.append(f"  {k}: {v}")
        elif 'length' in info:
            lines.append(f"Length: {info['length']}")
            if 'sample_items' in info:
                lines.append(f"Sample items: {info['sample_items']}")
        elif 'member_count' in info:
            lines.append(f"Member count: {info['member_count']}")
            if 'sample_members' in info:
                lines.append(f"Sample members: {info['sample_members']}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_get_memory_info(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_memory_info tool call."""
        memory = await self.get_memory_info()
        lines = ["Redis Memory Information:"]
        lines.append(f"Used memory: {memory['used_memory_human']} ({memory['used_memory']:,} bytes)")
        lines.append(f"Peak memory: {memory['used_memory_peak_human']} ({memory['used_memory_peak']:,} bytes)")
        lines.append(f"RSS memory: {memory['used_memory_rss_human']} ({memory['used_memory_rss']:,} bytes)")
        lines.append(f"Max memory: {memory['maxmemory_human']} ({memory['maxmemory']:,} bytes)")
        lines.append(f"Eviction policy: {memory['maxmemory_policy']}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_get_stats(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_stats tool call."""
        stats = await self.get_stats()
        lines = ["Redis Performance Statistics:"]
        lines.append(f"Connected clients: {stats['connected_clients']}")
        lines.append(f"Blocked clients: {stats['blocked_clients']}")
        lines.append(f"Total connections: {stats['total_connections_received']:,}")
        lines.append(f"Total commands: {stats['total_commands_processed']:,}")
        lines.append(f"Instantaneous OPS: {stats['instantaneous_ops_per_sec']}")
        lines.append(f"Keyspace hits: {stats['keyspace_hits']:,}")
        lines.append(f"Keyspace misses: {stats['keyspace_misses']:,}")
        lines.append(f"Hit rate: {stats['hit_rate']:.2%}")
        lines.append(f"CPU system: {stats['used_cpu_sys']:.2f}s")
        lines.append(f"CPU user: {stats['used_cpu_user']:.2f}s")

        return [TextContent(type="text", text="\n".join(lines))]

    async def run(self):
        """Run the MCP server."""
        # Connect to Redis
        await self.connect()

        # Setup server
        @self.server.list_tools()
        async def handle_list_tools():
            return self.create_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]):
            logger.info(f"Tool call: {name} with args {arguments}")
            if name == "list_keys":
                return await self.handle_list_keys(arguments)
            elif name == "get_key_info":
                return await self.handle_get_key_info(arguments)
            elif name == "get_memory_info":
                return await self.handle_get_memory_info(arguments)
            elif name == "get_stats":
                return await self.handle_get_stats(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

        # Run server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="redis-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main entry point."""
    server = RedisMCP()
    try:
        await server.run()
    finally:
        await server.disconnect()


if __name__ == "__main__":
    asyncio.run(main())