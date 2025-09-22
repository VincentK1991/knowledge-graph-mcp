"""
YAML Schema Loader for Knowledge Graph MCP Server

This module provides functionality to load domain-specific knowledge graph schemas
from YAML files, making it easy to support different domains and customize schemas.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class SchemaMetadata:
    """Metadata for a knowledge graph schema."""

    version: str
    name: str
    description: str
    categories: List[str]


class YAMLSchemaLoader:
    """
    Loads and manages knowledge graph schemas from YAML files.

    This class provides a flexible way to load domain-specific schemas,
    allowing users to easily customize entity types and relationships
    for different knowledge domains.
    """

    def __init__(self, schemas_directory: Optional[str] = None):
        """
        Initialize the schema loader.

        Args:
            schemas_directory: Path to directory containing YAML schema files.
                              If None, uses default schemas directory.
        """
        if schemas_directory is None:
            # Default to schemas directory relative to this file
            current_dir = Path(__file__).parent.parent.parent.parent
            self.schemas_directory = current_dir / "schemas"
        else:
            self.schemas_directory = Path(schemas_directory)

        self.loaded_schemas: Dict[str, Dict[str, Any]] = {}
        self._ensure_schemas_directory()

    def _ensure_schemas_directory(self):
        """Ensure the schemas directory exists."""
        self.schemas_directory.mkdir(parents=True, exist_ok=True)

    def load_schema(self, schema_name: str) -> Dict[str, Any]:
        """
        Load a specific schema by name.

        Args:
            schema_name: Name of the schema file (without .yaml extension)

        Returns:
            Dictionary containing the parsed schema

        Raises:
            FileNotFoundError: If schema file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        schema_file = self.schemas_directory / f"{schema_name}.yaml"

        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_data = yaml.safe_load(f)

            # Cache the loaded schema
            self.loaded_schemas[schema_name] = schema_data
            return schema_data

        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML schema {schema_name}: {e}")

    def get_available_schemas(self) -> List[str]:
        """
        Get list of available schema files.

        Returns:
            List of schema names (without .yaml extension)
        """
        if not self.schemas_directory.exists():
            return []

        schema_files = list(self.schemas_directory.glob("*.yaml"))
        return [f.stem for f in schema_files]

    def get_schema_metadata(self, schema_name: str) -> SchemaMetadata:
        """
        Get metadata for a specific schema.

        Args:
            schema_name: Name of the schema

        Returns:
            SchemaMetadata object
        """
        if schema_name not in self.loaded_schemas:
            self.load_schema(schema_name)

        schema_data = self.loaded_schemas[schema_name]
        metadata = schema_data.get("metadata", {})

        return SchemaMetadata(
            version=metadata.get("version", "1.0.0"),
            name=metadata.get("name", schema_name),
            description=metadata.get("description", ""),
            categories=metadata.get("categories", []),
        )

    def get_entity_types(self, schema_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get entity types from a schema.

        Args:
            schema_name: Name of the schema

        Returns:
            Dictionary of entity types and their definitions
        """
        if schema_name not in self.loaded_schemas:
            self.load_schema(schema_name)

        return self.loaded_schemas[schema_name].get("entity_types", {})

    def get_relationships(self, schema_name: str) -> List[Dict[str, Any]]:
        """
        Get relationships from a schema.

        Args:
            schema_name: Name of the schema

        Returns:
            List of relationship definitions
        """
        if schema_name not in self.loaded_schemas:
            self.load_schema(schema_name)

        return self.loaded_schemas[schema_name].get("relationships", [])

    def get_entity_schema(self, schema_name: str, entity_type: str) -> Dict[str, Any]:
        """
        Get schema for a specific entity type.

        Args:
            schema_name: Name of the schema
            entity_type: Type of entity

        Returns:
            Entity schema definition
        """
        entity_types = self.get_entity_types(schema_name)
        return entity_types.get(entity_type, {})

    def get_relationships_for_entity(
        self, schema_name: str, entity_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get all possible relationships for a given entity type.

        Args:
            schema_name: Name of the schema
            entity_type: Type of entity

        Returns:
            List of relationships involving the entity type
        """
        relationships = self.get_relationships(schema_name)
        return [
            rel
            for rel in relationships
            if rel.get("from") == entity_type or rel.get("to") == entity_type
        ]

    def get_relationship_types(self, schema_name: str) -> List[str]:
        """
        Get all unique relationship types from a schema.

        Args:
            schema_name: Name of the schema

        Returns:
            List of unique relationship types
        """
        relationships = self.get_relationships(schema_name)
        return list(
            set([rel.get("type", "") for rel in relationships if rel.get("type")])
        )

    def validate_relationship(
        self, schema_name: str, from_entity: str, to_entity: str, relationship_type: str
    ) -> bool:
        """
        Validate if a relationship is allowed between two entity types.

        Args:
            schema_name: Name of the schema
            from_entity: Source entity type
            to_entity: Target entity type
            relationship_type: Type of relationship

        Returns:
            True if relationship is valid, False otherwise
        """
        relationships = self.get_relationships(schema_name)

        for rel in relationships:
            if (
                rel.get("from") == from_entity
                and rel.get("to") == to_entity
                and rel.get("type") == relationship_type
            ):
                return True
        return False

    def merge_schemas(self, *schema_names: str) -> Dict[str, Any]:
        """
        Merge multiple schemas into one.

        Args:
            *schema_names: Names of schemas to merge

        Returns:
            Merged schema dictionary
        """
        merged_entity_types = {}
        merged_relationships = []
        merged_categories = set()

        for schema_name in schema_names:
            entity_types = self.get_entity_types(schema_name)
            relationships = self.get_relationships(schema_name)
            metadata = self.get_schema_metadata(schema_name)

            # Merge entity types (later schemas override earlier ones)
            merged_entity_types.update(entity_types)

            # Combine relationships (avoiding duplicates)
            for rel in relationships:
                if rel not in merged_relationships:
                    merged_relationships.append(rel)

            # Combine categories
            merged_categories.update(metadata.categories)

        return {
            "metadata": {
                "version": "1.0.0",
                "name": "Merged Schema",
                "description": f"Merged schema from: {', '.join(schema_names)}",
                "categories": list(merged_categories),
            },
            "entity_types": merged_entity_types,
            "relationships": merged_relationships,
        }

    def create_schema_summary(self, schema_name: str) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of a schema.

        Args:
            schema_name: Name of the schema

        Returns:
            Schema summary dictionary
        """
        entity_types = self.get_entity_types(schema_name)
        relationships = self.get_relationships(schema_name)
        metadata = self.get_schema_metadata(schema_name)

        # Group entities by category
        entity_categories = {}
        for entity_name, entity_def in entity_types.items():
            category = entity_def.get("category", "Uncategorized")
            if category not in entity_categories:
                entity_categories[category] = []
            entity_categories[category].append(entity_name)

        relationship_types = self.get_relationship_types(schema_name)

        return {
            "metadata": {
                "version": metadata.version,
                "name": metadata.name,
                "description": metadata.description,
            },
            "statistics": {
                "total_entity_types": len(entity_types),
                "total_relationships": len(relationships),
                "unique_relationship_types": len(relationship_types),
                "categories_count": len(entity_categories),
            },
            "entity_categories": entity_categories,
            "relationship_types": sorted(relationship_types),
            "constraints_summary": {
                "unique_constraints": len(
                    [e for e in entity_types.values() if "constraints" in e]
                ),
                "indexed_entities": len(
                    [e for e in entity_types.values() if "indexes" in e]
                ),
            },
        }

    def export_to_python_class(
        self, schema_name: str, class_name: str = "KnowledgeGraphSchema"
    ) -> str:
        """
        Export a YAML schema back to Python class format.

        Args:
            schema_name: Name of the schema to export
            class_name: Name of the generated Python class

        Returns:
            Python code as string
        """
        entity_types = self.get_entity_types(schema_name)
        relationships = self.get_relationships(schema_name)
        metadata = self.get_schema_metadata(schema_name)

        # Generate Python code
        python_code = f'''"""
Generated Knowledge Graph Schema: {metadata.name}
Version: {metadata.version}
Description: {metadata.description}
"""

from typing import Any, Dict, List


class {class_name}:
    """
    {metadata.description}
    """

    def __init__(self):
        self.entity_types = self._define_entity_types()
        self.relationships = self._define_relationships()

    def _define_entity_types(self) -> Dict[str, Dict[str, Any]]:
        """Define all entity types with their properties and constraints."""
        return {repr(entity_types)[1:-1]}

    def _define_relationships(self) -> List[Dict[str, Any]]:
        """Define all possible relationships between entities."""
        return {repr(relationships)}
'''

        return python_code


# Create a global schema loader instance
schema_loader = YAMLSchemaLoader()
