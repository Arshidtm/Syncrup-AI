"""
Webhook & Commit API Endpoints

Handles GitHub push webhooks, stores commits + diffs, and provides
commit listing and impact analysis retrieval.
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from typing import Optional

from src.db.database import get_db
from src.db import crud
from src.graph.manager import GraphManager
from src.engine.analyzer import ImpactEngine
from src.engine.groq_analyzer import GroqAnalyzer
from src.config.settings import settings

router = APIRouter(tags=["webhooks & commits"])

WEBHOOK_SECRET = getattr(settings, "github_webhook_secret", None) or ""
GITHUB_TOKEN = getattr(settings, "github_token", None) or ""  # Add this to settings if needed


# ── GitHub Webhook ────────────────────────────────────────────────────────

@router.post("/api/v1/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Receives GitHub push events, extracts commits & diffs,
    runs impact analysis, and stores results.
    """
    body = await request.body()

    # Verify signature (if secret configured)
    if WEBHOOK_SECRET:
        expected = "sha256=" + hmac.new(
            WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature_256 or ""):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)

    # Only handle push events
    if x_github_event and x_github_event != "push":
        return {"status": "ignored", "event": x_github_event}

    repo_url = payload.get("repository", {}).get("clone_url", "")
    repo_name = payload.get("repository", {}).get("name", "")
    branch = payload.get("ref", "").replace("refs/heads/", "")

    # Find repository in our database
    repos = db.query(crud.Repository).filter(
        crud.Repository.repo_name == repo_name
    ).all()

    if not repos:
        return {"status": "ignored", "reason": f"Repository '{repo_name}' not tracked"}

    results = []
    for db_repo in repos:
        project_id = db_repo.project_id

        for commit_data in payload.get("commits", []):
            sha = commit_data.get("id", "")
            author = commit_data.get("author", {}).get("name", "unknown")
            message = commit_data.get("message", "")
            timestamp = commit_data.get("timestamp")

            committed_at = None
            if timestamp:
                try:
                    committed_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except Exception:
                    pass

            # Build diff file list from commit data
            diff_files = []
            for f in commit_data.get("added", []):
                diff_files.append({"filename": f, "status": "added", "patch": ""})
            for f in commit_data.get("modified", []):
                diff_files.append({"filename": f, "status": "modified", "patch": ""})
            for f in commit_data.get("removed", []):
                diff_files.append({"filename": f, "status": "removed", "patch": ""})

            # Skip if already processed
            existing = crud.get_commit_by_sha(db, sha)
            if existing:
                continue

            # Store commit
            db_commit = crud.create_commit(
                db, project_id, db_repo.id,
                sha=sha, author=author, message=message,
                branch=branch, diff_files=diff_files,
                committed_at=committed_at,
            )

            # Run impact analysis for each changed file
            try:
                impact_engine = ImpactEngine(
                    settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password, project_id
                )
                groq_analyzer = GroqAnalyzer(settings.groq_api_key)

                for diff_file in diff_files:
                    filename = diff_file["filename"]
                    affected = impact_engine.find_affected_nodes(filename)
                    report = groq_analyzer.analyze_impact(
                        filename, affected,
                        changes=f"Commit: {message}",
                        code_context="",
                    )

                    crud.create_impact_report(
                        db, db_commit.id, project_id,
                        changed_file=filename,
                        impact_level=report.get("impact_level", "none"),
                        summary=report.get("summary", ""),
                        affected_items=report.get("affected_items", []),
                        recommendations=report.get("recommendations", []),
                        blast_zone_size=report.get("blast_zone_size", len(affected)),
                    )

                impact_engine.close()
            except Exception as e:
                print(f"⚠️  Impact analysis error for commit {sha[:8]}: {e}")

            results.append({
                "sha": sha,
                "message": message,
                "files_changed": len(diff_files),
            })

    return {
        "status": "processed",
        "commits_processed": len(results),
        "commits": results,
    }


# ── Commit Listing ────────────────────────────────────────────────────────

@router.get("/api/v1/projects/{project_id}/commits")
def list_commits(project_id: str, limit: int = 50, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    commits = crud.get_commits(db, project_id, limit=limit)
    return [
        {
            "id": c.id,
            "sha": c.sha,
            "author": c.author,
            "message": c.message,
            "branch": c.branch,
            "files_changed": len(c.diff_files) if c.diff_files else 0,
            "received_at": str(c.received_at),
            "committed_at": str(c.committed_at) if c.committed_at else None,
            "repo_name": c.repository.repo_name if c.repository else "",
        }
        for c in commits
    ]


@router.get("/api/v1/projects/{project_id}/commits/{commit_id}")
def get_commit_detail(project_id: str, commit_id: str, db: Session = Depends(get_db)):
    commit = crud.get_commit(db, commit_id)
    if not commit or commit.project_id != project_id:
        raise HTTPException(status_code=404, detail="Commit not found")

    return {
        "id": commit.id,
        "sha": commit.sha,
        "author": commit.author,
        "message": commit.message,
        "branch": commit.branch,
        "diff_files": commit.diff_files,
        "received_at": str(commit.received_at),
        "committed_at": str(commit.committed_at) if commit.committed_at else None,
        "repo_name": commit.repository.repo_name if commit.repository else "",
        "impact_reports": [
            {
                "id": r.id,
                "changed_file": r.changed_file,
                "impact_level": r.impact_level,
                "summary": r.summary,
                "affected_items": r.affected_items,
                "recommendations": r.recommendations,
                "blast_zone_size": r.blast_zone_size,
            }
            for r in commit.impact_reports
        ],
    }


@router.get("/api/v1/projects/{project_id}/commits/{commit_id}/impact")
def get_commit_impact(project_id: str, commit_id: str, db: Session = Depends(get_db)):
    reports = crud.get_impact_reports(db, commit_id)
    if not reports:
        raise HTTPException(status_code=404, detail="No impact reports found for this commit")
    return [
        {
            "id": r.id,
            "changed_file": r.changed_file,
            "impact_level": r.impact_level,
            "summary": r.summary,
            "affected_items": r.affected_items,
            "recommendations": r.recommendations,
            "blast_zone_size": r.blast_zone_size,
            "created_at": str(r.created_at),
        }
        for r in reports
    ]


# ── Manual Sync ───────────────────────────────────────────────────────────

@router.post("/api/v1/projects/{project_id}/commits/sync")
def sync_commits(project_id: str, db: Session = Depends(get_db)):
    """
    Manually fetch recent commits from GitHub API for all repos in the project.
    Triggers impact analysis for any new commits found.
    """
    import requests
    
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    results = []
    
    # Headers for GitHub API
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    for repo in project.repositories:
        try:
            # e.g. https://github.com/owner/repo.git -> https://api.github.com/repos/owner/repo/commits
            clean_url = repo.repo_url.rstrip("/")
            if clean_url.endswith(".git"):
                clean_url = clean_url[:-4]
            
            parts = clean_url.split("/")
            if len(parts) < 2: 
                print(f"⚠️  Invalid repo URL format: {repo.repo_url}")
                continue
                
            owner = parts[-2]
            name = parts[-1]
            api_url = f"https://api.github.com/repos/{owner}/{name}/commits"
            
            print(f"🔄 Syncing {repo.repo_name} from {api_url}...")

            # Fetch last 10 commits
            resp = requests.get(api_url, headers=headers, params={"per_page": 10})
            if resp.status_code != 200:
                print(f"❌ Sync failed for {repo.repo_name}: {resp.status_code} - {resp.text}")
                continue
            
            commits_data = resp.json()
            
            for c_data in commits_data:
                sha = c_data["sha"]
                
                # Skip if exists
                if crud.get_commit_by_sha(db, sha):
                    continue

                # Get commit details for diffs
                detail_resp = requests.get(c_data["url"], headers=headers)
                if detail_resp.status_code != 200: continue
                full_commit = detail_resp.json()

                author = full_commit["commit"]["author"]["name"]
                message = full_commit["commit"]["message"]
                date_str = full_commit["commit"]["author"]["date"]
                committed_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

                # Parse files
                diff_files = []
                for f in full_commit.get("files", []):
                    diff_files.append({
                        "filename": f["filename"],
                        "status": f["status"], # added, modified, removed
                        "patch": f.get("patch", "")
                    })

                # Store commit
                db_commit = crud.create_commit(
                    db, project_id, repo.id,
                    sha=sha, author=author, message=message,
                    branch="main", # limitation: API doesn't easily give branch for commit
                    diff_files=diff_files,
                    committed_at=committed_at
                )

                # Process Impact & Update Graph
                _process_commit_impact(db, project_id, db_commit, diff_files)
                
                results.append(sha)

        except Exception as e:
            print(f"❌ Error syncing {repo.repo_name}: {e}")

    return {"status": "synced", "new_commits": len(results), "shas": results}


def _process_commit_impact(db, project_id, commit, diff_files):
    """
    Helper to run impact analysis. 
    1. Re-parses changed files to update the graph.
    2. Runs impact analysis.
    """
    from src.discovery.crawler import CodeDiscovery
    from src.api.v1.repositories import WORKER_URLS
    import os
    import shutil
    from pathlib import Path

    try:
        impact_engine = ImpactEngine(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password, project_id
        )
        groq_analyzer = GroqAnalyzer(settings.groq_api_key)
        
        # 1. Update Graph for Changed Files
        # We need to pull the file content. Since we don't have the repo cloned, 
        # this is tricky. For now, we'll assume the graph is mostly static or 
        # we rely on the previous state. 
        # TODO: Ideally, we'd fetch the raw file content from GitHub and parse that.
        # For this iteration, we will skip re-parsing to avoid complex temp file management 
        # and just rely on existing graph for impact analysis.
        
        # 2. Run Analysis
        for diff_file in diff_files:
            filename = diff_file["filename"]
            
            # Simple affected node lookup
            affected = impact_engine.find_affected_nodes(filename)
            
            report = groq_analyzer.analyze_impact(
                filename, affected,
                changes=f"Commit: {commit.message}",
                code_context="",
            )

            crud.create_impact_report(
                db, commit.id, project_id,
                changed_file=filename,
                impact_level=report.get("impact_level", "none"),
                summary=report.get("summary", ""),
                affected_items=report.get("affected_items", []),
                recommendations=report.get("recommendations", []),
                blast_zone_size=report.get("blast_zone_size", len(affected)),
            )

        impact_engine.close()
    except Exception as e:
        print(f"⚠️  Impact analysis error: {e}")
