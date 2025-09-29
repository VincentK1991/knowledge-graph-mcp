"""
Vector index initialization for Knowledge Graph MCP server.
"""

import logging
from typing import Optional

from ..tools.db_operations import Neo4jConnector

logger = logging.getLogger("knowledge-graph-mcp.index_init")

async def ensure_vector_index_exists(
    index_name: str = "entity_embedding_index",
    dimensions: int = 384,
    similarity_function: str = "cosine",
    database: Optional[str] = None,
) -> bool:
    """Ensure vector index exists for Entity nodes."""
    # Check if index exists
    check_query = """
    SHOW INDEXES YIELD name, type
    WHERE name = $index_name AND type = 'VECTOR'
    RETURN count(*) > 0 as exists
    """

    result = await Neo4jConnector.execute_read_query(
        check_query, {"index_name": index_name}, database
    )

    if result and result[0].get("exists", False):
        logger.info(f"Vector index '{index_name}' already exists")
        return True

    # Create index
    create_query = f"""
    CREATE VECTOR INDEX {index_name} IF NOT EXISTS
    FOR (n:Entity) ON (n.embedding_vector)
    OPTIONS {{
      indexConfig: {{
        `vector.dimensions`: $dimensions,
        `vector.similarity_function`: $similarity_function
      }}
    }}
    """

    await Neo4jConnector.execute_write_query(
        create_query,
        {"dimensions": dimensions, "similarity_function": similarity_function},
        database,
    )

    logger.info(f"Vector index '{index_name}' created successfully")
    return True
