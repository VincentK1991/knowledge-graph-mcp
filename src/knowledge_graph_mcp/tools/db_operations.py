"""
Neo4j database operations for the Knowledge Graph MCP server.

This module provides Neo4j database connectivity and operations for managing
knowledge graph entities and relationships.
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, ClassVar, Dict, List, LiteralString, Optional, cast

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncManagedTransaction, AsyncSession
from neo4j.exceptions import ServiceUnavailable, TransientError

from ..utils.property_filter import clean_properties
from ..utils.text_extractor import extract_text_from_properties
from ..utils.vector_embedding import VectorEmbedding

logger = logging.getLogger("knowledge-graph-mcp.db_operations")


class Neo4jConnector:
    """
    Neo4j database connector for the Knowledge Graph MCP server.

    Manages connections to Neo4j database with connection pooling,
    automatic retry logic, and proper resource cleanup.
    """

    _drivers: ClassVar[Dict[str, AsyncDriver]] = {}

    @classmethod
    def _get_config_key(cls, uri: str, user: str) -> str:
        """Generate a unique key for the config to use as cache key."""
        return f"{uri}:{user}"

    @classmethod
    def _get_config_from_env(cls) -> tuple[str, str, str]:
        """
        Get Neo4j configuration from environment variables.

        Returns:
            Tuple of (uri, user, password)

        Raises:
            ValueError: If required environment variables are missing
        """
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7688")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")

        # Note: Using default password from Docker Compose configuration
        # In production, always set NEO4J_PASSWORD environment variable

        logger.info(f"Connecting to Neo4j at {uri} as user {user}")
        return uri, user, password

    @classmethod
    async def get_driver(
        cls,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> AsyncDriver:
        """
        Get or create an AsyncDriver based on the provided config or environment variables.

        Args:
            uri: Neo4j URI (defaults to NEO4J_URI env var or bolt://localhost:7687)
            user: Neo4j username (defaults to NEO4J_USER env var or 'neo4j')
            password: Neo4j password (defaults to NEO4J_PASSWORD env var)

        Returns:
            AsyncDriver instance

        Raises:
            ValueError: If password is not provided and NEO4J_PASSWORD is not set
        """
        # Use provided config or fall back to environment variables
        if uri is None or user is None or password is None:
            env_uri, env_user, env_password = cls._get_config_from_env()
            uri = uri or env_uri
            user = user or env_user
            password = password or env_password

        config_key = cls._get_config_key(uri, user)

        if config_key not in cls._drivers:
            logger.info(f"Creating new Neo4j driver for {uri}")
            cls._drivers[config_key] = AsyncGraphDatabase.driver(
                uri=uri,
                auth=(user, password),
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,  # 60 seconds
                encrypted=uri.startswith("neo4j+s://") or uri.startswith("bolt+s://"),
            )

        return cls._drivers[config_key]

    @classmethod
    async def close_driver(
        cls, uri: Optional[str] = None, user: Optional[str] = None
    ) -> None:
        """
        Close a specific driver or all drivers.

        Args:
            uri: Neo4j URI. If None along with user, closes all drivers.
            user: Neo4j username. If None along with uri, closes all drivers.
        """
        if uri is None and user is None:
            # Close all drivers
            logger.info("Closing all Neo4j drivers")
            for driver in cls._drivers.values():
                await driver.close()
            cls._drivers.clear()
        else:
            # Close specific driver
            if uri is None or user is None:
                env_uri, env_user, _ = cls._get_config_from_env()
                uri = uri or env_uri
                user = user or env_user

            config_key = cls._get_config_key(uri, user)
            if config_key in cls._drivers:
                logger.info(f"Closing Neo4j driver for {uri}")
                await cls._drivers[config_key].close()
                del cls._drivers[config_key]

    @classmethod
    @asynccontextmanager
    async def get_session(
        cls,
        database: Optional[str] = None,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager that yields a Neo4j session.
        The session is automatically closed when the context exits.

        Args:
            database: Database name (optional, uses default if not specified)
            uri: Neo4j URI (optional, uses environment variable if not specified)
            user: Neo4j username (optional, uses environment variable if not specified)
            password: Neo4j password (optional, uses environment variable if not specified)

        Usage:
        ```python
        async with Neo4jConnector.get_session() as session:
            result = await session.run("MATCH (n) RETURN n LIMIT 10")
            records = await result.data()
        ```
        """
        driver = await cls.get_driver(uri, user, password)
        async with driver.session(database=database) as session:
            yield session

    @classmethod
    async def execute_query(
        cls,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return the results as a list of dictionaries.

        Args:
            query: Cypher query string
            parameters: Query parameters (optional)
            database: Database name (optional)
            uri: Neo4j URI (optional, uses environment variable if not specified)
            user: Neo4j username (optional, uses environment variable if not specified)
            password: Neo4j password (optional, uses environment variable if not specified)

        Returns:
            List of records as dictionaries

        Raises:
            ServiceUnavailable: If Neo4j service is unavailable
            TransientError: If a transient error occurs (can be retried)
        """
        logger.debug(f"Executing query: {query[:100]}...")

        async with cls.get_session(database, uri, user, password) as session:
            try:
                result = await session.run(cast(LiteralString, query), parameters or {})
                data = await result.data()
                logger.debug(f"Query returned {len(data)} records")
                return data
            except (ServiceUnavailable, TransientError) as e:
                logger.error(f"Neo4j error executing query: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error executing query: {e}")
                raise

    @classmethod
    async def execute_write_query(
        cls,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a write Cypher query within a write transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters (optional)
            database: Database name (optional)
            uri: Neo4j URI (optional, uses environment variable if not specified)
            user: Neo4j username (optional, uses environment variable if not specified)
            password: Neo4j password (optional, uses environment variable if not specified)

        Returns:
            List of records as dictionaries
        """
        logger.debug(f"Executing write query: {query[:100]}...")

        async def _execute_write(tx: AsyncManagedTransaction) -> List[Dict[str, Any]]:
            result = await tx.run(cast(LiteralString, query), parameters or {})
            return await result.data()

        async with cls.get_session(database, uri, user, password) as session:
            try:
                data = await session.execute_write(_execute_write)
                logger.debug(f"Write query returned {len(data)} records")
                return data
            except (ServiceUnavailable, TransientError) as e:
                logger.error(f"Neo4j error executing write query: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error executing write query: {e}")
                raise

    @classmethod
    async def execute_read_query(
        cls,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a read Cypher query within a read transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters (optional)
            database: Database name (optional)
            uri: Neo4j URI (optional, uses environment variable if not specified)
            user: Neo4j username (optional, uses environment variable if not specified)
            password: Neo4j password (optional, uses environment variable if not specified)

        Returns:
            List of records as dictionaries
        """
        logger.debug(f"Executing read query: {query[:100]}...")

        async def _execute_read(tx: AsyncManagedTransaction) -> List[Dict[str, Any]]:
            result = await tx.run(cast(LiteralString, query), parameters or {})
            return await result.data()

        async with cls.get_session(database, uri, user, password) as session:
            try:
                data = await session.execute_read(_execute_read)
                logger.debug(f"Read query returned {len(data)} records")
                return data
            except (ServiceUnavailable, TransientError) as e:
                logger.error(f"Neo4j error executing read query: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error executing read query: {e}")
                raise

    @classmethod
    async def verify_connectivity(
        cls,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        """
        Verify that the Neo4j database is accessible.

        Args:
            uri: Neo4j URI (optional, uses environment variable if not specified)
            user: Neo4j username (optional, uses environment variable if not specified)
            password: Neo4j password (optional, uses environment variable if not specified)

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            driver = await cls.get_driver(uri, user, password)
            await driver.verify_connectivity()
            logger.info("Neo4j connectivity verified successfully")
            return True
        except Exception as e:
            logger.error(f"Neo4j connectivity failed: {type(e).__name__}: {e}")
            return False


# High-level database operations for knowledge graph management


async def create_node(
    entity_type: str, properties: Dict[str, Any], database: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a node in the Neo4j knowledge graph with Entity base type and vector embedding.

    Args:
        entity_type: The type/label of the entity (e.g., 'Service', 'Class', 'Database')
        properties: Properties to set on the node
        database: Database name (optional)

    Returns:
        Created node information including assigned ID and embedding

    Example:
        node = await create_node('Service', {
            'name': 'user-service',
            'version': '1.0.0',
            'status': 'active'
        })
    """

    # Sanitize entity type for use as label
    label = entity_type.replace(" ", "").replace("-", "_")

    try:
        # Extract text from properties for embedding
        embedding_text = extract_text_from_properties(entity_type, properties)
        logger.debug(f"Embedding text for {entity_type}: {embedding_text[:100]}...")

        # Generate embedding
        embedding_util = VectorEmbedding()
        embedding_vector = await embedding_util.embed(embedding_text)
        logger.debug(
            f"Generated embedding vector with {len(embedding_vector)} dimensions"
        )

        # Add embedding to properties
        enhanced_properties = {**properties, "embedding_vector": embedding_vector}

        # Build the CREATE query with Entity base type first, then specific label
        query = f"""
        CREATE (n:Entity:{label} $properties)
        RETURN elementId(n) as node_id, labels(n) as labels, properties(n) as node_properties
        """

        result = await Neo4jConnector.execute_write_query(
            query, {"properties": enhanced_properties}, database
        )

        if result:
            node_data = result[0]
            logger.info(
                f"Created {entity_type} node with ID {node_data['node_id']} and embedding"
            )
            return {
                "node_id": node_data["node_id"],
                "labels": node_data["labels"],
                "properties": clean_properties(node_data.get("node_properties", {})),
                "entity_type": entity_type,
                "embedding_generated": True,
                "embedding_dimensions": len(embedding_vector),
            }
        else:
            raise RuntimeError(f"Failed to create {entity_type} node")

    except Exception as e:
        logger.error(f"Error creating {entity_type} node with embedding: {e}")
        raise


async def create_relationship(
    from_node_id: str,
    to_node_id: str,
    relationship_type: str,
    properties: Optional[Dict[str, Any]] = None,
    database: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a relationship between two nodes in the knowledge graph.

    Args:
        from_node_id: Source node ID
        to_node_id: Target node ID
        relationship_type: Type of relationship (e.g., 'CONTAINS', 'DEPENDS_ON')
        properties: Optional properties for the relationship
        database: Database name (optional)

    Returns:
        Created relationship information

    Example:
        rel = await create_relationship(
            from_node_id="4:abc123:0",
            to_node_id="4:def456:1",
            relationship_type='CONTAINS',
            properties={'created_at': '2024-01-01T00:00:00Z'}
        )
    """
    # Sanitize relationship type
    rel_type = relationship_type.upper().replace(" ", "_").replace("-", "_")

    # Build the CREATE query
    if properties:
        query = f"""
        MATCH (a), (b)
        WHERE elementId(a) = $from_id AND elementId(b) = $to_id
        CREATE (a)-[r:{rel_type} $properties]->(b)
        RETURN elementId(r) as rel_id, type(r) as rel_type, properties(r) as rel_properties
        """
        params = {
            "from_id": from_node_id,
            "to_id": to_node_id,
            "properties": properties,
        }
    else:
        query = f"""
        MATCH (a), (b)
        WHERE elementId(a) = $from_id AND elementId(b) = $to_id
        CREATE (a)-[r:{rel_type}]->(b)
        RETURN elementId(r) as rel_id, type(r) as rel_type, properties(r) as rel_properties
        """
        params = {"from_id": from_node_id, "to_id": to_node_id}

    try:
        result = await Neo4jConnector.execute_write_query(query, params, database)

        if result:
            rel_data = result[0]
            logger.info(
                f"Created {relationship_type} relationship with ID {rel_data['rel_id']}"
            )
            return {
                "relationship_id": rel_data["rel_id"],
                "type": rel_data["rel_type"],
                "properties": rel_data.get("rel_properties", {}),
                "from_node_id": from_node_id,
                "to_node_id": to_node_id,
            }
        else:
            raise RuntimeError(f"Failed to create {relationship_type} relationship")

    except Exception as e:
        logger.error(f"Error creating {relationship_type} relationship: {e}")
        raise


async def query_nodes(
    entity_type: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Query nodes of a specific type with optional filters.

    Args:
        entity_type: The type/label of entities to query (optional, queries all if None)
        filters: Optional property filters
        limit: Maximum number of results (default: 100)
        database: Database name (optional)

    Returns:
        List of matching nodes with their properties and metadata

    Example:
        nodes = await query_nodes(
            entity_type='Service',
            filters={'status': 'active'},
            limit=50
        )
    """
    # Build the MATCH clause
    if entity_type:
        label = entity_type.replace(" ", "").replace("-", "_")
        match_clause = f"MATCH (n:{label})"
    else:
        match_clause = "MATCH (n)"

    # Build WHERE clause for filters
    where_conditions: list[str] = []
    params = {"limit": limit}

    if filters:
        for key, value in filters.items():
            param_name = f"filter_{key}"
            where_conditions.append(f"n.{key} = ${param_name}")
            params[param_name] = value

    where_clause = (
        " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    )

    # Build complete query
    query = f"""
    {match_clause}{where_clause}
    RETURN elementId(n) as node_id, labels(n) as labels, properties(n) as node_properties
    LIMIT $limit
    """

    try:
        result = await Neo4jConnector.execute_read_query(query, params, database)

        nodes: list[dict[str, Any]] = []
        for record in result:
            nodes.append(
                {
                    "node_id": record["node_id"],
                    "labels": record["labels"],
                    "properties": clean_properties(record.get("node_properties", {})),
                    "entity_type": entity_type or record["labels"][0]
                    if record["labels"]
                    else None,
                }
            )

        logger.info(f"Found {len(nodes)} nodes matching criteria")
        return nodes

    except Exception as e:
        logger.error(f"Error querying nodes: {e}")
        raise


async def execute_cypher(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Execute a custom Cypher query against the knowledge graph.

    Args:
        query: Cypher query string
        parameters: Optional query parameters
        database: Database name (optional)

    Returns:
        Query results as list of dictionaries

    Example:
        results = await execute_cypher(
            "MATCH (s:Service)-[:CONTAINS]->(m:Module) RETURN s.name, count(m) as module_count",
            {}
        )
    """
    try:
        # Determine if this is a write query based on common write operations
        write_operations = [
            "CREATE",
            "MERGE",
            "SET",
            "DELETE",
            "REMOVE",
            "DETACH DELETE",
        ]
        is_write_query = any(op in query.upper() for op in write_operations)

        if is_write_query:
            result = await Neo4jConnector.execute_write_query(
                query, parameters, database
            )
        else:
            result = await Neo4jConnector.execute_read_query(
                query, parameters, database
            )

        logger.info(
            f"Cypher query executed successfully, returned {len(result)} records"
        )

        # Filter embedding_vector from any properties in the results
        filtered_result = []
        for record in result:
            filtered_record = {}
            for key, value in record.items():
                # Check if this looks like node properties
                if isinstance(value, dict) and "embedding_vector" in value:
                    filtered_record[key] = clean_properties(value)
                else:
                    filtered_record[key] = value
            filtered_result.append(filtered_record)

        return filtered_result

    except Exception as e:
        logger.error(f"Error executing Cypher query: {e}")
        raise


async def health_check(database: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform a health check on the Neo4j database connection.

    Args:
        database: Database name (optional)

    Returns:
        Health check results including connectivity status and basic stats
    """
    try:
        # Test connectivity
        is_connected = await Neo4jConnector.verify_connectivity()

        if not is_connected:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": "Unable to connect to Neo4j database",
            }

        # Get basic database stats
        stats_query = """
        CALL db.stats.retrieve('GRAPH COUNTS') YIELD data
        RETURN data.nodes as node_count, data.relationships as relationship_count
        """

        try:
            stats_result = await Neo4jConnector.execute_read_query(
                stats_query, {}, database
            )
            stats = stats_result[0] if stats_result else {}
        except Exception:
            # Fallback to simpler query if db.stats is not available
            stats_query = "MATCH (n) RETURN count(n) as node_count"
            stats_result = await Neo4jConnector.execute_read_query(
                stats_query, {}, database
            )
            stats = {
                "node_count": stats_result[0]["node_count"],
                "relationship_count": "unknown",
            }

        return {
            "status": "healthy",
            "connected": True,
            "database": database or "default",
            "node_count": stats.get("node_count", 0),
            "relationship_count": stats.get("relationship_count", 0),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "connected": False, "error": str(e)}


# Cleanup function for graceful shutdown
async def close_connections():
    """Close all Neo4j database connections."""
    await Neo4jConnector.close_driver()
    logger.info("All Neo4j connections closed")
