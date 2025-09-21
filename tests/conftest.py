"""
Pytest configuration and shared fixtures for Knowledge Graph MCP tests.
"""

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    test_env = {
        "NEO4J_URI": "bolt://localhost:7688",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "test_password",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    return test_env


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j AsyncDriver for unit testing."""
    mock_driver = AsyncMock()
    mock_driver.verify_connectivity = AsyncMock(return_value=None)
    mock_driver.close = AsyncMock()

    # Mock session
    mock_session = AsyncMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=None)

    return mock_driver


@pytest.fixture
def mock_session():
    """Mock Neo4j AsyncSession for unit testing."""
    mock_session = AsyncMock()

    # Mock result object
    mock_result = AsyncMock()
    mock_result.data = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.execute_write = AsyncMock()
    mock_session.execute_read = AsyncMock()

    return mock_session


@pytest.fixture
def sample_node_data():
    """Sample node data for testing."""
    return {
        "node_id": "4:test:123",
        "labels": ["Service"],
        "node_properties": {
            "name": "test-service",
            "version": "1.0.0",
            "status": "active",
        },
    }


@pytest.fixture
def sample_relationship_data():
    """Sample relationship data for testing."""
    return {
        "rel_id": "5:test:456",
        "rel_type": "CONTAINS",
        "rel_properties": {"created_at": "2024-01-01T00:00:00Z", "strength": 1.0},
    }


@pytest.fixture
def sample_service_properties():
    """Sample service properties for testing."""
    return {
        "name": "user-authentication-service",
        "version": "2.1.0",
        "description": "Handles user authentication and authorization",
        "status": "active",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-20T14:45:00Z",
    }


@pytest.fixture
def sample_module_properties():
    """Sample module properties for testing."""
    return {
        "name": "auth_module",
        "path": "/src/auth/module.py",
        "language": "python",
        "lines_of_code": 150,
        "complexity_score": 2.5,
    }


@pytest.fixture
async def cleanup_test_data():
    """Fixture to clean up test data after tests."""
    # This runs after the test
    yield

    # Cleanup code here if needed for integration tests
    # For unit tests with mocks, no cleanup is needed
    pass


class MockNeo4jResult:
    """Mock Neo4j result object."""

    def __init__(self, data: list[Dict[str, Any]]):
        self._data = data

    async def data(self) -> list[Dict[str, Any]]:
        """Return the mock data."""
        return self._data


class MockNeo4jTransaction:
    """Mock Neo4j transaction object."""

    def __init__(self, result_data: list[Dict[str, Any]]):
        self.result_data = result_data

    async def run(
        self, query: str, parameters: Dict[str, Any] = None
    ) -> MockNeo4jResult:
        """Mock transaction run method."""
        return MockNeo4jResult(self.result_data)
