"""
Combined node and relationship creation MCP tools for Knowledge Graph server.
Handles creation of nodes and relationships in single operations with full validation.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from ..db_operations import create_node, create_relationship, execute_cypher
from ..schema_validation import (
    validate_entity_schema,
    validate_relationship_schema,
    validate_relationship_triplet,
)

logger = logging.getLogger("knowledge-graph-mcp.combined_tools")


def register_combined_tools(mcp: FastMCP):
    """Register all combined creation tools with the MCP server."""

    @mcp.tool()
    async def create_node_with_relationship(  # pyright: ignore
        from_node_id: str,
        to_entity_type: str,
        to_properties: Dict[str, Any],
        relationship_type: str,
        relationship_properties: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new node and connect it to an existing node with a relationship.

        Args:
            from_node_id: Element ID of the existing source node
            to_entity_type: Type of the new node to create (e.g., "Service", "Class", "Database")
            to_properties: Dictionary of properties for the new node
            relationship_type: Type of relationship to create (e.g., "CONTAINS", "DEPENDS_ON")
            relationship_properties: Optional dictionary of relationship properties
            database: Optional database name

        Returns:
            Created node and relationship information
        """
        try:
            logger.info(
                f"Creating {to_entity_type} node with {relationship_type} relationship via MCP"
            )

            # Step 1: Validate the new node schema
            node_validation = await validate_entity_schema(
                to_entity_type, json.dumps(to_properties)
            )
            if not node_validation["valid"]:
                return {
                    "success": False,
                    "error": "Node schema validation failed",
                    "node_validation_errors": node_validation["errors"],
                    "node_warnings": node_validation.get("warnings", []),
                }

            # Step 2: Create the new node first
            new_node = await create_node(to_entity_type, to_properties, database)
            new_node_id = new_node["node_id"]

            # Step 3: Validate the relationship
            rel_validation = await validate_relationship_schema(
                from_node_id, new_node_id, relationship_type, database
            )

            if not rel_validation["valid"]:
                # If relationship validation fails, we should delete the created node
                # to maintain consistency (rollback)
                try:
                    delete_query = "MATCH (n) WHERE elementId(n) = $node_id DELETE n"
                    await execute_cypher(
                        delete_query, {"node_id": new_node_id}, database
                    )
                    logger.info(
                        "Rolled back node creation due to relationship validation failure"
                    )
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback node creation: {rollback_error}")

                return {
                    "success": False,
                    "error": "Relationship validation failed",
                    "relationship_validation_errors": rel_validation["errors"],
                    "relationship_warnings": rel_validation.get("warnings", []),
                    "rollback_performed": True,
                }

            # Step 4: Create the relationship
            relationship = await create_relationship(
                from_node_id,
                new_node_id,
                relationship_type,
                relationship_properties,
                database,
            )

            return {
                "success": True,
                "created_node": new_node,
                "created_relationship": relationship,
                "node_validation": node_validation,
                "relationship_validation": rel_validation,
                "message": f"Successfully created {to_entity_type} node with {relationship_type} relationship",
            }

        except Exception as e:
            logger.error(f"Error creating node with relationship: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def create_nodes_with_relationship(  # pyright: ignore
        from_entity_type: str,
        from_properties: Dict[str, Any],
        to_entity_type: str,
        to_properties: Dict[str, Any],
        relationship_type: str,
        relationship_properties: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create two new nodes and connect them with a relationship.

        Args:
            from_entity_type: Type of the source node to create
            from_properties: Dictionary of properties for the source node
            to_entity_type: Type of the target node to create
            to_properties: Dictionary of properties for the target node
            relationship_type: Type of relationship to create
            relationship_properties: Optional dictionary of relationship properties
            database: Optional database name

        Returns:
            Created nodes and relationship information
        """
        try:
            logger.info(
                f"Creating {from_entity_type} and {to_entity_type} nodes with {relationship_type} relationship via MCP"
            )

            # Step 1: Validate both node schemas
            from_node_validation = await validate_entity_schema(
                from_entity_type, json.dumps(from_properties)
            )
            to_node_validation = await validate_entity_schema(
                to_entity_type, json.dumps(to_properties)
            )

            validation_errors = []
            if not from_node_validation["valid"]:
                validation_errors.extend(
                    [
                        f"Source node: {error}"
                        for error in from_node_validation["errors"]
                    ]
                )
            if not to_node_validation["valid"]:
                validation_errors.extend(
                    [f"Target node: {error}" for error in to_node_validation["errors"]]
                )

            if validation_errors:
                return {
                    "success": False,
                    "error": "Node schema validation failed",
                    "validation_errors": validation_errors,
                    "from_node_validation": from_node_validation,
                    "to_node_validation": to_node_validation,
                }

            # Step 2: Validate the relationship schema (using entity types)
            triplet_validation = validate_relationship_triplet(
                from_entity_type, to_entity_type, relationship_type
            )

            if not triplet_validation["valid"]:
                return {
                    "success": False,
                    "error": "Relationship validation failed",
                    "validation_errors": triplet_validation["errors"],
                    "suggestion": f"Check valid relationships for {from_entity_type} in the schema",
                }

            # Step 3: Create both nodes
            from_node = await create_node(from_entity_type, from_properties, database)
            from_node_id = from_node["node_id"]

            to_node = await create_node(to_entity_type, to_properties, database)
            to_node_id = to_node["node_id"]

            # Step 4: Create the relationship
            try:
                relationship = await create_relationship(
                    from_node_id,
                    to_node_id,
                    relationship_type,
                    relationship_properties,
                    database,
                )

                return {
                    "success": True,
                    "created_from_node": from_node,
                    "created_to_node": to_node,
                    "created_relationship": relationship,
                    "from_node_validation": from_node_validation,
                    "to_node_validation": to_node_validation,
                    "message": f"Successfully created {from_entity_type} and {to_entity_type} nodes with {relationship_type} relationship",
                }

            except Exception as rel_error:
                # If relationship creation fails, rollback both nodes
                try:
                    delete_query = """
                    MATCH (n)
                    WHERE elementId(n) = $from_node_id OR elementId(n) = $to_node_id
                    DELETE n
                    """
                    await execute_cypher(
                        delete_query,
                        {"from_node_id": from_node_id, "to_node_id": to_node_id},
                        database,
                    )
                    logger.info(
                        "Rolled back node creation due to relationship creation failure"
                    )
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback node creation: {rollback_error}")

                return {
                    "success": False,
                    "error": f"Relationship creation failed: {str(rel_error)}",
                    "rollback_performed": True,
                }

        except Exception as e:
            logger.error(f"Error creating nodes with relationship: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def create_graph_subgraph(  # pyright: ignore
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create multiple nodes and relationships in a single transaction.

        Args:
            nodes: List of node definitions with entity_type and properties
            relationships: List of relationship definitions
            database: Optional database name

        Returns:
            Created subgraph information with all nodes and relationships

        Important: The from_index and to_index in relationships refer to the array indices
        of nodes in the nodes array, NOT database node IDs. The function will:
        1. Create all nodes first and collect their database IDs
        2. Use the indices to map to the correct database node IDs for relationships
        3. Create relationships using the actual database node IDs

        Example nodes format:
        [
            {"entity_type": "Service", "properties": {"name": "api-service", "version": "1.0"}},    # index 0
            {"entity_type": "Database", "properties": {"name": "user-db", "type": "sql"}}           # index 1
        ]

        Example relationships format:
        [
            {
                "from_index": 0,      # Refers to first node (Service) in the nodes array
                "to_index": 1,        # Refers to second node (Database) in the nodes array
                "type": "OWNS",       # Service OWNS Database
                "properties": {}      # Optional relationship properties
            }
        ]

        The function ensures atomicity: if any node or relationship creation fails,
        all previously created nodes and relationships are rolled back.
        """
        try:
            logger.info("Creating graph subgraph via MCP")

            # Step 1: Validate all nodes
            node_validations = []
            for i, node_def in enumerate(nodes):
                if "entity_type" not in node_def or "properties" not in node_def:
                    return {
                        "success": False,
                        "error": f"Node {i} missing entity_type or properties",
                    }

                validation = await validate_entity_schema(
                    node_def["entity_type"], json.dumps(node_def["properties"])
                )
                node_validations.append(validation)

                if not validation["valid"]:
                    return {
                        "success": False,
                        "error": f"Node {i} ({node_def['entity_type']}) validation failed",
                        "validation_errors": validation["errors"],
                    }

            # Step 2: Validate all relationships
            for i, rel_def in enumerate(relationships):
                required_fields = ["from_index", "to_index", "type"]
                for field in required_fields:
                    if field not in rel_def:
                        return {
                            "success": False,
                            "error": f"Relationship {i} missing required field: {field}",
                        }

                from_idx = rel_def["from_index"]
                to_idx = rel_def["to_index"]

                if from_idx >= len(nodes) or to_idx >= len(nodes):
                    return {
                        "success": False,
                        "error": f"Relationship {i} has invalid node index",
                    }

                from_entity_type = nodes[from_idx]["entity_type"]
                to_entity_type = nodes[to_idx]["entity_type"]
                rel_type = rel_def["type"]

                triplet_validation = validate_relationship_triplet(
                    from_entity_type, to_entity_type, rel_type
                )
                if not triplet_validation["valid"]:
                    return {
                        "success": False,
                        "error": f"Invalid relationship {i}: {from_entity_type} {rel_type} {to_entity_type}",
                    }

            # Step 3: Create all nodes
            created_nodes = []
            node_ids = []

            for i, node_def in enumerate(nodes):
                try:
                    node = await create_node(
                        node_def["entity_type"], node_def["properties"], database
                    )
                    created_nodes.append(node)
                    node_ids.append(node["node_id"])
                except Exception as node_error:
                    # Rollback previously created nodes
                    if node_ids:
                        try:
                            delete_query = (
                                "MATCH (n) WHERE elementId(n) IN $node_ids DELETE n"
                            )
                            await execute_cypher(
                                delete_query, {"node_ids": node_ids}, database
                            )
                        except Exception as rollback_error:
                            logger.error(f"Failed to rollback nodes: {rollback_error}")

                    return {
                        "success": False,
                        "error": f"Failed to create node {i}: {str(node_error)}",
                        "rollback_performed": True,
                    }

            # Step 4: Create all relationships
            created_relationships = []

            for i, rel_def in enumerate(relationships):
                try:
                    from_node_id = node_ids[rel_def["from_index"]]
                    to_node_id = node_ids[rel_def["to_index"]]
                    rel_properties = rel_def.get("properties", {})

                    relationship = await create_relationship(
                        from_node_id,
                        to_node_id,
                        rel_def["type"],
                        rel_properties,
                        database,
                    )
                    created_relationships.append(relationship)

                except Exception as rel_error:
                    # Rollback all created nodes and relationships
                    try:
                        delete_query = (
                            "MATCH (n) WHERE elementId(n) IN $node_ids DETACH DELETE n"
                        )
                        await execute_cypher(
                            delete_query, {"node_ids": node_ids}, database
                        )
                    except Exception as rollback_error:
                        logger.error(f"Failed to rollback subgraph: {rollback_error}")

                    return {
                        "success": False,
                        "error": f"Failed to create relationship {i}: {str(rel_error)}",
                        "rollback_performed": True,
                    }

            return {
                "success": True,
                "created_nodes": created_nodes,
                "created_relationships": created_relationships,
                "node_validations": node_validations,
                "nodes_count": len(created_nodes),
                "relationships_count": len(created_relationships),
                "message": f"Successfully created subgraph with {len(created_nodes)} nodes and {len(created_relationships)} relationships",
            }

        except Exception as e:
            logger.error(f"Error creating subgraph: {str(e)}")
            return {"success": False, "error": str(e)}
