"""
Knowledge Graph Schema Resource for MCP Server

This module provides the schema definition and structure for the knowledge graph,
exposing entity types, relationships, and their constraints to ground AI interactions.
"""

import json
from typing import Any, Dict, List


class KnowledgeGraphSchema:
    """
    Comprehensive schema definition for the knowledge graph.
    Defines all entity types, relationships, and their properties.
    """

    def __init__(self):
        self.entity_types = self._define_entity_types()
        self.relationships = self._define_relationships()
        self.schema_summary = self._generate_schema_summary()

    def _define_entity_types(self) -> Dict[str, Dict[str, Any]]:
        """Define all entity types with their properties and constraints."""
        return {
            # Service Layer
            "Service": {
                "description": "A software service or application component",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "version": {"type": "string", "required": False},
                    "description": {"type": "string", "required": False},
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive", "deprecated"],
                    },
                    "created_at": {"type": "datetime", "required": True},
                    "updated_at": {"type": "datetime", "required": True},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "status"],
            },
            # Code Structure
            "Module": {
                "description": "A code module or package",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "path": {"type": "string", "required": True, "unique": True},
                    "language": {"type": "string", "required": True},
                    "lines_of_code": {"type": "integer", "required": False},
                    "complexity_score": {"type": "float", "required": False},
                },
                "constraints": ["UNIQUE (path)"],
                "indexes": ["name", "language", "path"],
            },
            "Class": {
                "description": "A class definition in code",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "full_name": {"type": "string", "required": True, "unique": True},
                    "visibility": {
                        "type": "string",
                        "enum": ["public", "private", "protected"],
                    },
                    "is_abstract": {"type": "boolean", "default": False},
                    "is_interface": {"type": "boolean", "default": False},
                    "line_number": {"type": "integer", "required": False},
                },
                "constraints": ["UNIQUE (full_name)"],
                "indexes": ["name", "full_name", "visibility"],
            },
            "Interface": {
                "description": "An interface definition",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "full_name": {"type": "string", "required": True, "unique": True},
                    "visibility": {
                        "type": "string",
                        "enum": ["public", "private", "protected"],
                    },
                    "line_number": {"type": "integer", "required": False},
                },
                "constraints": ["UNIQUE (full_name)"],
                "indexes": ["name", "full_name"],
            },
            "Function": {
                "description": "A function or procedure definition",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "full_name": {"type": "string", "required": True, "unique": True},
                    "parameters": {"type": "array", "required": False},
                    "return_type": {"type": "string", "required": False},
                    "visibility": {
                        "type": "string",
                        "enum": ["public", "private", "protected"],
                    },
                    "is_static": {"type": "boolean", "default": False},
                    "line_number": {"type": "integer", "required": False},
                    "complexity_score": {"type": "float", "required": False},
                },
                "constraints": ["UNIQUE (full_name)"],
                "indexes": ["name", "full_name", "visibility"],
            },
            "Method": {
                "description": "A method within a class",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "full_name": {"type": "string", "required": True, "unique": True},
                    "parameters": {"type": "array", "required": False},
                    "return_type": {"type": "string", "required": False},
                    "visibility": {
                        "type": "string",
                        "enum": ["public", "private", "protected"],
                    },
                    "is_static": {"type": "boolean", "default": False},
                    "is_abstract": {"type": "boolean", "default": False},
                    "line_number": {"type": "integer", "required": False},
                },
                "constraints": ["UNIQUE (full_name)"],
                "indexes": ["name", "full_name", "visibility"],
            },
            "Variable": {
                "description": "A variable or field definition",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "full_name": {"type": "string", "required": True, "unique": True},
                    "type": {"type": "string", "required": False},
                    "visibility": {
                        "type": "string",
                        "enum": ["public", "private", "protected"],
                    },
                    "is_static": {"type": "boolean", "default": False},
                    "is_constant": {"type": "boolean", "default": False},
                    "default_value": {"type": "string", "required": False},
                },
                "constraints": ["UNIQUE (full_name)"],
                "indexes": ["name", "full_name", "type"],
            },
            # Web Layer
            "Endpoint": {
                "description": "An API endpoint or web service endpoint",
                "properties": {
                    "path": {"type": "string", "required": True, "unique": True},
                    "method": {
                        "type": "string",
                        "enum": [
                            "GET",
                            "POST",
                            "PUT",
                            "DELETE",
                            "PATCH",
                            "HEAD",
                            "OPTIONS",
                        ],
                    },
                    "description": {"type": "string", "required": False},
                    "parameters": {"type": "array", "required": False},
                    "response_type": {"type": "string", "required": False},
                    "is_authenticated": {"type": "boolean", "default": False},
                    "rate_limit": {"type": "integer", "required": False},
                },
                "constraints": ["UNIQUE (path, method)"],
                "indexes": ["path", "method"],
            },
            "Route": {
                "description": "A routing definition",
                "properties": {
                    "pattern": {"type": "string", "required": True},
                    "name": {"type": "string", "required": False},
                    "middleware": {"type": "array", "required": False},
                    "parameters": {"type": "array", "required": False},
                },
                "indexes": ["pattern", "name"],
            },
            # Business Logic
            "BusinessRule": {
                "description": "A business rule or constraint",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "description": {"type": "string", "required": True},
                    "type": {
                        "type": "string",
                        "enum": ["validation", "calculation", "workflow", "constraint"],
                    },
                    "priority": {"type": "integer", "default": 1},
                    "is_active": {"type": "boolean", "default": True},
                    "conditions": {"type": "string", "required": False},
                    "actions": {"type": "string", "required": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type", "priority"],
            },
            "BusinessProcess": {
                "description": "A business process or workflow",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "description": {"type": "string", "required": True},
                    "version": {"type": "string", "required": False},
                    "status": {
                        "type": "string",
                        "enum": ["draft", "active", "deprecated"],
                    },
                    "steps": {"type": "array", "required": False},
                    "triggers": {"type": "array", "required": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "status"],
            },
            "BusinessCalculation": {
                "description": "A business calculation or formula",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "formula": {"type": "string", "required": True},
                    "description": {"type": "string", "required": False},
                    "input_parameters": {"type": "array", "required": False},
                    "output_type": {"type": "string", "required": False},
                    "precision": {"type": "integer", "required": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name"],
            },
            "BusinessEvent": {
                "description": "A business event or trigger",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "event_type": {"type": "string", "required": True},
                    "description": {"type": "string", "required": False},
                    "payload_schema": {"type": "string", "required": False},
                    "frequency": {
                        "type": "string",
                        "enum": ["once", "recurring", "on_demand"],
                    },
                    "is_active": {"type": "boolean", "default": True},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "event_type", "frequency"],
            },
            "BusinessEntity": {
                "description": "A core business entity or domain object",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "description": {"type": "string", "required": False},
                    "attributes": {"type": "array", "required": False},
                    "lifecycle_states": {"type": "array", "required": False},
                    "business_rules": {"type": "array", "required": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name"],
            },
            "BusinessDecision": {
                "description": "A business decision point or logic",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "description": {"type": "string", "required": False},
                    "decision_criteria": {"type": "string", "required": True},
                    "outcomes": {"type": "array", "required": False},
                    "decision_type": {
                        "type": "string",
                        "enum": ["automated", "manual", "hybrid"],
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "decision_type"],
            },
            # Database & Data
            "DatabaseCluster": {
                "description": "A database cluster or group",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "type": {
                        "type": "string",
                        "enum": ["sql", "nosql", "graph", "timeseries"],
                    },
                    "vendor": {"type": "string", "required": False},
                    "version": {"type": "string", "required": False},
                    "replication_type": {
                        "type": "string",
                        "enum": ["master-slave", "master-master", "sharded"],
                    },
                    "nodes_count": {"type": "integer", "required": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type", "vendor"],
            },
            "Database": {
                "description": "A database instance",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "type": {
                        "type": "string",
                        "enum": ["sql", "nosql", "graph", "timeseries"],
                    },
                    "vendor": {"type": "string", "required": False},
                    "version": {"type": "string", "required": False},
                    "size_mb": {"type": "integer", "required": False},
                    "connection_string": {
                        "type": "string",
                        "required": False,
                        "sensitive": True,
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type", "vendor"],
            },
            "Schema": {
                "description": "A database schema",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "description": {"type": "string", "required": False},
                    "version": {"type": "string", "required": False},
                    "created_at": {"type": "datetime", "required": False},
                    "updated_at": {"type": "datetime", "required": False},
                },
                "indexes": ["name"],
            },
            "Table": {
                "description": "A database table",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "full_name": {"type": "string", "required": True, "unique": True},
                    "description": {"type": "string", "required": False},
                    "row_count": {"type": "integer", "required": False},
                    "size_mb": {"type": "integer", "required": False},
                    "created_at": {"type": "datetime", "required": False},
                },
                "constraints": ["UNIQUE (full_name)"],
                "indexes": ["name", "full_name"],
            },
            "View": {
                "description": "A database view",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "full_name": {"type": "string", "required": True, "unique": True},
                    "definition": {"type": "string", "required": False},
                    "is_materialized": {"type": "boolean", "default": False},
                    "created_at": {"type": "datetime", "required": False},
                },
                "constraints": ["UNIQUE (full_name)"],
                "indexes": ["name", "full_name"],
            },
            "Index": {
                "description": "A database index",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "columns": {"type": "array", "required": True},
                    "is_unique": {"type": "boolean", "default": False},
                    "is_clustered": {"type": "boolean", "default": False},
                    "type": {
                        "type": "string",
                        "enum": ["btree", "hash", "bitmap", "fulltext"],
                    },
                },
                "indexes": ["name"],
            },
            "Trigger": {
                "description": "A database trigger",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "event": {"type": "string", "enum": ["INSERT", "UPDATE", "DELETE"]},
                    "timing": {
                        "type": "string",
                        "enum": ["BEFORE", "AFTER", "INSTEAD_OF"],
                    },
                    "definition": {"type": "string", "required": False},
                    "is_active": {"type": "boolean", "default": True},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "event", "timing"],
            },
            "StoredProcedure": {
                "description": "A stored procedure",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "parameters": {"type": "array", "required": False},
                    "return_type": {"type": "string", "required": False},
                    "definition": {"type": "string", "required": False},
                    "language": {"type": "string", "required": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name"],
            },
            "Collection": {
                "description": "A NoSQL collection or document store",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "document_count": {"type": "integer", "required": False},
                    "size_mb": {"type": "integer", "required": False},
                    "indexes": {"type": "array", "required": False},
                    "schema_validation": {"type": "string", "required": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name"],
            },
            "Document": {
                "description": "A document in a NoSQL collection",
                "properties": {
                    "id": {"type": "string", "required": True, "unique": True},
                    "schema_version": {"type": "string", "required": False},
                    "created_at": {"type": "datetime", "required": False},
                    "updated_at": {"type": "datetime", "required": False},
                    "size_bytes": {"type": "integer", "required": False},
                },
                "constraints": ["UNIQUE (id)"],
                "indexes": ["id"],
            },
            "Field": {
                "description": "A field in a document or collection",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "path": {"type": "string", "required": True},
                    "data_type": {"type": "string", "required": True},
                    "is_required": {"type": "boolean", "default": False},
                    "is_indexed": {"type": "boolean", "default": False},
                    "validation_rules": {"type": "string", "required": False},
                },
                "indexes": ["name", "path", "data_type"],
            },
            "Column": {
                "description": "A column in a database table",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "data_type": {"type": "string", "required": True},
                    "is_nullable": {"type": "boolean", "default": True},
                    "default_value": {"type": "string", "required": False},
                    "max_length": {"type": "integer", "required": False},
                    "precision": {"type": "integer", "required": False},
                    "scale": {"type": "integer", "required": False},
                },
                "indexes": ["name", "data_type"],
            },
            "PrimaryKey": {
                "description": "A primary key constraint",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "columns": {"type": "array", "required": True},
                    "is_clustered": {"type": "boolean", "default": True},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name"],
            },
            "ForeignKey": {
                "description": "A foreign key constraint",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "columns": {"type": "array", "required": True},
                    "referenced_columns": {"type": "array", "required": True},
                    "on_delete": {
                        "type": "string",
                        "enum": ["CASCADE", "SET_NULL", "RESTRICT", "NO_ACTION"],
                    },
                    "on_update": {
                        "type": "string",
                        "enum": ["CASCADE", "SET_NULL", "RESTRICT", "NO_ACTION"],
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name"],
            },
            "Constraint": {
                "description": "A database constraint",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "type": {
                        "type": "string",
                        "enum": ["CHECK", "UNIQUE", "NOT_NULL", "DEFAULT"],
                    },
                    "definition": {"type": "string", "required": True},
                    "is_active": {"type": "boolean", "default": True},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type"],
            },
            "Sequence": {
                "description": "A database sequence",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "start_value": {"type": "integer", "default": 1},
                    "increment": {"type": "integer", "default": 1},
                    "max_value": {"type": "integer", "required": False},
                    "min_value": {"type": "integer", "required": False},
                    "cycle": {"type": "boolean", "default": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name"],
            },
            # Configuration
            "EnvironmentVariable": {
                "description": "An environment variable",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "value": {"type": "string", "required": False, "sensitive": True},
                    "description": {"type": "string", "required": False},
                    "is_sensitive": {"type": "boolean", "default": False},
                    "environment": {
                        "type": "string",
                        "enum": ["development", "testing", "staging", "production"],
                    },
                },
                "constraints": ["UNIQUE (name, environment)"],
                "indexes": ["name", "environment"],
            },
            "ConfigurationFile": {
                "description": "A configuration file",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "path": {"type": "string", "required": True},
                    "format": {
                        "type": "string",
                        "enum": ["json", "yaml", "xml", "properties", "ini", "toml"],
                    },
                    "environment": {
                        "type": "string",
                        "enum": ["development", "testing", "staging", "production"],
                    },
                    "checksum": {"type": "string", "required": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "format", "environment"],
            },
            "Secret": {
                "description": "A secret or credential",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "type": {
                        "type": "string",
                        "enum": [
                            "api_key",
                            "password",
                            "certificate",
                            "token",
                            "connection_string",
                        ],
                    },
                    "description": {"type": "string", "required": False},
                    "expires_at": {"type": "datetime", "required": False},
                    "is_active": {"type": "boolean", "default": True},
                    "environment": {
                        "type": "string",
                        "enum": ["development", "testing", "staging", "production"],
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type", "environment"],
            },
            # Infrastructure
            "Server": {
                "description": "A physical or virtual server",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "ip_address": {"type": "string", "required": False},
                    "hostname": {"type": "string", "required": False},
                    "os": {"type": "string", "required": False},
                    "cpu_cores": {"type": "integer", "required": False},
                    "memory_gb": {"type": "integer", "required": False},
                    "storage_gb": {"type": "integer", "required": False},
                    "status": {
                        "type": "string",
                        "enum": ["online", "offline", "maintenance"],
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "ip_address", "status"],
            },
            "Container": {
                "description": "A containerized application",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "image": {"type": "string", "required": True},
                    "tag": {"type": "string", "required": False},
                    "status": {
                        "type": "string",
                        "enum": ["running", "stopped", "paused", "restarting"],
                    },
                    "ports": {"type": "array", "required": False},
                    "environment_variables": {"type": "array", "required": False},
                    "created_at": {"type": "datetime", "required": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "image", "status"],
            },
            "Pod": {
                "description": "A Kubernetes pod",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "namespace": {"type": "string", "required": True},
                    "status": {
                        "type": "string",
                        "enum": [
                            "pending",
                            "running",
                            "succeeded",
                            "failed",
                            "unknown",
                        ],
                    },
                    "node": {"type": "string", "required": False},
                    "created_at": {"type": "datetime", "required": False},
                    "labels": {"type": "object", "required": False},
                },
                "constraints": ["UNIQUE (name, namespace)"],
                "indexes": ["name", "namespace", "status"],
            },
            "Cluster": {
                "description": "A compute cluster",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "type": {
                        "type": "string",
                        "enum": ["kubernetes", "docker_swarm", "nomad", "mesos"],
                    },
                    "version": {"type": "string", "required": False},
                    "nodes_count": {"type": "integer", "required": False},
                    "status": {
                        "type": "string",
                        "enum": ["healthy", "degraded", "unhealthy"],
                    },
                    "created_at": {"type": "datetime", "required": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type", "status"],
            },
            "LoadBalancer": {
                "description": "A load balancer",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "type": {
                        "type": "string",
                        "enum": ["application", "network", "gateway"],
                    },
                    "algorithm": {
                        "type": "string",
                        "enum": [
                            "round_robin",
                            "least_connections",
                            "ip_hash",
                            "weighted",
                        ],
                    },
                    "health_check_path": {"type": "string", "required": False},
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive", "maintenance"],
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type", "status"],
            },
            "Gateway": {
                "description": "An API gateway or service gateway",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "type": {"type": "string", "enum": ["api", "service", "ingress"]},
                    "endpoints": {"type": "array", "required": False},
                    "authentication": {"type": "array", "required": False},
                    "rate_limiting": {"type": "object", "required": False},
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive", "maintenance"],
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type", "status"],
            },
            "Proxy": {
                "description": "A proxy server",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "type": {
                        "type": "string",
                        "enum": ["reverse", "forward", "transparent"],
                    },
                    "upstream_servers": {"type": "array", "required": False},
                    "ssl_enabled": {"type": "boolean", "default": False},
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive", "maintenance"],
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type", "status"],
            },
            "CDN": {
                "description": "A content delivery network",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "provider": {"type": "string", "required": False},
                    "edge_locations": {"type": "array", "required": False},
                    "cache_behaviors": {"type": "array", "required": False},
                    "ssl_certificate": {"type": "string", "required": False},
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive", "maintenance"],
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "provider", "status"],
            },
            "FileSystem": {
                "description": "A file system or storage system",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "type": {
                        "type": "string",
                        "enum": ["local", "nfs", "s3", "gcs", "azure_blob"],
                    },
                    "mount_point": {"type": "string", "required": False},
                    "capacity_gb": {"type": "integer", "required": False},
                    "used_gb": {"type": "integer", "required": False},
                    "status": {
                        "type": "string",
                        "enum": ["mounted", "unmounted", "error"],
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type", "status"],
            },
            "Bucket": {
                "description": "An object storage bucket",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "provider": {
                        "type": "string",
                        "enum": ["aws_s3", "gcs", "azure_blob", "minio"],
                    },
                    "region": {"type": "string", "required": False},
                    "versioning_enabled": {"type": "boolean", "default": False},
                    "encryption_enabled": {"type": "boolean", "default": False},
                    "public_access": {"type": "boolean", "default": False},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "provider", "region"],
            },
            "Volume": {
                "description": "A storage volume",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "type": {
                        "type": "string",
                        "enum": ["persistent", "ephemeral", "configmap", "secret"],
                    },
                    "size_gb": {"type": "integer", "required": False},
                    "access_mode": {
                        "type": "string",
                        "enum": ["ReadWriteOnce", "ReadOnlyMany", "ReadWriteMany"],
                    },
                    "storage_class": {"type": "string", "required": False},
                    "status": {
                        "type": "string",
                        "enum": ["bound", "available", "released", "failed"],
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type", "status"],
            },
            # Monitoring
            "LogStream": {
                "description": "A log stream or logging channel",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "source": {"type": "string", "required": False},
                    "level": {
                        "type": "string",
                        "enum": ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"],
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "text", "structured"],
                    },
                    "retention_days": {"type": "integer", "required": False},
                    "is_active": {"type": "boolean", "default": True},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "source", "level"],
            },
            "Metric": {
                "description": "A performance or business metric",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "type": {
                        "type": "string",
                        "enum": ["counter", "gauge", "histogram", "summary"],
                    },
                    "unit": {"type": "string", "required": False},
                    "description": {"type": "string", "required": False},
                    "labels": {"type": "array", "required": False},
                    "aggregation": {
                        "type": "string",
                        "enum": ["sum", "avg", "min", "max", "count"],
                    },
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "type"],
            },
            "Alert": {
                "description": "A monitoring alert or notification",
                "properties": {
                    "name": {"type": "string", "required": True, "unique": True},
                    "condition": {"type": "string", "required": True},
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                    "threshold": {"type": "float", "required": False},
                    "duration": {"type": "string", "required": False},
                    "notification_channels": {"type": "array", "required": False},
                    "is_active": {"type": "boolean", "default": True},
                },
                "constraints": ["UNIQUE (name)"],
                "indexes": ["name", "severity"],
            },
        }

    def _define_relationships(self) -> List[Dict[str, Any]]:
        """Define all possible relationships between entities."""
        return [
            # Service Level Relationships
            {
                "from": "Service",
                "to": "Module",
                "type": "CONTAINS",
                "description": "Service contains modules",
            },
            {
                "from": "Service",
                "to": "Endpoint",
                "type": "EXPOSES",
                "description": "Service exposes endpoints",
            },
            {
                "from": "Service",
                "to": "Route",
                "type": "EXPOSES",
                "description": "Service exposes routes",
            },
            {
                "from": "Service",
                "to": "Database",
                "type": "OWNS",
                "description": "Service owns database",
            },
            {
                "from": "Service",
                "to": "DatabaseCluster",
                "type": "OWNS",
                "description": "Service owns database cluster",
            },
            {
                "from": "Service",
                "to": "EnvironmentVariable",
                "type": "USES",
                "description": "Service uses environment variable",
            },
            {
                "from": "Service",
                "to": "ConfigurationFile",
                "type": "USES",
                "description": "Service uses configuration file",
            },
            {
                "from": "Service",
                "to": "Secret",
                "type": "USES",
                "description": "Service uses secret",
            },
            # Cross-Service Communication
            {
                "from": "Service",
                "to": "Service",
                "type": "CALLS_API",
                "description": "Service calls API of another service",
            },
            {
                "from": "Service",
                "to": "Service",
                "type": "PUBLISHES_EVENT",
                "description": "Service publishes event to another service",
            },
            {
                "from": "Service",
                "to": "Service",
                "type": "SUBSCRIBES_TO",
                "description": "Service subscribes to another service",
            },
            # Code Structure Relationships - Module Level
            {
                "from": "Module",
                "to": "Class",
                "type": "CONTAINS",
                "description": "Module contains class",
            },
            {
                "from": "Module",
                "to": "Interface",
                "type": "CONTAINS",
                "description": "Module contains interface",
            },
            {
                "from": "Module",
                "to": "Function",
                "type": "CONTAINS",
                "description": "Module contains function",
            },
            {
                "from": "Module",
                "to": "BusinessEntity",
                "type": "SERVES",
                "description": "Module serves business entity",
            },
            {
                "from": "Module",
                "to": "BusinessProcess",
                "type": "SERVES",
                "description": "Module serves business process",
            },
            # Class Level
            {
                "from": "Class",
                "to": "Interface",
                "type": "IMPLEMENTS",
                "description": "Class implements interface",
            },
            {
                "from": "Class",
                "to": "Class",
                "type": "EXTENDS",
                "description": "Class extends another class",
            },
            {
                "from": "Class",
                "to": "Class",
                "type": "COMPOSED_OF",
                "description": "Class is composed of another class",
            },
            {
                "from": "Class",
                "to": "Class",
                "type": "DEPENDS_ON",
                "description": "Class depends on another class",
            },
            {
                "from": "Class",
                "to": "Function",
                "type": "DEPENDS_ON",
                "description": "Class depends on function",
            },
            {
                "from": "Class",
                "to": "Variable",
                "type": "DEPENDS_ON",
                "description": "Class depends on variable",
            },
            {
                "from": "Class",
                "to": "Method",
                "type": "CONTAINS",
                "description": "Class contains method",
            },
            {
                "from": "Class",
                "to": "Variable",
                "type": "CONTAINS",
                "description": "Class contains variable",
            },
            {
                "from": "Class",
                "to": "BusinessEntity",
                "type": "IMPLEMENTS",
                "description": "Class implements business entity",
            },
            {
                "from": "Class",
                "to": "BusinessRule",
                "type": "ENFORCES",
                "description": "Class enforces business rule",
            },
            {
                "from": "Class",
                "to": "BusinessEntity",
                "type": "MANAGES",
                "description": "Class manages business entity",
            },
            # Interface Level
            {
                "from": "Interface",
                "to": "Interface",
                "type": "EXTENDS",
                "description": "Interface extends another interface",
            },
            {
                "from": "Interface",
                "to": "BusinessEntity",
                "type": "DEFINES",
                "description": "Interface defines business entity",
            },
            # Function Level
            {
                "from": "Function",
                "to": "Class",
                "type": "DEPENDS_ON",
                "description": "Function depends on class",
            },
            {
                "from": "Function",
                "to": "Function",
                "type": "DEPENDS_ON",
                "description": "Function depends on another function",
            },
            {
                "from": "Function",
                "to": "Method",
                "type": "DEPENDS_ON",
                "description": "Function depends on method",
            },
            {
                "from": "Function",
                "to": "Variable",
                "type": "DEPENDS_ON",
                "description": "Function depends on variable",
            },
            {
                "from": "Function",
                "to": "Function",
                "type": "CALLS",
                "description": "Function calls another function",
            },
            {
                "from": "Function",
                "to": "Method",
                "type": "CALLS",
                "description": "Function calls method",
            },
            {
                "from": "Function",
                "to": "BusinessCalculation",
                "type": "IMPLEMENTS",
                "description": "Function implements business calculation",
            },
            {
                "from": "Function",
                "to": "BusinessRule",
                "type": "IMPLEMENTS",
                "description": "Function implements business rule",
            },
            {
                "from": "Function",
                "to": "BusinessEvent",
                "type": "TRIGGERS",
                "description": "Function triggers business event",
            },
            {
                "from": "Function",
                "to": "BusinessDecision",
                "type": "EXECUTES",
                "description": "Function executes business decision",
            },
            {
                "from": "Function",
                "to": "Service",
                "type": "PUBLISHES_EVENT",
                "description": "Function publishes event to service",
            },
            {
                "from": "Function",
                "to": "Service",
                "type": "SUBSCRIBES_TO",
                "description": "Function subscribes to service",
            },
            # Method Level
            {
                "from": "Method",
                "to": "Class",
                "type": "DEPENDS_ON",
                "description": "Method depends on class",
            },
            {
                "from": "Method",
                "to": "Function",
                "type": "DEPENDS_ON",
                "description": "Method depends on function",
            },
            {
                "from": "Method",
                "to": "Method",
                "type": "DEPENDS_ON",
                "description": "Method depends on another method",
            },
            {
                "from": "Method",
                "to": "Variable",
                "type": "DEPENDS_ON",
                "description": "Method depends on variable",
            },
            {
                "from": "Method",
                "to": "Function",
                "type": "CALLS",
                "description": "Method calls function",
            },
            {
                "from": "Method",
                "to": "Method",
                "type": "CALLS",
                "description": "Method calls another method",
            },
            {
                "from": "Method",
                "to": "BusinessRule",
                "type": "IMPLEMENTS",
                "description": "Method implements business rule",
            },
            {
                "from": "Method",
                "to": "BusinessCalculation",
                "type": "IMPLEMENTS",
                "description": "Method implements business calculation",
            },
            {
                "from": "Method",
                "to": "BusinessProcess",
                "type": "ORCHESTRATES",
                "description": "Method orchestrates business process",
            },
            {
                "from": "Method",
                "to": "BusinessDecision",
                "type": "EXECUTES",
                "description": "Method executes business decision",
            },
            {
                "from": "Method",
                "to": "BusinessEvent",
                "type": "TRIGGERS",
                "description": "Method triggers business event",
            },
            {
                "from": "Method",
                "to": "BusinessRule",
                "type": "VALIDATES",
                "description": "Method validates business rule",
            },
            {
                "from": "Method",
                "to": "Service",
                "type": "PUBLISHES_EVENT",
                "description": "Method publishes event to service",
            },
            {
                "from": "Method",
                "to": "Service",
                "type": "SUBSCRIBES_TO",
                "description": "Method subscribes to service",
            },
            # Variable Level
            {
                "from": "Variable",
                "to": "BusinessEntity",
                "type": "STORES",
                "description": "Variable stores business entity",
            },
            {
                "from": "Variable",
                "to": "BusinessRule",
                "type": "REPRESENTS",
                "description": "Variable represents business rule",
            },
            # Web Layer Relationships
            {
                "from": "Route",
                "to": "Endpoint",
                "type": "MAPS_TO",
                "description": "Route maps to endpoint",
            },
            {
                "from": "Route",
                "to": "Function",
                "type": "HANDLED_BY",
                "description": "Route handled by function",
            },
            {
                "from": "Route",
                "to": "Method",
                "type": "HANDLED_BY",
                "description": "Route handled by method",
            },
            {
                "from": "Endpoint",
                "to": "Endpoint",
                "type": "CALLS_API",
                "description": "Endpoint calls another endpoint",
            },
            {
                "from": "Endpoint",
                "to": "BusinessRule",
                "type": "EXPOSES",
                "description": "Endpoint exposes business logic",
            },
            {
                "from": "Endpoint",
                "to": "Function",
                "type": "CALLS",
                "description": "Endpoint calls function",
            },
            {
                "from": "Endpoint",
                "to": "Method",
                "type": "CALLS",
                "description": "Endpoint calls method",
            },
            {
                "from": "Endpoint",
                "to": "Class",
                "type": "DEPENDS_ON",
                "description": "Endpoint depends on class",
            },
            # Business Logic Relationships
            {
                "from": "BusinessProcess",
                "to": "BusinessRule",
                "type": "CONTAINS",
                "description": "Business process contains business rule",
            },
            {
                "from": "BusinessProcess",
                "to": "BusinessEvent",
                "type": "TRIGGERS",
                "description": "Business process triggers business event",
            },
            {
                "from": "BusinessEvent",
                "to": "BusinessProcess",
                "type": "TRIGGERS",
                "description": "Business event triggers business process",
            },
            {
                "from": "BusinessDecision",
                "to": "BusinessRule",
                "type": "DEPENDS_ON",
                "description": "Business decision depends on business rule",
            },
            {
                "from": "BusinessCalculation",
                "to": "BusinessRule",
                "type": "USES",
                "description": "Business calculation uses business rule",
            },
            {
                "from": "BusinessEntity",
                "to": "BusinessRule",
                "type": "HAS",
                "description": "Business entity has business rule",
            },
            {
                "from": "BusinessEntity",
                "to": "BusinessProcess",
                "type": "PARTICIPATES_IN",
                "description": "Business entity participates in business process",
            },
            {
                "from": "BusinessEntity",
                "to": "BusinessEvent",
                "type": "GENERATES",
                "description": "Business entity generates business event",
            },
            # Database Hierarchical Relationships
            {
                "from": "DatabaseCluster",
                "to": "Database",
                "type": "CONTAINS",
                "description": "Database cluster contains database",
            },
            {
                "from": "Database",
                "to": "Schema",
                "type": "CONTAINS",
                "description": "Database contains schema",
            },
            {
                "from": "Schema",
                "to": "Table",
                "type": "CONTAINS",
                "description": "Schema contains table",
            },
            {
                "from": "Schema",
                "to": "View",
                "type": "CONTAINS",
                "description": "Schema contains view",
            },
            {
                "from": "Schema",
                "to": "StoredProcedure",
                "type": "CONTAINS",
                "description": "Schema contains stored procedure",
            },
            {
                "from": "Schema",
                "to": "Trigger",
                "type": "CONTAINS",
                "description": "Schema contains trigger",
            },
            {
                "from": "Table",
                "to": "Column",
                "type": "CONTAINS",
                "description": "Table contains column",
            },
            {
                "from": "Table",
                "to": "Index",
                "type": "CONTAINS",
                "description": "Table contains index",
            },
            {
                "from": "Table",
                "to": "PrimaryKey",
                "type": "CONTAINS",
                "description": "Table contains primary key",
            },
            {
                "from": "Table",
                "to": "ForeignKey",
                "type": "CONTAINS",
                "description": "Table contains foreign key",
            },
            {
                "from": "Table",
                "to": "Constraint",
                "type": "CONTAINS",
                "description": "Table contains constraint",
            },
            {
                "from": "Table",
                "to": "Trigger",
                "type": "CONTAINS",
                "description": "Table contains trigger",
            },
            # NoSQL Database Relationships
            {
                "from": "Database",
                "to": "Collection",
                "type": "CONTAINS",
                "description": "Database contains collection",
            },
            {
                "from": "Collection",
                "to": "Document",
                "type": "CONTAINS",
                "description": "Collection contains document",
            },
            {
                "from": "Document",
                "to": "Field",
                "type": "CONTAINS",
                "description": "Document contains field",
            },
            # Database References and Dependencies
            {
                "from": "Table",
                "to": "Table",
                "type": "REFERENCES",
                "description": "Table references another table",
            },
            {
                "from": "View",
                "to": "Table",
                "type": "DEPENDS_ON",
                "description": "View depends on table",
            },
            {
                "from": "Trigger",
                "to": "Table",
                "type": "ATTACHED_TO",
                "description": "Trigger attached to table",
            },
            {
                "from": "Index",
                "to": "Table",
                "type": "OPTIMIZES",
                "description": "Index optimizes table",
            },
            {
                "from": "StoredProcedure",
                "to": "Table",
                "type": "OPERATES_ON",
                "description": "Stored procedure operates on table",
            },
            {
                "from": "Constraint",
                "to": "Column",
                "type": "ENFORCES",
                "description": "Constraint enforces column",
            },
            {
                "from": "ForeignKey",
                "to": "PrimaryKey",
                "type": "REFERENCES",
                "description": "Foreign key references primary key",
            },
            {
                "from": "Sequence",
                "to": "Column",
                "type": "GENERATES",
                "description": "Sequence generates column values",
            },
            # Database Replication
            {
                "from": "Database",
                "to": "Database",
                "type": "REPLICATES_TO",
                "description": "Database replicates to another database",
            },
            {
                "from": "Database",
                "to": "DatabaseCluster",
                "type": "SHARDS_ACROSS",
                "description": "Database shards across database cluster",
            },
            # Code-to-Database Relationships
            {
                "from": "Class",
                "to": "Table",
                "type": "READS_FROM",
                "description": "Class reads from table",
            },
            {
                "from": "Class",
                "to": "Table",
                "type": "WRITES_TO",
                "description": "Class writes to table",
            },
            {
                "from": "Class",
                "to": "Collection",
                "type": "READS_FROM",
                "description": "Class reads from collection",
            },
            {
                "from": "Class",
                "to": "Collection",
                "type": "WRITES_TO",
                "description": "Class writes to collection",
            },
            {
                "from": "Method",
                "to": "Table",
                "type": "QUERIES",
                "description": "Method queries table",
            },
            {
                "from": "Method",
                "to": "Collection",
                "type": "QUERIES",
                "description": "Method queries collection",
            },
            {
                "from": "Function",
                "to": "Table",
                "type": "INSERTS_INTO",
                "description": "Function inserts into table",
            },
            {
                "from": "Function",
                "to": "Collection",
                "type": "INSERTS_INTO",
                "description": "Function inserts into collection",
            },
            {
                "from": "Function",
                "to": "Table",
                "type": "UPDATES",
                "description": "Function updates table",
            },
            {
                "from": "Function",
                "to": "Collection",
                "type": "UPDATES",
                "description": "Function updates collection",
            },
            {
                "from": "Function",
                "to": "Table",
                "type": "DELETES_FROM",
                "description": "Function deletes from table",
            },
            {
                "from": "Function",
                "to": "Collection",
                "type": "DELETES_FROM",
                "description": "Function deletes from collection",
            },
            # ORM/Mapping Relationships
            {
                "from": "Class",
                "to": "Table",
                "type": "MAPS_TO",
                "description": "Class maps to table",
            },
            {
                "from": "Class",
                "to": "Collection",
                "type": "MAPS_TO",
                "description": "Class maps to collection",
            },
            {
                "from": "Method",
                "to": "Column",
                "type": "MAPS_TO",
                "description": "Method maps to column",
            },
            {
                "from": "Method",
                "to": "Field",
                "type": "MAPS_TO",
                "description": "Method maps to field",
            },
            {
                "from": "Function",
                "to": "StoredProcedure",
                "type": "EXECUTES",
                "description": "Function executes stored procedure",
            },
            # Configuration Relationships
            {
                "from": "Class",
                "to": "EnvironmentVariable",
                "type": "USES",
                "description": "Class uses environment variable",
            },
            {
                "from": "Function",
                "to": "EnvironmentVariable",
                "type": "USES",
                "description": "Function uses environment variable",
            },
            {
                "from": "Method",
                "to": "EnvironmentVariable",
                "type": "USES",
                "description": "Method uses environment variable",
            },
            {
                "from": "Service",
                "to": "ConfigurationFile",
                "type": "LOADS",
                "description": "Service loads configuration file",
            },
            {
                "from": "Class",
                "to": "Secret",
                "type": "ACCESSES",
                "description": "Class accesses secret",
            },
            {
                "from": "Function",
                "to": "Secret",
                "type": "ACCESSES",
                "description": "Function accesses secret",
            },
            {
                "from": "Method",
                "to": "Secret",
                "type": "ACCESSES",
                "description": "Method accesses secret",
            },
            # Infrastructure Relationships - Deployment Hierarchy
            {
                "from": "Cluster",
                "to": "Pod",
                "type": "CONTAINS",
                "description": "Cluster contains pod",
            },
            {
                "from": "Pod",
                "to": "Container",
                "type": "CONTAINS",
                "description": "Pod contains container",
            },
            {
                "from": "Container",
                "to": "Service",
                "type": "RUNS",
                "description": "Container runs service",
            },
            {
                "from": "Server",
                "to": "Container",
                "type": "HOSTS",
                "description": "Server hosts container",
            },
            {
                "from": "Server",
                "to": "Service",
                "type": "HOSTS",
                "description": "Server hosts service",
            },
            # Infrastructure Dependencies
            {
                "from": "Service",
                "to": "Container",
                "type": "DEPLOYED_TO",
                "description": "Service deployed to container",
            },
            {
                "from": "Container",
                "to": "Server",
                "type": "RUNS_ON",
                "description": "Container runs on server",
            },
            {
                "from": "Service",
                "to": "LoadBalancer",
                "type": "USES",
                "description": "Service uses load balancer",
            },
            {
                "from": "Service",
                "to": "Gateway",
                "type": "USES",
                "description": "Service uses gateway",
            },
            {
                "from": "Service",
                "to": "Proxy",
                "type": "USES",
                "description": "Service uses proxy",
            },
            {
                "from": "Service",
                "to": "Bucket",
                "type": "STORES_IN",
                "description": "Service stores data in bucket",
            },
            {
                "from": "Service",
                "to": "FileSystem",
                "type": "USES",
                "description": "Service uses file system",
            },
            {
                "from": "Container",
                "to": "Volume",
                "type": "MOUNTS",
                "description": "Container mounts volume",
            },
            # Network Infrastructure
            {
                "from": "LoadBalancer",
                "to": "Service",
                "type": "ROUTES_TO",
                "description": "Load balancer routes to service",
            },
            {
                "from": "Gateway",
                "to": "Service",
                "type": "PROXIES_TO",
                "description": "Gateway proxies to service",
            },
            {
                "from": "Proxy",
                "to": "Service",
                "type": "FORWARDS_TO",
                "description": "Proxy forwards to service",
            },
            {
                "from": "CDN",
                "to": "Service",
                "type": "CACHES",
                "description": "CDN caches service",
            },
            # Monitoring Relationships
            {
                "from": "Service",
                "to": "LogStream",
                "type": "LOGS_TO",
                "description": "Service logs to log stream",
            },
            {
                "from": "Method",
                "to": "Metric",
                "type": "EMITS",
                "description": "Method emits metric",
            },
            {
                "from": "Function",
                "to": "Alert",
                "type": "TRIGGERS",
                "description": "Function triggers alert",
            },
            {
                "from": "Service",
                "to": "Alert",
                "type": "MONITORED_BY",
                "description": "Service monitored by alert",
            },
            {
                "from": "Container",
                "to": "LogStream",
                "type": "LOGS_TO",
                "description": "Container logs to log stream",
            },
            {
                "from": "Server",
                "to": "Metric",
                "type": "EMITS",
                "description": "Server emits metric",
            },
            # Storage Relationships
            {
                "from": "Service",
                "to": "Bucket",
                "type": "READS_FROM",
                "description": "Service reads from bucket",
            },
            {
                "from": "Service",
                "to": "Bucket",
                "type": "WRITES_TO",
                "description": "Service writes to bucket",
            },
            {
                "from": "Function",
                "to": "FileSystem",
                "type": "ACCESSES",
                "description": "Function accesses file system",
            },
            {
                "from": "Container",
                "to": "Volume",
                "type": "USES",
                "description": "Container uses volume",
            },
        ]

    def _generate_schema_summary(self) -> Dict[str, Any]:
        """Generate a comprehensive summary of the schema."""
        entity_count = len(self.entity_types)
        relationship_count = len(self.relationships)

        entity_categories = {
            "Service Layer": ["Service"],
            "Code Structure": [
                "Module",
                "Class",
                "Interface",
                "Function",
                "Method",
                "Variable",
            ],
            "Web Layer": ["Endpoint", "Route"],
            "Business Logic": [
                "BusinessRule",
                "BusinessProcess",
                "BusinessCalculation",
                "BusinessEvent",
                "BusinessEntity",
                "BusinessDecision",
            ],
            "Database & Data": [
                "DatabaseCluster",
                "Database",
                "Schema",
                "Table",
                "View",
                "Index",
                "Trigger",
                "StoredProcedure",
                "Collection",
                "Document",
                "Field",
                "Column",
                "PrimaryKey",
                "ForeignKey",
                "Constraint",
                "Sequence",
            ],
            "Configuration": ["EnvironmentVariable", "ConfigurationFile", "Secret"],
            "Infrastructure": [
                "Server",
                "Container",
                "Pod",
                "Cluster",
                "LoadBalancer",
                "Gateway",
                "Proxy",
                "CDN",
                "FileSystem",
                "Bucket",
                "Volume",
            ],
            "Monitoring": ["LogStream", "Metric", "Alert"],
        }

        relationship_types = list(set([rel["type"] for rel in self.relationships]))

        return {
            "version": "1.0.0",
            "description": "Comprehensive knowledge graph schema for software architecture and infrastructure",
            "statistics": {
                "total_entity_types": entity_count,
                "total_relationship_types": relationship_count,
                "unique_relationship_types": len(relationship_types),
            },
            "entity_categories": entity_categories,
            "relationship_types": sorted(relationship_types),
            "constraints_summary": {
                "unique_constraints": len(
                    [e for e in self.entity_types.values() if "constraints" in e]
                ),
                "indexed_entities": len(
                    [e for e in self.entity_types.values() if "indexes" in e]
                ),
            },
            "usage_guidelines": {
                "entity_creation": "All entities must include required properties and follow naming conventions",
                "relationship_creation": "Relationships must exist between valid entity types as defined in the schema",
                "property_validation": "Properties must match defined types and constraints",
                "indexing": "Use indexed properties for efficient querying",
            },
        }

    def get_entity_schema(self, entity_type: str) -> Dict[str, Any]:
        """Get schema for a specific entity type."""
        return self.entity_types.get(entity_type, {})

    def get_relationships_for_entity(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get all possible relationships for a given entity type."""
        return [
            rel
            for rel in self.relationships
            if rel["from"] == entity_type or rel["to"] == entity_type
        ]

    def get_relationship_types(self) -> List[str]:
        """Get all unique relationship types."""
        return list(set([rel["type"] for rel in self.relationships]))

    def validate_relationship(
        self, from_entity: str, to_entity: str, relationship_type: str
    ) -> bool:
        """Validate if a relationship is allowed between two entity types."""
        for rel in self.relationships:
            if (
                rel["from"] == from_entity
                and rel["to"] == to_entity
                and rel["type"] == relationship_type
            ):
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert the entire schema to a dictionary."""
        return {
            "entity_types": self.entity_types,
            "relationships": self.relationships,
            "schema_summary": self.schema_summary,
        }

    def to_json(self) -> str:
        """Convert the entire schema to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)


# Create a global schema instance
knowledge_graph_schema = KnowledgeGraphSchema()
