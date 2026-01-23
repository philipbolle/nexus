#!/usr/bin/env python3
"""
ChromaDB MCP Server for NEXUS

Provides read-only access to ChromaDB vector store for inspection and queries.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent

from config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChromaDBMCP:
    """ChromaDB MCP server implementation."""

    def __init__(self):
        self.server = Server("chromadb-mcp")
        self.client: Optional[chromadb.Client] = None
        self.collection: Optional[chromadb.Collection] = None

    async def connect(self):
        """Initialize ChromaDB client."""
        if self.client is None:
            try:
                self.client = chromadb.HttpClient(
                    host=settings.chromadb_host,
                    port=settings.chromadb_port
                )
                logger.info(f"ChromaDB connected to {settings.chromadb_host}:{settings.chromadb_port}")

                # Try to get the default collection
                try:
                    self.collection = self.client.get_collection(settings.chromadb_collection)
                    logger.info(f"Using collection '{settings.chromadb_collection}'")
                except Exception as e:
                    logger.warning(f"Collection '{settings.chromadb_collection}' not found: {e}")
                    self.collection = None

            except Exception as e:
                logger.error(f"ChromaDB connection failed: {e}")
                raise

    async def disconnect(self):
        """Close ChromaDB client."""
        self.client = None
        self.collection = None
        logger.info("ChromaDB client closed")

    async def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections."""
        if not self.client:
            raise RuntimeError("ChromaDB not connected. Call connect() first.")

        try:
            collections = self.client.list_collections()
            result = []
            for coll in collections:
                result.append({
                    "name": coll.name,
                    "id": coll.id,
                    "metadata": coll.metadata
                })
            return result
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise ValueError(f"ChromaDB error: {str(e)}")

    async def get_collection_info(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a collection."""
        if not self.client:
            raise RuntimeError("ChromaDB not connected. Call connect() first.")

        try:
            coll_name = collection_name or settings.chromadb_collection
            collection = self.client.get_collection(coll_name)

            # Get count (limited to avoid performance issues)
            count = collection.count()

            # Get sample items (first 5)
            results = collection.peek(limit=5)

            return {
                "name": collection.name,
                "id": collection.id,
                "metadata": collection.metadata,
                "count": count,
                "sample_items": {
                    "ids": results["ids"][:5] if results["ids"] else [],
                    "documents": results["documents"][:5] if results["documents"] else [],
                    "metadatas": results["metadatas"][:5] if results["metadatas"] else []
                }
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise ValueError(f"ChromaDB error: {str(e)}")

    async def query_collection(
        self,
        query_text: str,
        collection_name: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Query a collection with text."""
        if not self.client:
            raise RuntimeError("ChromaDB not connected. Call connect() first.")

        try:
            coll_name = collection_name or settings.chromadb_collection
            collection = self.client.get_collection(coll_name)

            results = collection.query(
                query_texts=[query_text],
                n_results=min(limit, 10)  # Limit to 10 for safety
            )

            return {
                "collection": coll_name,
                "query": query_text,
                "results": {
                    "ids": results["ids"][0] if results["ids"] else [],
                    "documents": results["documents"][0] if results["documents"] else [],
                    "distances": results["distances"][0] if results["distances"] else [],
                    "metadatas": results["metadatas"][0] if results["metadatas"] else []
                }
            }
        except Exception as e:
            logger.error(f"Failed to query collection: {e}")
            raise ValueError(f"ChromaDB error: {str(e)}")

    async def get_system_info(self) -> Dict[str, Any]:
        """Get ChromaDB system information."""
        if not self.client:
            raise RuntimeError("ChromaDB not connected. Call connect() first.")

        try:
            # ChromaDB HTTP client doesn't have a direct info method
            # We'll return basic connection info
            return {
                "host": settings.chromadb_host,
                "port": settings.chromadb_port,
                "default_collection": settings.chromadb_collection,
                "status": "connected"
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            raise ValueError(f"ChromaDB error: {str(e)}")

    def create_tools(self) -> List[Tool]:
        """Create MCP tools for ChromaDB operations."""
        return [
            Tool(
                name="list_collections",
                description="List all collections in ChromaDB",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_collection_info",
                description="Get information about a ChromaDB collection",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "collection_name": {
                            "type": "string",
                            "description": "Collection name (default: from config)"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="query_collection",
                description="Query a ChromaDB collection with text",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query_text": {
                            "type": "string",
                            "description": "Text to search for"
                        },
                        "collection_name": {
                            "type": "string",
                            "description": "Collection name (default: from config)"
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum results (default: 5, max: 10)",
                            "default": 5
                        }
                    },
                    "required": ["query_text"]
                }
            ),
            Tool(
                name="get_system_info",
                description="Get ChromaDB system information",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]

    async def handle_list_collections(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle list_collections tool call."""
        collections = await self.list_collections()
        if not collections:
            return [TextContent(type="text", text="No collections found")]

        lines = [f"Found {len(collections)} collections:"]
        for coll in collections:
            lines.append(f"\n- {coll['name']} (ID: {coll['id']})")
            if coll.get('metadata'):
                lines.append(f"  Metadata: {coll['metadata']}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_get_collection_info(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_collection_info tool call."""
        collection_name = arguments.get("collection_name")
        info = await self.get_collection_info(collection_name)

        lines = [f"Collection: {info['name']}"]
        lines.append(f"ID: {info['id']}")
        lines.append(f"Document count: {info['count']:,}")

        if info.get('metadata'):
            lines.append(f"Metadata: {info['metadata']}")

        if info.get('sample_items') and info['sample_items']['ids']:
            lines.append("\nSample documents:")
            for i, (doc_id, document) in enumerate(zip(
                info['sample_items']['ids'],
                info['sample_items']['documents']
            )):
                lines.append(f"\n{i+1}. ID: {doc_id}")
                if document:
                    preview = document[:200] + "..." if len(document) > 200 else document
                    lines.append(f"   Document: {preview}")
                if (info['sample_items']['metadatas'] and
                    i < len(info['sample_items']['metadatas']) and
                    info['sample_items']['metadatas'][i]):
                    lines.append(f"   Metadata: {info['sample_items']['metadatas'][i]}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_query_collection(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle query_collection tool call."""
        query_text = arguments.get("query_text")
        collection_name = arguments.get("collection_name")
        limit = arguments.get("limit", 5)

        if not query_text:
            raise ValueError("query_text is required")

        results = await self.query_collection(query_text, collection_name, limit)

        lines = [f"Query results for '{query_text}' in collection '{results['collection']}':"]
        if not results['results']['ids']:
            lines.append("No results found.")
            return [TextContent(type="text", text="\n".join(lines))]

        for i, (doc_id, document, distance) in enumerate(zip(
            results['results']['ids'],
            results['results']['documents'],
            results['results']['distances']
        )):
            lines.append(f"\n{i+1}. ID: {doc_id}")
            lines.append(f"   Distance: {distance:.4f}")
            if document:
                preview = document[:200] + "..." if len(document) > 200 else document
                lines.append(f"   Document: {preview}")

            if (results['results']['metadatas'] and
                i < len(results['results']['metadatas']) and
                results['results']['metadatas'][i]):
                lines.append(f"   Metadata: {results['results']['metadatas'][i]}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_get_system_info(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_system_info tool call."""
        info = await self.get_system_info()
        lines = ["ChromaDB System Information:"]
        lines.append(f"Host: {info['host']}")
        lines.append(f"Port: {info['port']}")
        lines.append(f"Default collection: {info['default_collection']}")
        lines.append(f"Status: {info['status']}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def run(self):
        """Run the MCP server."""
        # Connect to ChromaDB
        await self.connect()

        # Setup server
        @self.server.list_tools()
        async def handle_list_tools():
            return self.create_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]):
            logger.info(f"Tool call: {name} with args {arguments}")
            if name == "list_collections":
                return await self.handle_list_collections(arguments)
            elif name == "get_collection_info":
                return await self.handle_get_collection_info(arguments)
            elif name == "query_collection":
                return await self.handle_query_collection(arguments)
            elif name == "get_system_info":
                return await self.handle_get_system_info(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

        # Run server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="chromadb-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main entry point."""
    server = ChromaDBMCP()
    try:
        await server.run()
    finally:
        await server.disconnect()


if __name__ == "__main__":
    asyncio.run(main())