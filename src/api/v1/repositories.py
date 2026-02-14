"""
Repository API Endpoints

Manage repositories within a project: add, remove, process all repos,
connect two repos, manage connections.
"""
import os
import subprocess
import shutil
import stat
import gc
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from src.db.database import get_db
from src.db import crud
from src.discovery.crawler import CodeDiscovery
from src.graph.manager import GraphManager
from src.config.settings import settings

router = APIRouter(prefix="/api/v1/projects/{project_id}/repositories", tags=["repositories"])

WORKER_URLS = {
    "python": settings.python_worker_url,
    "typescript": settings.typescript_worker_url,
}


# ── Schemas ───────────────────────────────────────────────────────────────

class RepoAdd(BaseModel):
    repo_url: str = Field(..., min_length=5)


class ConnectionCreate(BaseModel):
    source_repo_id: str
    target_repo_id: str
    label: Optional[str] = "depends_on"


# ── Helpers ───────────────────────────────────────────────────────────────

def _remove_readonly(func, path, _excinfo):
    """Handle read-only files (common in .git directories on Windows)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _process_single_repo(repo_id: str, project_id: str, repo_url: str, repo_name: str):
    """Clone, parse, and build graph for a single repository (runs in background)."""
    from src.db.database import SessionLocal
    db = SessionLocal()
    try:
        crud.update_repo_status(db, repo_id, "processing")

        clone_path = Path(os.getcwd()) / "repos" / repo_name

        # Clone or pull
        if clone_path.exists():
            subprocess.run(["git", "pull"], cwd=clone_path, check=True, capture_output=True)
        else:
            clone_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", repo_url, str(clone_path)], check=True, capture_output=True)

        # Discover & parse
        discovery = CodeDiscovery(str(clone_path), WORKER_URLS)
        files_data = discovery.discover_and_parse()

        # Build graph
        graph = GraphManager(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password, project_id
        )
        try:
            for file_analysis in files_data:
                graph.update_file_structure(file_analysis)
            graph.link_calls_to_definitions()
        finally:
            graph.close()

        # Cleanup clone
        try:
            gc.collect()
            time.sleep(0.5)
            for attempt in range(3):
                try:
                    shutil.rmtree(clone_path, onerror=_remove_readonly)
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(1 * (attempt + 1))
                    else:
                        raise
        except Exception as e:
            print(f"⚠️  Cleanup warning for {repo_name}: {e}")

        crud.update_repo_status(db, repo_id, "ready", files_processed=len(files_data))
        print(f"✅ Processed {repo_name}: {len(files_data)} files")

    except Exception as e:
        crud.update_repo_status(db, repo_id, "error", error_message=str(e))
        print(f"❌ Failed to process {repo_name}: {e}")
    finally:
        db.close()


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def add_repository(project_id: str, body: RepoAdd, db: Session = Depends(get_db)):
    """Add a repository URL to the project (does NOT process it yet)."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    repo = crud.add_repository(db, project_id, body.repo_url)
    return {
        "id": repo.id,
        "repo_url": repo.repo_url,
        "repo_name": repo.repo_name,
        "status": repo.status,
    }


@router.delete("/{repo_id}")
def remove_repository(project_id: str, repo_id: str, db: Session = Depends(get_db)):
    """Remove a repository from the project and clean up its graph nodes."""
    repo = crud.get_repository(db, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Clean up Neo4j nodes
    try:
        graph = GraphManager(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password, project_id
        )
        graph.delete_repo_nodes(repo.repo_name)
        graph.close()
    except Exception as e:
        print(f"⚠️  Graph cleanup warning for {repo.repo_name}: {e}")

    success = crud.delete_repository(db, repo_id)
    if not success:
        raise HTTPException(status_code=404, detail="Repository not found")
        
    return {"status": "deleted", "repo_id": repo_id}


@router.post("/process-all")
def process_all_repos(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Kick off background processing for all pending/error repos in the project.
    Clones each repo, parses files, builds the Neo4j graph, then deletes the clone.
    """
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    repos_to_process = [r for r in project.repositories if r.status in ("pending", "error")]
    if not repos_to_process:
        return {"status": "nothing_to_process", "message": "All repositories are already processed."}

    for repo in repos_to_process:
        background_tasks.add_task(
            _process_single_repo, repo.id, project_id, repo.repo_url, repo.repo_name
        )

    return {
        "status": "processing",
        "repos_queued": len(repos_to_process),
        "repos": [{"id": r.id, "repo_name": r.repo_name} for r in repos_to_process],
    }


# ── Connections (sub-resource) ────────────────────────────────────────────

conn_router = APIRouter(prefix="/api/v1/projects/{project_id}/connections", tags=["connections"])


@conn_router.post("", status_code=201)
def create_connection(project_id: str, body: ConnectionCreate, db: Session = Depends(get_db)):
    """Connect two repos within the project (visual + logical link)."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate repos exist
    source = crud.get_repository(db, body.source_repo_id)
    target = crud.get_repository(db, body.target_repo_id)
    if not source or not target:
        raise HTTPException(status_code=404, detail="One or both repositories not found")
    if source.project_id != project_id or target.project_id != project_id:
        raise HTTPException(status_code=400, detail="Repositories must belong to this project")

    conn = crud.create_connection(db, project_id, body.source_repo_id, body.target_repo_id, body.label)

    # Also create a cross-repo link in Neo4j
    try:
        graph = GraphManager(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password, project_id
        )
        with graph.driver.session() as session:
            session.run("""
                MATCH (s:File {project_id: $pid}) WHERE s.name STARTS WITH $source_prefix
                MATCH (t:File {project_id: $pid}) WHERE t.name STARTS WITH $target_prefix
                WITH s, t LIMIT 1
                MERGE (s)-[:CROSS_REPO_DEPENDS_ON {label: $label}]->(t)
            """, pid=project_id, source_prefix=source.repo_name,
                 target_prefix=target.repo_name, label=body.label or "depends_on")
        graph.close()
    except Exception as e:
        print(f"⚠️  Neo4j cross-repo link warning: {e}")

    return {
        "id": conn.id,
        "source_repo_id": conn.source_repo_id,
        "target_repo_id": conn.target_repo_id,
        "label": conn.label,
    }


@conn_router.get("")
def list_connections(project_id: str, db: Session = Depends(get_db)):
    connections = crud.get_connections(db, project_id)
    return [
        {
            "id": c.id,
            "source_repo_id": c.source_repo_id,
            "target_repo_id": c.target_repo_id,
            "source_repo_name": c.source_repo.repo_name if c.source_repo else "",
            "target_repo_name": c.target_repo.repo_name if c.target_repo else "",
            "label": c.label,
        }
        for c in connections
    ]


@conn_router.delete("/{connection_id}")
def delete_connection(project_id: str, connection_id: str, db: Session = Depends(get_db)):
    success = crud.delete_connection(db, connection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"status": "deleted", "connection_id": connection_id}
