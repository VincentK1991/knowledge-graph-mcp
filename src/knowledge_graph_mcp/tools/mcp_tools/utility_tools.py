"""
Utility MCP tools for Knowledge Graph server.
Handles custom queries, health checks, cleanup, and validation.
"""

import json
import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from ...resources.schemas import knowledge_graph_schema
from ..db_operations import execute_cypher, health_check

logger = logging.getLogger("knowledge-graph-mcp.utility_tools")


def register_utility_tools(mcp: FastMCP):
    """Register all utility tools with the MCP server."""

    @mcp.tool()
    async def execute_custom_cypher(
        query: str, parameters: Optional[str] = None, database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a custom Cypher query against the knowledge graph.

        Args:
            query: Cypher query string
            parameters: Optional JSON string of query parameters
            database: Optional database name

        Returns:
            Query execution results
        """
        try:
            logger.info("Executing custom Cypher query via MCP")

            # Parse parameters if provided
            parsed_parameters = None
            if parameters:
                parsed_parameters = json.loads(parameters)

            # Execute the query
            result = await execute_cypher(query, parsed_parameters, database)

            return {
                "success": True,
                "results": result,
                "result_count": len(result),
                "query": query,
                "parameters": parsed_parameters,
                "message": f"Query executed successfully, returned {len(result)} records",
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in parameters: {str(e)}")
            return {"success": False, "error": f"Invalid JSON in parameters: {str(e)}"}
        except Exception as e:
            logger.error(f"Error executing custom query: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_graph_health() -> Dict[str, Any]:
        """
        Get health status and statistics for the knowledge graph database.

        Returns:
            Health check results and database statistics
        """
        try:
            logger.info("Getting graph health status via MCP")

            health = await health_check()

            return {
                "success": True,
                "health": health,
                "message": f"Graph health status: {health.get('status', 'unknown')}",
            }

        except Exception as e:
            logger.error(f"Error getting graph health: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def cleanup_graph_data(
        entity_types: Optional[str] = None,
        confirm: bool = False,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Clean up test or temporary data from the knowledge graph.

        Args:
            entity_types: Optional JSON array of entity types to clean up
            confirm: Must be True to actually perform cleanup (safety measure)
            database: Optional database name

        Returns:
            Cleanup operation results
        """
        try:
            logger.info("Cleaning up graph data via MCP")

            if not confirm:
                return {
                    "success": False,
                    "error": "Cleanup requires confirm=True for safety",
                }

            # Parse entity types if provided
            cleanup_labels = []
            if entity_types:
                cleanup_labels = json.loads(entity_types)

            if cleanup_labels:
                # Clean up specific entity types
                deleted_counts = []
                for label in cleanup_labels:
                    delete_query = (
                        f"MATCH (n:{label}) DETACH DELETE n RETURN count(n) as deleted"
                    )
                    result = await execute_cypher(delete_query, {}, database)
                    deleted_count = result[0]["deleted"] if result else 0
                    deleted_counts.append(
                        {"entity_type": label, "deleted": deleted_count}
                    )

                total_deleted = sum(item["deleted"] for item in deleted_counts)

                return {
                    "success": True,
                    "cleanup_details": deleted_counts,
                    "total_deleted": total_deleted,
                    "message": f"Cleaned up {total_deleted} nodes from specified entity types",
                }
            else:
                # Clean up test/temporary data (safer default)
                cleanup_query = """
                MATCH (n)
                WHERE any(label IN labels(n) WHERE label CONTAINS 'Test' OR label CONTAINS 'Temp')
                   OR any(prop IN keys(n) WHERE toString(n[prop]) CONTAINS 'test' OR toString(n[prop]) CONTAINS 'temp')
                DETACH DELETE n
                RETURN count(n) as deleted
                """

                result = await execute_cypher(cleanup_query, {}, database)
                deleted_count = result[0]["deleted"] if result else 0

                return {
                    "success": True,
                    "deleted_count": deleted_count,
                    "cleanup_type": "test_and_temporary_data",
                    "message": f"Cleaned up {deleted_count} test/temporary nodes",
                }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in entity_types: {str(e)}")
            return {
                "success": False,
                "error": f"Invalid JSON in entity_types: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Error cleaning up graph data: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def validate_entity_schema(
        entity_type: str, properties: str
    ) -> Dict[str, Any]:
        """
        Validate an entity against the knowledge graph schema.

        Args:
            entity_type: The type of entity to validate
            properties: JSON string of entity properties to validate

        Returns:
            Validation result with success status and any errors
        """
        try:
            logger.info(f"Validating entity of type: {entity_type}")

            # Parse properties
            parsed_properties = json.loads(properties)

            # Get entity schema
            entity_schema = knowledge_graph_schema.get_entity_schema(entity_type)
            if not entity_schema:
                return {
                    "valid": False,
                    "errors": [f"Unknown entity type: {entity_type}"],
                }

            errors = []
            warnings = []

            # Check required properties
            required_props = [
                prop_name
                for prop_name, prop_def in entity_schema.get("properties", {}).items()
                if prop_def.get("required", False)
            ]

            for req_prop in required_props:
                if req_prop not in parsed_properties:
                    errors.append(f"Missing required property: {req_prop}")

            # Check property types and constraints
            for prop_name, prop_value in parsed_properties.items():
                if prop_name in entity_schema.get("properties", {}):
                    prop_def = entity_schema["properties"][prop_name]

                    # Check enum values
                    if "enum" in prop_def and prop_value not in prop_def["enum"]:
                        errors.append(
                            f"Invalid value for {prop_name}. Must be one of: {prop_def['enum']}"
                        )

                    # Check data types (basic validation)
                    expected_type = prop_def.get("type")
                    if expected_type == "integer" and not isinstance(prop_value, int):
                        errors.append(f"Property {prop_name} must be an integer")
                    elif expected_type == "boolean" and not isinstance(
                        prop_value, bool
                    ):
                        errors.append(f"Property {prop_name} must be a boolean")
                    elif expected_type == "array" and not isinstance(prop_value, list):
                        errors.append(f"Property {prop_name} must be an array")
                else:
                    warnings.append(
                        f"Property {prop_name} is not defined in schema for {entity_type}"
                    )

            return {
                "valid": len(errors) == 0,
                "entity_type": entity_type,
                "errors": errors,
                "warnings": warnings,
                "validated_properties": list(parsed_properties.keys()),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in properties: {str(e)}")
            return {"valid": False, "errors": [f"Invalid JSON in properties: {str(e)}"]}
        except Exception as e:
            logger.error(f"Error validating entity: {str(e)}")
            raise

    @mcp.tool()
    async def validate_relationship(
        from_entity_type: str, to_entity_type: str, relationship_type: str
    ) -> Dict[str, Any]:
        """
        Validate if a relationship is allowed between two entity types.

        Args:
            from_entity_type: The source entity type
            to_entity_type: The target entity type
            relationship_type: The type of relationship

        Returns:
            Validation result indicating if the relationship is valid
        """
        try:
            logger.info(
                f"Validating relationship: {from_entity_type} -{relationship_type}-> {to_entity_type}"
            )

            is_valid = knowledge_graph_schema.validate_relationship(
                from_entity_type, to_entity_type, relationship_type
            )

            result = {
                "valid": is_valid,
                "from_entity_type": from_entity_type,
                "to_entity_type": to_entity_type,
                "relationship_type": relationship_type,
            }

            if not is_valid:
                # Provide helpful suggestions
                valid_relationships = (
                    knowledge_graph_schema.get_relationships_for_entity(
                        from_entity_type
                    )
                )
                suggestions = [
                    rel
                    for rel in valid_relationships
                    if rel["from"] == from_entity_type and rel["to"] == to_entity_type
                ]

                if suggestions:
                    result["suggestions"] = [rel["type"] for rel in suggestions]
                    result["message"] = (
                        f"Invalid relationship type. Valid types between {from_entity_type} and {to_entity_type}: {[rel['type'] for rel in suggestions]}"
                    )
                else:
                    result["message"] = (
                        f"No valid relationships defined between {from_entity_type} and {to_entity_type}"
                    )

            return result

        except Exception as e:
            logger.error(f"Error validating relationship: {str(e)}")
            raise
