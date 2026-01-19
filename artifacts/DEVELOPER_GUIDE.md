# Developer Guide

Guide for contributors and developers extending the Nexus AI Engine.

## Table of Contents

- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Adding Language Support](#adding-language-support)
- [Extending the Graph Schema](#extending-the-graph-schema)
- [Custom Analyzers](#custom-analyzers)
- [Testing](#testing)
- [Debugging](#debugging)
- [Contributing](#contributing)

## Project Structure

```
New folder/
├── src/
│   ├── api/                    # API request/response models
│   │   ├── __init__.py
│   │   └── models.py          # Pydantic models
│   ├── config/                # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py        # Environment settings
│   ├── discovery/             # Code discovery and scanning
│   │   ├── __init__.py
│   │   └── crawler.py         # File scanner
│   ├── engine/                # Core analysis engines
│   │   ├── __init__.py
│   │   ├── analyzer.py        # Impact analysis
│   │   ├── groq_analyzer.py   # AI-powered analysis
│   │   └── vector_sync.py     # (Future: vector embeddings)
│   ├── graph/                 # Graph database management
│   │   ├── __init__.py
│   │   └── manager.py         # Neo4j operations
│   ├── models/                # Domain models
│   │   ├── __init__.py
│   │   └── project.py         # Project registry
│   ├── utils/                 # Utility modules
│   │   ├── __init__.py
│   │   ├── logger.py          # Logging configuration
│   │   └── path_normalizer.py # Path handling
│   ├── workers/               # Language-specific parsers
│   │   ├── python/
│   │   │   ├── __init__.py
│   │   │   ├── main.py        # FastAPI worker server
│   │   │   └── parser.py      # Tree-sitter Python parser
│   │   └── typescript/
│   │       ├── __init__.py
│   │       ├── main.py        # FastAPI worker server
│   │       └── parser.py      # Tree-sitter TypeScript parser
│   ├── api_server.py          # Main API server
│   ├── main.py                # CLI tool for file changes
│   └── exceptions.py          # Custom exceptions
├── .env.example               # Environment template
├── .gitignore
├── requirements.txt           # Python dependencies
├── clear_database.py          # Utility to clear Neo4j
├── visualize_graph.py         # Graph data export
├── graph_visualization.html   # Interactive graph viewer
├── LINE_NUMBER_FIX.md        # Technical note
└── README.md                  # Project overview
```

## Development Setup

### 1. Fork and Clone

```bash
git clone <your-fork-url>
cd "New folder"
```

### 2. Create Development Environment

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3. Set Up Pre-commit Hooks (Optional)

```bash
pip install pre-commit
pre-commit install
```

### 4. Configure Development Environment

Copy `.env.example` to `.env` and configure with your development credentials.

### 5. Start Development Neo4j

Use a separate Neo4j database for development to avoid affecting production data.

## Code Style

### Python Conventions

- **PEP 8**: Follow Python PEP 8 style guide
- **Type Hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings for all public functions and classes
- **Line Length**: Maximum 100 characters (flexible for readability)

### Example Function

```python
def analyze_impact(filename: str, changes: str = "") -> dict:
    """
    Analyzes the impact of changes to a file.
    
    Args:
        filename: Path to the changed file (relative to project root)
        changes: Optional description of what changed
        
    Returns:
        Dictionary containing impact analysis results with keys:
        - impact_level: Severity of impact
        - affected_items: List of affected code symbols
        - recommendations: Suggested actions
        
    Raises:
        FileNotFoundError: If the specified file doesn't exist
        ProjectNotFoundError: If project_id is invalid
    """
    # Implementation
    pass
```

### Imports Organization

```python
# Standard library imports
import os
import sys
from typing import Dict, List, Optional

# Third-party imports
from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase

# Local imports
from src.config.settings import settings
from src.utils.logger import logger
```

## Adding Language Support

To add support for a new programming language (e.g., Java, Go, Rust):

### 1. Install Tree-sitter Grammar

```bash
pip install tree-sitter-java  # Example for Java
```

### 2. Create Worker Directory

```
src/workers/java/
├── __init__.py
├── main.py
└── parser.py
```

### 3. Implement Parser

Create `src/workers/java/parser.py`:

```python
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

class JavaParser:
    def __init__(self):
        self.JAVA_LANGUAGE = Language(tsjava.language())
        self.parser = Parser(self.JAVA_LANGUAGE)
    
    def parse_code(self, code: str) -> dict:
        """
        Parse Java code and extract definitions and calls.
        
        Returns:
            {
                "definitions": [{"type": "method", "name": "foo", "line": 10}],
                "calls": [{"name": "bar", "parent": "foo", "line": 12}],
                "imports": [{"content": "import java.util.List", "line": 1}]
            }
        """
        tree = self.parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        
        results = {
            "definitions": [],
            "calls": [],
            "imports": []
        }
        
        self._traverse(root_node, results)
        return results
    
    def _traverse(self, node, results, parent_symbol=None):
        # Extract method definitions
        if node.type == "method_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                results["definitions"].append({
                    "type": "method",
                    "name": name_node.text.decode("utf8"),
                    "line": node.start_point[0] + 1
                })
        
        # Extract method calls
        elif node.type == "method_invocation":
            name_node = node.child_by_field_name("name")
            if name_node:
                results["calls"].append({
                    "name": name_node.text.decode("utf8"),
                    "parent": parent_symbol,
                    "line": node.start_point[0] + 1
                })
        
        # Recursively traverse children
        for child in node.children:
            self._traverse(child, results, parent_symbol)
```

### 4. Create Worker Server

Create `src/workers/java/main.py`:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from .parser import JavaParser

app = FastAPI()
parser = JavaParser()

class ParseRequest(BaseModel):
    code: str
    filename: str

@app.post("/parse")
def parse_code(request: ParseRequest):
    result = parser.parse_code(request.code)
    return {
        "filename": request.filename,
        "data": result
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)  # New port
```

### 5. Update Configuration

Add to `.env.example`:
```env
JAVA_WORKER_URL=http://localhost:8003
```

Update `src/config/settings.py`:
```python
class Settings(BaseSettings):
    # ... existing settings ...
    java_worker_url: str = "http://localhost:8003"
```

### 6. Update Code Discovery

Update `src/discovery/crawler.py`:

```python
ext_to_worker = {
    ".py": "python",
    ".ts": "typescript",
    ".js": "typescript",
    ".java": "java",  # Add new mapping
}
```

### 7. Update API Server Lifespan

Update `src/api_server.py` to start the Java worker:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing workers ...
    workers.append(subprocess.Popen([sys.executable, "src/workers/java/main.py"]))
    yield
    # ... cleanup ...
```

## Extending the Graph Schema

### Adding New Node Types

To add a new node type (e.g., `Interface`):

1. **Update Graph Manager** (`src/graph/manager.py`):

```python
# In _create_structure method
for definition in data["definitions"]:
    if definition["type"] == "interface":
        label = "Interface"
    elif definition["type"] == "function":
        label = "Function"
    # ... existing logic ...
    
    tx.run(f"""
        MERGE (d:{label} {{name: $name, filename: $filename, project_id: $project_id}})
        SET d.line = $line
        WITH d
        MATCH (f:File {{name: $filename, project_id: $project_id}})
        MERGE (f)-[:CONTAINS]->(d)
    """, name=definition["name"], filename=filename, project_id=project_id, line=line)
```

2. **Update Impact Engine** (`src/engine/analyzer.py`):

```python
query = """
    MATCH (target {filename: $filename, project_id: $project_id})
    WHERE target:Function OR target:Class OR target:Interface  // Add new type
    // ... rest of query ...
"""
```

### Adding New Relationships

To add a new relationship type (e.g., `IMPLEMENTS`):

```python
# In graph manager
tx.run("""
    MATCH (c:Class {name: $class_name, project_id: $project_id})
    MATCH (i:Interface {name: $interface_name, project_id: $project_id})
    MERGE (c)-[:IMPLEMENTS]->(i)
""", class_name=class_name, interface_name=interface_name, project_id=project_id)
```

## Custom Analyzers

### Creating a Rule-Based Analyzer

To create a custom analyzer that doesn't use LLM:

```python
# src/engine/rule_based_analyzer.py

class RuleBasedAnalyzer:
    """
    Analyzes impact using predefined rules instead of LLM.
    """
    
    def analyze_impact(self, filename: str, affected_nodes: list) -> dict:
        """
        Apply rule-based impact analysis.
        
        Rules:
        - Changes to auth functions = HIGH impact
        - Changes to utility functions = LOW impact
        - Changes affecting >5 files = HIGH impact
        """
        impact_level = "low"
        
        # Rule 1: Check if auth-related
        if "auth" in filename.lower():
            impact_level = "high"
        
        # Rule 2: Check blast zone size
        if len(affected_nodes) > 5:
            impact_level = "high"
        elif len(affected_nodes) > 2:
            impact_level = "medium"
        
        return {
            "impact_level": impact_level,
            "summary": f"Rule-based analysis: {len(affected_nodes)} items affected",
            "changed_file": filename,
            "affected_items": affected_nodes,
            "recommendations": self._generate_recommendations(impact_level)
        }
    
    def _generate_recommendations(self, impact_level: str) -> list:
        if impact_level == "high":
            return [
                "Review all affected files carefully",
                "Run full test suite",
                "Consider staged rollout"
            ]
        return ["Review affected files", "Run relevant tests"]
```

### Using Custom Analyzer

Update `src/api_server.py`:

```python
from src.engine.rule_based_analyzer import RuleBasedAnalyzer

@app.post("/check-impact")
async def check_impact(request: ImpactCheckRequest):
    # ... existing code ...
    
    # Choose analyzer based on configuration
    if settings.use_llm_analyzer:
        analyzer = GroqAnalyzer(GROQ_API_KEY)
    else:
        analyzer = RuleBasedAnalyzer()
    
    report = analyzer.analyze_impact(filename, affected)
    # ... rest of code ...
```

## Testing

### Manual Testing

Currently, the project uses manual testing. Here's how to test changes:

#### 1. Test Parser

```python
# Test Python parser
from src.workers.python.parser import PythonParser

code = """
def foo():
    bar()
"""

parser = PythonParser()
result = parser.parse_code(code)
print(result)
# Should show definitions and calls
```

#### 2. Test Graph Operations

```python
from src.graph.manager import GraphManager
from src.config.settings import settings

graph = GraphManager(
    settings.neo4j_uri,
    settings.neo4j_user,
    settings.neo4j_password,
    "test-project"
)

# Test creating nodes
analysis = {
    "filename": "test.py",
    "data": {
        "definitions": [{"type": "function", "name": "test_func", "line": 1}],
        "calls": [],
        "imports": []
    }
}

graph.update_file_structure(analysis)
graph.close()
```

#### 3. Test API Endpoints

```bash
# Test initialization
curl -X POST http://localhost:8000/initialize-graph \
  -H "Content-Type: application/json" \
  -d '{"project_id": "test", "project_path": "."}'

# Test impact check
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{"project_id": "test", "filename": "src/main.py"}'
```

### Future: Automated Testing

Recommended test structure for future implementation:

```
tests/
├── unit/
│   ├── test_parsers.py
│   ├── test_graph_manager.py
│   └── test_impact_engine.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_worker_communication.py
└── fixtures/
    └── sample_projects/
```

## Debugging

### Debugging Graph Queries

Use Neo4j Browser to inspect the graph:

1. Open Neo4j Browser: `http://localhost:7474`
2. Run Cypher queries:

```cypher
// View all nodes for a project
MATCH (n {project_id: "my-project"})
RETURN n
LIMIT 25

// View all relationships
MATCH (n {project_id: "my-project"})-[r]->(m)
RETURN n, r, m
LIMIT 50

// Find orphaned calls (not linked to definitions)
MATCH (c:Call {project_id: "my-project"})
WHERE NOT (c)-[:TARGETS]->()
RETURN c

// View dependency chain
MATCH path = (n {project_id: "my-project"})-[:DEPENDS_ON_SYMBOL*1..3]->(m)
RETURN path
```

### Debugging LLM Responses

Enable raw response logging in `src/engine/groq_analyzer.py`:

```python
# Add after getting response
logger.info(f"Raw LLM response: {response_text}")
```

### Debugging Path Normalization

```python
from src.utils.path_normalizer import PathNormalizer

normalizer = PathNormalizer("d:/projects/my-app")

# Test path conversion
abs_path = "d:/projects/my-app/src/auth/login.py"
rel_path = normalizer.to_relative(abs_path)
print(f"Relative: {rel_path}")  # Should be: src/auth/login.py

# Test reverse conversion
back_to_abs = normalizer.to_absolute(rel_path)
print(f"Absolute: {back_to_abs}")
```

### Debugging Worker Communication

Check worker logs:

```bash
# Start workers manually to see logs
python src/workers/python/main.py
# In another terminal:
python src/workers/typescript/main.py
```

Test worker directly:

```bash
curl -X POST http://localhost:8001/parse \
  -H "Content-Type: application/json" \
  -d '{"code": "def foo(): pass", "filename": "test.py"}'
```

## Contributing

### Contribution Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow code style guidelines
   - Add docstrings to new functions
   - Update relevant documentation

3. **Test your changes**
   - Manually test affected functionality
   - Verify no regressions

4. **Commit with descriptive messages**
   ```bash
   git commit -m "Add support for Java language parsing"
   ```

5. **Push and create pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Pull Request Guidelines

- **Title**: Clear, concise description of changes
- **Description**: Explain what changed and why
- **Testing**: Describe how you tested the changes
- **Documentation**: Update relevant docs if needed

### Code Review Process

- All PRs require review before merging
- Address review comments promptly
- Keep PRs focused on a single feature/fix

## Future Enhancements

Areas where contributions are especially welcome:

- **Automated Testing**: Unit and integration test suite
- **File Watching**: Auto-reindex on file changes
- **More Languages**: Go, Rust, Java, C++, etc.
- **Advanced Stitching**: LLM-based API contract detection
- **Performance**: Caching, batch processing
- **Authentication**: API key or OAuth support
- **UI**: Web-based dashboard for impact analysis
- **CI/CD Integration**: GitHub Actions, GitLab CI plugins
