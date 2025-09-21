"""
Unit tests for MCP server resources and tools.
Tests the MCP server endpoints and resource serving.
"""

import json

import pytest
from knowledge_graph_mcp.resources.schemas import knowledge_graph_schema
from knowledge_graph_mcp.server import (
    get_complete_schema,
    get_entity_schema,
    get_entity_types,
    get_relationships,
    get_schema_summary,
    get_validation_guide,
    validate_entity_schema,
    validate_relationship,
)


class TestMCPServerResources:
    """Test cases for MCP server resource endpoints."""

    @pytest.mark.asyncio
    async def test_get_complete_schema(self):
        """Test complete schema resource."""
        result = await get_complete_schema()

        # Should return valid JSON
        parsed = json.loads(result)

        assert "entity_types" in parsed
        assert "relationships" in parsed
        assert "schema_summary" in parsed

    @pytest.mark.asyncio
    async def test_get_schema_summary(self):
        """Test schema summary resource."""
        result = await get_schema_summary()

        parsed = json.loads(result)

        assert "version" in parsed
        assert "statistics" in parsed
        assert "entity_categories" in parsed
        assert "relationship_types" in parsed

    @pytest.mark.asyncio
    async def test_get_entity_types(self):
        """Test entity types resource."""
        result = await get_entity_types()

        parsed = json.loads(result)

        # Should contain known entity types
        assert "Service" in parsed
        assert "Module" in parsed
        assert "Database" in parsed

        # Check structure of entity definitions
        service_def = parsed["Service"]
        assert "description" in service_def
        assert "properties" in service_def

    @pytest.mark.asyncio
    async def test_get_relationships(self):
        """Test relationships resource."""
        result = await get_relationships()

        parsed = json.loads(result)

        assert isinstance(parsed, list)
        assert len(parsed) > 0

        # Check relationship structure
        for rel in parsed[:5]:  # Check first 5
            assert "from" in rel
            assert "to" in rel
            assert "type" in rel
            assert "description" in rel

    @pytest.mark.asyncio
    async def test_get_entity_schema_valid(self):
        """Test getting schema for valid entity type."""
        result = await get_entity_schema("Service")

        parsed = json.loads(result)

        assert "entity_type" in parsed
        assert parsed["entity_type"] == "Service"
        assert "schema" in parsed
        assert "possible_relationships" in parsed

        # Check schema structure
        schema = parsed["schema"]
        assert "description" in schema
        assert "properties" in schema

    @pytest.mark.asyncio
    async def test_get_entity_schema_invalid(self):
        """Test getting schema for invalid entity type."""
        with pytest.raises(ValueError, match="Entity type 'InvalidEntity' not found"):
            await get_entity_schema("InvalidEntity")

    @pytest.mark.asyncio
    async def test_get_validation_guide(self):
        """Test validation guide resource."""
        result = await get_validation_guide()

        parsed = json.loads(result)

        assert "title" in parsed
        assert "sections" in parsed
        assert "examples" in parsed

        # Check sections
        sections = parsed["sections"]
        expected_sections = [
            "entity_creation",
            "relationship_creation",
            "data_types",
            "best_practices",
        ]

        for section in expected_sections:
            assert section in sections


class TestMCPServerTools:
    """Test cases for MCP server tool endpoints."""

    @pytest.mark.asyncio
    async def test_validate_entity_schema_valid(self):
        """Test entity schema validation with valid data."""
        properties = json.dumps(
            {
                "name": "test-service",
                "version": "1.0.0",
                "status": "active",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        )

        result = await validate_entity_schema("Service", properties)

        assert result["valid"] is True
        assert result["entity_type"] == "Service"
        assert len(result["errors"]) == 0
        assert "name" in result["validated_properties"]

    @pytest.mark.asyncio
    async def test_validate_entity_schema_missing_required(self):
        """Test entity schema validation with missing required properties."""
        properties = json.dumps(
            {
                "version": "1.0.0",
                "status": "active",
                # Missing required 'name', 'created_at', 'updated_at'
            }
        )

        result = await validate_entity_schema("Service", properties)

        assert result["valid"] is False
        assert len(result["errors"]) > 0

        # Should have errors for missing required properties
        error_text = " ".join(result["errors"])
        assert "name" in error_text
        assert "created_at" in error_text
        assert "updated_at" in error_text

    @pytest.mark.asyncio
    async def test_validate_entity_schema_invalid_enum(self):
        """Test entity schema validation with invalid enum values."""
        properties = json.dumps(
            {
                "name": "test-service",
                "status": "invalid_status",  # Invalid enum value
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        )

        result = await validate_entity_schema("Service", properties)

        assert result["valid"] is False
        assert len(result["errors"]) > 0

        # Should have error about invalid enum value
        error_text = " ".join(result["errors"])
        assert "status" in error_text
        assert "active" in error_text or "inactive" in error_text

    @pytest.mark.asyncio
    async def test_validate_entity_schema_invalid_json(self):
        """Test entity schema validation with invalid JSON."""
        invalid_json = "{ invalid json structure"

        result = await validate_entity_schema("Service", invalid_json)

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert (
            "JSON parsing error" in result["errors"][0]
            or "Invalid JSON" in result["errors"][0]
        )

    @pytest.mark.asyncio
    async def test_validate_entity_schema_unknown_entity(self):
        """Test entity schema validation with unknown entity type."""
        properties = json.dumps({"name": "test"})

        result = await validate_entity_schema("UnknownEntity", properties)

        assert result["valid"] is False
        assert "Unknown entity type" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_validate_entity_schema_extra_properties(self):
        """Test entity schema validation with extra properties."""
        properties = json.dumps(
            {
                "name": "test-service",
                "status": "active",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "extra_property": "not_in_schema",
            }
        )

        result = await validate_entity_schema("Service", properties)

        # Should be valid but have warnings
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert "extra_property" in result["warnings"][0]

    @pytest.mark.asyncio
    async def test_validate_relationship_valid(self):
        """Test relationship validation with valid relationship."""
        result = await validate_relationship("Service", "Module", "CONTAINS")

        assert result["valid"] is True
        assert result["from_entity_type"] == "Service"
        assert result["to_entity_type"] == "Module"
        assert result["relationship_type"] == "CONTAINS"

    @pytest.mark.asyncio
    async def test_validate_relationship_invalid(self):
        """Test relationship validation with invalid relationship."""
        result = await validate_relationship("Service", "Module", "INVALID_REL")

        assert result["valid"] is False
        assert "message" in result

        # Should provide suggestions if valid relationships exist
        if "suggestions" in result:
            assert isinstance(result["suggestions"], list)
            assert "CONTAINS" in result["suggestions"]

    @pytest.mark.asyncio
    async def test_validate_relationship_nonexistent_entities(self):
        """Test relationship validation with non-existent entity types."""
        result = await validate_relationship("NonExistent1", "NonExistent2", "CONTAINS")

        assert result["valid"] is False
        assert "No valid relationships" in result["message"]

    @pytest.mark.asyncio
    async def test_validate_relationship_suggestions(self):
        """Test relationship validation suggestions."""
        result = await validate_relationship("Service", "Database", "INVALID_REL")

        assert result["valid"] is False

        if "suggestions" in result:
            # Should suggest "OWNS" as valid relationship between Service and Database
            assert "OWNS" in result["suggestions"]


class TestSchemaConsistency:
    """Test schema consistency and integrity."""

    def test_all_entities_have_required_fields(self):
        """Test that all entities have required schema fields."""
        for entity_name, entity_def in knowledge_graph_schema.entity_types.items():
            assert "description" in entity_def, f"{entity_name} missing description"
            assert "properties" in entity_def, f"{entity_name} missing properties"
            assert len(entity_def["properties"]) > 0, f"{entity_name} has no properties"

    def test_relationship_entity_references_valid(self):
        """Test that all relationships reference valid entities."""
        entity_names = set(knowledge_graph_schema.entity_types.keys())

        for rel in knowledge_graph_schema.relationships:
            assert rel["from"] in entity_names, f"Invalid from entity: {rel['from']}"
            assert rel["to"] in entity_names, f"Invalid to entity: {rel['to']}"

    def test_no_duplicate_relationships(self):
        """Test that there are no duplicate relationship definitions."""
        seen_relationships = set()

        for rel in knowledge_graph_schema.relationships:
            rel_key = (rel["from"], rel["to"], rel["type"])
            assert rel_key not in seen_relationships, (
                f"Duplicate relationship: {rel_key}"
            )
            seen_relationships.add(rel_key)

    def test_entity_property_consistency(self):
        """Test entity property definition consistency."""
        for entity_name, entity_def in knowledge_graph_schema.entity_types.items():
            for prop_name, prop_def in entity_def["properties"].items():
                # Required field should be boolean
                if "required" in prop_def:
                    assert isinstance(prop_def["required"], bool)

                # Default values should match type
                if "default" in prop_def:
                    default_val = prop_def["default"]
                    prop_type = prop_def["type"]

                    if prop_type == "boolean":
                        assert isinstance(default_val, bool)
                    elif prop_type == "integer":
                        assert isinstance(default_val, int)
                    elif prop_type == "string":
                        assert isinstance(default_val, str)

    def test_constraint_format_consistency(self):
        """Test that constraint formats are consistent."""
        for entity_name, entity_def in knowledge_graph_schema.entity_types.items():
            if "constraints" in entity_def:
                for constraint in entity_def["constraints"]:
                    assert isinstance(constraint, str)
                    # Should start with constraint type
                    assert any(
                        constraint.startswith(ct)
                        for ct in ["UNIQUE", "CHECK", "NOT NULL"]
                    )

    def test_index_field_validity(self):
        """Test that indexed fields exist in entity properties."""
        for entity_name, entity_def in knowledge_graph_schema.entity_types.items():
            if "indexes" in entity_def:
                properties = entity_def["properties"]
                for index_field in entity_def["indexes"]:
                    assert index_field in properties, (
                        f"Index field {index_field} not found in {entity_name} properties"
                    )
