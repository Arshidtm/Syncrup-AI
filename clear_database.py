"""
Clear all data from the Neo4j graph database.
WARNING: This will delete ALL nodes and relationships in the database!
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def clear_database():
    """Delete all nodes and relationships from the database"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # Count nodes before deletion
            count_result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = count_result.single()["count"]
            
            print(f"Found {node_count} nodes in the database")
            
            if node_count == 0:
                print("Database is already empty!")
                return
            
            # Confirm deletion
            confirm = input(f"\n⚠️  WARNING: This will DELETE ALL {node_count} nodes and their relationships!\nType 'DELETE' to confirm: ")
            
            if confirm != "DELETE":
                print("❌ Cancelled. No data was deleted.")
                return
            
            # Delete all nodes and relationships
            print("\n🗑️  Deleting all data...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # Verify deletion
            verify_result = session.run("MATCH (n) RETURN count(n) as count")
            remaining = verify_result.single()["count"]
            
            if remaining == 0:
                print(f"✅ Successfully deleted all {node_count} nodes and their relationships!")
                print("Database is now empty.")
            else:
                print(f"⚠️  Warning: {remaining} nodes still remain in the database")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        driver.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Neo4j Database Cleanup Tool")
    print("=" * 60)
    print(f"\nConnecting to: {NEO4J_URI}")
    print(f"User: {NEO4J_USER}\n")
    
    clear_database()
