"""
Relationship management MCP tools for Knowledge Graph server.
Handles relationship creation, querying, and deletion.
"""

import json
import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from ..db_operations import create_relationship, execute_cypher
from ..schema_validation import validate_relationship_schema

logger = logging.getLogger("knowledge-graph-mcp.relationship_tools")


def register_relationship_tools(mcp: FastMCP):
    """Register all relationship management tools with the MCP server."""

    @mcp.tool()
    async def create_graph_relationship(
        from_node_id: str,
        to_node_id: str,
        relationship_type: str,
        properties: Optional[str] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a relationship between two nodes in the knowledge graph.

        Args:
            from_node_id: Element ID of the source node
            to_node_id: Element ID of the target node
            relationship_type: Type of relationship (e.g., "CONTAINS", "DEPENDS_ON")
            properties: Optional JSON string of relationship properties
            database: Optional database name

        Returns:
            Created relationship information
        """
        try:
            logger.info(f"Creating {relationship_type} relationship via MCP")

            # Parse properties if provided
            parsed_properties = None
            if properties:
                parsed_properties = json.loads(properties)

            # Validate the relationship before creating
            validation = await validate_relationship_schema(
                from_node_id, to_node_id, relationship_type, database
            )

            if not validation["valid"]:
                return {
                    "success": False,
                    "error": "Relationship validation failed",
                    "validation_errors": validation["errors"],
                    "warnings": validation.get("warnings", []),
                }

            # Create the relationship
            relationship = await create_relationship(
                from_node_id, to_node_id, relationship_type, parsed_properties, database
            )

            return {
                "success": True,
                "relationship": relationship,
                "message": f"Successfully created {relationship_type} relationship",
                "validation_info": validation.get("info", {}),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in properties: {str(e)}")
            return {"success": False, "error": f"Invalid JSON in properties: {str(e)}"}
        except Exception as e:
            logger.error(f"Error creating relationship: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def query_graph_relationships(
        from_entity_type: Optional[str] = None,
        to_entity_type: Optional[str] = None,
        relationship_type: Optional[str] = None,
        limit: int = 100,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Query relationships in the knowledge graph.

        Args:
            from_entity_type: Optional source entity type filter
            to_entity_type: Optional target entity type filter
            relationship_type: Optional relationship type filter
            limit: Maximum number of results to return
            database: Optional database name

        Returns:
            Query results with matching relationships
        """
        try:
            logger.info("Querying relationships via MCP")

            # Build query based on filters
            params = {"limit": limit}

            if from_entity_type and to_entity_type and relationship_type:
                match_clause = f"MATCH (a:{from_entity_type})-[r:{relationship_type}]->(b:{to_entity_type})"
            elif from_entity_type and to_entity_type:
                match_clause = f"MATCH (a:{from_entity_type})-[r]->(b:{to_entity_type})"
            elif relationship_type:
                match_clause = f"MATCH (a)-[r:{relationship_type}]->(b)"
            else:
                match_clause = "MATCH (a)-[r]->(b)"

            query = f"""
            {match_clause}
            RETURN elementId(a) as from_node_id, labels(a) as from_labels,
                   elementId(r) as relationship_id, type(r) as relationship_type, properties(r) as rel_properties,
                   elementId(b) as to_node_id, labels(b) as to_labels
            LIMIT $limit
            """

            result = await execute_cypher(query, params, database)

            relationships = []
            for record in result:
                relationships.append(
                    {
                        "relationship_id": record["relationship_id"],
                        "type": record["relationship_type"],
                        "properties": record["rel_properties"],
                        "from_node": {
                            "node_id": record["from_node_id"],
                            "labels": record["from_labels"],
                        },
                        "to_node": {
                            "node_id": record["to_node_id"],
                            "labels": record["to_labels"],
                        },
                    }
                )

            return {
                "success": True,
                "relationships": relationships,
                "count": len(relationships),
                "filters": {
                    "from_entity_type": from_entity_type,
                    "to_entity_type": to_entity_type,
                    "relationship_type": relationship_type,
                },
                "message": f"Found {len(relationships)} matching relationships",
            }

        except Exception as e:
            logger.error(f"Error querying relationships: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def validate_graph_relationship(
        from_node_id: str,
        to_node_id: str,
        relationship_type: str,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate a relationship against the schema without creating it.

        Args:
            from_node_id: Element ID of the source node
            to_node_id: Element ID of the target node
            relationship_type: Type of relationship to validate
            database: Optional database name

        Returns:
            Validation result with detailed information
        """
        try:
            logger.info(f"Validating {relationship_type} relationship via MCP")

            validation = await validate_relationship_schema(
                from_node_id, to_node_id, relationship_type, database
            )

            return {
                "success": True,
                "valid": validation["valid"],
                "relationship_type": relationship_type,
                "validation_errors": validation["errors"],
                "warnings": validation.get("warnings", []),
                "info": validation.get("info", {}),
                "message": "Validation completed"
                if validation["valid"]
                else "Validation failed",
            }

        except Exception as e:
            logger.error(f"Error validating relationship: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def delete_graph_relationship(
        relationship_id: str, database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a relationship from the knowledge graph.

        Args:
            relationship_id: The element ID of the relationship to delete
            database: Optional database name

        Returns:
            Deletion result information
        """
        try:
            logger.info(f"Deleting relationship {relationship_id} via MCP")

            # Delete the relationship
            delete_query = """
            MATCH ()-[r]->()
            WHERE elementId(r) = $relationship_id
            DELETE r
            RETURN count(r) as deleted
            """

            result = await execute_cypher(
                delete_query, {"relationship_id": relationship_id}, database
            )

            if result and result[0]["deleted"] > 0:
                return {
                    "success": True,
                    "relationship_id": relationship_id,
                    "message": f"Successfully deleted relationship {relationship_id}",
                }
            else:
                return {
                    "success": False,
                    "error": f"Relationship with ID {relationship_id} not found",
                }

        except Exception as e:
            logger.error(f"Error deleting relationship: {str(e)}")
            return {"success": False, "error": str(e)}













