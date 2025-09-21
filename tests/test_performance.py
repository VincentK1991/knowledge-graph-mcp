"""
Performance tests for Knowledge Graph MCP server.
Tests performance characteristics and benchmarks.
"""

import asyncio
import time
from typing import List

import pytest
from knowledge_graph_mcp.tools.db_operations import (
    create_node,
    create_relationship,
    execute_cypher,
    query_nodes,
)


@pytest.mark.performance
@pytest.mark.neo4j
class TestPerformance:
    """Performance test cases."""

    @classmethod
    def setup_class(cls):
        """Setup for performance tests."""
        cls.test_nodes: List[str] = []
        cls.test_relationships: List[str] = []

    @classmethod
    async def cleanup_performance_data(cls):
        """Clean up performance test data."""
        try:
            await execute_cypher("""
                MATCH (n)
                WHERE any(label IN labels(n) WHERE label CONTAINS 'Performance')
                DETACH DELETE n
            """)
        except Exception as e:
            print(f"Performance cleanup warning: {e}")

    @pytest.fixture(autouse=True)
    async def cleanup_after_test(self):
        """Cleanup after each performance test."""
        yield
        await self.cleanup_performance_data()

    @pytest.mark.asyncio
    async def test_node_creation_performance(self):
        """Test node creation performance."""
        node_count = 100
        start_time = time.time()

        # Create nodes sequentially
        for i in range(node_count):
            node = await create_node(
                "PerformanceTestNode",
                {"name": f"perf_node_{i}", "index": i, "created_at": time.time()},
            )
            self.test_nodes.append(node["node_id"])

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 30.0, (
            f"Creating {node_count} nodes took too long: {total_time:.2f}s"
        )

        nodes_per_second = node_count / total_time
        assert nodes_per_second > 3.0, (
            f"Node creation rate too slow: {nodes_per_second:.2f} nodes/s"
        )

        print(
            f"Created {node_count} nodes in {total_time:.2f}s ({nodes_per_second:.2f} nodes/s)"
        )

    @pytest.mark.asyncio
    async def test_concurrent_node_creation_performance(self):
        """Test concurrent node creation performance."""
        node_count = 50
        start_time = time.time()

        # Create nodes concurrently
        tasks = []
        for i in range(node_count):
            task = create_node(
                "PerformanceConcurrentNode",
                {"name": f"concurrent_node_{i}", "index": i, "created_at": time.time()},
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        total_time = end_time - start_time

        # Count successful creations
        successful_nodes = [
            r for r in results if isinstance(r, dict) and "node_id" in r
        ]
        self.test_nodes.extend([node["node_id"] for node in successful_nodes])

        # Performance assertions
        assert len(successful_nodes) == node_count, (
            f"Only {len(successful_nodes)} of {node_count} nodes created"
        )
        assert total_time < 15.0, (
            f"Concurrent creation took too long: {total_time:.2f}s"
        )

        nodes_per_second = node_count / total_time
        assert nodes_per_second > 5.0, (
            f"Concurrent creation rate too slow: {nodes_per_second:.2f} nodes/s"
        )

        print(
            f"Created {node_count} nodes concurrently in {total_time:.2f}s ({nodes_per_second:.2f} nodes/s)"
        )

    @pytest.mark.asyncio
    async def test_relationship_creation_performance(self):
        """Test relationship creation performance."""
        # First create nodes for relationships
        nodes = []
        for i in range(20):
            node = await create_node(
                "PerformanceRelNode", {"name": f"rel_node_{i}", "index": i}
            )
            nodes.append(node)
            self.test_nodes.append(node["node_id"])

        # Create relationships between consecutive nodes
        relationship_count = len(nodes) - 1
        start_time = time.time()

        for i in range(relationship_count):
            rel = await create_relationship(
                nodes[i]["node_id"],
                nodes[i + 1]["node_id"],
                "PERFORMANCE_NEXT",
                {"sequence": i, "created_at": time.time()},
            )
            self.test_relationships.append(rel["relationship_id"])

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 10.0, (
            f"Creating {relationship_count} relationships took too long: {total_time:.2f}s"
        )

        rels_per_second = relationship_count / total_time
        assert rels_per_second > 2.0, (
            f"Relationship creation rate too slow: {rels_per_second:.2f} rels/s"
        )

        print(
            f"Created {relationship_count} relationships in {total_time:.2f}s ({rels_per_second:.2f} rels/s)"
        )

    @pytest.mark.asyncio
    async def test_query_performance_large_dataset(self):
        """Test query performance with larger dataset."""
        # Create a larger dataset
        dataset_size = 200

        # Create nodes with different categories for filtering
        for i in range(dataset_size):
            await create_node(
                "PerformanceQueryNode",
                {
                    "name": f"query_node_{i}",
                    "category": f"category_{i % 10}",  # 10 different categories
                    "value": i,
                    "is_even": i % 2 == 0,
                },
            )

        # Test different query patterns
        start_time = time.time()

        # Query 1: Get all nodes
        all_nodes = await query_nodes("PerformanceQueryNode", limit=dataset_size)
        query1_time = time.time() - start_time

        assert len(all_nodes) == dataset_size
        assert query1_time < 2.0, f"Query all took too long: {query1_time:.2f}s"

        # Query 2: Filtered query
        start_time = time.time()
        filtered_nodes = await query_nodes(
            "PerformanceQueryNode", {"category": "category_5"}, limit=50
        )
        query2_time = time.time() - start_time

        assert len(filtered_nodes) == 20  # Should be 200/10 = 20 nodes in category_5
        assert query2_time < 1.0, f"Filtered query took too long: {query2_time:.2f}s"

        # Query 3: Complex Cypher query
        start_time = time.time()
        complex_result = await execute_cypher("""
            MATCH (n:PerformanceQueryNode)
            WHERE n.value > 100 AND n.is_even = true
            RETURN n.name, n.value, n.category
            ORDER BY n.value DESC
            LIMIT 20
        """)
        query3_time = time.time() - start_time

        assert len(complex_result) == 20
        assert query3_time < 1.0, f"Complex query took too long: {query3_time:.2f}s"

        print(
            f"Query performance: all={query1_time:.3f}s, filtered={query2_time:.3f}s, complex={query3_time:.3f}s"
        )

    @pytest.mark.asyncio
    async def test_connection_pool_performance(self):
        """Test connection pool performance under load."""
        # Simulate multiple concurrent database operations
        operation_count = 30

        async def random_operation(index: int):
            """Perform a random database operation."""
            if index % 3 == 0:
                # Create node
                return await create_node(
                    "PerformancePoolTest",
                    {"name": f"pool_test_{index}", "operation_type": "create"},
                )
            elif index % 3 == 1:
                # Query nodes
                return await query_nodes("PerformancePoolTest", limit=10)
            else:
                # Execute simple query
                return await execute_cypher("RETURN timestamp() as current_time")

        start_time = time.time()

        # Execute operations concurrently
        tasks = [random_operation(i) for i in range(operation_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # Count successful operations
        successful_ops = [r for r in results if not isinstance(r, Exception)]

        # Performance assertions
        success_rate = len(successful_ops) / operation_count
        assert success_rate >= 0.95, (
            f"Success rate too low under load: {success_rate:.2f}"
        )
        assert total_time < 10.0, (
            f"Concurrent operations took too long: {total_time:.2f}s"
        )

        ops_per_second = operation_count / total_time
        assert ops_per_second > 5.0, (
            f"Operation rate too slow: {ops_per_second:.2f} ops/s"
        )

        print(
            f"Executed {operation_count} concurrent operations in {total_time:.2f}s ({ops_per_second:.2f} ops/s)"
        )

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """Test memory usage stability during operations."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform many operations
        for batch in range(5):
            batch_nodes = []

            # Create batch of nodes
            for i in range(20):
                node = await create_node(
                    "PerformanceMemoryTest",
                    {
                        "batch": batch,
                        "index": i,
                        "data": "x" * 1000,  # 1KB of data per node
                    },
                )
                batch_nodes.append(node)
                self.test_nodes.append(node["node_id"])

            # Create some relationships
            for i in range(len(batch_nodes) - 1):
                rel = await create_relationship(
                    batch_nodes[i]["node_id"],
                    batch_nodes[i + 1]["node_id"],
                    "MEMORY_TEST_REL",
                )
                self.test_relationships.append(rel["relationship_id"])

            # Query the data
            await query_nodes("PerformanceMemoryTest", {"batch": batch})

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100, (
            f"Memory usage increased too much: {memory_increase:.2f}MB"
        )

        print(
            f"Memory usage: {initial_memory:.2f}MB -> {final_memory:.2f}MB (increase: {memory_increase:.2f}MB)"
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_large_graph_traversal_performance(self):
        """Test performance of traversal queries on larger graphs."""
        # Create a hierarchical structure: 1 Service -> 5 Modules -> 20 Classes -> 100 Methods

        # Create service
        service = await create_node(
            "PerformanceService",
            {"name": "large-graph-service", "type": "enterprise_service"},
        )
        self.test_nodes.append(service["node_id"])

        # Create modules
        modules = []
        for i in range(5):
            module = await create_node(
                "PerformanceModule",
                {"name": f"module_{i}", "path": f"/src/module_{i}.py"},
            )
            modules.append(module)
            self.test_nodes.append(module["node_id"])

            # Connect service to module
            rel = await create_relationship(
                service["node_id"], module["node_id"], "CONTAINS"
            )
            self.test_relationships.append(rel["relationship_id"])

        # Create classes for each module
        classes = []
        for module in modules:
            for i in range(4):  # 4 classes per module = 20 total
                class_node = await create_node(
                    "PerformanceClass",
                    {
                        "name": f"Class_{module['properties']['name']}_{i}",
                        "visibility": "public",
                    },
                )
                classes.append(class_node)
                self.test_nodes.append(class_node["node_id"])

                # Connect module to class
                rel = await create_relationship(
                    module["node_id"], class_node["node_id"], "CONTAINS"
                )
                self.test_relationships.append(rel["relationship_id"])

        # Create methods for each class
        for class_node in classes:
            for i in range(5):  # 5 methods per class = 100 total
                method = await create_node(
                    "PerformanceMethod",
                    {
                        "name": f"method_{i}",
                        "visibility": "public",
                        "return_type": "void",
                    },
                )
                self.test_nodes.append(method["node_id"])

                # Connect class to method
                rel = await create_relationship(
                    class_node["node_id"], method["node_id"], "CONTAINS"
                )
                self.test_relationships.append(rel["relationship_id"])

        print(
            f"Created large graph: 1 service, {len(modules)} modules, {len(classes)} classes, {len(self.test_nodes) - 1 - len(modules) - len(classes)} methods"
        )

        # Test traversal performance
        traversal_queries = [
            # Query 1: Find all methods in the service
            """
            MATCH (s:PerformanceService)-[:CONTAINS*3]->(m:PerformanceMethod)
            RETURN count(m) as method_count
            """,
            # Query 2: Find all classes in a specific module
            """
            MATCH (mod:PerformanceModule)-[:CONTAINS]->(c:PerformanceClass)
            WHERE mod.name = 'module_0'
            RETURN count(c) as class_count
            """,
            # Query 3: Complex path query
            """
            MATCH path = (s:PerformanceService)-[:CONTAINS*]->(m:PerformanceMethod)
            RETURN length(path) as path_length, count(path) as path_count
            LIMIT 10
            """,
        ]

        for i, query in enumerate(traversal_queries):
            start_time = time.time()
            result = await execute_cypher(query)
            query_time = time.time() - start_time

            assert query_time < 2.0, (
                f"Traversal query {i + 1} took too long: {query_time:.2f}s"
            )
            assert len(result) > 0, f"Traversal query {i + 1} returned no results"

            print(f"Traversal query {i + 1}: {query_time:.3f}s")

    @pytest.mark.asyncio
    async def test_bulk_query_performance(self):
        """Test bulk query operations performance."""
        # Create test dataset
        dataset_size = 500

        print(f"Creating {dataset_size} nodes for bulk query testing...")
        for i in range(dataset_size):
            node = await create_node(
                "PerformanceBulkQuery",
                {
                    "name": f"bulk_node_{i}",
                    "category": f"cat_{i % 20}",  # 20 categories
                    "value": i * 2,
                    "is_prime": i
                    in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47],
                },
            )
            self.test_nodes.append(node["node_id"])

        # Test various bulk query patterns
        bulk_queries = [
            ("Count all", "MATCH (n:PerformanceBulkQuery) RETURN count(n) as total"),
            (
                "Filter by category",
                "MATCH (n:PerformanceBulkQuery) WHERE n.category = 'cat_5' RETURN count(n) as count",
            ),
            (
                "Range query",
                "MATCH (n:PerformanceBulkQuery) WHERE n.value >= 100 AND n.value <= 200 RETURN count(n) as count",
            ),
            (
                "Boolean filter",
                "MATCH (n:PerformanceBulkQuery) WHERE n.is_prime = true RETURN count(n) as count",
            ),
            (
                "Complex aggregation",
                """
                MATCH (n:PerformanceBulkQuery)
                RETURN n.category, count(n) as node_count, avg(n.value) as avg_value
                ORDER BY node_count DESC
                LIMIT 5
            """,
            ),
        ]

        for query_name, query in bulk_queries:
            start_time = time.time()
            result = await execute_cypher(query)
            query_time = time.time() - start_time

            assert query_time < 1.0, f"{query_name} took too long: {query_time:.2f}s"
            assert len(result) > 0, f"{query_name} returned no results"

            print(f"{query_name}: {query_time:.3f}s")

    @pytest.mark.asyncio
    async def test_connection_reuse_performance(self):
        """Test connection reuse and pooling performance."""
        operation_count = 100

        # Test with connection reuse
        start_time = time.time()

        for i in range(operation_count):
            # Alternate between different operations
            if i % 4 == 0:
                await execute_cypher("RETURN timestamp() as time")
            elif i % 4 == 1:
                await query_nodes("PerformanceConnectionTest", limit=1)
            elif i % 4 == 2:
                node = await create_node(
                    "PerformanceConnectionTest", {"name": f"conn_test_{i}", "index": i}
                )
                self.test_nodes.append(node["node_id"])
            else:
                await execute_cypher(
                    "MATCH (n:PerformanceConnectionTest) RETURN count(n) as count LIMIT 1"
                )

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 15.0, (
            f"Connection reuse test took too long: {total_time:.2f}s"
        )

        ops_per_second = operation_count / total_time
        assert ops_per_second > 10.0, (
            f"Operation rate with connection reuse too slow: {ops_per_second:.2f} ops/s"
        )

        print(
            f"Connection reuse test: {operation_count} operations in {total_time:.2f}s ({ops_per_second:.2f} ops/s)"
        )

    @pytest.mark.asyncio
    async def test_cleanup_performance(self):
        """Test cleanup operation performance."""
        # Create test data to clean up
        cleanup_nodes = []
        for i in range(100):
            node = await create_node(
                "PerformanceCleanupTest",
                {"name": f"cleanup_node_{i}", "to_be_deleted": True},
            )
            cleanup_nodes.append(node["node_id"])

        # Test bulk cleanup performance
        start_time = time.time()

        cleanup_result = await execute_cypher("""
            MATCH (n:PerformanceCleanupTest)
            WHERE n.to_be_deleted = true
            DETACH DELETE n
            RETURN count(n) as deleted_count
        """)

        cleanup_time = time.time() - start_time

        # Performance assertions
        assert cleanup_time < 2.0, f"Cleanup took too long: {cleanup_time:.2f}s"
        assert cleanup_result[0]["deleted_count"] == 100, "Not all nodes were deleted"

        print(f"Cleaned up 100 nodes in {cleanup_time:.3f}s")
