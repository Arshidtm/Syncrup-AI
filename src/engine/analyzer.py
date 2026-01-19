"""
Impact Analysis Engine

This module implements the core impact analysis algorithm that identifies code affected
by changes to a specific file. It uses Neo4j graph traversal to find all downstream
dependencies at the symbol level (functions and classes).

Algorithm:
    1. Find all symbols (functions/classes) defined in the changed file
    2. Traverse DEPENDS_ON_SYMBOL relationships to find dependent symbols
    3. Collect affected files, symbols, line numbers, and dependency metadata
    4. Return structured impact data for AI analysis

Key Features:
    - Symbol-level precision (not just file-level)
    - Handles function renames (queries by filename property)
    - Returns line numbers for precise navigation
    - Supports multi-project isolation via project_id
    - Limits results to prevent runaway queries (100 max)

Graph Traversal Strategy:
    The query finds symbols by their filename property rather than following
    CONTAINS relationships. This ensures renamed or deleted symbols are still
    found if they have the filename property set.

Output Format:
    Returns a list of dictionaries with:
    - file: Path to affected file
    - symbol: Name of affected symbol
    - symbol_type: "function" or "class"
    - line_number: Line where symbol is defined
    - depends_on: Name of symbol in changed file
    - depends_on_type: Type of dependency
    - depends_on_line: Line number of dependency

Example:
    engine = ImpactEngine(uri, user, password, "my-project")
    affected = engine.find_affected_nodes("src/auth/login.py")
    # Returns: [{"file": "src/api/routes.py", "symbol": "login_endpoint", ...}]
    engine.close()
"""
from neo4j import GraphDatabase


class ImpactEngine:
    def __init__(self, uri, user, password, project_id="default"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.project_id = project_id

    def close(self):
        self.driver.close()

    def find_affected_nodes(self, filename: str):
        """
        Finds dependencies at the FILE level, not symbol level.
        This works even after function renames because we query by filename property.
        Returns detailed information including line numbers and symbol types.
        """
        query = """
        // Find ALL Functions/Classes that belong to this file (by filename property)
        // This includes renamed/deleted ones that no longer have [:CONTAINS] from File
        MATCH (target {filename: $filename, project_id: $project_id})
        WHERE target:Function OR target:Class
        
        // Find who depends on these targets
        MATCH (caller {project_id: $project_id})-[:DEPENDS_ON_SYMBOL]->(target)
        
        // Get the file containing the caller
        MATCH (caller_file:File {project_id: $project_id})-[:CONTAINS]->(caller)
        
        RETURN DISTINCT 
            caller_file.name as affected_file, 
            caller.name as affected_symbol,
            caller.line as affected_line,
            labels(caller) as caller_labels,
            target.name as dependency_name,
            target.line as dependency_line,
            labels(target) as target_labels
        LIMIT 100
        """
        
        with self.driver.session() as session:
            result = session.run(query, filename=filename, project_id=self.project_id)
            impacts = []
            for record in result:
                # Determine symbol type from labels
                caller_labels = record["caller_labels"]
                target_labels = record["target_labels"]
                
                caller_type = "function" if "Function" in caller_labels else "class" if "Class" in caller_labels else "unknown"
                target_type = "function" if "Function" in target_labels else "class" if "Class" in target_labels else "unknown"
                
                impacts.append({
                    "file": record["affected_file"],
                    "symbol": record["affected_symbol"],
                    "symbol_type": caller_type,
                    "line_number": record["affected_line"],
                    "depends_on": record["dependency_name"],
                    "depends_on_type": target_type,
                    "depends_on_line": record["dependency_line"]
                })
            return impacts

    def generate_impact_report(self, filename: str, affected_nodes: list):
        if not affected_nodes:
            return f"No downstream symbol-level impact detected for changes in {filename}."
        
        report = f"Detailed Symbol-Level Impact Report for {filename}:\n"
        report += "========================================================\n"
        for node in affected_nodes:
            report += f"- [File: {node['file']}] -> [Symbol: {node['symbol']}] depends on '{node['depends_on']}'\n"
        
        report += "\nRecommendation: Check the logic in these specific functions for regressions."
        return report
