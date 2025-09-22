"""
Knowledge Graph Schema Resource for MCP Server

This module provides the schema definition and structure for the knowledge graph,
exposing entity types, relationships, and their constraints to ground AI interactions.

All schemas are now loaded dynamically from YAML files for better maintainability
and domain-specific customization.
"""

import json
import logging
from typing import Any, Dict, List
from .schema_loader import schema_loader

logger = logging.getLogger(__name__)


class KnowledgeGraphSchema:
    """
    Modern knowledge graph schema that loads from YAML files.

    This class provides a clean interface for accessing schema information
    while loading schemas dynamically from YAML files, allowing for easy
    customization and domain-specific schemas.
    """

    def __init__(self, schema_name: str = "software_engineering"):
        """
        Initialize with a specific schema.

        Args:
            schema_name: Name of the YAML schema to load (default: software_engineering)
        """
        self.schema_name = schema_name
        self.loader = schema_loader

        try:
            # Load the specified schema
            self.schema_data = self.loader.load_schema(schema_name)
            self.entity_types = self.loader.get_entity_types(schema_name)
            self.relationships = self.loader.get_relationships(schema_name)
            self.schema_summary = self.loader.create_schema_summary(schema_name)
            logger.info(f"Loaded YAML schema: {schema_name}")
        except FileNotFoundError as e:
            logger.error(f"Schema '{schema_name}' not found: {e}")
            raise FileNotFoundError(f"Schema '{schema_name}' not found. Available schemas: {self.loader.get_available_schemas()}")
        except Exception as e:
            logger.error(f"Error loading schema '{schema_name}': {e}")
            raise

    def get_entity_schema(self, entity_type: str) -> Dict[str, Any]:
        """Get schema for a specific entity type."""
        return self.entity_types.get(entity_type, {})

    def get_relationships_for_entity(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get all possible relationships for a given entity type."""
        return self.loader.get_relationships_for_entity(self.schema_name, entity_type)

    def get_relationship_types(self) -> List[str]:
        """Get all unique relationship types."""
        return self.loader.get_relationship_types(self.schema_name)

    def validate_relationship(
        self, from_entity: str, to_entity: str, relationship_type: str
    ) -> bool:
        """Validate if a relationship is allowed between two entity types."""
        return self.loader.validate_relationship(
            self.schema_name, from_entity, to_entity, relationship_type
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the entire schema to a dictionary."""
        return {
            "entity_types": self.entity_types,
            "relationships": self.relationships,
            "schema_summary": self.schema_summary,
        }

    def to_json(self) -> str:
        """Convert the entire schema to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def switch_schema(self, schema_name: str):
        """
        Switch to a different schema.

        Args:
            schema_name: Name of the new schema to load
        """
        self.__init__(schema_name)

    def get_available_schemas(self) -> List[str]:
        """Get list of available schema files."""
        return self.loader.get_available_schemas()

    def get_schema_metadata(self):
        """Get metadata for the current schema."""
        return self.loader.get_schema_metadata(self.schema_name)

    def merge_with_schemas(self, *other_schema_names: str) -> Dict[str, Any]:
        """
        Merge current schema with other schemas.

        Args:
            *other_schema_names: Names of other schemas to merge with

        Returns:
            Merged schema dictionary
        """
        all_schemas = [self.schema_name] + list(other_schema_names)
        return self.loader.merge_schemas(*all_schemas)


# Create global schema instances
knowledge_graph_schema = KnowledgeGraphSchema()  # Default software engineering schema

# For backward compatibility, also expose the schema as default_schema
default_schema = knowledge_graph_schema
