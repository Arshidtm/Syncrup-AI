"""Simple Neo4j connection test"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

try:
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    
    with driver.session() as session:
        # Count total nodes
        result = session.run("MATCH (n) RETURN count(n) as total")
        total = result.single()["total"]
        print(f"Total nodes in database: {total}")
        
        # Check for api_client file
        result = session.run("""
            MATCH (f:File) 
            WHERE f.name CONTAINS 'api_client'
            RETURN f.name as name, f.project_id as pid
        """)
        files = list(result)
        print(f"\nFiles containing 'api_client': {len(files)}")
        for f in files:
            print(f"  - {f['name']} (project: {f['pid']})")
            
            # Check symbols in this file
            result2 = session.run("""
                MATCH (file:File {name: $name, project_id: $pid})-[:CONTAINS]->(s)
                RETURN s.name as symbol, labels(s) as labels
                LIMIT 10
            """, name=f['name'], pid=f['pid'])
            symbols = list(result2)
            print(f"    Symbols ({len(symbols)}):")
            for s in symbols:
                print(f"      - {s['symbol']} ({s['labels']})")
    
    driver.close()
    print("\n✓ Connection successful")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
