import sys
import os
import json
from src.discovery.crawler import CodeDiscovery
from src.graph.manager import GraphManager
from src.engine.analyzer import ImpactEngine
from src.engine.groq_analyzer import GroqAnalyzer

# Import new utilities
from src.config.settings import settings
from src.utils.logger import logger

# Configuration from settings
WORKER_URLS = {
    "python": settings.python_worker_url,
    "typescript": settings.typescript_worker_url
}

NEO4J_URI = settings.neo4j_uri
NEO4J_USER = settings.neo4j_user
NEO4J_PASSWORD = settings.neo4j_password
GROQ_API_KEY = settings.groq_api_key

def handle_file_change(filename: str, changes: str = ""):
    """
    Activated when a user pushes a change to a file.
    1. Parse the changed file.
    2. Update Neo4j.
    3. Run Impact Analysis (Phase 3).
    """
    logger.info(f"Checking impact for: {filename}")
    if changes:
        logger.info(f"Change Context: {changes}")
    
    # 1. Initialize logic (use "default" project for backward compatibility)
    root = os.getcwd()
    project_id = "default"  # For legacy checker_tool usage
    discovery = CodeDiscovery(root, WORKER_URLS)
    graph = GraphManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, project_id)
    impact_engine = ImpactEngine(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, project_id)
    groq_analyzer = GroqAnalyzer(GROQ_API_KEY)
    
    # 2. Re-parse the specific file
    file_path = os.path.join(root, filename)
    if not os.path.exists(file_path):
        logger.error(f"File {filename} not found.")
        return

    # Read the code context to help the LLM see what actually changed
    code_context = ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code_context = f.read()
    except Exception as e:
        logger.warning(f"Could not read code context: {e}")

    logger.info("Step 1: Parsing changed file...")
    # Convert to relative path from project root
    if os.path.isabs(filename):
        filename = os.path.relpath(filename, root)
    
    # Normalize path separators to match the graph (backslashes on Windows)
    filename = filename.replace('/', os.sep)
    clean_filename = filename.replace(os.sep, '/') # Ensure graph always uses forward slashes
    
    # Determine worker
    ext = os.path.splitext(filename)[1]
    worker_key = "python" if ext == ".py" else "typescript" if ext == ".ts" else None
    
    if not worker_key or worker_key not in WORKER_URLS:
        logger.error(f"No worker configured for extension {ext}")
        return

    analysis = discovery._send_to_worker(file_path, WORKER_URLS[worker_key])
    
    if analysis:
        # 3. Update Graph
        logger.info("Step 2: Updating Knowledge Graph...")
        analysis["filename"] = filename  # Use OS-normalized path
        graph.update_file_structure(analysis)
        graph.link_calls_to_definitions()
        
        # 4. Trigger Impact Analysis
        logger.info("Step 3: Calculating Blast Zone traversal...")
        affected = impact_engine.find_affected_nodes(filename)  # Use OS-normalized path
        
        logger.info("Step 4: Generating LLM Insight using Groq...")
        report = groq_analyzer.analyze_impact(clean_filename, affected, changes=changes, code_context=code_context)
        
        # Display the structured JSON report
        print("\n" + "=== IMPACT REPORT (AI GENERATED) ===")
        if isinstance(report, dict):
            print(json.dumps(report, indent=2))
        else:
            print(report)
        print("====================================")
    
    graph.close()
    impact_engine.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        changed_file = sys.argv[1]
        handle_file_change(changed_file)
    else:
        logger.error("Usage: python src/main.py <changed_filename>")
