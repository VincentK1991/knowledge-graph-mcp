"""
Simple property filtering for Knowledge Graph MCP server.
"""

from typing import Any, Dict


def clean_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove embedding_vector from node properties.

    Args:
        properties: Node properties dictionary

    Returns:
        Properties with embedding_vector removed
    """
    return {k: v for k, v in properties.items() if k != "embedding_vector"}
