# Knowledge Graph MCP Server

A Model Context Protocol (MCP) server for managing knowledge graphs with Neo4j backend. Provides AI agents with the ability to create, query, and analyze knowledge graph structures.
Our knowledge graph MCP is useful for encoding and modeling domain specific knowledge in a way that is accessible to both human and AI alike.


## Use Cases

### Software Engineering Documentation
Our knowledge graph schemas are specifically designed for software engineering domains, featuring **8 categories** that represent common software development knowledge, with **48 entity types** and **149 relationships**. This comprehensive schema enables:

- **Automatic Code Documentation**: Connect this MCP server to your favorite AI coding tools to automatically document code repositories, capturing complex relationships and dependencies
- **Cross-Repository Analysis**: Track long-range dependencies that span multiple repositories, services, and databases
- **Architecture Visualization**: Map out system architectures and understand how different components interact
- **Technical Debt Management**: Identify and track technical debt across your entire codebase ecosystem

### Domain-Specific Knowledge Modeling
While our current implementation focuses on software engineering, the server is designed for extensibility. Visionary users can adapt the MCP server to their specific domain needs by:

- **Custom Schema Definition**: Replace or extend the existing schemas with domain-specific entities and relationships
- **Knowledge Domain Encoding**: Model any structured knowledge domain where relationships between entities are critical
- **Expert Knowledge Capture**: Encode domain expertise in a format that's accessible to both humans and AI systems

The key insight is that **schemas** (the lists of entities and their associated relationships) are fundamental to modeling specific knowledge domains effectively. We provide the infrastructure and leave the domain expertise encoding to our users.

## Features

- 🔧 **CRUD Operations**: Full create, read, update, delete for nodes and relationships
- 🧠 **Entity Normalization**: Automatic duplicate detection and merging
- 📊 **Graph Analytics**: Structure analysis and statistics
- ✅ **Schema Validation**: Automatic validation against predefined schema
- 🔋 **Battery Included**: Pre-configured integration with Neo4j, the industry-leading graph database
- 🧪 **Comprehensive Tests**: Unit, integration, and performance tests

## Quick Start

### 1. Install Dependencies

```bash
cd mcp_servers/knowledge-graph-mcp
uv venv
source .venv/bin/activate
uv sync
```

### 2. Start Neo4j Database

```bash
cd docker
docker-compose up -d
```

### 3. Set Environment Variables

```bash
export NEO4J_URI="bolt://localhost:7688"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password"
```

### 4. Test the Server

```bash
python -m pytest tests/ -v
```

## Registering with Cursor or CLI tools


Add to your Cursor MCP configuration file (`~/.cursor/mcp_servers.json` or similar):

```json
{
  "mcpServers": {
    "knowledge-graph-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path-to-your-mcp-server/knowledge-graph-mcp",
        "-m",
        "knowledge_graph_mcp.server"
      ],
      "env": {
        "NEO4J_URI": "bolt://localhost:7688",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password"
      }
    }
  }
}

```


## Environment Variables

### Required Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `NEO4J_URI` | Neo4j database URI | `bolt://localhost:7688` | `bolt://localhost:7688` |
| `NEO4J_USER` | Neo4j username | `neo4j` | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `password` | `your-secure-password` |


#### For Docker Deployment
```yaml
environment:
  - NEO4J_URI=bolt://neo4j:7687
  - NEO4J_USER=neo4j
  - NEO4J_PASSWORD=password
```

## Future Enhancements

Here's what's coming next:

### 🎯 Near-term Goals
- **📋 Flexible Schema Configuration**: Extract graph schemas to separate YAML files for easy customization across different knowledge domains
- **✅ Enhanced Relationship Validation**: Implement comprehensive schema validation for all relationship types
- **🔍 Semantic Search**: Add vector indexing capabilities for intelligent, meaning-based graph queries

### 🚀 Future Vision
- **📊 Interactive Graph Visualization**: Built-in MCP tool for interactive visualization of graph data
- **🧠 Advanced Entity Normalization**: AI powered duplicate detection and entity resolution
- **🔗 Graph Clustering & Communities**: Automatic discovery of related entity clusters and knowledge communities
