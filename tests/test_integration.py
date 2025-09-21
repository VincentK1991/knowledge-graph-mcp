"""
Integration tests for Knowledge Graph MCP server.
Tests actual database operations against a real Neo4j instance.
"""

import asyncio
import os
from datetime import datetime
from typing import List

import pytest
from knowledge_graph_mcp.tools.db_operations import (
    Neo4jConnector,
    create_node,
    create_relationship,
    execute_cypher,
    health_check,
    query_nodes,
)


@pytest.mark.integration
@pytest.mark.neo4j
class TestNeo4jIntegration:
    """Integration tests that require a running Neo4j instance."""

    @classmethod
    def setup_class(cls):
        """Set up environment for integration tests."""
        # Set test environment variables
        os.environ["NEO4J_URI"] = "bolt://localhost:7688"
        os.environ["NEO4J_USER"] = "neo4j"
        os.environ["NEO4J_PASSWORD"] = "password"

        cls.test_nodes: List[str] = []
        cls.test_relationships: List[str] = []

    @classmethod
    async def cleanup_test_data(cls):
        """Clean up all test data."""
        try:
            # Clean up relationships first
            for rel_id in cls.test_relationships:
                await execute_cypher(
                    "MATCH ()-[r]->() WHERE elementId(r) = $rel_id DELETE r",
                    {"rel_id": rel_id},
                )

            # Clean up nodes
            for node_id in cls.test_nodes:
                await execute_cypher(
                    "MATCH (n) WHERE elementId(n) = $node_id DETACH DELETE n",
                    {"node_id": node_id},
                )

            # Final cleanup of any remaining test data
            await execute_cypher("""
                MATCH (n)
                WHERE any(label IN labels(n) WHERE label CONTAINS 'Test')
                   OR any(prop IN keys(n) WHERE n[prop] CONTAINS 'test' OR n[prop] CONTAINS 'integration')
                DETACH DELETE n
            """)

        except Exception as e:
            print(f"Cleanup warning: {e}")
        finally:
            cls.test_nodes.clear()
            cls.test_relationships.clear()

    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Setup
        yield
        # Cleanup after each test
        await self.cleanup_test_data()

    @pytest.mark.asyncio
    async def test_connectivity(self):
        """Test actual database connectivity."""
        is_connected = await Neo4jConnector.verify_connectivity()
        assert is_connected is True, "Failed to connect to Neo4j database"

    @pytest.mark.asyncio
    async def test_health_check_real(self):
        """Test health check against real database."""
        health = await health_check()

        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert "node_count" in health
        assert "relationship_count" in health

    @pytest.mark.asyncio
    async def test_node_lifecycle(self):
        """Test complete node lifecycle: create, query, update, delete."""
        # Create node
        node = await create_node(
            "IntegrationTestService",
            {
                "name": "integration-test-service",
                "version": "1.0.0",
                "status": "active",
                "created_at": datetime.now().isoformat(),
            },
        )

        assert "node_id" in node
        assert node["entity_type"] == "IntegrationTestService"
        assert node["properties"]["name"] == "integration-test-service"

        node_id = node["node_id"]
        self.test_nodes.append(node_id)

        # Query the created node
        found_nodes = await query_nodes(
            "IntegrationTestService", {"name": "integration-test-service"}
        )

        assert len(found_nodes) == 1
        assert found_nodes[0]["node_id"] == node_id
        assert found_nodes[0]["properties"]["name"] == "integration-test-service"

        # Update node properties
        update_result = await execute_cypher(
            "MATCH (n) WHERE elementId(n) = $node_id SET n.status = 'updated' RETURN n",
            {"node_id": node_id},
        )

        assert len(update_result) == 1

        # Verify update
        updated_nodes = await query_nodes(
            "IntegrationTestService", {"name": "integration-test-service"}
        )
        assert updated_nodes[0]["properties"]["status"] == "updated"

    @pytest.mark.asyncio
    async def test_relationship_lifecycle(self):
        """Test complete relationship lifecycle."""
        # Create two nodes
        service_node = await create_node(
            "IntegrationTestService",
            {"name": "service-for-relationship-test", "type": "web_service"},
        )

        module_node = await create_node(
            "IntegrationTestModule",
            {"name": "module-for-relationship-test", "path": "/integration/test.py"},
        )

        service_id = service_node["node_id"]
        module_id = module_node["node_id"]
        self.test_nodes.extend([service_id, module_id])

        # Create relationship
        relationship = await create_relationship(
            service_id,
            module_id,
            "CONTAINS",
            {
                "created_at": datetime.now().isoformat(),
                "relationship_strength": 0.9,
                "test_marker": "integration_test",
            },
        )

        assert "relationship_id" in relationship
        assert relationship["type"] == "CONTAINS"
        assert relationship["properties"]["test_marker"] == "integration_test"

        rel_id = relationship["relationship_id"]
        self.test_relationships.append(rel_id)

        # Query relationship
        rel_query = """
        MATCH (s:IntegrationTestService)-[r:CONTAINS]->(m:IntegrationTestModule)
        WHERE elementId(r) = $rel_id
        RETURN elementId(s) as service_id, elementId(m) as module_id,
               elementId(r) as rel_id, properties(r) as rel_props
        """

        rel_result = await execute_cypher(rel_query, {"rel_id": rel_id})

        assert len(rel_result) == 1
        assert rel_result[0]["service_id"] == service_id
        assert rel_result[0]["module_id"] == module_id
        assert rel_result[0]["rel_props"]["test_marker"] == "integration_test"

    @pytest.mark.asyncio
    async def test_complex_graph_operations(self):
        """Test complex graph operations with multiple entities and relationships."""
        # Create a small graph: Service -> Module -> Class -> Method
        service = await create_node(
            "IntegrationTestService",
            {
                "name": "complex-test-service",
                "description": "Service for complex graph testing",
            },
        )

        module = await create_node(
            "IntegrationTestModule",
            {
                "name": "auth_module",
                "path": "/src/auth/module.py",
                "language": "python",
            },
        )

        class_node = await create_node(
            "IntegrationTestClass",
            {
                "name": "AuthController",
                "full_name": "auth.AuthController",
                "visibility": "public",
            },
        )

        method = await create_node(
            "IntegrationTestMethod",
            {
                "name": "authenticate",
                "full_name": "auth.AuthController.authenticate",
                "visibility": "public",
                "return_type": "bool",
            },
        )

        # Track nodes for cleanup
        node_ids = [
            service["node_id"],
            module["node_id"],
            class_node["node_id"],
            method["node_id"],
        ]
        self.test_nodes.extend(node_ids)

        # Create relationships
        service_module_rel = await create_relationship(
            service["node_id"], module["node_id"], "CONTAINS"
        )

        module_class_rel = await create_relationship(
            module["node_id"], class_node["node_id"], "CONTAINS"
        )

        class_method_rel = await create_relationship(
            class_node["node_id"], method["node_id"], "CONTAINS"
        )

        # Track relationships for cleanup
        rel_ids = [
            service_module_rel["relationship_id"],
            module_class_rel["relationship_id"],
            class_method_rel["relationship_id"],
        ]
        self.test_relationships.extend(rel_ids)

        # Test complex traversal query
        traversal_query = """
        MATCH path = (s:IntegrationTestService)-[:CONTAINS*]->(m:IntegrationTestMethod)
        WHERE s.name = 'complex-test-service'
        RETURN length(path) as path_length,
               [node in nodes(path) | elementId(node)] as node_ids,
               [rel in relationships(path) | type(rel)] as rel_types
        """

        traversal_result = await execute_cypher(traversal_query)

        assert len(traversal_result) == 1
        assert traversal_result[0]["path_length"] == 3  # 3 relationships in path
        assert len(traversal_result[0]["node_ids"]) == 4  # 4 nodes in path
        assert traversal_result[0]["rel_types"] == ["CONTAINS", "CONTAINS", "CONTAINS"]

    @pytest.mark.asyncio
    async def test_batch_operations_performance(self):
        """Test batch operations for performance."""
        import time

        # Create multiple nodes in batch
        start_time = time.time()
        batch_nodes = []

        for i in range(10):
            node = await create_node(
                "IntegrationTestBatch",
                {
                    "batch_id": i,
                    "name": f"batch_node_{i}",
                    "created_at": datetime.now().isoformat(),
                },
            )
            batch_nodes.append(node)
            self.test_nodes.append(node["node_id"])

        node_creation_time = time.time() - start_time

        # Create relationships between consecutive nodes
        start_time = time.time()
        batch_rels = []

        for i in range(len(batch_nodes) - 1):
            rel = await create_relationship(
                batch_nodes[i]["node_id"],
                batch_nodes[i + 1]["node_id"],
                "NEXT_IN_SEQUENCE",
                {"sequence_order": i},
            )
            batch_rels.append(rel)
            self.test_relationships.append(rel["relationship_id"])

        rel_creation_time = time.time() - start_time

        # Verify all nodes and relationships were created
        assert len(batch_nodes) == 10
        assert len(batch_rels) == 9

        # Performance assertions (reasonable thresholds)
        assert node_creation_time < 5.0, (
            f"Node creation took too long: {node_creation_time}s"
        )
        assert rel_creation_time < 5.0, (
            f"Relationship creation took too long: {rel_creation_time}s"
        )

        # Test batch query
        batch_query_result = await query_nodes("IntegrationTestBatch", limit=20)
        assert len(batch_query_result) == 10

    @pytest.mark.asyncio
    async def test_transaction_rollback_simulation(self):
        """Test transaction behavior with errors."""
        # This test simulates what happens when a transaction fails

        # Create a node successfully
        node = await create_node(
            "IntegrationTestTransaction", {"name": "transaction-test-node"}
        )

        node_id = node["node_id"]
        self.test_nodes.append(node_id)

        # Try to create an invalid relationship (should fail)
        with pytest.raises(Exception):
            await create_relationship(node_id, "invalid-node-id", "TEST_REL")

        # Verify the original node still exists
        found_nodes = await query_nodes(
            "IntegrationTestTransaction", {"name": "transaction-test-node"}
        )
        assert len(found_nodes) == 1
        assert found_nodes[0]["node_id"] == node_id

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent database operations."""
        # Create multiple nodes concurrently
        tasks = []
        for i in range(5):
            task = create_node(
                "IntegrationTestConcurrent",
                {"name": f"concurrent_node_{i}", "thread_id": i},
            )
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all succeeded
        successful_nodes = [
            r for r in results if isinstance(r, dict) and "node_id" in r
        ]
        assert len(successful_nodes) == 5

        # Track for cleanup
        for node in successful_nodes:
            self.test_nodes.append(node["node_id"])

        # Verify all nodes were created with unique IDs
        node_ids = [node["node_id"] for node in successful_nodes]
        assert len(set(node_ids)) == 5  # All IDs should be unique

    @pytest.mark.asyncio
    async def test_large_property_handling(self):
        """Test handling of large property values."""
        large_text = "A" * 10000  # 10KB string
        large_list = list(range(1000))  # Large list

        node = await create_node(
            "IntegrationTestLarge",
            {
                "name": "large-property-test",
                "large_text": large_text,
                "large_list": large_list,
                "normal_prop": "normal_value",
            },
        )

        assert "node_id" in node
        self.test_nodes.append(node["node_id"])

        # Verify large properties were stored correctly
        found_nodes = await query_nodes(
            "IntegrationTestLarge", {"name": "large-property-test"}
        )

        assert len(found_nodes) == 1
        assert found_nodes[0]["properties"]["large_text"] == large_text
        assert found_nodes[0]["properties"]["large_list"] == large_list
        assert found_nodes[0]["properties"]["normal_prop"] == "normal_value"

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self):
        """Test Unicode and special character handling."""
        unicode_properties = {
            "name": "unicode-test-服务",
            "description": "Service with émojis 🚀🎉 and spëcial chars",
            "chinese": "测试服务",
            "arabic": "خدمة الاختبار",
            "special_chars": "!@#$%^&*()_+-=[]{}|;:,.<>?",
        }

        node = await create_node("IntegrationTestUnicode", unicode_properties)

        assert "node_id" in node
        self.test_nodes.append(node["node_id"])

        # Verify Unicode properties were stored correctly
        found_nodes = await query_nodes(
            "IntegrationTestUnicode", {"chinese": "测试服务"}
        )

        assert len(found_nodes) == 1
        assert found_nodes[0]["properties"]["chinese"] == "测试服务"
        assert (
            found_nodes[0]["properties"]["description"]
            == "Service with émojis 🚀🎉 and spëcial chars"
        )

    @pytest.mark.asyncio
    async def test_connection_resilience(self):
        """Test connection resilience and recovery."""
        # Test multiple operations to ensure connection stability
        operations = []

        for i in range(20):
            if i % 2 == 0:
                # Create node operation
                op = create_node(
                    "IntegrationTestResilience",
                    {"name": f"resilience_node_{i}", "operation_index": i},
                )
            else:
                # Query operation
                op = query_nodes("IntegrationTestResilience", limit=5)

            operations.append(op)

        # Execute all operations
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Count successful operations
        successful_ops = [r for r in results if not isinstance(r, Exception)]
        failed_ops = [r for r in results if isinstance(r, Exception)]

        # Should have high success rate
        success_rate = len(successful_ops) / len(results)
        assert success_rate >= 0.9, f"Success rate too low: {success_rate}"

        # Track created nodes for cleanup
        for result in successful_ops:
            if isinstance(result, dict) and "node_id" in result:
                self.test_nodes.append(result["node_id"])

    @pytest.mark.asyncio
    async def test_query_performance(self):
        """Test query performance with larger datasets."""
        # Create test dataset
        for i in range(50):
            node = await create_node(
                "IntegrationTestPerformance",
                {
                    "name": f"perf_node_{i}",
                    "category": "even" if i % 2 == 0 else "odd",
                    "value": i * 10,
                },
            )
            self.test_nodes.append(node["node_id"])

        # Test various query patterns
        import time

        # Test 1: Query all nodes of type
        start_time = time.time()
        all_perf_nodes = await query_nodes("IntegrationTestPerformance", limit=100)
        query_all_time = time.time() - start_time

        assert len(all_perf_nodes) == 50
        assert query_all_time < 1.0, f"Query all took too long: {query_all_time}s"

        # Test 2: Query with filter
        start_time = time.time()
        even_nodes = await query_nodes(
            "IntegrationTestPerformance", {"category": "even"}, limit=50
        )
        query_filter_time = time.time() - start_time

        assert len(even_nodes) == 25
        assert query_filter_time < 1.0, (
            f"Query with filter took too long: {query_filter_time}s"
        )

        # Test 3: Complex Cypher query
        start_time = time.time()
        complex_result = await execute_cypher("""
            MATCH (n:IntegrationTestPerformance)
            WHERE n.value > 200
            RETURN n.name, n.value, n.category
            ORDER BY n.value DESC
            LIMIT 10
        """)
        complex_query_time = time.time() - start_time

        assert len(complex_result) == 10
        assert complex_query_time < 1.0, (
            f"Complex query took too long: {complex_query_time}s"
        )

    @pytest.mark.asyncio
    async def test_data_type_preservation(self):
        """Test that various data types are preserved correctly."""
        test_properties = {
            "string_prop": "test_string",
            "int_prop": 42,
            "float_prop": 3.14159,
            "bool_true": True,
            "bool_false": False,
            "list_prop": [1, 2, 3, "mixed", True],
            "dict_prop": {"nested": "value", "number": 123},
            "null_prop": None,
            "empty_string": "",
            "zero_value": 0,
            "negative_number": -42,
        }

        node = await create_node("IntegrationTestDataTypes", test_properties)
        self.test_nodes.append(node["node_id"])

        # Query back and verify data types
        found_nodes = await query_nodes(
            "IntegrationTestDataTypes", {"string_prop": "test_string"}
        )

        assert len(found_nodes) == 1
        props = found_nodes[0]["properties"]

        assert props["string_prop"] == "test_string"
        assert props["int_prop"] == 42
        assert props["float_prop"] == 3.14159
        assert props["bool_true"] is True
        assert props["bool_false"] is False
        assert props["list_prop"] == [1, 2, 3, "mixed", True]
        assert props["dict_prop"] == {"nested": "value", "number": 123}
        assert props["empty_string"] == ""
        assert props["zero_value"] == 0
        assert props["negative_number"] == -42
        # Note: null_prop might be omitted by Neo4j

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery and connection stability."""
        # Create a valid node first
        valid_node = await create_node(
            "IntegrationTestError", {"name": "valid-node-before-error"}
        )
        self.test_nodes.append(valid_node["node_id"])

        # Try invalid operations that should fail
        try:
            await execute_cypher("INVALID CYPHER SYNTAX HERE")
            assert False, "Should have raised an exception"
        except Exception:
            pass  # Expected

        try:
            await create_relationship("invalid-id-1", "invalid-id-2", "TEST_REL")
            assert False, "Should have raised an exception"
        except Exception:
            pass  # Expected

        # Verify connection is still working after errors
        health = await health_check()
        assert health["status"] == "healthy"

        # Create another valid node to confirm recovery
        recovery_node = await create_node(
            "IntegrationTestError", {"name": "valid-node-after-error"}
        )
        self.test_nodes.append(recovery_node["node_id"])

        # Verify both nodes exist
        error_test_nodes = await query_nodes("IntegrationTestError")
        assert len(error_test_nodes) == 2
