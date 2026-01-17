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
