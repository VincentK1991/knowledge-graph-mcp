"""
Vector search MCP tools for Knowledge Graph server.
Handles semantic search and similarity queries using vector embeddings.
"""

import json
import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from ...utils.property_filter import clean_properties
from ...utils.text_extractor import extract_text_from_properties
from ...utils.vector_embedding import VectorEmbedding
from ..db_operations import Neo4jConnector

logger = logging.getLogger("knowledge-graph-mcp.vector_tools")


def register_vector_tools(mcp: FastMCP):
    """Register all vector search tools with the MCP server."""

    @mcp.tool()
    async def query_nodes_by_similarity(  # pyright: ignore
        query_text: str,
        entity_type: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.8,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Find nodes similar to the given query text using vector similarity search.

        Args:
            query_text: Text to search for similar nodes
            entity_type: Optional entity type filter (e.g., "Service", "Database")
            limit: Maximum number of results to return (default: 10)
            threshold: Similarity threshold (0.0-1.0, default: 0.8)
            database: Optional database name

        Returns:
            Dictionary with similar nodes and their similarity scores
        """
        try:
            logger.info(f"Vector similarity search for: '{query_text[:50]}...'")

            # Generate embedding for query text
            embedding_util = VectorEmbedding()
            query_vector = await embedding_util.embed(query_text)

            # Build entity type filter
            type_filter = ""
            if entity_type:
                sanitized_type = entity_type.replace(" ", "").replace("-", "_")
                type_filter = f"AND n:{sanitized_type}"

            # Vector similarity query
            query = f"""
            CALL db.index.vector.queryNodes('entity_embedding_index', $limit, $query_vector)
            YIELD node, score
            WHERE score >= $threshold {type_filter}
            RETURN elementId(node) as node_id,
                   labels(node) as labels,
                   properties(node) as properties,
                   score
            ORDER BY score DESC
            """

            result = await Neo4jConnector.execute_read_query(
                query,
                {
                    "query_vector": query_vector,
                    "limit": limit,
                    "threshold": threshold,
                },
                database,
            )

            # Format results
            similar_nodes = []
            for record in result:
                similar_nodes.append(
                    {
                        "node_id": record["node_id"],
                        "labels": record["labels"],
                        "properties": clean_properties(record.get("properties", {})),
                        "similarity_score": round(record["score"], 4),
                    }
                )

            return {
                "success": True,
                "query_text": query_text,
                "entity_type": entity_type,
                "threshold": threshold,
                "total_results": len(similar_nodes),
                "similar_nodes": similar_nodes,
            }

        except Exception as e:
            logger.error(f"Error in vector similarity search: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def find_related_entities(  # pyright: ignore
        entity_type: str,
        properties: str,
        limit: int = 5,
        threshold: float = 0.7,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Find entities related to a given entity using its properties for semantic search.

        Args:
            entity_type: Type of the source entity
            properties: JSON string of entity properties to use for similarity
            limit: Maximum number of results to return (default: 5)
            threshold: Similarity threshold (0.0-1.0, default: 0.7)
            database: Optional database name

        Returns:
            Dictionary with related entities and their similarity scores
        """
        try:
            logger.info(f"Finding entities related to {entity_type}")

            # Parse properties
            parsed_properties = json.loads(properties)

            # Generate embedding text from properties
            embedding_text = extract_text_from_properties(
                entity_type, parsed_properties
            )

            # Generate embedding
            embedding_util = VectorEmbedding()
            query_vector = await embedding_util.embed(embedding_text)

            # Find similar entities (excluding same entity type to find relationships)
            query = """
            CALL db.index.vector.queryNodes('entity_embedding_index', $limit * 2, $query_vector)
            YIELD node, score
            WHERE score >= $threshold
            WITH node, score
            WHERE NOT $entity_type IN labels(node)
            RETURN elementId(node) as node_id,
                   labels(node) as labels,
                   properties(node) as properties,
                   score
            ORDER BY score DESC
            LIMIT $limit
            """

            result = await Neo4jConnector.execute_read_query(
                query,
                {
                    "query_vector": query_vector,
                    "entity_type": entity_type.replace(" ", "").replace("-", "_"),
                    "limit": limit,
                    "threshold": threshold,
                },
                database,
            )

            # Format results
            related_entities = []
            for record in result:
                related_entities.append(
                    {
                        "node_id": record["node_id"],
                        "labels": record["labels"],
                        "properties": clean_properties(record.get("properties", {})),
                        "similarity_score": round(record["score"], 4),
                    }
                )

            return {
                "success": True,
                "source_entity_type": entity_type,
                "threshold": threshold,
                "total_results": len(related_entities),
                "related_entities": related_entities,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in properties: {str(e)}")
            return {"success": False, "error": f"Invalid JSON in properties: {str(e)}"}
        except Exception as e:
            logger.error(f"Error finding related entities: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def semantic_search(  # pyright: ignore
        query_text: str,
        limit: int = 20,
        threshold: float = 0.6,
        include_entity_types: Optional[str] = None,
        exclude_entity_types: Optional[str] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform general semantic search across all entity types in the knowledge graph.

        Args:
            query_text: Text query for semantic search
            limit: Maximum number of results to return (default: 20)
            threshold: Similarity threshold (0.0-1.0, default: 0.6)
            include_entity_types: Optional JSON array of entity types to include
            exclude_entity_types: Optional JSON array of entity types to exclude
            database: Optional database name

        Returns:
            Dictionary with search results grouped by entity type
        """
        try:
            logger.info(f"Semantic search for: '{query_text[:50]}...'")

            # Parse type filters
            include_types = []
            exclude_types = []

            if include_entity_types:
                include_types = json.loads(include_entity_types)
            if exclude_entity_types:
                exclude_types = json.loads(exclude_entity_types)

            # Generate embedding for query
            embedding_util = VectorEmbedding()
            query_vector = await embedding_util.embed(query_text)

            # Build type filters
            type_conditions = []
            if include_types:
                sanitized_include = [
                    t.replace(" ", "").replace("-", "_") for t in include_types
                ]
                include_condition = " OR ".join([f"n:{t}" for t in sanitized_include])
                type_conditions.append(f"({include_condition})")

            if exclude_types:
                sanitized_exclude = [
                    t.replace(" ", "").replace("-", "_") for t in exclude_types
                ]
                for exclude_type in sanitized_exclude:
                    type_conditions.append(f"NOT n:{exclude_type}")

            where_clause = ""
            if type_conditions:
                where_clause = "AND " + " AND ".join(type_conditions)

            # Vector similarity query across all entities
            query = f"""
            CALL db.index.vector.queryNodes('entity_embedding_index', $limit, $query_vector)
            YIELD node, score
            WHERE score >= $threshold {where_clause}
            RETURN elementId(node) as node_id,
                   labels(node) as labels,
                   properties(node) as properties,
                   score
            ORDER BY score DESC
            """

            result = await Neo4jConnector.execute_read_query(
                query,
                {
                    "query_vector": query_vector,
                    "limit": limit,
                    "threshold": threshold,
                },
                database,
            )

            # Group results by entity type
            results_by_type = {}
            total_results = 0

            for record in result:
                # Get primary entity type (skip 'Entity' base type)
                labels = record["labels"]
                entity_type = next(
                    (label for label in labels if label != "Entity"), "Unknown"
                )

                if entity_type not in results_by_type:
                    results_by_type[entity_type] = []

                results_by_type[entity_type].append(
                    {
                        "node_id": record["node_id"],
                        "labels": labels,
                        "properties": clean_properties(record.get("properties", {})),
                        "similarity_score": round(record["score"], 4),
                    }
                )
                total_results += 1

            return {
                "success": True,
                "query_text": query_text,
                "threshold": threshold,
                "total_results": total_results,
                "entity_types_found": list(results_by_type.keys()),
                "include_types": include_types,
                "exclude_types": exclude_types,
                "results_by_type": results_by_type,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in type filters: {str(e)}")
            return {
                "success": False,
                "error": f"Invalid JSON in type filters: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return {"success": False, "error": str(e)}
