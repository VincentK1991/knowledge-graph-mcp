"""
Schema resources for Knowledge Graph MCP server.
Handles all schema-related resource endpoints.
"""

import json
import logging

from mcp.server.fastmcp import FastMCP

from .schemas import knowledge_graph_schema

logger = logging.getLogger("knowledge-graph-mcp.schema_resources")


def register_schema_resources(mcp: FastMCP):
    """Register all schema resources with the MCP server."""

    @mcp.resource("knowledge-graph://schema/complete")
    async def get_complete_schema() -> str:
        """
        Get the complete knowledge graph schema including all entity types and relationships.

        This resource provides comprehensive information about:
        - All available entity types with their properties and constraints
        - All possible relationships between entities
        - Schema validation rules and guidelines
        - Usage examples and best practices
        """
        try:
            logger.info("Serving complete knowledge graph schema")
            return knowledge_graph_schema.to_json()
        except Exception as e:
            logger.error(f"Error serving complete schema: {str(e)}")
            raise

    @mcp.resource("knowledge-graph://schema/summary")
    async def get_schema_summary() -> str:
        """
        Get a high-level summary of the knowledge graph schema.

        This resource provides:
        - Statistics about entity types and relationships
        - Entity categories and groupings
        - Available relationship types
        - Usage guidelines
        """
        try:
            logger.info("Serving knowledge graph schema summary")
            return json.dumps(knowledge_graph_schema.schema_summary, indent=2)
        except Exception as e:
            logger.error(f"Error serving schema summary: {str(e)}")
            raise

    @mcp.resource("knowledge-graph://schema/entities")
    async def get_entity_types() -> str:
        """
        Get all available entity types with their properties and constraints.

        This resource provides detailed information about:
        - Entity type definitions
        - Required and optional properties
        - Data types and validation rules
        - Unique constraints and indexes
        """
        try:
            logger.info("Serving entity types schema")
            return json.dumps(knowledge_graph_schema.entity_types, indent=2)
        except Exception as e:
            logger.error(f"Error serving entity types: {str(e)}")
            raise

    @mcp.resource("knowledge-graph://schema/relationships")
    async def get_relationships() -> str:
        """
        Get all possible relationships between entity types.

        This resource provides:
        - Valid relationship combinations
        - Relationship types and their meanings
        - Directional relationship information
        - Relationship descriptions and use cases
        """
        try:
            logger.info("Serving relationships schema")
            return json.dumps(knowledge_graph_schema.relationships, indent=2)
        except Exception as e:
            logger.error(f"Error serving relationships: {str(e)}")
            raise

    @mcp.resource("knowledge-graph://schema/entity/{entity_type}")
    async def get_entity_schema(entity_type: str) -> str:
        """
        Get schema information for a specific entity type.

        Args:
            entity_type: The name of the entity type (e.g., "Service", "Class", "Database")

        Returns:
            Detailed schema information for the specified entity type
        """
        try:
            logger.info(f"Serving schema for entity type: {entity_type}")
            entity_schema = knowledge_graph_schema.get_entity_schema(entity_type)

            if not entity_schema:
                raise ValueError(f"Entity type '{entity_type}' not found in schema")

            # Also include possible relationships for this entity
            relationships = knowledge_graph_schema.get_relationships_for_entity(
                entity_type
            )

            result = {
                "entity_type": entity_type,
                "schema": entity_schema,
                "possible_relationships": relationships,
            }

            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Error serving entity schema for {entity_type}: {str(e)}")
            raise

    @mcp.resource("knowledge-graph://schema/validation-guide")
    async def get_validation_guide() -> str:
        """
        Get validation rules and guidelines for working with the knowledge graph.

        This resource provides:
        - Entity creation guidelines
        - Relationship validation rules
        - Property type requirements
        - Best practices for data modeling
        """
        try:
            logger.info("Serving validation guide")

            guide = {
                "version": "1.0.0",
                "title": "Knowledge Graph Validation Guide",
                "sections": {
                    "entity_creation": {
                        "description": "Guidelines for creating entities in the knowledge graph",
                        "rules": [
                            "All required properties must be provided",
                            "Property values must match defined data types",
                            "Unique constraints must be respected",
                            "Use consistent naming conventions (snake_case for properties)",
                            "Provide meaningful descriptions for business entities",
                        ],
                    },
                    "relationship_creation": {
                        "description": "Guidelines for creating relationships between entities",
                        "rules": [
                            "Relationships must exist between valid entity type combinations",
                            "Use predefined relationship types from the schema",
                            "Ensure directional relationships are created correctly",
                            "Avoid creating duplicate relationships",
                            "Include relationship properties when relevant",
                        ],
                    },
                    "data_types": {
                        "supported_types": [
                            "string",
                            "integer",
                            "float",
                            "boolean",
                            "datetime",
                            "array",
                            "object",
                            "enum",
                        ],
                        "validation_rules": [
                            "String properties should have reasonable length limits",
                            "Enum properties must use predefined values",
                            "DateTime properties should use ISO 8601 format",
                            "Array properties should contain homogeneous data types",
                            "Sensitive properties should be marked and handled appropriately",
                        ],
                    },
                    "best_practices": {
                        "modeling": [
                            "Start with core business entities",
                            "Model relationships that provide business value",
                            "Use consistent entity and property naming",
                            "Document complex business rules and calculations",
                            "Regularly review and update the schema",
                        ],
                        "performance": [
                            "Create indexes on frequently queried properties",
                            "Use constraints to maintain data integrity",
                            "Avoid deeply nested relationship chains in queries",
                            "Consider relationship direction for query optimization",
                            "Monitor query performance and adjust indexes",
                        ],
                    },
                },
                "examples": {
                    "valid_entity": {
                        "type": "Service",
                        "properties": {
                            "name": "user-authentication-service",
                            "version": "2.1.0",
                            "description": "Handles user authentication and authorization",
                            "status": "active",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-20T14:45:00Z",
                        },
                    },
                    "valid_relationship": {
                        "from_entity": {"type": "Service", "name": "user-service"},
                        "to_entity": {"type": "Database", "name": "user-db"},
                        "relationship_type": "OWNS",
                        "description": "User service owns and manages the user database",
                    },
                },
            }

            return json.dumps(guide, indent=2)
        except Exception as e:
            logger.error(f"Error serving validation guide: {str(e)}")
            raise
