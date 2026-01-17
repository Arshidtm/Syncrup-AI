"""Check dependencies for api_client.ts"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

filename = "frontend_app\\services\\api_client.ts"
project_id = "sample2"

with driver.session() as session:
    print(f"Checking dependencies for: {filename}")
    print(f"Project ID: {project_id}\n")
    
    # Check what symbols are in this file
    print("1. SYMBOLS IN THIS FILE:")
    result = session.run("""
        MATCH (f:File {name: $filename, project_id: $project_id})-[:CONTAINS]->(s)
        RETURN s.name as symbol, labels(s) as labels, s.line as line, s.filename as sym_filename
    """, filename=filename, project_id=project_id)
    symbols = list(result)
    for s in symbols:
        print(f"   - {s['symbol']} ({s['labels']}) at line {s['line']}")
        print(f"     filename property: {s['sym_filename']}")
    
    # Check if any symbols have the filename property set correctly
    print("\n2. CHECKING FILENAME PROPERTY ON SYMBOLS:")
    result = session.run("""
        MATCH (s)
        WHERE s.filename = $filename AND s.project_id = $project_id
        RETURN s.name as symbol, labels(s) as labels
    """, filename=filename, project_id=project_id)
    symbols_with_filename = list(result)
    print(f"   Symbols with filename='{filename}': {len(symbols_with_filename)}")
    for s in symbols_with_filename:
        print(f"   - {s['symbol']} ({s['labels']})")
    
    # Check for incoming dependencies (who depends on this file's symbols)
    print("\n3. INCOMING DEPENDENCIES (who calls these symbols):")
    result = session.run("""
        MATCH (target {filename: $filename, project_id: $project_id})
        WHERE target:Function OR target:Class
        MATCH (caller {project_id: $project_id})-[:DEPENDS_ON_SYMBOL]->(target)
        MATCH (caller_file:File {project_id: $project_id})-[:CONTAINS]->(caller)
        RETURN caller_file.name as caller_file, caller.name as caller_symbol, target.name as target_symbol
    """, filename=filename, project_id=project_id)
    incoming = list(result)
    print(f"   Found {len(incoming)} incoming dependencies:")
    for dep in incoming:
        print(f"   - {dep['caller_file']}::{dep['caller_symbol']} -> {dep['target_symbol']}")
    
    # Check ALL dependencies in the project
    print("\n4. ALL DEPENDENCIES IN PROJECT 'sample2':")
    result = session.run("""
        MATCH (caller {project_id: 'sample2'})-[r:DEPENDS_ON_SYMBOL]->(target {project_id: 'sample2'})
        RETURN caller.name as caller, target.name as target, caller.filename as caller_file, target.filename as target_file
        LIMIT 20
    """)
    all_deps = list(result)
    print(f"   Total dependencies in project: {len(all_deps)}")
    for dep in all_deps:
        print(f"   - {dep['caller_file']}::{dep['caller']} -> {dep['target_file']}::{dep['target']}")
    
    # Check all files in the project
    print("\n5. ALL FILES IN PROJECT 'sample2':")
    result = session.run("""
        MATCH (f:File {project_id: 'sample2'})
        RETURN f.name as filename
    """)
    files = list(result)
    print(f"   Total files: {len(files)}")
    for f in files:
        print(f"   - {f['filename']}")

driver.close()
