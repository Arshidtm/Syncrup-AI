"""
Project API Endpoints

CRUD operations for projects: create, list, get detail, delete.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List

from src.db.database import get_db
from src.db import crud

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


# ── Request / Response Schemas ────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = ""


class RepoOut(BaseModel):
    id: str
    repo_url: str
    repo_name: str
    status: str
    files_processed: int

    class Config:
        from_attributes = True


class ConnectionOut(BaseModel):
    id: str
    source_repo_id: str
    target_repo_id: str
    label: str

    class Config:
        from_attributes = True


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    created_at: str
    repo_count: int = 0
    repositories: List[RepoOut] = []
    connections: List[ConnectionOut] = []

    class Config:
        from_attributes = True


class ProjectListItem(BaseModel):
    id: str
    name: str
    description: str
    created_at: str
    repo_count: int = 0

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    existing = crud.get_project_by_name(db, body.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Project '{body.name}' already exists")
    project = crud.create_project(db, body.name, body.description)
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": str(project.created_at),
    }


@router.get("")
def list_projects(db: Session = Depends(get_db)):
    projects = crud.get_projects(db)
    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "created_at": str(p.created_at),
            "repo_count": len(p.repositories) if p.repositories else 0,
        })
    return result


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": str(project.created_at),
        "updated_at": str(project.updated_at),
        "repo_count": len(project.repositories),
        "repositories": [
            {
                "id": r.id,
                "repo_url": r.repo_url,
                "repo_name": r.repo_name,
                "status": r.status,
                "files_processed": r.files_processed,
                "error_message": r.error_message,
                "created_at": str(r.created_at),
            }
            for r in project.repositories
        ],
        "connections": [
            {
                "id": c.id,
                "source_repo_id": c.source_repo_id,
                "target_repo_id": c.target_repo_id,
                "source_repo_name": c.source_repo.repo_name if c.source_repo else "",
                "target_repo_name": c.target_repo.repo_name if c.target_repo else "",
                "label": c.label,
            }
            for c in project.connections
        ],
    }


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    success = crud.delete_project(db, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted", "project_id": project_id}
