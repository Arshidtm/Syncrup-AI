"""
Nexus AI Engine - Main API Server

This module implements the FastAPI-based REST API server that serves as the main entry point
for all client interactions with the Nexus AI Engine. It provides endpoints for:

- Project initialization and repository indexing
- Impact analysis for code changes
- Graph data retrieval for visualization
- Graph database management

The server automatically manages language worker processes (Python and TypeScript parsers)
through FastAPI's lifespan events, ensuring workers are started on server startup and
gracefully terminated on shutdown.

Multi-Project Support:
    All operations are scoped by project_id, allowing multiple projects to be analyzed
    simultaneously with isolated graph data in Neo4j.

Worker Architecture:
    Language-specific parsers run as separate FastAPI services on different ports:
    - Python worker: Port 8001
    - TypeScript worker: Port 8002
    
    Workers are spawned as subprocesses and communicate via HTTP.

Configuration:
    All settings are loaded from environment variables via pydantic-settings.
    See .env.example for required configuration.

Example:
    Start the server:
        $ python src/api_server.py
    
    Initialize a project:
        $ curl -X POST http://localhost:8000/initialize-graph \\
               -H "Content-Type: application/json" \\
               -d '{"project_id": "my-app", "project_path": "/path/to/project"}'
"""
from fastapi import FastAPI, HTTPException

import os
import subprocess
import time
import sys
from typing import Optional
from contextlib import asynccontextmanager

# Ensure the project root is in sys.path
sys.path.append(os.getcwd())

# Import core modules
from src.discovery.crawler import CodeDiscovery
from src.graph.manager import GraphManager
from src.engine.analyzer import ImpactEngine
from src.engine.groq_analyzer import GroqAnalyzer

# Import new utilities
from src.config.settings import settings
from src.models.project import project_registry
from src.utils.logger import logger
from src.exceptions import ProjectNotFoundError, PathNormalizationError
from src.api.models import (
    InitRequest, ImpactCheckRequest, ImpactCheckResponse,
    RepoRequest, AffectedItem, ImpactLevel
)

# Configuration from settings
NEO4J_URI = settings.neo4j_uri
NEO4J_USER = settings.neo4j_user
NEO4J_PASSWORD = settings.neo4j_password
GROQ_API_KEY = settings.groq_api_key
WORKER_URLS = {
    "python": settings.python_worker_url,
    "typescript": settings.typescript_worker_url
}

# --- LIFESPAN MANAGER (Starts/Stops Workers) ---
workers = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: Start parser workers
    print("Starting background parser workers...")
    env = {**os.environ, "PYTHONPATH": os.getcwd()}
    
    py_worker = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.workers.python.main:app", "--port", "8001"], 
                                  env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ts_worker = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.workers.typescript.main:app", "--port", "8002"],
                                  env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    workers.extend([py_worker, ts_worker])
    print("Waiting for workers to initialize...")
    time.sleep(5) # Give workers time to boot
    
    yield
    
    # SHUTDOWN: Cleanup workers
    print("Shutting down background workers...")
    for w in workers:
        w.terminate()
    print("Cleanup complete.")

app = FastAPI(title="Nexus AI Engine API", lifespan=lifespan)

# --- API ENDPOINTS ---

@app.post("/add-repository")
async def add_repository(request: RepoRequest):
    """
    Clones a GitHub repository and adds it to the knowledge graph with the specified project_id.
    The local clone is deleted after processing to save disk space.
    """
    try:
        import subprocess
        import shutil
        from pathlib import Path
        
        # Extract repo name from URL
        repo_name = request.repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        clone_path = Path(os.getcwd()) / "repos" / repo_name
        
        # Clone or pull repository
        if clone_path.exists():
            subprocess.run(["git", "pull"], cwd=clone_path, check=True)
        else:
            clone_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", request.repo_url, str(clone_path)], check=True)
        
        # Discover and parse files
        discovery = CodeDiscovery(str(clone_path), WORKER_URLS)
        files_data = discovery.discover_and_parse()
        
        # Add to graph with project_id
        graph = GraphManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, request.project_id)
        try:
            for file_analysis in files_data:
                graph.update_file_structure(file_analysis)
            
            # Link calls within the project
            graph.link_calls_to_definitions()
        finally:
            # Ensure graph connection is closed before deleting files
            graph.close()
        
        # Clean up: Delete the local clone after processing
        try:
            if clone_path.exists():
                # On Windows, ensure all file handles are released
                import time
                time.sleep(0.5)  # Brief pause to ensure file handles are released
                shutil.rmtree(clone_path, ignore_errors=False)
                print(f"✅ Cleaned up local clone: {clone_path}")
        except Exception as cleanup_error:
            print(f"⚠️ Warning: Could not delete clone directory: {cleanup_error}")
            # Don't fail the request if cleanup fails
        
        return {
            "status": "success",
            "repo": repo_name,
            "url": request.repo_url,
            "project_id": request.project_id,
            "files_processed": len(files_data),
            "local_clone_removed": clone_path.exists() == False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/initialize")
async def initialize_graph(request: InitRequest):
    """
    Scans the project directory and builds the baseline Knowledge Graph.
    Registers the project in the project registry.
    """
    try:
        # Use the provided project_path instead of current directory
        root = os.path.join(os.getcwd(), request.project_path)
        logger.info(f"Initializing project '{request.project_id}' from: {root}")

        # Register project in registry
        project_registry.register(
            project_id=request.project_id,
            name=request.project_id,
            root_path=root
        )
        logger.info(f"Registered project '{request.project_id}' in registry")

        discovery = CodeDiscovery(root, WORKER_URLS)
        graph = GraphManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, request.project_id)
        
        # 1. Clear Graph for this project
        logger.info(f"Clearing existing graph data for project '{request.project_id}'")
        with graph.driver.session() as session:
            session.run("MATCH (n {project_id: $project_id}) DETACH DELETE n", project_id=request.project_id)

        # 2. Parse and Update
        logger.info("Discovering and parsing files...")
        files_data = discovery.discover_and_parse()
        logger.info(f"Found {len(files_data)} files to process")
        
        for file_analysis in files_data:
            graph.update_file_structure(file_analysis)
        
        # 3. Resolve Relationships
        logger.info("Linking function calls to definitions...")
        graph.link_calls_to_definitions()
        graph.close()
        
        logger.info(f"Successfully initialized project '{request.project_id}'")
        return {
            "status": "success", 
            "message": f"Graph initialized for {request.project_path}", 
            "files_processed": len(files_data),
            "project_id": request.project_id
        }
    except Exception as e:
        logger.error(f"Failed to initialize project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/check-impact", response_model=ImpactCheckResponse)
async def check_impact(request: ImpactCheckRequest):
    """
    Performs impact analysis for a specific file change.
    Uses PathNormalizer from project registry for consistent path handling.
    """
    try:
        logger.info(f"Impact check requested for file: {request.filename} in project: {request.project_id}")
        
        # 1. Get project and path normalizer
        try:
            normalizer = project_registry.get_normalizer(request.project_id)
            project = project_registry.get(request.project_id)
        except ProjectNotFoundError as e:
            logger.error(f"Project not found: {request.project_id}")
            raise HTTPException(status_code=404, detail=str(e))
        
        # 2. Normalize the filename
        try:
            normalized_filename = normalizer.normalize(request.filename)
            logger.info(f"Normalized path: {request.filename} -> {normalized_filename}")
        except ValueError as e:
            logger.error(f"Path normalization failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid file path: {str(e)}")
        
        # 3. Setup components
        discovery = CodeDiscovery(project.root_path, WORKER_URLS)
        graph = GraphManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, request.project_id)
        impact_engine = ImpactEngine(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, request.project_id)
        groq_analyzer = GroqAnalyzer(GROQ_API_KEY)
        
        # 4. Read code context if file exists
        code_context = ""
        if normalizer.exists(request.filename):
            file_path = normalizer.to_absolute(normalized_filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code_context = f.read()
                logger.info(f"Read code context from file ({len(code_context)} chars)")
            except Exception as e:
                logger.warning(f"Could not read file: {str(e)}")
        else:
            logger.warning(f"File not found locally: {request.filename}, using graph data only")
        
        # 5. Update graph if file exists locally
        ext = os.path.splitext(normalized_filename)[1]
        worker_key = "python" if ext == ".py" else "typescript" if ext in [".ts", ".tsx"] else None
        
        if worker_key and normalizer.exists(request.filename):
            file_path = normalizer.to_absolute(normalized_filename)
            logger.info(f"Parsing file with {worker_key} worker")
            analysis = discovery._send_to_worker(str(file_path), WORKER_URLS[worker_key])
            if analysis:
                analysis["filename"] = normalized_filename
                graph.update_file_structure(analysis)
                graph.link_calls_to_definitions()
                logger.info("Graph updated successfully")
        
        # 6. Perform impact analysis
        logger.info("Finding affected nodes...")
        affected = impact_engine.find_affected_nodes(normalized_filename)
        logger.info(f"Found {len(affected)} affected items")
        
        logger.info("Generating LLM analysis...")
        impact_report = groq_analyzer.analyze_impact(
            normalized_filename, 
            affected, 
            changes=request.changes or "", 
            code_context=code_context
        )
        
        graph.close()
        impact_engine.close()
        
        # 7. Return structured response
        if isinstance(impact_report, dict):
            impact_report["status"] = "success"
            impact_report["blast_zone_size"] = len(affected)
            logger.info(f"Impact analysis complete: {impact_report.get('impact_level', 'unknown')}")
            return impact_report
        else:
            # Fallback for unexpected response format
            logger.warning("Unexpected impact report format, using fallback")
            return {
                "status": "success",
                "impact_level": ImpactLevel.ERROR,
                "summary": "Analysis completed but response format unexpected",
                "changed_file": normalized_filename,
                "affected_items": [],
                "recommendations": ["Manual review recommended"],
                "blast_zone_size": len(affected)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Impact analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph-data")
async def get_graph_data(project_id: str = "default"):
    """
    Returns the graph structure (Nodes & Edges) for frontend visualization.
    Query param project_id specifies which project to visualize.
    """
    try:
        graph = GraphManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, project_id)
        data = graph.get_graph_data()
        graph.close()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear-graph")
async def clear_graph(project_id: Optional[str] = None):
    """
    Clears the knowledge graph. If project_id is provided, only clears that project.
    Otherwise, clears the entire graph. WARNING: This operation cannot be undone!
    """
    try:
        graph = GraphManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, project_id or "default")
        
        with graph.driver.session() as session:
            if project_id:
                # Clear only this project
                result = session.run("""
                    MATCH (n {project_id: $project_id})
                    DETACH DELETE n
                    """, project_id=project_id)
                summary = result.consume()
                message = f"Cleared project: {project_id}"
            else:
                # Clear entire graph
                result = session.run("MATCH (n) DETACH DELETE n")
                summary = result.consume()
                message = "Cleared entire graph"
            
        graph.close()
        
        return {
            "status": "success",
            "message": message,
            "project_id": project_id,
            "nodes_deleted": summary.counters.nodes_deleted,
            "relationships_deleted": summary.counters.relationships_deleted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
