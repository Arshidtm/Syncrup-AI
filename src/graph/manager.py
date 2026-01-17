from neo4j import GraphDatabase

class GraphManager:
    def __init__(self, uri, user, password, project_id="default"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.project_id = project_id  # Store project_id for all operations

    def close(self):
        self.driver.close()

    def update_file_structure(self, analysis_result):
        """
        Updates the Neo4j graph with the results from the ingestion pipeline.
        analysis_result format:
        {
            "filename": "path/to/file.py",
            "data": {
                "definitions": [{"type": "function", "name": "foo", "line": 10}, ...],
                "calls": [{"name": "bar", "line": 12}, ...],
                "imports": [...]
            }
        }
        """
        filename = analysis_result["filename"]
        data = analysis_result["data"]
        
        with self.driver.session() as session:
            session.execute_write(self._create_structure, filename, data, self.project_id)

    @staticmethod
    def _create_structure(tx, filename, data, project_id):
        # Create File Node
        tx.run("MERGE (f:File {name: $filename, project_id: $project_id})", filename=filename, project_id=project_id)
        
        # Create Definition Nodes and CONTAINS relationship
        for definition in data["definitions"]:
            label = "Function" if definition["type"] == "function" else "Class"
            tx.run(f"""
                MERGE (d:{label} {{name: $name, filename: $filename, project_id: $project_id}})
                WITH d
                MATCH (f:File {{name: $filename, project_id: $project_id}})
                MERGE (f)-[:CONTAINS]->(d)
                """, name=definition["name"], filename=filename, project_id=project_id)

        # Create Calls and link to their PARENT Definition (Function/Class)
        for call in data["calls"]:
            parent = call.get("parent")
            
            # Step 1: Create Call node first (always succeeds)
            tx.run("""
                MERGE (c:Call {name: $name, line: $line, filename: $filename, project_id: $project_id})
                SET c.parent = $parent
                """, name=call["name"], line=call["line"], filename=filename, parent=parent, project_id=project_id)
            
            # Step 2: Link to File (separate query to avoid transaction failures)
            tx.run("""
                MATCH (f:File {name: $filename, project_id: $project_id})
                MATCH (c:Call {name: $name, line: $line, filename: $filename, project_id: $project_id})
                MERGE (f)-[:PERFORMS_CALL]->(c)
                """, name=call["name"], line=call["line"], filename=filename, project_id=project_id)
            
            # Step 3: Link to parent symbol if it exists
            if parent:
                tx.run("""
                    MATCH (c:Call {name: $name, line: $line, filename: $filename, project_id: $project_id})
                    OPTIONAL MATCH (p {name: $parent_name, filename: $filename, project_id: $project_id})
                    WHERE p:Function OR p:Class
                    FOREACH (ignoreMe IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (p)-[:CALLS_OUT]->(c)
                    )
                    """, name=call["name"], line=call["line"], filename=filename, parent_name=parent, project_id=project_id)

    def link_calls_to_definitions(self):
        """
        Post-processing step to resolve calls to their actual definitions.
        Only links calls within the same project_id.
        """
        with self.driver.session() as session:
            session.execute_write(self._resolve_calls, self.project_id)

    @staticmethod
    def _resolve_calls(tx, project_id):
        # 1. Link calls to definitions by name (Internal linking) - scoped to project
        tx.run("""
            MATCH (c:Call {project_id: $project_id}), (f:Function {project_id: $project_id})
            WHERE c.name = f.name
            MERGE (c)-[:TARGETS]->(f)
            """, project_id=project_id)
        
        
        # 2. Generic API Contract Stitching (Cross-Language)
        # Link HTTP method calls (post, get, put, delete, fetch) to backend functions
        # This is a heuristic - matches by finding functions that might be API endpoints
        tx.run("""
            MATCH (c:Call {project_id: $project_id})
            WHERE c.name IN ['post', 'get', 'put', 'delete', 'fetch', 'request']
            
            // Try to find backend functions that might be endpoints
            // Look for functions with common API patterns like 'create_', 'get_', 'update_', 'delete_'
            MATCH (f:Function {project_id: $project_id})
            WHERE f.name STARTS WITH 'create_' 
               OR f.name STARTS WITH 'get_' 
               OR f.name STARTS WITH 'update_'
               OR f.name STARTS WITH 'delete_'
               OR f.name STARTS WITH 'api_'
               OR f.name CONTAINS 'endpoint'
            
            // Create cross-language link
            MERGE (c)-[:CALLS_ENDPOINT]->(f)
            MERGE (c)-[:TARGETS]->(f)
            """, project_id=project_id)
        
        # 3. Create DEPENDS_ON_SYMBOL for traversal (The critical relationship for impact analysis!)
        tx.run("""
            MATCH (caller {project_id: $project_id})-[:CALLS_OUT]->(c:Call {project_id: $project_id})-[:TARGETS]->(target:Function {project_id: $project_id})
            MERGE (caller)-[:DEPENDS_ON_SYMBOL]->(target)
            """, project_id=project_id)
        
    def get_graph_data(self):
        """
        Retrieves the entire graph as a JSON-serializable list of nodes and edges.
        Filters by project_id to only return data for this project.
        """
        nodes = []
        edges = []
        with self.driver.session() as session:
            # Get nodes - filtered by project_id
            nodes_result = session.run("""
                MATCH (n {project_id: $project_id})
                WHERE n:File OR n:Function OR n:Class OR n:Call
                RETURN elementId(n) as id, labels(n)[0] as label, n.name as name
                """, project_id=self.project_id)
            
            for record in nodes_result:
                nodes.append({
                    "id": record["id"],
                    "label": record["label"] + ": " + record["name"]
                })
            
            # Get edges - filtered by project_id
            edges_result = session.run("""
                MATCH (n {project_id: $project_id})-[r]->(m {project_id: $project_id})
                RETURN elementId(n) as source, elementId(m) as target, type(r) as type
                """, project_id=self.project_id)
            
            for record in edges_result:
                edges.append({
                    "from": record["source"],
                    "to": record["target"],
                    "label": record["type"]
                })
        
        return {"nodes": nodes, "edges": edges}
