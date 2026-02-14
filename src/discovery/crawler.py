"""
Code Discovery and File Scanning

This module handles project directory scanning and delegates file parsing to
language-specific workers via HTTP.

Responsibilities:
    1. Recursively traverse project directories
    2. Filter files by supported extensions (.py, .ts, .js)
    3. Respect .gitignore patterns from the project root
    4. Exclude common non-essential directories even without .gitignore
    5. Send files to appropriate language workers
    6. Aggregate parsing results

Worker Delegation:
    Files are routed to workers based on extension:
    - .py → Python worker (port 8001)
    - .ts, .js → TypeScript worker (port 8002)

Exclusion Strategy:
    Two-layer filtering ensures junk files are never processed:

    Layer 1 - Hardcoded exclusions (always applied):
        Directories: node_modules, __pycache__, .git, venv, dist, build, etc.
        Files: *.pyc, *.pyo, *.so, package-lock.json, yarn.lock, etc.

    Layer 2 - .gitignore patterns (applied when .gitignore exists):
        Parsed using the `pathspec` library with gitignore-style matching.
        This catches project-specific exclusions (e.g. /output/, /logs/).

Worker Communication:
    Workers are HTTP services that accept:
    - code: File contents as string
    - filename: Relative path from project root

    Workers return:
    - definitions: Functions and classes
    - calls: Function invocations
    - imports: Import statements

Error Handling:
    - Continues on individual file failures
    - Logs errors for debugging
    - Returns None for failed files

Example:
    discovery = CodeDiscovery("/path/to/project", {
        "python": "http://localhost:8001",
        "typescript": "http://localhost:8002"
    })
    results = discovery.discover_and_parse()
    # Returns: [{"filename": "...", "data": {...}}, ...]
"""
import os

import requests
import json
from pathlib import Path

try:
    import pathspec
except ImportError:
    pathspec = None

# ---------------------------------------------------------------------------
# Hardcoded exclusion lists — these are ALWAYS filtered out regardless of
# whether a .gitignore exists. Covers the most common cases where a user
# forgot to set up .gitignore or committed junk into the repo.
# ---------------------------------------------------------------------------

EXCLUDED_DIRS = {
    # Version control
    ".git", ".svn", ".hg",
    # Python
    "__pycache__", ".mypy_cache", ".pytest_cache", ".tox",
    "venv", "env", ".env", ".venv", "ai_env", "syncrup_env",
    "*.egg-info",
    # JavaScript / Node
    "node_modules", "bower_components",
    # Build & dist artifacts
    "dist", "build", "out", "_build",
    # Framework caches
    ".next", ".nuxt", ".cache", ".parcel-cache", ".turbo",
    # IDE / editor
    ".vscode", ".idea", ".fleet",
    # Coverage & testing
    "coverage", "htmlcov", ".nyc_output",
    # Misc
    ".terraform", ".gradle", "target", "vendor",
    ".docker", ".devcontainer",
}

EXCLUDED_FILE_EXTENSIONS = {
    # Compiled Python
    ".pyc", ".pyo", ".pyd",
    # Shared libraries
    ".so", ".dll", ".dylib",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".rar", ".7z",
    # Images (not source code)
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".bmp", ".webp",
    # Fonts
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Data / binary
    ".db", ".sqlite", ".sqlite3", ".pkl", ".h5", ".hdf5",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    # Misc
    ".min.js", ".map", ".lock",
}

EXCLUDED_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".gitkeep",
    ".npmrc",
    ".yarnrc",
}


class CodeDiscovery:
    def __init__(self, project_root: str, worker_urls: dict):
        self.project_root = Path(project_root)
        self.worker_urls = worker_urls
        self._gitignore_spec = self._load_gitignore()

    # ------------------------------------------------------------------
    # .gitignore loading
    # ------------------------------------------------------------------
    def _load_gitignore(self):
        """Parse .gitignore from the project root (if it exists)."""
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.is_file() and pathspec is not None:
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    return pathspec.PathSpec.from_lines("gitwildmatch", f)
            except Exception as e:
                print(f"⚠️  Could not parse .gitignore: {e}")
        return None

    # ------------------------------------------------------------------
    # Exclusion logic
    # ------------------------------------------------------------------
    def _should_exclude(self, path: Path) -> bool:
        """Return True if the path should be skipped."""
        # 1. Check if ANY directory component matches the hardcoded list
        for part in path.relative_to(self.project_root).parts:
            if part in EXCLUDED_DIRS:
                return True

        # 2. Check file name against the hardcoded excluded-files set
        if path.name in EXCLUDED_FILES:
            return True

        # 3. Check file extension against excluded extensions
        if path.suffix.lower() in EXCLUDED_FILE_EXTENSIONS:
            return True

        # 4. Check against .gitignore patterns (if loaded)
        if self._gitignore_spec is not None:
            rel = str(path.relative_to(self.project_root)).replace("\\", "/")
            if self._gitignore_spec.match_file(rel):
                return True

        return False

    # ------------------------------------------------------------------
    # Main discovery
    # ------------------------------------------------------------------
    def discover_and_parse(self):
        """Scans the project directory and sends files to workers."""
        results = []

        # Supported extensions and their worker keys
        ext_to_worker = {
            ".py": "python",
            ".ts": "typescript",
            ".js": "typescript"
        }

        skipped_count = 0

        for path in self.project_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in ext_to_worker:
                continue

            # Apply exclusion filters
            if self._should_exclude(path):
                skipped_count += 1
                continue

            worker_key = ext_to_worker[path.suffix]
            if worker_key in self.worker_urls:
                print(f"Parsing {path} using {worker_key} worker...")
                file_results = self._send_to_worker(path, self.worker_urls[worker_key])
                if file_results:
                    results.append(file_results)

        if skipped_count:
            print(f"⏭️  Skipped {skipped_count} file(s) matching exclusion rules.")

        return results

    def _send_to_worker(self, file_path: Path, worker_url: str):
        try:
            # Ensure file_path is a Path object
            if isinstance(file_path, str):
                file_path = Path(file_path)

            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            response = requests.post(
                f"{worker_url}/parse",
                json={
                    "code": code,
                    "filename": str(file_path.relative_to(self.project_root))
                }
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error from worker for {file_path}: {response.text}")
        except Exception as e:
            print(f"Failed to process {file_path}: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    root = "d:/Arshid/practice/Nexus_ai_engine"
    workers = {
        "python": "http://localhost:8001"
    }
    discovery = CodeDiscovery(root, workers)
    # results = discovery.discover_and_parse()
    # print(json.dumps(results, indent=2))
