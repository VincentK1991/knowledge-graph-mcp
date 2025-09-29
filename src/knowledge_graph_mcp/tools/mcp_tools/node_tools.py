"""
Node management MCP tools for Knowledge Graph server.
Handles node creation, querying, updating, and deletion.
"""

import json
import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from ...utils.property_filter import clean_properties
from ..db_operations import create_node, execute_cypher, query_nodes
from ..schema_validation import validate_entity_schema

logger = logging.getLogger("knowledge-graph-mcp.node_tools")


def register_node_tools(mcp: FastMCP):
    """Register all node management tools with the MCP server."""

    @mcp.tool()
    async def create_graph_node(  # pyright: ignore
        entity_type: str, properties: str, database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new node in the knowledge graph.

        Args:
            entity_type: The type of entity to create (e.g., "Service", "Class", "Database")
            properties: JSON string of node properties
            database: Optional database name

        Returns:
            Created node information including ID and properties
        """
        try:
            logger.info(f"Creating {entity_type} node via MCP")

            # Parse and validate properties
            parsed_properties = json.loads(properties)

            # Validate against schema
            validation = await validate_entity_schema(entity_type, properties)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": "Schema validation failed",
                    "validation_errors": validation["errors"],
                    "warnings": validation.get("warnings", []),
                }

            # Create the node
            node = await create_node(entity_type, parsed_properties, database)

            return {
                "success": True,
                "node": node,
                "message": f"Successfully created {entity_type} node",
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in properties: {str(e)}")
            return {"success": False, "error": f"Invalid JSON in properties: {str(e)}"}
        except Exception as e:
            logger.error(f"Error creating node: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def query_graph_nodes(  # pyright: ignore
        entity_type: Optional[str] = None,
        filters: Optional[str] = None,
        limit: int = 100,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Query nodes in the knowledge graph.

        Args:
            entity_type: Optional entity type to filter by (e.g., "Service", "Class")
            filters: Optional JSON string of property filters
            limit: Maximum number of results to return (default: 100)
            database: Optional database name

        Returns:
            Query results with matching nodes
        """
        try:
            logger.info(f"Querying {entity_type or 'all'} nodes via MCP")

            # Parse filters if provided
            parsed_filters = None
            if filters:
                parsed_filters = json.loads(filters)

            # Query nodes
            nodes = await query_nodes(entity_type, parsed_filters, limit, database)

            return {
                "success": True,
                "nodes": nodes,
                "count": len(nodes),
                "entity_type": entity_type,
                "filters_applied": parsed_filters,
                "message": f"Found {len(nodes)} matching nodes",
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in filters: {str(e)}")
            return {"success": False, "error": f"Invalid JSON in filters: {str(e)}"}
        except Exception as e:
            logger.error(f"Error querying nodes: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def update_graph_node(  # pyright: ignore
        node_id: str, properties: str, database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update properties of an existing node in the knowledge graph.

        Args:
            node_id: The element ID of the node to update
            properties: JSON string of properties to set/update
            database: Optional database name

        Returns:
            Update result information
        """
        try:
            logger.info(f"Updating node {node_id} via MCP")

            # Parse properties
            parsed_properties = json.loads(properties)

            # Build SET clauses for properties
            set_clauses = []
            params = {"node_id": node_id}

            for key, value in parsed_properties.items():
                param_name = f"prop_{key}"
                set_clauses.append(f"n.{key} = ${param_name}")
                params[param_name] = value

            if not set_clauses:
                return {"success": False, "error": "No properties provided for update"}

            # Execute update query
            update_query = f"""
            MATCH (n)
            WHERE elementId(n) = $node_id
            SET {", ".join(set_clauses)}
            RETURN elementId(n) as node_id, labels(n) as labels, properties(n) as node_properties
            """

            result = await execute_cypher(update_query, params, database)

            if result:
                updated_node = result[0]
                return {
                    "success": True,
                    "node": {
                        "node_id": updated_node["node_id"],
                        "labels": updated_node["labels"],
                        "properties": clean_properties(updated_node["node_properties"]),
                    },
                    "updated_properties": list(parsed_properties.keys()),
                    "message": f"Successfully updated node {node_id}",
                }
            else:
                return {"success": False, "error": f"Node with ID {node_id} not found"}

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in properties: {str(e)}")
            return {"success": False, "error": f"Invalid JSON in properties: {str(e)}"}
        except Exception as e:
            logger.error(f"Error updating node: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def delete_graph_node(  # pyright: ignore
        node_id: str, force_delete: bool = False, database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a node from the knowledge graph.

        Args:
            node_id: The element ID of the node to delete
            force_delete: If True, deletes all relationships before deleting node
            database: Optional database name

        Returns:
            Deletion result information
        """
        try:
            logger.info(f"Deleting node {node_id} via MCP (force: {force_delete})")

            # Check if node exists first
            check_query = (
                "MATCH (n) WHERE elementId(n) = $node_id RETURN count(n) as exists"
            )
            check_result = await execute_cypher(
                check_query, {"node_id": node_id}, database
            )

            if not check_result or check_result[0]["exists"] == 0:
                return {"success": False, "error": f"Node with ID {node_id} not found"}

            # Delete node (with or without relationships)
            if force_delete:
                delete_query = "MATCH (n) WHERE elementId(n) = $node_id DETACH DELETE n RETURN count(n) as deleted"
            else:
                delete_query = "MATCH (n) WHERE elementId(n) = $node_id DELETE n RETURN count(n) as deleted"

            result = await execute_cypher(delete_query, {"node_id": node_id}, database)

            if result and result[0]["deleted"] > 0:
                return {
                    "success": True,
                    "node_id": node_id,
                    "force_delete": force_delete,
                    "message": f"Successfully deleted node {node_id}",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to delete node (may have relationships - use force_delete=True)",
                }

        except Exception as e:
            logger.error(f"Error deleting node: {str(e)}")
            return {"success": False, "error": str(e)}
