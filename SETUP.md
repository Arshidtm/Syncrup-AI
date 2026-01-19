# Setup Guide

Complete installation and configuration guide for Nexus AI Engine.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Neo4j Setup](#neo4j-setup)
- [Environment Configuration](#environment-configuration)
- [Starting the System](#starting-the-system)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Windows-Specific Notes](#windows-specific-notes)

## Prerequisites

Before installing Nexus AI Engine, ensure you have the following:

### Required

- **Python 3.10 or higher**
  ```bash
  python --version
  # Should output: Python 3.10.x or higher
  ```

- **Neo4j Database** (one of the following):
  - Neo4j Desktop (recommended for local development)
  - Neo4j Docker container
  - Neo4j AuraDB (cloud-hosted)

- **Groq API Key**
  - Sign up at [Groq Console](https://console.groq.com)
  - Create an API key for LLaMA-3 access

- **Git** (for cloning repositories)
  ```bash
  git --version
  ```

### Optional

- **Node.js** (for markdown linting during development)
- **Neo4j Browser** (for manual graph inspection)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "New folder"
```

### 2. Create Virtual Environment (Recommended)

**Windows**:
```bash
python -m venv venv
venv\Scripts\activate
```

**Unix/macOS**:
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies installed**:
- `neo4j` - Neo4j Python driver
- `groq` - Groq API client
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `requests` - HTTP client
- `tree-sitter>=0.22.0` - Code parsing library
- `tree-sitter-python` - Python grammar
- `tree-sitter-typescript` - TypeScript grammar
- `pydantic>=2.0.0` - Data validation
- `pydantic-settings>=2.0.0` - Settings management
- `python-dotenv` - Environment variable loading

### 4. Verify Installation

```bash
python -c "import fastapi, neo4j, groq, tree_sitter; print('All dependencies installed successfully!')"
```

## Neo4j Setup

Choose one of the following Neo4j installation methods:

### Option 1: Neo4j Desktop (Recommended for Development)

1. **Download Neo4j Desktop**
   - Visit [neo4j.com/download](https://neo4j.com/download/)
   - Download and install Neo4j Desktop for your OS

2. **Create a New Database**
   - Open Neo4j Desktop
   - Click "New" → "Create Project"
   - Click "Add" → "Local DBMS"
   - Set name: `nexus-ai-engine`
   - Set password (remember this for `.env` configuration)
   - Click "Create"

3. **Start the Database**
   - Click "Start" on your database
   - Wait for status to show "Active"

4. **Note Connection Details**
   - Default URI: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: (what you set during creation)

### Option 2: Neo4j Docker

1. **Pull Neo4j Image**
   ```bash
   docker pull neo4j:latest
   ```

2. **Run Neo4j Container**
   ```bash
   docker run \
     --name nexus-neo4j \
     -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/your_password \
     -v $HOME/neo4j/data:/data \
     neo4j:latest
   ```

3. **Verify Container is Running**
   ```bash
   docker ps
   # Should show nexus-neo4j container
   ```

4. **Connection Details**
   - URI: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: `your_password`

### Option 3: Neo4j AuraDB (Cloud)

1. **Create Free Instance**
   - Visit [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura/)
   - Sign up and create a free instance

2. **Download Credentials**
   - Save the connection URI and password provided

3. **Connection Details**
   - URI: (provided by AuraDB, e.g., `neo4j+s://xxxxx.databases.neo4j.io`)
   - Username: `neo4j`
   - Password: (provided during setup)

## Environment Configuration

### 1. Create `.env` File

Copy the example environment file:

```bash
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` with your actual credentials:

```env
# Neo4j Database Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Groq API Configuration
GROQ_API_KEY=gsk_your_groq_api_key_here

# Worker URLs (default values, change only if needed)
PYTHON_WORKER_URL=http://localhost:8001
TYPESCRIPT_WORKER_URL=http://localhost:8002
```

### Configuration Details

#### Neo4j Configuration

- **NEO4J_URI**: Connection URI for your Neo4j database
  - Local: `bolt://localhost:7687`
  - Docker: `bolt://localhost:7687`
  - AuraDB: `neo4j+s://xxxxx.databases.neo4j.io`

- **NEO4J_USER**: Database username (usually `neo4j`)

- **NEO4J_PASSWORD**: Database password you set during Neo4j setup

#### Groq API Configuration

- **GROQ_API_KEY**: Your Groq API key
  - Get from [console.groq.com](https://console.groq.com)
  - Format: `gsk_...`
  - Used for AI-powered impact analysis

#### Worker Configuration

- **PYTHON_WORKER_URL**: URL for Python parser worker
  - Default: `http://localhost:8001`
  - Change only if port 8001 is unavailable

- **TYPESCRIPT_WORKER_URL**: URL for TypeScript parser worker
  - Default: `http://localhost:8002`
  - Change only if port 8002 is unavailable

### 3. Verify Configuration

Test your configuration:

```bash
python -c "from src.config.settings import settings; print(f'Neo4j: {settings.neo4j_uri}'); print('Config loaded successfully!')"
```

## Starting the System

### 1. Start the API Server

The API server automatically starts worker processes via the lifespan manager.

```bash
python src/api_server.py
```

**Expected Output**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 2. Verify Workers Started

Check that workers are running on their respective ports:

**Python Worker (Port 8001)**:
```bash
curl http://localhost:8001
# Should return: {"message": "Python Worker is running"}
```

**TypeScript Worker (Port 8002)**:
```bash
curl http://localhost:8002
# Should return: {"message": "TypeScript Worker is running"}
```

### 3. Access the API

The API is now available at:
```
http://localhost:8000
```

View API documentation:
```
http://localhost:8000/docs
```

## Verification

### 1. Test API Health

```bash
curl http://localhost:8000/docs
# Should return FastAPI Swagger UI
```

### 2. Initialize a Test Project

```bash
curl -X POST http://localhost:8000/initialize-graph \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test-project",
    "project_path": "."
  }'
```

**Expected Response**:
```json
{
  "status": "success",
  "message": "Graph initialized successfully",
  "project_id": "test-project",
  "files_processed": 23,
  "nodes_created": 95,
  "relationships_created": 142
}
```

### 3. Verify Graph Data

```bash
curl http://localhost:8000/graph-data?project_id=test-project
```

Should return nodes and edges JSON.

### 4. Open Graph Visualization

Open `graph_visualization.html` in your browser and verify the graph renders.

## Troubleshooting

### Common Issues

#### Issue: "Connection refused" to Neo4j

**Symptoms**:
```
neo4j.exceptions.ServiceUnavailable: Failed to establish connection to ('localhost', 7687)
```

**Solutions**:
1. Verify Neo4j is running:
   - Neo4j Desktop: Check database status is "Active"
   - Docker: `docker ps` should show container running
   - AuraDB: Check instance status in console

2. Check connection details in `.env`:
   - Verify `NEO4J_URI` matches your Neo4j instance
   - Test credentials in Neo4j Browser

3. Test connection manually:
   ```bash
   python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'your_password')); driver.verify_connectivity(); print('Connected!')"
   ```

#### Issue: Workers not starting

**Symptoms**:
```
Error from worker for file.py: Connection refused
```

**Solutions**:
1. Check ports 8001 and 8002 are available:
   ```bash
   # Windows
   netstat -ano | findstr :8001
   netstat -ano | findstr :8002
   
   # Unix/macOS
   lsof -i :8001
   lsof -i :8002
   ```

2. Verify worker files exist:
   ```bash
   ls src/workers/python/main.py
   ls src/workers/typescript/main.py
   ```

3. Start workers manually for debugging:
   ```bash
   python src/workers/python/main.py
   # In another terminal:
   python src/workers/typescript/main.py
   ```

#### Issue: "Invalid API key" from Groq

**Symptoms**:
```
Error communicating with Groq API: Invalid API key
```

**Solutions**:
1. Verify `GROQ_API_KEY` in `.env` is correct
2. Check key is active at [console.groq.com](https://console.groq.com)
3. Ensure key starts with `gsk_`
4. Test key manually:
   ```bash
   curl https://api.groq.com/openai/v1/models \
     -H "Authorization: Bearer $GROQ_API_KEY"
   ```

#### Issue: "Module not found" errors

**Symptoms**:
```
ModuleNotFoundError: No module named 'tree_sitter'
```

**Solutions**:
1. Verify virtual environment is activated
2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

3. Check Python version:
   ```bash
   python --version
   # Must be 3.10 or higher
   ```

#### Issue: Path normalization errors (Windows)

**Symptoms**:
```
File not found: src\auth\login.py
```

**Solutions**:
1. Use forward slashes in API requests:
   ```json
   {"filename": "src/auth/login.py"}
   ```

2. Or use double backslashes:
   ```json
   {"filename": "src\\\\auth\\\\login.py"}
   ```

3. See [LINE_NUMBER_FIX.md](LINE_NUMBER_FIX.md) for details

## Windows-Specific Notes

### Path Handling

- **API Requests**: Use forward slashes (`/`) in filenames
- **Graph Storage**: Paths are normalized to forward slashes internally
- **Local Paths**: Can use backslashes (`\`) when specifying `project_path`

### Virtual Environment Activation

```bash
# Command Prompt
venv\Scripts\activate.bat

# PowerShell
venv\Scripts\Activate.ps1
```

If PowerShell script execution is disabled:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Port Conflicts

Check for port conflicts:
```bash
netstat -ano | findstr :8000
netstat -ano | findstr :8001
netstat -ano | findstr :8002
```

Kill process using a port:
```bash
taskkill /PID <process_id> /F
```

## Next Steps

After successful setup:

1. **Read the documentation**:
   - [API_REFERENCE.md](API_REFERENCE.md) - Learn about all endpoints
   - [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - See practical examples
   - [ARCHITECTURE.md](ARCHITECTURE.md) - Understand the system design

2. **Index your first project**:
   ```bash
   curl -X POST http://localhost:8000/initialize-graph \
     -H "Content-Type: application/json" \
     -d '{"project_id": "my-project", "project_path": "/path/to/project"}'
   ```

3. **Try impact analysis**:
   ```bash
   curl -X POST http://localhost:8000/check-impact \
     -H "Content-Type: application/json" \
     -d '{"project_id": "my-project", "filename": "src/file.py"}'
   ```

4. **Visualize the graph**:
   - Open `graph_visualization.html` in your browser

## Support

For issues not covered in this guide:
- Check [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for advanced topics
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system internals
- Open an issue on GitHub (if applicable)
