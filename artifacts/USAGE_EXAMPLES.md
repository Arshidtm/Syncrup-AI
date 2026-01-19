# Usage Examples

Practical examples and common workflows for using Nexus AI Engine.

## Table of Contents

- [Example 1: Analyzing a Local Python Project](#example-1-analyzing-a-local-python-project)
- [Example 2: Adding a GitHub Repository](#example-2-adding-a-github-repository)
- [Example 3: Checking Impact of a File Change](#example-3-checking-impact-of-a-file-change)
- [Example 4: Visualizing the Dependency Graph](#example-4-visualizing-the-dependency-graph)
- [Example 5: Multi-Project Setup](#example-5-multi-project-setup)
- [Example 6: Interpreting Impact Reports](#example-6-interpreting-impact-reports)
- [Real-World Scenario: Refactoring a Shared Utility](#real-world-scenario-refactoring-a-shared-utility)

## Example 1: Analyzing a Local Python Project

**Scenario**: You have a local Python project and want to build its dependency graph.

### Step 1: Start the API Server

```bash
python src/api_server.py
```

### Step 2: Initialize the Graph

```bash
curl -X POST http://localhost:8000/initialize-graph \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-python-app",
    "project_path": "d:/projects/my-python-app"
  }'
```

**Response**:
```json
{
  "status": "success",
  "message": "Graph initialized successfully",
  "project_id": "my-python-app",
  "files_processed": 42,
  "nodes_created": 187,
  "relationships_created": 312
}
```

### Step 3: View the Graph

Open `graph_visualization.html` in your browser and enter `my-python-app` as the project ID.

---

## Example 2: Adding a GitHub Repository

**Scenario**: You want to analyze a public GitHub repository without cloning it manually.

### Request

```bash
curl -X POST http://localhost:8000/add-repository \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "fastapi-example",
    "repo_url": "https://github.com/tiangolo/fastapi.git"
  }'
```

**What Happens**:
1. Repository is cloned to a temporary directory
2. All Python and TypeScript files are parsed
3. Knowledge graph is built in Neo4j
4. Temporary clone is deleted
5. Graph data persists for future queries

**Response**:
```json
{
  "status": "success",
  "message": "Repository indexed successfully",
  "project_id": "fastapi-example",
  "files_processed": 156,
  "nodes_created": 892,
  "relationships_created": 1547
}
```

---

## Example 3: Checking Impact of a File Change

**Scenario**: You modified `src/auth/login.py` and want to know what's affected.

### Request

```bash
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-python-app",
    "filename": "src/auth/login.py",
    "changes": "Changed authenticate_user to require email instead of username"
  }'
```

### Response

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
      "impact_reason": "Calls authenticate_user with username parameter, needs update to email",
      "breaking": true
    },
    {
      "file": "src/api/admin.py",
      "symbol": "admin_login",
      "symbol_type": "function",
      "line_number": 23,
      "depends_on": "authenticate_user",
      "impact_reason": "Depends on authenticate_user signature",
      "breaking": true
    },
    {
      "file": "tests/test_auth.py",
      "symbol": "test_login",
      "symbol_type": "function",
      "line_number": 12,
      "depends_on": "authenticate_user",
      "impact_reason": "Test calls authenticate_user, needs update",
      "breaking": true
    }
  ],
  "recommendations": [
    "Update all callers to pass email instead of username",
    "Add migration script for existing username-based authentication",
    "Update API documentation to reflect new parameter",
    "Run full test suite to catch any missed dependencies"
  ],
  "blast_zone_size": 3
}
```

### What to Do Next

1. Review each affected file listed
2. Update `src/api/routes.py` line 45
3. Update `src/api/admin.py` line 23
4. Update `tests/test_auth.py` line 12
5. Follow the recommendations

---

## Example 4: Visualizing the Dependency Graph

**Scenario**: You want to see the visual representation of your codebase dependencies.

### Step 1: Get Graph Data

```bash
curl http://localhost:8000/graph-data?project_id=my-python-app > graph_data.json
```

### Step 2: Open Visualization

1. Open `graph_visualization.html` in your browser
2. The graph will automatically load for the default project
3. To view a specific project, modify the URL:
   ```
   file:///path/to/graph_visualization.html?project_id=my-python-app
   ```

### Step 3: Interact with the Graph

- **Zoom**: Mouse wheel
- **Pan**: Click and drag
- **Select Node**: Click on a node to highlight its connections
- **Node Colors**:
  - Blue: File nodes
  - Yellow: Function nodes
  - Pink: Class nodes
  - Green: Call nodes

---

## Example 5: Multi-Project Setup

**Scenario**: You're working on a microservices architecture with separate frontend and backend projects.

### Initialize Backend Project

```bash
curl -X POST http://localhost:8000/initialize-graph \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "backend-api",
    "project_path": "d:/projects/backend"
  }'
```

### Initialize Frontend Project

```bash
curl -X POST http://localhost:8000/initialize-graph \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "frontend-app",
    "project_path": "d:/projects/frontend"
  }'
```

### Check Impact in Backend

```bash
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "backend-api",
    "filename": "src/api/endpoints.py"
  }'
```

### Check Impact in Frontend

```bash
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "frontend-app",
    "filename": "src/services/apiClient.ts"
  }'
```

### View Separate Graphs

```bash
# Backend graph
curl http://localhost:8000/graph-data?project_id=backend-api

# Frontend graph
curl http://localhost:8000/graph-data?project_id=frontend-app
```

---

## Example 6: Interpreting Impact Reports

### Scenario 1: No Impact

**Request**:
```bash
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-app",
    "filename": "src/utils/internal_helper.py"
  }'
```

**Response**:
```json
{
  "status": "success",
  "impact_level": "none",
  "summary": "No downstream dependencies found for src/utils/internal_helper.py. This change is isolated.",
  "changed_file": "src/utils/internal_helper.py",
  "affected_items": [],
  "recommendations": [],
  "blast_zone_size": 0
}
```

**Interpretation**: Safe to modify - no other code depends on this file.

---

### Scenario 2: Low Impact

**Response**:
```json
{
  "impact_level": "low",
  "summary": "Minor utility function change affects 1 caller",
  "blast_zone_size": 1,
  "affected_items": [
    {
      "file": "src/services/data_processor.py",
      "symbol": "process_data",
      "breaking": false
    }
  ],
  "recommendations": [
    "Review the single caller to ensure compatibility"
  ]
}
```

**Interpretation**: Low risk - only one dependency, likely non-breaking.

---

### Scenario 3: Medium Impact

**Response**:
```json
{
  "impact_level": "medium",
  "summary": "Database model change affects 4 services",
  "blast_zone_size": 4,
  "affected_items": [
    {
      "file": "src/services/user_service.py",
      "symbol": "get_user",
      "breaking": true
    },
    {
      "file": "src/services/auth_service.py",
      "symbol": "validate_token",
      "breaking": false
    }
  ],
  "recommendations": [
    "Update all affected services",
    "Run integration tests",
    "Consider backward compatibility"
  ]
}
```

**Interpretation**: Moderate risk - multiple dependencies, some breaking. Requires careful review and testing.

---

### Scenario 4: High Impact

**Response**:
```json
{
  "impact_level": "high",
  "summary": "Core authentication function modified, affects 12 endpoints across 5 files",
  "blast_zone_size": 12,
  "affected_items": [
    // ... many affected items ...
  ],
  "recommendations": [
    "Conduct thorough code review",
    "Run full test suite",
    "Consider staged rollout",
    "Update all API documentation",
    "Notify dependent teams"
  ]
}
```

**Interpretation**: High risk - widespread impact. Requires:
- Comprehensive testing
- Careful deployment strategy
- Team coordination
- Possible feature flag

---

## Real-World Scenario: Refactoring a Shared Utility

### Context

You have a shared utility function `format_date()` in `src/utils/date_helpers.py` that's used throughout your application. You want to refactor it to use a different date library.

### Step 1: Check Current Dependencies

```bash
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-app",
    "filename": "src/utils/date_helpers.py",
    "changes": "Planning to refactor format_date() to use date-fns instead of moment"
  }'
```

**Response**:
```json
{
  "impact_level": "high",
  "summary": "Utility function used in 8 different modules",
  "blast_zone_size": 8,
  "affected_items": [
    {"file": "src/api/routes.py", "symbol": "get_events", "line_number": 34},
    {"file": "src/services/event_service.py", "symbol": "create_event", "line_number": 45},
    {"file": "src/services/user_service.py", "symbol": "format_user_data", "line_number": 67},
    {"file": "src/reports/generator.py", "symbol": "generate_report", "line_number": 23},
    {"file": "src/api/admin.py", "symbol": "export_data", "line_number": 89},
    {"file": "src/workers/scheduler.py", "symbol": "schedule_task", "line_number": 12},
    {"file": "tests/test_events.py", "symbol": "test_event_creation", "line_number": 56},
    {"file": "tests/test_reports.py", "symbol": "test_report_dates", "line_number": 78}
  ],
  "recommendations": [
    "Create a compatibility layer to maintain the same API",
    "Update all 8 callers to use the new format",
    "Add comprehensive tests for the new implementation",
    "Consider deprecation period with warnings",
    "Update documentation for all affected modules"
  ]
}
```

### Step 2: Create Refactoring Plan

Based on the impact report:

1. **Files to Update**: 8 files (6 source + 2 test files)
2. **Strategy**: Create compatibility wrapper to minimize breaking changes
3. **Testing**: Update 2 test files, add new tests
4. **Rollout**: Gradual migration with deprecation warnings

### Step 3: Implement with Compatibility Layer

```python
# src/utils/date_helpers.py (new version)
from datetime import datetime
import warnings

def format_date(date, format_str="YYYY-MM-DD"):
    """
    Format a date using date-fns.
    
    DEPRECATED: The format_str parameter is changing.
    Old format: "YYYY-MM-DD" (moment.js style)
    New format: "yyyy-MM-dd" (date-fns style)
    """
    # Translate old format to new format
    if "YYYY" in format_str:
        warnings.warn(
            "Moment.js format strings are deprecated. Use date-fns format.",
            DeprecationWarning
        )
        format_str = format_str.replace("YYYY", "yyyy")
        format_str = format_str.replace("DD", "dd")
    
    # New implementation using date-fns
    return date.strftime(format_str)
```

### Step 4: Verify No Regressions

Re-run impact analysis after changes:

```bash
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-app",
    "filename": "src/utils/date_helpers.py",
    "changes": "Refactored format_date() with backward compatibility"
  }'
```

### Step 5: Gradual Migration

Update callers one by one, verifying each:

```bash
# After updating src/api/routes.py
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-app",
    "filename": "src/api/routes.py"
  }'
```

### Step 6: Final Cleanup

Once all callers are updated, remove the compatibility layer and re-check:

```bash
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-app",
    "filename": "src/utils/date_helpers.py",
    "changes": "Removed deprecated compatibility layer"
  }'
```

---

## Tips and Best Practices

### When to Check Impact

- ✅ **Before** making changes to shared utilities
- ✅ **Before** refactoring core business logic
- ✅ **Before** changing function signatures
- ✅ **After** making changes to verify nothing broke
- ✅ **During** code review to understand change scope

### Interpreting Blast Zone Size

| Size | Risk Level | Action |
|------|------------|--------|
| 0 | None | Safe to proceed |
| 1-2 | Low | Quick review of affected files |
| 3-5 | Medium | Careful review + targeted testing |
| 6-10 | High | Comprehensive review + full testing |
| 10+ | Critical | Team review + staged rollout |

### Using the Changes Parameter

Always provide context in the `changes` parameter for better AI analysis:

**Good**:
```json
{
  "changes": "Changed authenticate_user signature: removed username param, added email param"
}
```

**Better**:
```json
{
  "changes": "Breaking change: authenticate_user now accepts email instead of username. Return type unchanged. All callers must be updated to pass user.email instead of user.username"
}
```

### Clearing and Re-indexing

If the graph seems out of sync:

```bash
# Clear specific project
curl -X DELETE "http://localhost:8000/clear-graph?project_id=my-app"

# Re-initialize
curl -X POST http://localhost:8000/initialize-graph \
  -H "Content-Type: application/json" \
  -d '{"project_id": "my-app", "project_path": "d:/projects/my-app"}'
```

---

## Common Workflows

### Workflow 1: Pre-Commit Check

```bash
# Before committing changes to auth.py
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-app",
    "filename": "src/auth.py",
    "changes": "Added two-factor authentication support"
  }'

# Review impact report
# Update affected files if needed
# Run tests
# Commit changes
```

### Workflow 2: Understanding a New Codebase

```bash
# 1. Index the project
curl -X POST http://localhost:8000/initialize-graph \
  -H "Content-Type: application/json" \
  -d '{"project_id": "new-project", "project_path": "/path/to/project"}'

# 2. Visualize the graph
# Open graph_visualization.html

# 3. Explore key files
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{"project_id": "new-project", "filename": "src/main.py"}'
```

### Workflow 3: Safe Refactoring

```bash
# 1. Check current impact
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{"project_id": "my-app", "filename": "src/utils/helpers.py"}'

# 2. Note all affected files
# 3. Make changes
# 4. Re-check impact
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{"project_id": "my-app", "filename": "src/utils/helpers.py", "changes": "Refactored helper functions"}'

# 5. Verify blast zone hasn't grown unexpectedly
# 6. Update all affected files
# 7. Test thoroughly
```

---

## Next Steps

- Explore [API_REFERENCE.md](API_REFERENCE.md) for complete endpoint documentation
- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand how the system works
- Check [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) if you want to extend the system
