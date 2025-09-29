"""
Analytics and normalization MCP tools for Knowledge Graph server.
Handles entity normalization, duplicate detection, and graph analysis.
"""

import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from ...utils.property_filter import clean_properties
from ..db_operations import create_relationship, execute_cypher

logger = logging.getLogger("knowledge-graph-mcp.analytics_tools")


def register_analytics_tools(mcp: FastMCP):
    """Register all analytics and normalization tools with the MCP server."""

    @mcp.tool()
    async def find_similar_nodes(  # pyright: ignore
        entity_type: Optional[str] = None,
        similarity_threshold: float = 0.8,
        comparison_property: str = "name",
        limit: int = 50,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Find similar nodes based on property similarity.

        Args:
            entity_type: Optional entity type to filter by (e.g., "Service", "Class")
            similarity_threshold: Similarity threshold for matching (0.0-1.0)
            comparison_property: Property to compare for similarity (default: "name")
            limit: Maximum number of similar pairs to return
            database: Optional database name

        Returns:
            List of similar node pairs with similarity scores
        """
        try:
            logger.info(
                f"Finding similar nodes via MCP (threshold: {similarity_threshold})"
            )

            # Build query based on whether entity_type is specified
            if entity_type:
                match_clause = f"MATCH (n1:{entity_type}), (n2:{entity_type})"
            else:
                match_clause = "MATCH (n1), (n2)"

            # Find potential similar nodes based on property similarity
            similar_query = f"""
            {match_clause}
            WHERE elementId(n1) < elementId(n2)
              AND n1.{comparison_property} IS NOT NULL
              AND n2.{comparison_property} IS NOT NULL
              AND (
                n1.{comparison_property} = n2.{comparison_property}
                OR toLower(toString(n1.{comparison_property})) = toLower(toString(n2.{comparison_property}))
                OR (
                  size(toString(n1.{comparison_property})) > 3
                  AND size(toString(n2.{comparison_property})) > 3
                  AND toLower(toString(n1.{comparison_property})) CONTAINS toLower(toString(n2.{comparison_property}))
                )
                OR (
                  size(toString(n2.{comparison_property})) > 3
                  AND size(toString(n1.{comparison_property})) > 3
                  AND toLower(toString(n2.{comparison_property})) CONTAINS toLower(toString(n1.{comparison_property}))
                )
              )
            RETURN
              elementId(n1) as node1_id,
              labels(n1) as node1_labels,
              n1.{comparison_property} as node1_value,
              properties(n1) as node1_props,
              elementId(n2) as node2_id,
              labels(n2) as node2_labels,
              n2.{comparison_property} as node2_value,
              properties(n2) as node2_props,
              CASE
                WHEN n1.{comparison_property} = n2.{comparison_property} THEN 1.0
                WHEN toLower(toString(n1.{comparison_property})) = toLower(toString(n2.{comparison_property})) THEN 0.95
                WHEN toLower(toString(n1.{comparison_property})) CONTAINS toLower(toString(n2.{comparison_property})) THEN 0.8
                WHEN toLower(toString(n2.{comparison_property})) CONTAINS toLower(toString(n1.{comparison_property})) THEN 0.8
                ELSE 0.0
              END as similarity_score
            ORDER BY similarity_score DESC
            LIMIT $limit
            """

            params = {"threshold": similarity_threshold, "limit": limit}
            similar_nodes = await execute_cypher(similar_query, params, database)

            # Filter by threshold and clean properties
            filtered_results = []
            for node in similar_nodes:
                if node["similarity_score"] >= similarity_threshold:
                    cleaned_node = {**node}
                    if "node1_props" in cleaned_node:
                        cleaned_node["node1_props"] = clean_properties(
                            cleaned_node["node1_props"]
                        )
                    if "node2_props" in cleaned_node:
                        cleaned_node["node2_props"] = clean_properties(
                            cleaned_node["node2_props"]
                        )
                    filtered_results.append(cleaned_node)

            return {
                "success": True,
                "entity_type": entity_type,
                "comparison_property": comparison_property,
                "similarity_threshold": similarity_threshold,
                "similar_pairs": filtered_results,
                "pairs_found": len(filtered_results),
                "total_candidates": len(similar_nodes),
                "message": f"Found {len(filtered_results)} similar node pairs",
            }

        except Exception as e:
            logger.error(f"Error finding similar nodes: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def find_isolated_nodes(  # pyright: ignore
        entity_type: Optional[str] = None,
        max_path_length: int = 3,
        include_completely_isolated: bool = True,
        limit: int = 100,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Find isolated nodes that have no connections or very limited connectivity.

        Args:
            entity_type: Optional entity type to filter by (e.g., "Service", "Class")
            max_path_length: Maximum path length to consider a node isolated (default: 3)
            include_completely_isolated: Include nodes with zero connections (default: True)
            limit: Maximum number of isolated nodes to return
            database: Optional database name

        Returns:
            List of isolated nodes with their connectivity information
        """
        try:
            logger.info(
                f"Finding isolated nodes via MCP (max_path_length: {max_path_length})"
            )

            isolated_nodes = []

            if include_completely_isolated:
                # Find completely isolated nodes (no relationships at all)
                if entity_type:
                    isolated_query = f"""
                    MATCH (n:{entity_type})
                    WHERE NOT (n)--()
                    RETURN
                      elementId(n) as node_id,
                      labels(n) as node_labels,
                      properties(n) as node_properties,
                      0 as connection_count,
                      0 as max_reachable_distance,
                      'completely_isolated' as isolation_type
                    LIMIT $limit
                    """
                else:
                    isolated_query = """
                    MATCH (n)
                    WHERE NOT (n)--()
                    RETURN
                      elementId(n) as node_id,
                      labels(n) as node_labels,
                      properties(n) as node_properties,
                      0 as connection_count,
                      0 as max_reachable_distance,
                      'completely_isolated' as isolation_type
                    LIMIT $limit
                    """

                completely_isolated = await execute_cypher(
                    isolated_query, {"limit": limit}, database
                )
                isolated_nodes.extend(completely_isolated)

            # Find nodes with limited connectivity (can't reach far in the graph)
            remaining_limit = limit - len(isolated_nodes)
            if remaining_limit > 0 and max_path_length > 0:
                if entity_type:
                    limited_connectivity_query = f"""
                    MATCH (n:{entity_type})
                    WHERE (n)--() // Has at least one connection
                    WITH n
                    CALL {{
                      WITH n
                      MATCH path = (n)-[*1..{max_path_length}]->(target)
                      RETURN count(DISTINCT target) as reachable_nodes,
                             max(length(path)) as max_distance
                    }}
                    WITH n, reachable_nodes, max_distance
                    WHERE reachable_nodes <= {max_path_length * 2} // Arbitrary threshold for "limited"
                    RETURN
                      elementId(n) as node_id,
                      labels(n) as node_labels,
                      properties(n) as node_properties,
                      size((n)--()) as connection_count,
                      max_distance as max_reachable_distance,
                      'limited_connectivity' as isolation_type
                    ORDER BY connection_count ASC, reachable_nodes ASC
                    LIMIT $remaining_limit
                    """
                else:
                    limited_connectivity_query = f"""
                    MATCH (n)
                    WHERE (n)--() // Has at least one connection
                    WITH n
                    CALL {{
                      WITH n
                      MATCH path = (n)-[*1..{max_path_length}]->(target)
                      RETURN count(DISTINCT target) as reachable_nodes,
                             max(length(path)) as max_distance
                    }}
                    WITH n, reachable_nodes, max_distance
                    WHERE reachable_nodes <= {max_path_length * 2} // Arbitrary threshold for "limited"
                    RETURN
                      elementId(n) as node_id,
                      labels(n) as node_labels,
                      properties(n) as node_properties,
                      size((n)--()) as connection_count,
                      max_distance as max_reachable_distance,
                      'limited_connectivity' as isolation_type
                    ORDER BY connection_count ASC, reachable_nodes ASC
                    LIMIT $remaining_limit
                    """

                limited_connectivity = await execute_cypher(
                    limited_connectivity_query,
                    {"remaining_limit": remaining_limit},
                    database,
                )
                isolated_nodes.extend(limited_connectivity)

            # Categorize results
            completely_isolated_count = len(
                [
                    n
                    for n in isolated_nodes
                    if n["isolation_type"] == "completely_isolated"
                ]
            )
            limited_connectivity_count = len(
                [
                    n
                    for n in isolated_nodes
                    if n["isolation_type"] == "limited_connectivity"
                ]
            )

            # Clean embedding vectors from node properties
            cleaned_isolated_nodes = []
            for node in isolated_nodes:
                cleaned_node = {**node}
                if "node_properties" in cleaned_node:
                    cleaned_node["node_properties"] = clean_properties(
                        cleaned_node["node_properties"]
                    )
                cleaned_isolated_nodes.append(cleaned_node)

            return {
                "success": True,
                "entity_type": entity_type,
                "max_path_length": max_path_length,
                "include_completely_isolated": include_completely_isolated,
                "isolated_nodes": cleaned_isolated_nodes,
                "total_isolated": len(isolated_nodes),
                "completely_isolated_count": completely_isolated_count,
                "limited_connectivity_count": limited_connectivity_count,
                "summary": {
                    "completely_isolated": completely_isolated_count,
                    "limited_connectivity": limited_connectivity_count,
                    "total": len(isolated_nodes),
                },
                "message": f"Found {len(isolated_nodes)} isolated nodes ({completely_isolated_count} completely isolated, {limited_connectivity_count} with limited connectivity)",
            }

        except Exception as e:
            logger.error(f"Error finding isolated nodes: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def merge_duplicate_entities(  # pyright: ignore
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
            RETURN elementId(target) as other_node_id, type(r) as rel_type, properties(r) as rel_props, 'outgoing' as direction
            UNION
            MATCH (source)-[r]->(merge)
            WHERE elementId(merge) = $merge_id
            RETURN elementId(source) as other_node_id, type(r) as rel_type, properties(r) as rel_props, 'incoming' as direction
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
                            rel["other_node_id"],
                            rel["rel_type"],
                            rel["rel_props"],
                            database,
                        )
                    else:  # incoming
                        await create_relationship(
                            rel["other_node_id"],
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
    async def analyze_graph_structure(database: Optional[str] = None) -> Dict[str, Any]:  # pyright: ignore
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
