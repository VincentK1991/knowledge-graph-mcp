"""
Unit tests for Neo4jConnector class.
Tests connection management, query execution, and error handling with mocking.
"""

from unittest.mock import AsyncMock, patch

import pytest
from knowledge_graph_mcp.tools.db_operations import Neo4jConnector
from neo4j.exceptions import ServiceUnavailable, TransientError


class TestNeo4jConnector:
    """Test cases for Neo4jConnector class."""

    def test_get_config_key(self):
        """Test configuration key generation."""
        key = Neo4jConnector._get_config_key("bolt://localhost:7688", "neo4j")
        assert key == "bolt://localhost:7688:neo4j"

    def test_get_config_from_env(self, mock_env_vars):
        """Test environment variable configuration loading."""
        uri, user, password = Neo4jConnector._get_config_from_env()

        assert uri == "bolt://localhost:7688"
        assert user == "neo4j"
        assert password == "test_password"

    def test_get_config_from_env_defaults(self, monkeypatch):
        """Test default configuration values."""
        # Remove password to test defaults
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        monkeypatch.setenv("NEO4J_PASSWORD", "password")  # Set default

        uri, user, password = Neo4jConnector._get_config_from_env()

        assert uri == "bolt://localhost:7688"
        assert user == "neo4j"
        assert password == "password"

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.AsyncGraphDatabase.driver")
    async def test_get_driver_new_connection(self, mock_driver_factory, mock_env_vars):
        """Test creating a new driver connection."""
        mock_driver = AsyncMock()
        mock_driver_factory.return_value = mock_driver

        # Clear any existing drivers
        Neo4jConnector._drivers.clear()

        driver = await Neo4jConnector.get_driver()

        assert driver == mock_driver
        mock_driver_factory.assert_called_once_with(
            uri="bolt://localhost:7688",
            auth=("neo4j", "test_password"),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=60,
            encrypted=False,
        )

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.AsyncGraphDatabase.driver")
    async def test_get_driver_cached_connection(
        self, mock_driver_factory, mock_env_vars
    ):
        """Test reusing cached driver connection."""
        mock_driver = AsyncMock()
        mock_driver_factory.return_value = mock_driver

        # Clear and setup cache
        Neo4jConnector._drivers.clear()

        # First call should create driver
        driver1 = await Neo4jConnector.get_driver()

        # Second call should reuse cached driver
        driver2 = await Neo4jConnector.get_driver()

        assert driver1 == driver2
        assert mock_driver_factory.call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_close_driver_all(self):
        """Test closing all drivers."""
        # Setup mock drivers
        mock_driver1 = AsyncMock()
        mock_driver2 = AsyncMock()

        Neo4jConnector._drivers = {
            "uri1:user1": mock_driver1,
            "uri2:user2": mock_driver2,
        }

        await Neo4jConnector.close_driver()

        mock_driver1.close.assert_called_once()
        mock_driver2.close.assert_called_once()
        assert len(Neo4jConnector._drivers) == 0

    @pytest.mark.asyncio
    async def test_close_driver_specific(self, mock_env_vars):
        """Test closing specific driver."""
        mock_driver = AsyncMock()
        config_key = "bolt://localhost:7688:neo4j"

        Neo4jConnector._drivers = {config_key: mock_driver}

        await Neo4jConnector.close_driver("bolt://localhost:7688", "neo4j")

        mock_driver.close.assert_called_once()
        assert config_key not in Neo4jConnector._drivers

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.get_driver")
    async def test_get_session(self, mock_get_driver):
        """Test session context manager."""
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_get_driver.return_value = mock_driver
        mock_driver.session.return_value = mock_context_manager

        async with Neo4jConnector.get_session(database="test_db") as session:
            assert session == mock_session

        mock_driver.session.assert_called_once_with(database="test_db")

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.get_session")
    async def test_execute_query_success(self, mock_get_session):
        """Test successful query execution."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data.return_value = [{"test": "value"}]
        mock_session.run.return_value = mock_result

        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await Neo4jConnector.execute_query("RETURN 1")

        assert result == [{"test": "value"}]
        mock_session.run.assert_called_once()

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.get_session")
    async def test_execute_query_service_unavailable(self, mock_get_session):
        """Test query execution with service unavailable error."""
        mock_session = AsyncMock()
        mock_session.run.side_effect = ServiceUnavailable("Service unavailable")

        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(ServiceUnavailable):
            await Neo4jConnector.execute_query("RETURN 1")

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.get_session")
    async def test_execute_write_query(self, mock_get_session):
        """Test write query execution with transaction."""
        mock_session = AsyncMock()
        mock_session.execute_write.return_value = [{"created": "node"}]

        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await Neo4jConnector.execute_write_query("CREATE (n) RETURN n")

        assert result == [{"created": "node"}]
        mock_session.execute_write.assert_called_once()

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.get_session")
    async def test_execute_read_query(self, mock_get_session):
        """Test read query execution with transaction."""
        mock_session = AsyncMock()
        mock_session.execute_read.return_value = [{"found": "data"}]

        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await Neo4jConnector.execute_read_query("MATCH (n) RETURN n")

        assert result == [{"found": "data"}]
        mock_session.execute_read.assert_called_once()

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.get_driver")
    async def test_verify_connectivity_success(self, mock_get_driver):
        """Test successful connectivity verification."""
        mock_driver = AsyncMock()
        mock_driver.verify_connectivity.return_value = None
        mock_get_driver.return_value = mock_driver

        result = await Neo4jConnector.verify_connectivity()

        assert result is True
        mock_driver.verify_connectivity.assert_called_once()

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.get_driver")
    async def test_verify_connectivity_failure(self, mock_get_driver):
        """Test connectivity verification failure."""
        mock_driver = AsyncMock()
        mock_driver.verify_connectivity.side_effect = ServiceUnavailable(
            "Connection failed"
        )
        mock_get_driver.return_value = mock_driver

        result = await Neo4jConnector.verify_connectivity()

        assert result is False

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.get_session")
    async def test_execute_query_with_parameters(self, mock_get_session):
        """Test query execution with parameters."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data.return_value = [{"param_value": "test"}]
        mock_session.run.return_value = mock_result

        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        parameters = {"param": "test_value"}
        result = await Neo4jConnector.execute_query("RETURN $param", parameters)

        assert result == [{"param_value": "test"}]
        # Verify parameters were passed correctly
        call_args = mock_session.run.call_args
        assert call_args[0][1] == parameters  # Second argument should be parameters

    @pytest.mark.asyncio
    @patch("knowledge_graph_mcp.tools.db_operations.Neo4jConnector.get_session")
    async def test_execute_query_transient_error(self, mock_get_session):
        """Test query execution with transient error."""
        mock_session = AsyncMock()
        mock_session.run.side_effect = TransientError("Transient error")

        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(TransientError):
            await Neo4jConnector.execute_query("RETURN 1")

    def test_encrypted_connection_detection(self):
        """Test encrypted connection detection logic."""
        # Test encrypted URIs
        encrypted_uris = ["neo4j+s://localhost:7687", "bolt+s://localhost:7687"]

        for uri in encrypted_uris:
            encrypted = uri.startswith("neo4j+s://") or uri.startswith("bolt+s://")
            assert encrypted is True

        # Test non-encrypted URIs
        non_encrypted_uris = ["bolt://localhost:7687", "neo4j://localhost:7687"]

        for uri in non_encrypted_uris:
            encrypted = uri.startswith("neo4j+s://") or uri.startswith("bolt+s://")
            assert encrypted is False
