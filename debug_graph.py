"""
Debug script to check what's in the Neo4j graph database
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 80)
print("NEO4J GRAPH DATABASE INSPECTION")
print("=" * 80)

with driver.session() as session:
    # Check all projects
    print("\n1. PROJECTS IN DATABASE:")
    result = session.run("MATCH (n) RETURN DISTINCT n.project_id as project_id")
    projects = [record["project_id"] for record in result if record["project_id"]]
    print(f"   Found {len(projects)} project(s): {projects}")
    
    # Check all files
    print("\n2. FILES IN DATABASE:")
    result = session.run("MATCH (f:File) RETURN f.name as filename, f.project_id as project_id LIMIT 20")
    files = list(result)
    print(f"   Total files (showing first 20):")
    for record in files:
        print(f"   - [{record['project_id']}] {record['filename']}")
    
    # Check TypeScript files specifically
    print("\n3. TYPESCRIPT FILES:")
    result = session.run("""
        MATCH (f:File) 
        WHERE f.name ENDS WITH '.ts' OR f.name ENDS WITH '.tsx'
        RETURN f.name as filename, f.project_id as project_id
        LIMIT 20
    """)
    ts_files = list(result)
    print(f"   Found {len(ts_files)} TypeScript file(s):")
    for record in ts_files:
        print(f"   - [{record['project_id']}] {record['filename']}")
    
    # Check for the specific file
    print("\n4. CHECKING FOR api_client.ts:")
    result = session.run("""
        MATCH (f:File) 
        WHERE f.name CONTAINS 'api_client'
        RETURN f.name as filename, f.project_id as project_id
    """)
    api_files = list(result)
    if api_files:
        for record in api_files:
            print(f"   ✓ Found: [{record['project_id']}] {record['filename']}")
            
            # Check what functions/classes are in this file
            result2 = session.run("""
                MATCH (f:File {name: $filename, project_id: $project_id})-[:CONTAINS]->(node)
                RETURN node.name as symbol, labels(node) as labels, node.line as line
            """, filename=record['filename'], project_id=record['project_id'])
            symbols = list(result2)
            print(f"   Symbols in file ({len(symbols)}):")
            for sym in symbols:
                symbol_type = "Function" if "Function" in sym["labels"] else "Class" if "Class" in sym["labels"] else "Unknown"
                print(f"     - {sym['symbol']} ({symbol_type}) at line {sym['line']}")
            
            # Check dependencies
            result3 = session.run("""
                MATCH (target {filename: $filename, project_id: $project_id})
                WHERE target:Function OR target:Class
                MATCH (caller)-[:DEPENDS_ON_SYMBOL]->(target)
                MATCH (caller_file:File)-[:CONTAINS]->(caller)
                RETURN caller_file.name as caller_file, caller.name as caller_symbol
            """, filename=record['filename'], project_id=record['project_id'])
            deps = list(result3)
            print(f"   Dependencies ({len(deps)}):")
            for dep in deps:
                print(f"     - {dep['caller_file']} -> {dep['caller_symbol']}")
    else:
        print("   ✗ File not found in database")
    
    # Check total node count
    print("\n5. DATABASE STATISTICS:")
    result = session.run("MATCH (n) RETURN count(n) as total")
    total = result.single()["total"]
    print(f"   Total nodes: {total}")
    
    result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
    total_rels = result.single()["total"]
    print(f"   Total relationships: {total_rels}")

driver.close()
print("\n" + "=" * 80)
