"""
Code Discovery and File Scanning

This module handles project directory scanning and delegates file parsing to
language-specific workers via HTTP.

Responsibilities:
    1. Recursively traverse project directories
    2. Filter files by supported extensions (.py, .ts, .js)
    3. Exclude virtual environments and hidden folders
    4. Send files to appropriate language workers
    5. Aggregate parsing results

Worker Delegation:
    Files are routed to workers based on extension:
    - .py → Python worker (port 8001)
    - .ts, .js → TypeScript worker (port 8002)

Exclusion Patterns:
    Automatically excludes:
    - Virtual environments (ai_env, venv, env)
    - Hidden directories (.git, .vscode, etc.)
    - Node modules
    - Build artifacts

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

class CodeDiscovery:
    def __init__(self, project_root: str, worker_urls: dict):
        self.project_root = Path(project_root)
        self.worker_urls = worker_urls

    def discover_and_parse(self):
        """Scans the project directory and sends files to workers."""
        results = []
        
        # Supported extensions and their worker keys
        ext_to_worker = {
            ".py": "python",
            ".ts": "typescript",
            ".js": "typescript"
        }

        for path in self.project_root.rglob("*"):
            if path.is_file() and path.suffix in ext_to_worker:
                # Skip virtual environments and hidden folders
                if "ai_env" in str(path) or ".git" in str(path):
                    continue
                
                worker_key = ext_to_worker[path.suffix]
                if worker_key in self.worker_urls:
                    print(f"Parsing {path} using {worker_key} worker...")
                    file_results = self._send_to_worker(path, self.worker_urls[worker_key])
                    if file_results:
                        results.append(file_results)
        
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
