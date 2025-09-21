"""
Analytics and normalization MCP tools for Knowledge Graph server.
Handles entity normalization, duplicate detection, and graph analysis.
"""

import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from ..db_operations import create_relationship, execute_cypher

logger = logging.getLogger("knowledge-graph-mcp.analytics_tools")


def register_analytics_tools(mcp: FastMCP):
    """Register all analytics and normalization tools with the MCP server."""

    @mcp.tool()
    async def normalize_entities(
        entity_type: str,
        similarity_threshold: float = 0.8,
        merge_strategy: str = "keep_latest",
        dry_run: bool = True,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Normalize entities by finding and merging duplicates or similar entities.

        Args:
            entity_type: The type of entities to normalize (e.g., "Service", "Class")
            similarity_threshold: Similarity threshold for matching (0.0-1.0)
            merge_strategy: Strategy for merging - "keep_latest", "keep_oldest", "merge_properties"
            dry_run: If True, only reports what would be normalized without making changes
            database: Optional database name

        Returns:
            Normalization results including duplicates found and actions taken
        """
        try:
            logger.info(
                f"Normalizing {entity_type} entities via MCP (dry_run: {dry_run})"
            )

            # Find potential duplicates based on name similarity
            duplicate_query = f"""
            MATCH (n1:{entity_type}), (n2:{entity_type})
            WHERE elementId(n1) < elementId(n2)
              AND (
                n1.name = n2.name
                OR (n1.name IS NOT NULL AND n2.name IS NOT NULL AND
                    toLower(n1.name) = toLower(n2.name))
              )
            RETURN elementId(n1) as node1_id, n1.name as name1, properties(n1) as props1,
                   elementId(n2) as node2_id, n2.name as name2, properties(n2) as props2,
                   CASE
                     WHEN n1.name = n2.name THEN 1.0
                     WHEN toLower(n1.name) = toLower(n2.name) THEN 0.9
                     ELSE 0.0
                   END as similarity_score
            ORDER BY similarity_score DESC
            """

            params = {"threshold": similarity_threshold}
            duplicates = await execute_cypher(duplicate_query, params, database)

            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "entity_type": entity_type,
                    "duplicates_found": duplicates,
                    "duplicate_count": len(duplicates),
                    "similarity_threshold": similarity_threshold,
                    "message": f"Found {len(duplicates)} potential duplicate pairs (dry run)",
                }

            # Perform actual normalization
            normalized_pairs = []
            for dup in duplicates:
                try:
                    node1_id = dup["node1_id"]
                    node2_id = dup["node2_id"]

                    # Simple strategy: keep first node, merge second
                    keep_node_id, merge_node_id = node1_id, node2_id

                    # Delete relationships to merge_node and recreate to keep_node
                    # This is a simplified approach
                    delete_query = (
                        "MATCH (n) WHERE elementId(n) = $node_id DETACH DELETE n"
                    )
                    await execute_cypher(
                        delete_query, {"node_id": merge_node_id}, database
                    )

                    normalized_pairs.append(
                        {
                            "kept_node_id": keep_node_id,
                            "merged_node_id": merge_node_id,
                            "similarity_score": dup["similarity_score"],
                            "strategy": merge_strategy,
                        }
                    )

                except Exception as e:
                    logger.error(
                        f"Error normalizing pair {dup['node1_id']}, {dup['node2_id']}: {e}"
                    )
                    continue

            return {
                "success": True,
                "dry_run": False,
                "entity_type": entity_type,
                "duplicates_found": len(duplicates),
                "normalized_pairs": normalized_pairs,
                "normalized_count": len(normalized_pairs),
                "merge_strategy": merge_strategy,
                "message": f"Normalized {len(normalized_pairs)} duplicate pairs",
            }

        except Exception as e:
            logger.error(f"Error normalizing entities: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def merge_duplicate_entities(
        keep_node_id: str,
        merge_node_id: str,
        merge_strategy: str = "merge_properties",
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Merge two duplicate entities into one.

        Args:
            keep_node_id: Element ID of the node to keep
            merge_node_id: Element ID of the node to merge and delete
            merge_strategy: How to merge - "keep_properties", "merge_properties", "overwrite_properties"
            database: Optional database name

        Returns:
            Merge operation results
        """
        try:
            logger.info(f"Merging entities {merge_node_id} into {keep_node_id} via MCP")

            # Get properties from both nodes
            props_query = """
            MATCH (keep), (merge)
            WHERE elementId(keep) = $keep_id AND elementId(merge) = $merge_id
            RETURN properties(keep) as keep_props, properties(merge) as merge_props,
                   labels(keep) as keep_labels, labels(merge) as merge_labels
            """

            props_result = await execute_cypher(
                props_query,
                {"keep_id": keep_node_id, "merge_id": merge_node_id},
                database,
            )

            if not props_result:
                return {"success": False, "error": "One or both nodes not found"}

            keep_props = props_result[0]["keep_props"]
            merge_props = props_result[0]["merge_props"]

            # Merge properties based on strategy
            if merge_strategy == "merge_properties":
                # Merge properties, merge_props takes precedence
                final_props = {**keep_props, **merge_props}
            elif merge_strategy == "overwrite_properties":
                # Use only merge_props
                final_props = merge_props
            else:  # keep_properties
                # Use only keep_props
                final_props = keep_props

            # Update keep_node with final properties
            if merge_strategy != "keep_properties":
                set_clauses = []
                params = {"keep_id": keep_node_id}

                for key, value in final_props.items():
                    param_name = f"prop_{key}"
                    set_clauses.append(f"keep.{key} = ${param_name}")
                    params[param_name] = value

                if set_clauses:
                    update_query = f"""
                    MATCH (keep)
                    WHERE elementId(keep) = $keep_id
                    SET {", ".join(set_clauses)}
                    """
                    await execute_cypher(update_query, params, database)

            # Transfer relationships from merge_node to keep_node
            # Get all relationships of merge_node
            rel_query = """
            MATCH (merge)-[r]->(target)
            WHERE elementId(merge) = $merge_id
            RETURN elementId(target) as target_id, type(r) as rel_type, properties(r) as rel_props, 'outgoing' as direction
            UNION
            MATCH (source)-[r]->(merge)
            WHERE elementId(merge) = $merge_id
            RETURN elementId(source) as source_id, type(r) as rel_type, properties(r) as rel_props, 'incoming' as direction
            """

            relationships = await execute_cypher(
                rel_query, {"merge_id": merge_node_id}, database
            )

            # Recreate relationships with keep_node
            transferred_rels = 0
            for rel in relationships:
                try:
                    if rel["direction"] == "outgoing":
                        await create_relationship(
                            keep_node_id,
                            rel["target_id"],
                            rel["rel_type"],
                            rel["rel_props"],
                            database,
                        )
                    else:  # incoming
                        await create_relationship(
                            rel["source_id"],
                            keep_node_id,
                            rel["rel_type"],
                            rel["rel_props"],
                            database,
                        )
                    transferred_rels += 1
                except Exception as e:
                    logger.warning(f"Failed to transfer relationship: {e}")

            # Delete the merge_node
            await execute_cypher(
                "MATCH (n) WHERE elementId(n) = $node_id DETACH DELETE n RETURN count(n) as deleted",
                {"node_id": merge_node_id},
                database,
            )

            return {
                "success": True,
                "kept_node_id": keep_node_id,
                "merged_node_id": merge_node_id,
                "merge_strategy": merge_strategy,
                "transferred_relationships": transferred_rels,
                "final_properties": final_props,
                "message": f"Successfully merged {merge_node_id} into {keep_node_id}",
            }

        except Exception as e:
            logger.error(f"Error merging entities: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def analyze_graph_structure(database: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze the overall structure and statistics of the knowledge graph.

        Args:
            database: Optional database name

        Returns:
            Graph structure analysis and statistics
        """
        try:
            logger.info("Analyzing graph structure via MCP")

            # Get basic counts
            basic_stats_query = """
            MATCH (n)
            OPTIONAL MATCH ()-[r]->()
            RETURN count(DISTINCT n) as node_count, count(DISTINCT r) as relationship_count
            """

            basic_stats = await execute_cypher(basic_stats_query, {}, database)

            # Get entity type distribution
            entity_stats_query = """
            MATCH (n)
            UNWIND labels(n) as label
            RETURN label, count(n) as count
            ORDER BY count DESC
            """

            entity_stats = await execute_cypher(entity_stats_query, {}, database)

            # Get relationship type distribution
            rel_stats_query = """
            MATCH ()-[r]->()
            RETURN type(r) as relationship_type, count(r) as count
            ORDER BY count DESC
            """

            rel_stats = await execute_cypher(rel_stats_query, {}, database)

            # Get connectivity analysis
            connectivity_query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r_out]->()
            OPTIONAL MATCH (n)<-[r_in]-()
            RETURN
                count(DISTINCT n) as total_nodes,
                count(DISTINCT r_out) as outgoing_relationships,
                count(DISTINCT r_in) as incoming_relationships,
                avg(size((n)-[]-())) as avg_degree
            """

            connectivity_stats = await execute_cypher(connectivity_query, {}, database)

            return {
                "success": True,
                "basic_statistics": basic_stats[0] if basic_stats else {},
                "entity_distribution": entity_stats,
                "relationship_distribution": rel_stats,
                "connectivity_analysis": connectivity_stats[0]
                if connectivity_stats
                else {},
                "message": "Graph structure analysis completed",
            }

        except Exception as e:
            logger.error(f"Error analyzing graph structure: {str(e)}")
            return {"success": False, "error": str(e)}
