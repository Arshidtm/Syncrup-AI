from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import subprocess
import time
import sys
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure the project root is in sys.path so 'src' can be imported correctly
sys.path.append(os.getcwd())

from src.discovery.crawler import CodeDiscovery
from src.graph.manager import GraphManager
from src.engine.analyzer import ImpactEngine
from src.engine.groq_analyzer import GroqAnalyzer

# Configuration - Load from environment variables
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WORKER_URLS = {
    "python": os.getenv("PYTHON_WORKER_URL", "http://localhost:8001"),
    "typescript": os.getenv("TYPESCRIPT_WORKER_URL", "http://localhost:8002")
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

class ImpactRequest(BaseModel):
    project_id: str
    filename: str
    changes: Optional[str] = ""

class InitRequest(BaseModel):
    project_id: str
    project_path: Optional[str] = "project_demo"

class RepoRequest(BaseModel):
    project_id: str
    repo_url: str

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
    """
    try:
        # Use the provided project_path instead of current directory
        root = os.path.join(os.getcwd(), request.project_path)
        print(f"Indexing project from: {root}")

        discovery = CodeDiscovery(root, WORKER_URLS)
        graph = GraphManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, request.project_id)
        
        # 1. Clear Graph
        with graph.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

        # 2. Parse and Update
        files_data = discovery.discover_and_parse()
        for file_analysis in files_data:
            graph.update_file_structure(file_analysis)
        
        # 3. Resolve Relationships
        graph.link_calls_to_definitions()
        graph.close()
        
        return {"status": "success", "message": f"Graph initialized for {request.project_path}", "files_processed": len(files_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/check-impact")
async def check_impact(request: ImpactRequest):
    """
    Performs impact analysis for a specific file change.
    """
    try:
        # 1. Setup
        root = os.getcwd()
        discovery = CodeDiscovery(root, WORKER_URLS)
        graph = GraphManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, request.project_id)
        impact_engine = ImpactEngine(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, request.project_id)
        groq_analyzer = GroqAnalyzer(GROQ_API_KEY)

        # 2. Determine file and code context
        file_path = os.path.join(root, request.filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File {request.filename} not found")
        
        with open(file_path, "r", encoding="utf-8") as f:
            code_context = f.read()

        # 3. Update Graph for the specific file
        # Get the project root for this project_id
        project_root = os.path.join(os.getcwd(), "project_demo")  # This should match initialization
        
        # Convert to relative path from project root (not workspace root)
        rel_path = os.path.relpath(file_path, project_root)
        normalized_filename = rel_path.replace('/', os.sep)  # Use OS-specific separators
        
        ext = os.path.splitext(request.filename)[1]
        worker_key = "python" if ext == ".py" else "typescript" if ext == ".ts" else None
        
        if not worker_key:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        analysis = discovery._send_to_worker(file_path, WORKER_URLS[worker_key])
        if analysis:
            analysis["filename"] = normalized_filename  # Use OS-normalized path
            graph.update_file_structure(analysis)
            graph.link_calls_to_definitions()

        # 4. Impact Analysis
        affected = impact_engine.find_affected_nodes(normalized_filename)  # Use OS-normalized path
        report = groq_analyzer.analyze_impact(normalized_filename, affected, changes=request.changes, code_context=code_context)

        graph.close()
        impact_engine.close()

        return {
            "status": "success",
            "filename": normalized_filename,
            "impact_report": report,
            "blast_zone_size": len(affected)
        }
    except Exception as e:
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
