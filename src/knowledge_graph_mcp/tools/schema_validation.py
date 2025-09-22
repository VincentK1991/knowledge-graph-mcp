"""
Schema validation functions for Knowledge Graph MCP server.

This module provides comprehensive validation functions for entities and relationships
against the YAML-based schema system. All validation logic is centralized here
for consistency and reusability across different MCP tools.
"""

import json
import logging
from typing import Any, Dict, Optional

from ..resources.schemas import knowledge_graph_schema
from .db_operations import execute_cypher

logger = logging.getLogger("knowledge-graph-mcp.schema_validation")


async def validate_entity_schema(entity_type: str, properties: str) -> Dict[str, Any]:
    """
    Validate an entity against the schema.

    Args:
        entity_type: The type of entity to validate (e.g., "Service", "Class", "Database")
        properties: JSON string of entity properties

    Returns:
        Dictionary with validation results including:
        - valid: Boolean indicating if validation passed
        - entity_type: The entity type that was validated
        - errors: List of validation errors
        - warnings: List of validation warnings
        - validated_properties: List of property names that were validated
    """
    try:
        # Parse properties
        parsed_properties = json.loads(properties)

        # Get entity schema
        entity_schema = knowledge_graph_schema.get_entity_schema(entity_type)
        if not entity_schema:
            return {"valid": False, "errors": [f"Unknown entity type: {entity_type}"]}

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
                elif expected_type == "boolean" and not isinstance(prop_value, bool):
                    errors.append(f"Property {prop_name} must be a boolean")
                elif expected_type == "array" and not isinstance(prop_value, list):
                    errors.append(f"Property {prop_name} must be an array")
                elif expected_type == "float" and not isinstance(
                    prop_value, (int, float)
                ):
                    errors.append(f"Property {prop_name} must be a number")
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
        return {"valid": False, "errors": [f"Invalid JSON in properties: {str(e)}"]}
    except Exception as e:
        logger.error(f"Error validating entity schema: {str(e)}")
        raise


async def validate_relationship_schema(
    from_node_id: str,
    to_node_id: str,
    relationship_type: str,
    database: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate a relationship against the schema.

    This function validates that:
    1. The relationship type exists in the schema
    2. The from_node and to_node entity types are compatible
    3. The triplet (from_entity_type, relationship_type, to_entity_type) is allowed

    Args:
        from_node_id: Element ID of the source node
        to_node_id: Element ID of the target node
        relationship_type: Type of relationship to validate
        database: Optional database name

    Returns:
        Dictionary with validation results including:
        - valid: Boolean indicating if validation passed
        - relationship_type: The relationship type that was validated
        - errors: List of validation errors
        - warnings: List of validation warnings
        - info: Dictionary with additional information about the nodes and validation
    """
    try:
        errors = []
        warnings = []
        info = {}

        # 1. Check if relationship type exists in schema
        valid_relationship_types = knowledge_graph_schema.get_relationship_types()
        if relationship_type not in valid_relationship_types:
            errors.append(f"Unknown relationship type: {relationship_type}")
            errors.append(
                f"Valid relationship types: {', '.join(sorted(valid_relationship_types))}"
            )
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "info": info,
            }

        # 2. Get the entity types of the from and to nodes
        node_query = """
        MATCH (from_node), (to_node)
        WHERE elementId(from_node) = $from_node_id AND elementId(to_node) = $to_node_id
        RETURN labels(from_node) as from_labels, labels(to_node) as to_labels
        """

        result = await execute_cypher(
            node_query,
            {"from_node_id": from_node_id, "to_node_id": to_node_id},
            database,
        )

        if not result:
            errors.append("One or both nodes not found")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "info": info,
            }

        from_labels = result[0]["from_labels"]
        to_labels = result[0]["to_labels"]

        if not from_labels or not to_labels:
            errors.append("One or both nodes have no labels (entity types)")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "info": info,
            }

        # Get the primary entity type (first label) for each node
        from_entity_type = from_labels[0]
        to_entity_type = to_labels[0]

        info["from_entity_type"] = from_entity_type
        info["to_entity_type"] = to_entity_type
        info["from_labels"] = from_labels
        info["to_labels"] = to_labels

        # 3. Validate the relationship triplet against schema
        is_valid_triplet = knowledge_graph_schema.validate_relationship(
            from_entity_type, to_entity_type, relationship_type
        )

        if not is_valid_triplet:
            errors.append(
                f"Invalid relationship: {from_entity_type} {relationship_type} {to_entity_type}"
            )

            # Provide helpful suggestions
            valid_relationships_from = (
                knowledge_graph_schema.get_relationships_for_entity(from_entity_type)
            )

            # Find valid relationship types between these entity types
            valid_between = []
            for rel in valid_relationships_from:
                if (
                    rel.get("from") == from_entity_type
                    and rel.get("to") == to_entity_type
                ):
                    valid_between.append(rel.get("type"))

            if valid_between:
                errors.append(
                    f"Valid relationship types between {from_entity_type} and {to_entity_type}: {', '.join(valid_between)}"
                )
            else:
                errors.append(
                    f"No valid relationships defined between {from_entity_type} and {to_entity_type} in the schema"
                )

                # Suggest valid targets for the relationship type
                valid_targets = []
                for rel in knowledge_graph_schema.relationships:
                    if (
                        rel.get("from") == from_entity_type
                        and rel.get("type") == relationship_type
                    ):
                        valid_targets.append(rel.get("to"))

                if valid_targets:
                    errors.append(
                        f"Valid target entity types for {from_entity_type} {relationship_type}: {', '.join(set(valid_targets))}"
                    )

        # 4. Additional warnings for multiple labels
        if len(from_labels) > 1:
            warnings.append(
                f"From node has multiple labels: {from_labels}. Using {from_entity_type} for validation."
            )

        if len(to_labels) > 1:
            warnings.append(
                f"To node has multiple labels: {to_labels}. Using {to_entity_type} for validation."
            )

        return {
            "valid": len(errors) == 0,
            "relationship_type": relationship_type,
            "errors": errors,
            "warnings": warnings,
            "info": info,
        }

    except Exception as e:
        logger.error(f"Error validating relationship schema: {str(e)}")
        return {
            "valid": False,
            "errors": [f"Validation error: {str(e)}"],
            "warnings": [],
            "info": {},
        }


def validate_entity_type_exists(entity_type: str) -> Dict[str, Any]:
    """
    Validate that an entity type exists in the schema.

    Args:
        entity_type: The entity type to check

    Returns:
        Dictionary with validation results
    """
    entity_schema = knowledge_graph_schema.get_entity_schema(entity_type)

    if not entity_schema:
        return {
            "valid": False,
            "entity_type": entity_type,
            "error": f"Unknown entity type: {entity_type}",
            "available_types": list(knowledge_graph_schema.entity_types.keys()),
        }

    return {"valid": True, "entity_type": entity_type, "schema": entity_schema}


def validate_relationship_type_exists(relationship_type: str) -> Dict[str, Any]:
    """
    Validate that a relationship type exists in the schema.

    Args:
        relationship_type: The relationship type to check

    Returns:
        Dictionary with validation results
    """
    valid_types = knowledge_graph_schema.get_relationship_types()

    if relationship_type not in valid_types:
        return {
            "valid": False,
            "relationship_type": relationship_type,
            "error": f"Unknown relationship type: {relationship_type}",
            "available_types": sorted(valid_types),
        }

    return {"valid": True, "relationship_type": relationship_type}


def validate_relationship_triplet(
    from_entity_type: str, to_entity_type: str, relationship_type: str
) -> Dict[str, Any]:
    """
    Validate a relationship triplet without database queries.

    This is useful for validating relationships before nodes are created.

    Args:
        from_entity_type: Source entity type
        to_entity_type: Target entity type
        relationship_type: Relationship type

    Returns:
        Dictionary with validation results
    """
    # Check if entity types exist
    from_validation = validate_entity_type_exists(from_entity_type)
    to_validation = validate_entity_type_exists(to_entity_type)
    rel_validation = validate_relationship_type_exists(relationship_type)

    errors = []
    if not from_validation["valid"]:
        errors.append(from_validation["error"])
    if not to_validation["valid"]:
        errors.append(to_validation["error"])
    if not rel_validation["valid"]:
        errors.append(rel_validation["error"])

    if errors:
        return {"valid": False, "errors": errors}

    # Check if the triplet is valid
    is_valid = knowledge_graph_schema.validate_relationship(
        from_entity_type, to_entity_type, relationship_type
    )

    if not is_valid:
        # Find valid alternatives
        valid_relationships = knowledge_graph_schema.get_relationships_for_entity(
            from_entity_type
        )
        valid_between = [
            rel.get("type")
            for rel in valid_relationships
            if rel.get("from") == from_entity_type and rel.get("to") == to_entity_type
        ]

        error_msg = f"Invalid relationship: {from_entity_type} {relationship_type} {to_entity_type}"
        suggestions = []

        if valid_between:
            suggestions.append(
                f"Valid relationships between {from_entity_type} and {to_entity_type}: {', '.join(valid_between)}"
            )
        else:
            # Find valid targets for this relationship type from this entity
            valid_targets = [
                rel.get("to")
                for rel in knowledge_graph_schema.relationships
                if rel.get("from") == from_entity_type
                and rel.get("type") == relationship_type
            ]
            if valid_targets:
                suggestions.append(
                    f"Valid targets for {from_entity_type} {relationship_type}: {', '.join(set(valid_targets))}"
                )

        return {
            "valid": False,
            "errors": [error_msg],
            "suggestions": suggestions,
            "from_entity_type": from_entity_type,
            "to_entity_type": to_entity_type,
            "relationship_type": relationship_type,
        }

    return {
        "valid": True,
        "from_entity_type": from_entity_type,
        "to_entity_type": to_entity_type,
        "relationship_type": relationship_type,
    }
