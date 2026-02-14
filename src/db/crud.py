"""
CRUD Operations for the Nexus database.

Thin wrappers around SQLAlchemy queries, used by the API endpoints.
"""
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

from src.db.models import Project, Repository, RepoConnection, Commit, ImpactReport


# ── Projects ──────────────────────────────────────────────────────────────

def create_project(db: Session, name: str, description: str = "") -> Project:
    project = Project(name=name, description=description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_projects(db: Session) -> List[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


def get_project(db: Session, project_id: str) -> Optional[Project]:
    return (
        db.query(Project)
        .options(joinedload(Project.repositories), joinedload(Project.connections))
        .filter(Project.id == project_id)
        .first()
    )


def get_project_by_name(db: Session, name: str) -> Optional[Project]:
    return db.query(Project).filter(Project.name == name).first()


def delete_project(db: Session, project_id: str) -> bool:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        db.delete(project)
        db.commit()
        return True
    return False


# ── Repositories ──────────────────────────────────────────────────────────

def add_repository(db: Session, project_id: str, repo_url: str) -> Repository:
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo = Repository(project_id=project_id, repo_url=repo_url, repo_name=repo_name)
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


def get_repositories(db: Session, project_id: str) -> List[Repository]:
    return db.query(Repository).filter(Repository.project_id == project_id).all()


def get_repository(db: Session, repo_id: str) -> Optional[Repository]:
    return db.query(Repository).filter(Repository.id == repo_id).first()


def update_repo_status(db: Session, repo_id: str, status: str,
                        files_processed: int = 0, error_message: str = None):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if repo:
        repo.status = status
        repo.files_processed = files_processed
        if error_message is not None:
            repo.error_message = error_message
        db.commit()
        db.refresh(repo)
    return repo


def delete_repository(db: Session, repo_id: str) -> bool:
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if repo:
        db.delete(repo)
        db.commit()
        return True
    return False


# ── Repo Connections ──────────────────────────────────────────────────────

def create_connection(db: Session, project_id: str,
                       source_repo_id: str, target_repo_id: str,
                       label: str = "depends_on") -> RepoConnection:
    conn = RepoConnection(
        project_id=project_id,
        source_repo_id=source_repo_id,
        target_repo_id=target_repo_id,
        label=label,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


def get_connections(db: Session, project_id: str) -> List[RepoConnection]:
    return (
        db.query(RepoConnection)
        .options(joinedload(RepoConnection.source_repo), joinedload(RepoConnection.target_repo))
        .filter(RepoConnection.project_id == project_id)
        .all()
    )


def delete_connection(db: Session, connection_id: str) -> bool:
    conn = db.query(RepoConnection).filter(RepoConnection.id == connection_id).first()
    if conn:
        db.delete(conn)
        db.commit()
        return True
    return False


# ── Commits ───────────────────────────────────────────────────────────────

def create_commit(db: Session, project_id: str, repository_id: str,
                   sha: str, author: str, message: str, branch: str,
                   diff_files: list, committed_at=None) -> Commit:
    commit = Commit(
        project_id=project_id,
        repository_id=repository_id,
        sha=sha,
        author=author,
        message=message,
        branch=branch,
        diff_files=diff_files,
        committed_at=committed_at,
    )
    db.add(commit)
    db.commit()
    db.refresh(commit)
    return commit


def get_commits(db: Session, project_id: str, limit: int = 50) -> List[Commit]:
    return (
        db.query(Commit)
        .filter(Commit.project_id == project_id)
        .order_by(Commit.received_at.desc())
        .limit(limit)
        .all()
    )


def get_commit(db: Session, commit_id: str) -> Optional[Commit]:
    return (
        db.query(Commit)
        .options(joinedload(Commit.impact_reports), joinedload(Commit.repository))
        .filter(Commit.id == commit_id)
        .first()
    )


def get_commit_by_sha(db: Session, sha: str) -> Optional[Commit]:
    return db.query(Commit).filter(Commit.sha == sha).first()


# ── Impact Reports ────────────────────────────────────────────────────────

def create_impact_report(db: Session, commit_id: str, project_id: str,
                          changed_file: str, impact_level: str,
                          summary: str, affected_items: list,
                          recommendations: list, blast_zone_size: int) -> ImpactReport:
    report = ImpactReport(
        commit_id=commit_id,
        project_id=project_id,
        changed_file=changed_file,
        impact_level=impact_level,
        summary=summary,
        affected_items=affected_items,
        recommendations=recommendations,
        blast_zone_size=blast_zone_size,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_impact_reports(db: Session, commit_id: str) -> List[ImpactReport]:
    return (
        db.query(ImpactReport)
        .filter(ImpactReport.commit_id == commit_id)
        .order_by(ImpactReport.created_at)
        .all()
    )
