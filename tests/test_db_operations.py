"""
Unit tests for high-level database operations.
Tests create_node, create_relationship, query_nodes, etc. with mocking.
"""

from unittest.mock import patch

import pytest
from knowledge_graph_mcp.tools.db_operations import (
    close_connections,
    create_node,
    create_relationship,
    execute_cypher,
    health_check,
    query_nodes,
)


class TestDatabaseOperations:
    """Test cases for high-level database operations."""

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query")
    async def test_create_node_success(self, mock_execute_write, sample_node_data):
        """Test successful node creation."""
        mock_execute_write.return_value = [sample_node_data]

        result = await create_node(
            "Service", {"name": "test-service", "version": "1.0.0", "status": "active"}
        )

        assert result["node_id"] == "4:test:123"
        assert result["labels"] == ["Service"]
        assert result["properties"]["name"] == "test-service"
        assert result["entity_type"] == "Service"

        # Verify the query was called correctly
        mock_execute_write.assert_called_once()
        call_args = mock_execute_write.call_args
        assert "CREATE (n:Service $properties)" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query")
    async def test_create_node_empty_result(self, mock_execute_write):
        """Test node creation with empty result."""
        mock_execute_write.return_value = []

        with pytest.raises(RuntimeError, match="Failed to create Service node"):
            await create_node("Service", {"name": "test"})

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query")
    async def test_create_node_label_sanitization(
        self, mock_execute_write, sample_node_data
    ):
        """Test entity type label sanitization."""
        mock_execute_write.return_value = [sample_node_data]

        await create_node("Test Service-Type", {"name": "test"})

        # Verify label was sanitized (spaces removed, hyphens converted to underscores)
        call_args = mock_execute_write.call_args
        assert "CREATE (n:TestService_Type $properties)" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query")
    async def test_create_relationship_with_properties(
        self, mock_execute_write, sample_relationship_data
    ):
        """Test relationship creation with properties."""
        mock_execute_write.return_value = [sample_relationship_data]

        result = await create_relationship(
            "4:test:123",
            "4:test:456",
            "CONTAINS",
            {"created_at": "2024-01-01T00:00:00Z"},
        )

        assert result["relationship_id"] == "5:test:456"
        assert result["type"] == "CONTAINS"
        assert result["properties"]["created_at"] == "2024-01-01T00:00:00Z"
        assert result["from_node_id"] == "4:test:123"
        assert result["to_node_id"] == "4:test:456"

        # Verify the query was called correctly
        mock_execute_write.assert_called_once()
        call_args = mock_execute_write.call_args
        assert "CREATE (a)-[r:CONTAINS $properties]->(b)" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query")
    async def test_create_relationship_without_properties(self, mock_execute_write):
        """Test relationship creation without properties."""
        sample_data = {
            "rel_id": "5:test:789",
            "rel_type": "DEPENDS_ON",
            "rel_properties": {},
        }
        mock_execute_write.return_value = [sample_data]

        result = await create_relationship("4:test:123", "4:test:456", "DEPENDS_ON")

        assert result["relationship_id"] == "5:test:789"
        assert result["type"] == "DEPENDS_ON"
        assert result["properties"] == {}

        # Verify the query doesn't include properties
        call_args = mock_execute_write.call_args
        assert "CREATE (a)-[r:DEPENDS_ON]->(b)" in call_args[0][0]
        assert "$properties" not in call_args[0][0]

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query")
    async def test_create_relationship_type_sanitization(self, mock_execute_write):
        """Test relationship type sanitization."""
        sample_data = {
            "rel_id": "5:test:789",
            "rel_type": "TEST_REL_TYPE",
            "rel_properties": {},
        }
        mock_execute_write.return_value = [sample_data]

        await create_relationship("4:test:123", "4:test:456", "test rel-type")

        # Verify relationship type was sanitized
        call_args = mock_execute_write.call_args
        assert "CREATE (a)-[r:TEST_REL_TYPE]->(b)" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query")
    async def test_query_nodes_all(self, mock_execute_read):
        """Test querying all nodes."""
        mock_data = [
            {
                "node_id": "4:test:1",
                "labels": ["Service"],
                "node_properties": {"name": "service1"},
            },
            {
                "node_id": "4:test:2",
                "labels": ["Module"],
                "node_properties": {"name": "module1"},
            },
        ]
        mock_execute_read.return_value = mock_data

        result = await query_nodes(limit=10)

        assert len(result) == 2
        assert result[0]["node_id"] == "4:test:1"
        assert result[0]["entity_type"] == "Service"  # Inferred from first label
        assert result[1]["entity_type"] == "Module"  # Inferred from first label

        # Verify query structure
        call_args = mock_execute_read.call_args
        assert "MATCH (n)" in call_args[0][0]
        assert call_args[0][1]["limit"] == 10

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query")
    async def test_query_nodes_by_type(self, mock_execute_read):
        """Test querying nodes by specific type."""
        mock_data = [
            {
                "node_id": "4:test:1",
                "labels": ["Service"],
                "node_properties": {"name": "service1"},
            }
        ]
        mock_execute_read.return_value = mock_data

        result = await query_nodes("Service", limit=5)

        assert len(result) == 1
        assert result[0]["entity_type"] == "Service"

        # Verify query structure
        call_args = mock_execute_read.call_args
        assert "MATCH (n:Service)" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query")
    async def test_query_nodes_with_filters(self, mock_execute_read):
        """Test querying nodes with property filters."""
        mock_data = [
            {
                "node_id": "4:test:1",
                "labels": ["Service"],
                "node_properties": {"name": "active-service"},
            }
        ]
        mock_execute_read.return_value = mock_data

        result = await query_nodes(
            "Service", {"status": "active", "version": "1.0"}, limit=5
        )

        assert len(result) == 1

        # Verify query structure and parameters
        call_args = mock_execute_read.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "MATCH (n:Service)" in query
        assert "WHERE" in query
        assert "n.status = $filter_status" in query
        assert "n.version = $filter_version" in query
        assert params["filter_status"] == "active"
        assert params["filter_version"] == "1.0"

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query")
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query")
    async def test_execute_cypher_read_query(
        self, mock_execute_write, mock_execute_read
    ):
        """Test execute_cypher with read query."""
        mock_execute_read.return_value = [{"count": 5}]

        result = await execute_cypher("MATCH (n) RETURN count(n)")

        assert result == [{"count": 5}]
        mock_execute_read.assert_called_once()
        mock_execute_write.assert_not_called()

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query")
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query")
    async def test_execute_cypher_write_query(
        self, mock_execute_write, mock_execute_read
    ):
        """Test execute_cypher with write query."""
        mock_execute_write.return_value = [{"created": "node"}]

        result = await execute_cypher("CREATE (n:Test) RETURN n")

        assert result == [{"created": "node"}]
        mock_execute_write.assert_called_once()
        mock_execute_read.assert_not_called()

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query")
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query")
    async def test_execute_cypher_query_type_detection(
        self, mock_execute_write, mock_execute_read
    ):
        """Test automatic query type detection."""
        write_queries = [
            "CREATE (n) RETURN n",
            "MERGE (n:Test) RETURN n",
            "SET n.prop = 'value'",
            "DELETE n",
            "REMOVE n.prop",
            "DETACH DELETE n",
        ]

        for query in write_queries:
            mock_execute_write.return_value = [{"result": "write"}]
            await execute_cypher(query)
            mock_execute_write.assert_called()
            mock_execute_write.reset_mock()

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.verify_connectivity")
    async def test_health_check_success(self, mock_verify):
        """Test successful health check."""
        mock_verify.return_value = True

        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query"
        ) as mock_read:
            mock_read.return_value = [{"node_count": 10, "relationship_count": 5}]

            result = await health_check()

            assert result["status"] == "healthy"
            assert result["connected"] is True
            assert result["node_count"] == 10
            assert result["relationship_count"] == 5

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.verify_connectivity")
    async def test_health_check_connection_failure(self, mock_verify):
        """Test health check with connection failure."""
        mock_verify.return_value = False

        result = await health_check()

        assert result["status"] == "unhealthy"
        assert result["connected"] is False
        assert "error" in result

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.verify_connectivity")
    async def test_health_check_stats_fallback(self, mock_verify):
        """Test health check with stats query fallback."""
        mock_verify.return_value = True

        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query"
        ) as mock_read:
            # First call fails (stats not available), second call succeeds (fallback)
            mock_read.side_effect = [
                Exception("Stats not available"),
                [{"node_count": 8}],
            ]

            result = await health_check()

            assert result["status"] == "healthy"
            assert result["node_count"] == 8
            assert result["relationship_count"] == "unknown"

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.close_driver")
    async def test_close_connections(self, mock_close_driver):
        """Test closing all connections."""
        await close_connections()

        mock_close_driver.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_node_property_validation(self):
        """Test node creation with various property types."""
        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query"
        ) as mock_write:
            mock_write.return_value = [
                {
                    "node_id": "4:test:123",
                    "labels": ["TestEntity"],
                    "node_properties": {
                        "string_prop": "test",
                        "int_prop": 42,
                        "float_prop": 3.14,
                        "bool_prop": True,
                        "list_prop": [1, 2, 3],
                    },
                }
            ]

            properties = {
                "string_prop": "test",
                "int_prop": 42,
                "float_prop": 3.14,
                "bool_prop": True,
                "list_prop": [1, 2, 3],
            }

            result = await create_node("TestEntity", properties)

            assert result["properties"]["string_prop"] == "test"
            assert result["properties"]["int_prop"] == 42
            assert result["properties"]["float_prop"] == 3.14
            assert result["properties"]["bool_prop"] is True
            assert result["properties"]["list_prop"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_query_nodes_empty_result(self):
        """Test querying nodes with empty result."""
        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query"
        ) as mock_read:
            mock_read.return_value = []

            result = await query_nodes("NonExistentType")

            assert result == []

    @pytest.mark.asyncio
    async def test_query_nodes_filter_parameter_building(self):
        """Test query parameter building for filters."""
        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query"
        ) as mock_read:
            mock_read.return_value = []

            filters = {"status": "active", "version": "1.0.0", "priority": 1}

            await query_nodes("Service", filters, limit=20)

            call_args = mock_read.call_args
            query = call_args[0][0]
            params = call_args[0][1]

            # Check WHERE clause construction
            assert "n.status = $filter_status" in query
            assert "n.version = $filter_version" in query
            assert "n.priority = $filter_priority" in query

            # Check parameters
            assert params["filter_status"] == "active"
            assert params["filter_version"] == "1.0.0"
            assert params["filter_priority"] == 1
            assert params["limit"] == 20

    @pytest.mark.asyncio
    async def test_execute_cypher_with_parameters(self):
        """Test execute_cypher with parameters."""
        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query"
        ) as mock_read:
            mock_read.return_value = [{"result": "success"}]

            parameters = {"name": "test", "value": 42}
            result = await execute_cypher(
                "MATCH (n {name: $name, value: $value}) RETURN n", parameters
            )

            assert result == [{"result": "success"}]

            call_args = mock_read.call_args
            assert call_args[0][1] == parameters

    @pytest.mark.asyncio
    async def test_create_relationship_error_handling(self):
        """Test relationship creation error handling."""
        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query"
        ) as mock_write:
            mock_write.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                await create_relationship("4:test:123", "4:test:456", "TEST_REL")

    @pytest.mark.asyncio
    async def test_query_nodes_entity_type_inference(self):
        """Test entity type inference from labels."""
        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query"
        ) as mock_read:
            mock_read.return_value = [
                {
                    "node_id": "4:test:1",
                    "labels": ["Service", "Active"],
                    "node_properties": {"name": "test"},
                },
                {
                    "node_id": "4:test:2",
                    "labels": [],
                    "node_properties": {"name": "unlabeled"},
                },
            ]

            result = await query_nodes()  # No specific entity type

            assert len(result) == 2
            assert result[0]["entity_type"] == "Service"  # First label used
            assert result[1]["entity_type"] is None  # No labels

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self):
        """Test health check exception handling."""
        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.verify_connectivity"
        ) as mock_verify:
            mock_verify.side_effect = Exception("Connection timeout")

            result = await health_check()

            assert result["status"] == "unhealthy"
            assert result["connected"] is False
            assert "Connection timeout" in result["error"]


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_create_node_special_characters(self):
        """Test node creation with special characters in properties."""
        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_write_query"
        ) as mock_write:
            mock_write.return_value = [
                {
                    "node_id": "4:test:123",
                    "labels": ["Service"],
                    "node_properties": {
                        "name": "test-service@domain.com",
                        "description": "Service with special chars: !@#$%^&*()",
                        "unicode": "测试服务",
                    },
                }
            ]

            properties = {
                "name": "test-service@domain.com",
                "description": "Service with special chars: !@#$%^&*()",
                "unicode": "测试服务",
            }

            result = await create_node("Service", properties)

            assert result["properties"]["name"] == "test-service@domain.com"
            assert result["properties"]["unicode"] == "测试服务"

    @pytest.mark.asyncio
    async def test_query_nodes_large_limit(self):
        """Test querying with large limit values."""
        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query"
        ) as mock_read:
            mock_read.return_value = []

            await query_nodes(limit=10000)

            call_args = mock_read.call_args
            assert call_args[0][1]["limit"] == 10000

    @pytest.mark.asyncio
    async def test_execute_cypher_empty_parameters(self):
        """Test execute_cypher with empty parameters."""
        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query"
        ) as mock_read:
            mock_read.return_value = [{"result": "ok"}]

            result = await execute_cypher("RETURN 1", {})

            assert result == [{"result": "ok"}]

            call_args = mock_read.call_args
            assert call_args[0][1] == {}

    @pytest.mark.asyncio
    async def test_execute_cypher_none_parameters(self):
        """Test execute_cypher with None parameters."""
        with patch(
            "knowledge_graph_mcp.tools.db_operations.Neo4jConnector.execute_read_query"
        ) as mock_read:
            mock_read.return_value = [{"result": "ok"}]

            result = await execute_cypher("RETURN 1", None)

            assert result == [{"result": "ok"}]

        call_args = mock_read.call_args
        assert (
            call_args[0][1] is None or call_args[0][1] == {}
        )  # None parameters are acceptable
