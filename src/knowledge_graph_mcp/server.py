#!/usr/bin/env python3
# type: ignore

"""
MCP server for Knowledge Graph with Neo4j backend.
Clean main entry point that registers all resources and tools from modular components.
"""

import asyncio
import logging

from mcp.server.fastmcp import FastMCP

from .resources.mcp_resources import register_schema_resources
from .resources.schemas import knowledge_graph_schema
from .tools.db_operations import close_connections
from .tools.mcp_tools.analytics_tools import register_analytics_tools
from .tools.mcp_tools.combined_tools import register_combined_tools
from .tools.mcp_tools.node_tools import register_node_tools
from .tools.mcp_tools.relationship_tools import register_relationship_tools
from .tools.mcp_tools.utility_tools import register_utility_tools
from .tools.mcp_tools.vector_tools import register_vector_tools
from .utils.index_init import ensure_vector_index_exists

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("knowledge-graph-mcp")

mcp = FastMCP("knowledge-graph-mcp")


async def initialize_vector_system():
    """Initialize vector system during server startup."""
    try:
        logger.info("Initializing vector system...")

        # Get vector configuration
        # Ensure vector index exists
        await ensure_vector_index_exists(
            index_name="entity_embedding_index",
            dimensions=384,
            similarity_function="cosine",
        )

        logger.info("Vector system initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Vector system initialization failed: {e}")
        logger.error("""This may indicate:
        1. Neo4j database is not running
        2. Neo4j version doesn't support vector indexes (requires 5.11+)
        3. Database connection configuration is incorrect""")
        raise


def main():
    """Main entry point for the MCP server."""
    logger.info("Starting Knowledge Graph MCP Server")
    logger.info(
        f"Schema loaded with {len(knowledge_graph_schema.entity_types)} entity types"
    )
    logger.info(
        f"Schema loaded with {len(knowledge_graph_schema.relationships)} relationship definitions"
    )

    # Initialize vector system before starting server
    try:
        asyncio.run(initialize_vector_system())
    except Exception as e:
        logger.error(f"Failed to initialize vector system: {e}")
        logger.error(
            "Server startup aborted due to vector system initialization failure"
        )
        return

    # Register all components
    logger.info("Registering MCP resources and tools...")

    # Register schema resources
    register_schema_resources(mcp)
    logger.info("Schema resources registered")

    # Register tool modules
    register_node_tools(mcp)
    register_relationship_tools(mcp)
    register_combined_tools(mcp)
    register_analytics_tools(mcp)
    register_utility_tools(mcp)
    register_vector_tools(mcp)
    logger.info("All MCP tools registered successfully")

    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Shutting down Knowledge Graph MCP Server")
    finally:
        # Cleanup on shutdown
        try:
            asyncio.run(close_connections())
            logger.info("Database connections closed")
        except Exception as e:
            logger.warning(f"Error during connection cleanup: {e}")
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    main()
