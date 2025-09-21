"""
Unit tests for schema resources and validation.
Tests the knowledge graph schema functionality.
"""

import json

from knowledge_graph_mcp.resources.schemas import (
    KnowledgeGraphSchema,
    knowledge_graph_schema,
)


class TestKnowledgeGraphSchema:
    """Test cases for KnowledgeGraphSchema class."""

    def test_schema_initialization(self):
        """Test schema initialization and basic properties."""
        schema = KnowledgeGraphSchema()

        assert len(schema.entity_types) > 0
        assert len(schema.relationships) > 0
        assert "schema_summary" in schema.__dict__

    def test_entity_types_structure(self):
        """Test entity types structure and required fields."""
        for entity_name, entity_def in knowledge_graph_schema.entity_types.items():
            assert "description" in entity_def
            assert "properties" in entity_def

            # Check properties structure
            for prop_name, prop_def in entity_def["properties"].items():
                assert "type" in prop_def
                assert prop_def["type"] in [
                    "string",
                    "integer",
                    "float",
                    "boolean",
                    "datetime",
                    "array",
                    "object",
                    "enum",
                ]

    def test_relationships_structure(self):
        """Test relationships structure and required fields."""
        for relationship in knowledge_graph_schema.relationships:
            assert "from" in relationship
            assert "to" in relationship
            assert "type" in relationship
            assert "description" in relationship

            # Verify entity types exist
            assert relationship["from"] in knowledge_graph_schema.entity_types
            assert relationship["to"] in knowledge_graph_schema.entity_types

    def test_get_entity_schema(self):
        """Test getting schema for specific entity type."""
        service_schema = knowledge_graph_schema.get_entity_schema("Service")

        assert service_schema is not None
        assert "description" in service_schema
        assert "properties" in service_schema
        assert "name" in service_schema["properties"]

    def test_get_entity_schema_nonexistent(self):
        """Test getting schema for non-existent entity type."""
        schema = knowledge_graph_schema.get_entity_schema("NonExistentEntity")
        assert schema == {}

    def test_get_relationships_for_entity(self):
        """Test getting relationships for specific entity."""
        service_relationships = knowledge_graph_schema.get_relationships_for_entity(
            "Service"
        )

        assert len(service_relationships) > 0

        # Verify all returned relationships involve Service
        for rel in service_relationships:
            assert rel["from"] == "Service" or rel["to"] == "Service"

    def test_get_relationship_types(self):
        """Test getting all unique relationship types."""
        rel_types = knowledge_graph_schema.get_relationship_types()

        assert len(rel_types) > 0
        assert isinstance(rel_types, list)

        # Check for expected relationship types
        expected_types = ["CONTAINS", "DEPENDS_ON", "IMPLEMENTS", "USES"]
        for expected_type in expected_types:
            assert expected_type in rel_types

    def test_validate_relationship_valid(self):
        """Test validating valid relationships."""
        # Test known valid relationships
        valid_cases = [
            ("Service", "Module", "CONTAINS"),
            ("Class", "Interface", "IMPLEMENTS"),
            ("Function", "BusinessRule", "IMPLEMENTS"),
            ("Service", "Database", "OWNS"),
        ]

        for from_entity, to_entity, rel_type in valid_cases:
            is_valid = knowledge_graph_schema.validate_relationship(
                from_entity, to_entity, rel_type
            )
            assert is_valid is True, (
                f"{from_entity} -{rel_type}-> {to_entity} should be valid"
            )

    def test_validate_relationship_invalid(self):
        """Test validating invalid relationships."""
        # Test known invalid relationships
        invalid_cases = [
            ("Service", "Module", "INVALID_RELATIONSHIP"),
            ("NonExistentEntity", "Service", "CONTAINS"),
            ("Service", "NonExistentEntity", "CONTAINS"),
        ]

        for from_entity, to_entity, rel_type in invalid_cases:
            is_valid = knowledge_graph_schema.validate_relationship(
                from_entity, to_entity, rel_type
            )
            assert is_valid is False, (
                f"{from_entity} -{rel_type}-> {to_entity} should be invalid"
            )

    def test_schema_summary_structure(self):
        """Test schema summary structure and content."""
        summary = knowledge_graph_schema.schema_summary

        assert "version" in summary
        assert "description" in summary
        assert "statistics" in summary
        assert "entity_categories" in summary
        assert "relationship_types" in summary

        # Check statistics
        stats = summary["statistics"]
        assert "total_entity_types" in stats
        assert "total_relationship_types" in stats
        assert "unique_relationship_types" in stats

        # Verify statistics are correct
        assert stats["total_entity_types"] == len(knowledge_graph_schema.entity_types)
        assert stats["total_relationship_types"] == len(
            knowledge_graph_schema.relationships
        )

    def test_entity_categories(self):
        """Test entity categorization."""
        categories = knowledge_graph_schema.schema_summary["entity_categories"]

        expected_categories = [
            "Service Layer",
            "Code Structure",
            "Web Layer",
            "Business Logic",
            "Database & Data",
            "Configuration",
            "Infrastructure",
            "Monitoring",
        ]

        for category in expected_categories:
            assert category in categories
            assert len(categories[category]) > 0

    def test_to_dict_conversion(self):
        """Test schema conversion to dictionary."""
        schema_dict = knowledge_graph_schema.to_dict()

        assert "entity_types" in schema_dict
        assert "relationships" in schema_dict
        assert "schema_summary" in schema_dict

        # Verify structure matches original
        assert len(schema_dict["entity_types"]) == len(
            knowledge_graph_schema.entity_types
        )
        assert len(schema_dict["relationships"]) == len(
            knowledge_graph_schema.relationships
        )

    def test_to_json_serialization(self):
        """Test schema JSON serialization."""
        schema_json = knowledge_graph_schema.to_json()

        # Should be valid JSON
        parsed = json.loads(schema_json)

        assert "entity_types" in parsed
        assert "relationships" in parsed
        assert "schema_summary" in parsed

    def test_entity_constraints_and_indexes(self):
        """Test entity constraints and indexes configuration."""
        entities_with_constraints = 0
        entities_with_indexes = 0

        for entity_name, entity_def in knowledge_graph_schema.entity_types.items():
            if "constraints" in entity_def:
                entities_with_constraints += 1
                assert isinstance(entity_def["constraints"], list)
                assert len(entity_def["constraints"]) > 0

            if "indexes" in entity_def:
                entities_with_indexes += 1
                assert isinstance(entity_def["indexes"], list)
                assert len(entity_def["indexes"]) > 0

        # Most entities should have constraints and indexes
        assert (
            entities_with_constraints > len(knowledge_graph_schema.entity_types) * 0.7
        )
        assert entities_with_indexes > len(knowledge_graph_schema.entity_types) * 0.8

    def test_property_type_validation(self):
        """Test property type definitions."""
        valid_types = [
            "string",
            "integer",
            "float",
            "boolean",
            "datetime",
            "array",
            "object",
            "enum",
        ]

        for entity_name, entity_def in knowledge_graph_schema.entity_types.items():
            for prop_name, prop_def in entity_def["properties"].items():
                assert prop_def["type"] in valid_types, (
                    f"Invalid type in {entity_name}.{prop_name}: {prop_def['type']}"
                )

                # If enum type, should have enum values
                if prop_def["type"] == "enum":
                    assert "enum" in prop_def
                    assert isinstance(prop_def["enum"], list)
                    assert len(prop_def["enum"]) > 0

    def test_relationship_bidirectionality(self):
        """Test that relationships make sense bidirectionally."""
        relationship_pairs = {}

        for rel in knowledge_graph_schema.relationships:
            key = (rel["from"], rel["to"])
            if key not in relationship_pairs:
                relationship_pairs[key] = []
            relationship_pairs[key].append(rel["type"])

        # Check for some expected bidirectional relationships
        service_module = relationship_pairs.get(("Service", "Module"), [])
        assert "CONTAINS" in service_module

        class_interface = relationship_pairs.get(("Class", "Interface"), [])
        assert "IMPLEMENTS" in class_interface

    def test_schema_version_consistency(self):
        """Test schema version consistency."""
        summary = knowledge_graph_schema.schema_summary

        assert "version" in summary
        assert summary["version"] == "1.0.0"

    def test_usage_guidelines_presence(self):
        """Test that usage guidelines are present and complete."""
        guidelines = knowledge_graph_schema.schema_summary["usage_guidelines"]

        expected_guidelines = [
            "entity_creation",
            "relationship_creation",
            "property_validation",
            "indexing",
        ]

        for guideline in expected_guidelines:
            assert guideline in guidelines
            assert isinstance(guidelines[guideline], str)
            assert len(guidelines[guideline]) > 0
