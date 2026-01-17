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
            target.name as dependency_name
        LIMIT 100
        """
        
        with self.driver.session() as session:
            result = session.run(query, filename=filename, project_id=self.project_id)
            impacts = []
            for record in result:
                impacts.append({
                    "file": record["affected_file"],
                    "symbol": record["affected_symbol"],
                    "depends_on": record["dependency_name"]
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
