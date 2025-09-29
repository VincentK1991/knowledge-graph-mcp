"""
Text extraction utilities for generating embeddings from node properties.
"""

from typing import Any, Dict


def extract_text_from_properties(entity_type: str, properties: Dict[str, Any]) -> str:
    """
    Extract and format text from node properties for embedding generation.

    Args:
        entity_type: The type of entity (e.g., "Service", "Database", "Class")
        properties: Dictionary of node properties

    Returns:
        Formatted text string suitable for embedding generation
    """
    # Start with entity type as context
    text_parts = [f"Entity Type: {entity_type}"]

    # Extract string properties and format them
    for key, value in properties.items():
        # Skip non-string values and embedding-related properties
        if key == "embedding_vector" or not isinstance(value, str):
            continue

        # Skip empty strings
        if not value.strip():
            continue

        # Format as "key: value"
        text_parts.append(f"{key}: {value}")

    # Join all parts with newlines for clear structure
    return "\n".join(text_parts)


def get_embeddable_properties(properties: Dict[str, Any]) -> Dict[str, str]:
    """
    Get only the string properties that should be used for embedding.

    Args:
        properties: Dictionary of node properties

    Returns:
        Dictionary containing only string properties suitable for embedding
    """
    embeddable = {}

    for key, value in properties.items():
        # Only include string values that are not empty
        if isinstance(value, str) and value.strip():
            # Skip embedding-related properties to avoid recursion
            if key != "embedding_vector":
                embeddable[key] = value

    return embeddable
