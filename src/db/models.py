"""
SQLAlchemy ORM Models

Defines the relational schema for:
- Projects
- Repositories (per project)
- Repo Connections (cross-repo links drawn on canvas)
- Commits (received via GitHub webhooks)
- Impact Reports (AI analysis per commit)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from src.db.database import Base


def _uuid():
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    repositories = relationship("Repository", back_populates="project", cascade="all, delete-orphan")
    connections = relationship("RepoConnection", back_populates="project", cascade="all, delete-orphan")
    commits = relationship("Commit", back_populates="project", cascade="all, delete-orphan")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    repo_url = Column(String, nullable=False)
    repo_name = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | processing | ready | error
    files_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    project = relationship("Project", back_populates="repositories")
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")


class RepoConnection(Base):
    __tablename__ = "repo_connections"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    source_repo_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    target_repo_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    label = Column(String, default="depends_on")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    project = relationship("Project", back_populates="connections")
    source_repo = relationship("Repository", foreign_keys=[source_repo_id])
    target_repo = relationship("Repository", foreign_keys=[target_repo_id])


class Commit(Base):
    __tablename__ = "commits"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    sha = Column(String, nullable=False, index=True)
    author = Column(String, default="")
    message = Column(Text, default="")
    branch = Column(String, default="main")
    diff_files = Column(JSON, default=list)       # [{filename, status, patch, additions, deletions}]
    committed_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    project = relationship("Project", back_populates="commits")
    repository = relationship("Repository", back_populates="commits")
    impact_reports = relationship("ImpactReport", back_populates="commit", cascade="all, delete-orphan")


class ImpactReport(Base):
    __tablename__ = "impact_reports"

    id = Column(String, primary_key=True, default=_uuid)
    commit_id = Column(String, ForeignKey("commits.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    changed_file = Column(String, nullable=False)
    impact_level = Column(String, default="none")  # none | low | medium | high | error
    summary = Column(Text, default="")
    affected_items = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    blast_zone_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    commit = relationship("Commit", back_populates="impact_reports")
