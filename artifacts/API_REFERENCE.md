# API Reference

Complete documentation for all Nexus AI Engine API endpoints.

## Base URL

```
http://localhost:8000
```

## Table of Contents

- [Endpoints Overview](#endpoints-overview)
- [Request/Response Models](#requestresponse-models)
- [Endpoint Details](#endpoint-details)
- [Error Handling](#error-handling)

## Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| [`/add-repository`](#post-add-repository) | POST | Clone and index a GitHub repository |
| [`/initialize-graph`](#post-initialize-graph) | POST | Scan local project and build knowledge graph |
| [`/check-impact`](#post-check-impact) | POST | Analyze impact of file changes |
| [`/graph-data`](#get-graph-data) | GET | Retrieve graph visualization data |
| [`/clear-graph`](#delete-clear-graph) | DELETE | Clear project graph data |

## Request/Response Models

### Common Types

#### ImpactLevel (Enum)
```python
"none" | "low" | "medium" | "high" | "error"
```

### Request Models

#### InitRequest
```json
{
  "project_id": "string",          // Required: Unique project identifier
  "project_path": "string"         // Optional: Path to project directory (default: "project_demo")
}
```

#### RepoRequest
```json
{
  "project_id": "string",          // Required: Project identifier
  "repo_url": "string"             // Required: GitHub repository URL
}
```

#### ImpactCheckRequest
```json
{
  "project_id": "string",          // Required: Project identifier
  "filename": "string",            // Required: File path (absolute or relative)
  "changes": "string"              // Optional: Description of changes made
}
```

### Response Models

#### AffectedItem
```json
{
  "file": "string",                // File containing the affected symbol
  "symbol": "string",              // Name of the affected symbol
  "symbol_type": "string",         // Type of symbol (function, class, etc.)
  "line_number": 42,               // Line number where symbol is defined (nullable)
  "depends_on": "string",          // Symbol this depends on
  "impact_reason": "string",       // Explanation of why this is affected
  "breaking": true                 // Whether this is a breaking change
}
```

#### ImpactCheckResponse
```json
{
  "status": "success",             // Request status
  "impact_level": "high",          // Overall impact severity
  "summary": "string",             // Brief summary of the impact
  "changed_file": "string",        // File that was changed
  "affected_items": [              // List of affected code items
    // Array of AffectedItem objects
  ],
  "recommendations": [             // Recommended actions
    "string"
  ],
  "blast_zone_size": 3             // Number of affected items
}
```

## Endpoint Details

### POST /add-repository

Clone a GitHub repository and add it to the knowledge graph.

**Description**: 
Clones a GitHub repository to a temporary directory, scans all supported files, builds the knowledge graph, and then deletes the local clone to save disk space. The graph data persists in Neo4j.

**Request Body**:
```json
{
  "project_id": "my-backend-api",
  "repo_url": "https://github.com/username/repository.git"
}
```

**Success Response** (200 OK):
```json
{
  "status": "success",
  "message": "Repository indexed successfully",
  "project_id": "my-backend-api",
  "files_processed": 42,
  "nodes_created": 156,
  "relationships_created": 234
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/add-repository \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-backend-api",
    "repo_url": "https://github.com/username/repository.git"
  }'
```

**Notes**:
- Requires Git to be installed and accessible
- Repository must be publicly accessible (no authentication support yet)
- Temporary clone is deleted after indexing
- Processing time depends on repository size

---

### POST /initialize-graph

Scan a local project directory and build the baseline knowledge graph.

**Description**: 
Scans the specified project directory, parses all supported files (Python, TypeScript), creates nodes and relationships in Neo4j, and registers the project in the project registry.

**Request Body**:
```json
{
  "project_id": "local-project",
  "project_path": "d:/projects/my-app"
}
```

**Success Response** (200 OK):
```json
{
  "status": "success",
  "message": "Graph initialized successfully",
  "project_id": "local-project",
  "files_processed": 28,
  "nodes_created": 95,
  "relationships_created": 142
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/initialize-graph \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "local-project",
    "project_path": "d:/projects/my-app"
  }'
```

**Notes**:
- Path can be absolute or relative
- Automatically excludes virtual environments and `.git` directories
- Supports Python (`.py`) and TypeScript/JavaScript (`.ts`, `.js`) files
- Creates project-specific `PathNormalizer` for consistent path handling

---

### POST /check-impact

Perform impact analysis for a specific file change.

**Description**: 
Re-parses the specified file, updates the knowledge graph, traverses dependencies to find affected code, and uses AI (Groq/LLaMA-3) to generate an intelligent impact report with recommendations.

**Request Body**:
```json
{
  "project_id": "my-backend-api",
  "filename": "src/auth/login.py",
  "changes": "Changed authenticate_user function signature to accept email instead of username"
}
```

**Success Response** (200 OK):
```json
{
  "status": "success",
  "impact_level": "high",
  "summary": "Function signature change affects 3 callers across 2 files",
  "changed_file": "src/auth/login.py",
  "affected_items": [
    {
      "file": "src/api/routes.py",
      "symbol": "login_endpoint",
      "symbol_type": "function",
      "line_number": 45,
      "depends_on": "authenticate_user",
      "impact_reason": "Function signature changed from username to email parameter",
      "breaking": true
    },
    {
      "file": "src/api/admin.py",
      "symbol": "admin_login",
      "symbol_type": "function",
      "line_number": 23,
      "depends_on": "authenticate_user",
      "impact_reason": "Calls authenticate_user with username parameter",
      "breaking": true
    }
  ],
  "recommendations": [
    "Update all callers to pass email instead of username",
    "Add migration script to convert existing username-based auth",
    "Update API documentation to reflect new parameter"
  ],
  "blast_zone_size": 2
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-backend-api",
    "filename": "src/auth/login.py",
    "changes": "Changed function signature"
  }'
```

**Notes**:
- Filename can be absolute or relative path
- The `changes` parameter is optional but provides better AI analysis
- Returns empty `affected_items` if no downstream dependencies found
- Line numbers are extracted from Neo4j graph data
- AI analysis requires valid Groq API key

**No Impact Response** (200 OK):
```json
{
  "status": "success",
  "impact_level": "none",
  "summary": "No downstream dependencies found for src/utils/helper.py. This change is isolated.",
  "changed_file": "src/utils/helper.py",
  "affected_items": [],
  "recommendations": [],
  "blast_zone_size": 0
}
```

---

### GET /graph-data

Retrieve the graph structure for frontend visualization.

**Description**: 
Returns all nodes and edges for the specified project in a format suitable for graph visualization libraries (e.g., Vis.js).

**Query Parameters**:
- `project_id` (string, default: "default") - Project identifier

**Success Response** (200 OK):
```json
{
  "nodes": [
    {
      "id": "4:a1b2c3d4-e5f6-7890-abcd-ef1234567890:0",
      "label": "File: src/auth/login.py"
    },
    {
      "id": "4:a1b2c3d4-e5f6-7890-abcd-ef1234567891:1",
      "label": "Function: authenticate_user"
    }
  ],
  "edges": [
    {
      "from": "4:a1b2c3d4-e5f6-7890-abcd-ef1234567890:0",
      "to": "4:a1b2c3d4-e5f6-7890-abcd-ef1234567891:1",
      "label": "CONTAINS"
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:8000/graph-data?project_id=my-backend-api
```

**Notes**:
- Node IDs are Neo4j element IDs (unique identifiers)
- Labels combine node type and name for readability
- Edge labels indicate relationship types
- Used by `graph_visualization.html` for rendering

---

### DELETE /clear-graph

Clear the knowledge graph for a project or the entire database.

**Description**: 
Deletes all nodes and relationships for the specified project. If no `project_id` is provided, clears the entire graph database. **WARNING: This operation cannot be undone!**

**Query Parameters**:
- `project_id` (string, optional) - Project identifier to clear. If omitted, clears entire graph.

**Success Response** (200 OK):
```json
{
  "status": "success",
  "message": "Graph cleared for project: my-backend-api",
  "nodes_deleted": 95,
  "relationships_deleted": 142
}
```

**Example (Clear specific project)**:
```bash
curl -X DELETE "http://localhost:8000/clear-graph?project_id=my-backend-api"
```

**Example (Clear entire graph)**:
```bash
curl -X DELETE http://localhost:8000/clear-graph
```

**Notes**:
- Use with caution - operation is irreversible
- Clearing entire graph affects all projects
- Project must be re-indexed after clearing
- Does not remove project from project registry

---

## Error Handling

### Common Error Responses

#### 400 Bad Request
Returned when request validation fails.

```json
{
  "detail": [
    {
      "loc": ["body", "filename"],
      "msg": "filename cannot be empty",
      "type": "value_error"
    }
  ]
}
```

#### 404 Not Found
Returned when a resource is not found.

```json
{
  "detail": "Project not found: invalid-project-id"
}
```

#### 500 Internal Server Error
Returned when an unexpected error occurs.

```json
{
  "detail": "Error communicating with Neo4j database: Connection refused"
}
```

### Error Scenarios

| Scenario | Status Code | Error Message |
|----------|-------------|---------------|
| Empty filename in impact check | 400 | "filename cannot be empty" |
| Project not found | 404 | "Project not found: {project_id}" |
| File not found during impact check | 404 | "File {filename} not found" |
| Neo4j connection failure | 500 | "Error communicating with Neo4j database" |
| Groq API failure | 500 | "Error communicating with Groq API" |
| Worker not responding | 500 | "Error from worker for {file_path}" |
| Invalid repository URL | 500 | "Failed to clone repository" |

### Troubleshooting

**Workers not starting**:
- Check that ports 8001 and 8002 are available
- Verify Python workers are in `src/workers/python/main.py` and `src/workers/typescript/main.py`
- Check API server logs for worker startup errors

**Neo4j connection errors**:
- Verify Neo4j is running and accessible
- Check `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` in `.env`
- Test connection with Neo4j Browser

**Groq API errors**:
- Verify `GROQ_API_KEY` is set in `.env`
- Check API key is valid at [Groq Console](https://console.groq.com)
- Verify internet connectivity

**Path normalization issues (Windows)**:
- Ensure paths use forward slashes in graph queries
- Use `PathNormalizer` from project registry
- Check [LINE_NUMBER_FIX.md](LINE_NUMBER_FIX.md) for path handling details

## Authentication & Authorization

> [!WARNING]
> **No Authentication**: The current version does not implement authentication or authorization. All endpoints are publicly accessible. Do not expose this API to the internet without adding proper security measures.

**Future Enhancements**:
- API key authentication
- Role-based access control (RBAC)
- Project-level permissions
- Rate limiting

## Rate Limiting

Currently, there is no rate limiting implemented. Consider adding rate limiting in production deployments to prevent abuse.

## Versioning

The API does not currently use versioning. All endpoints are at the base URL. Future versions may introduce versioned endpoints (e.g., `/v1/check-impact`).
