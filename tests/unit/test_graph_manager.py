"""
Unit tests for GraphManager.

Tests Neo4j graph operations including:
- Node creation
- Relationship establishment
- Multi-project isolation
- Graph data retrieval
"""
import pytest
from src.graph.manager import GraphManager
from src.config.settings import settings


@pytest.fixture
def graph_manager():
    """Fixture to create a GraphManager instance for testing"""
    manager = GraphManager(
        settings.neo4j_uri,
        settings.neo4j_user,
        settings.neo4j_password,
        "test-project"
    )
    yield manager
    # Cleanup: Clear test data after each test
    with manager.driver.session() as session:
        session.run("MATCH (n {project_id: 'test-project'}) DETACH DELETE n")
    manager.close()


class TestGraphManager:
    """Test suite for GraphManager"""
    
    def test_create_file_node(self, graph_manager):
        """Test creating a File node"""
        analysis = {
            "filename": "test.py",
            "data": {
                "definitions": [],
                "calls": [],
                "imports": []
            }
        }
        
        graph_manager.update_file_structure(analysis)
        
        # Verify file node was created
        with graph_manager.driver.session() as session:
            result = session.run(
                "MATCH (f:File {name: $name, project_id: $project_id}) RETURN f",
                name="test.py",
                project_id="test-project"
            )
            assert result.single() is not None
    
    def test_create_function_node(self, graph_manager):
        """Test creating a Function node with line number"""
        analysis = {
            "filename": "test.py",
            "data": {
                "definitions": [
                    {"type": "function", "name": "test_func", "line": 10}
                ],
                "calls": [],
                "imports": []
            }
        }
        
        graph_manager.update_file_structure(analysis)
        
        # Verify function node with line number
        with graph_manager.driver.session() as session:
            result = session.run(
                "MATCH (f:Function {name: $name, project_id: $project_id}) RETURN f.line as line",
                name="test_func",
                project_id="test-project"
            )
            record = result.single()
            assert record is not None
            assert record["line"] == 10
    
    def test_contains_relationship(self, graph_manager):
        """Test CONTAINS relationship between File and Function"""
        analysis = {
            "filename": "test.py",
            "data": {
                "definitions": [
                    {"type": "function", "name": "my_function", "line": 5}
                ],
                "calls": [],
                "imports": []
            }
        }
        
        graph_manager.update_file_structure(analysis)
        
        # Verify CONTAINS relationship
        with graph_manager.driver.session() as session:
            result = session.run("""
                MATCH (f:File {name: $filename, project_id: $project_id})
                      -[:CONTAINS]->(func:Function {name: $func_name})
                RETURN func
            """, filename="test.py", func_name="my_function", project_id="test-project")
            assert result.single() is not None
    
    def test_link_calls_to_definitions(self, graph_manager):
        """Test linking calls to their definitions"""
        # Create a function definition
        analysis1 = {
            "filename": "utils.py",
            "data": {
                "definitions": [
                    {"type": "function", "name": "helper", "line": 1}
                ],
                "calls": [],
                "imports": []
            }
        }
        
        # Create a call to that function
        analysis2 = {
            "filename": "main.py",
            "data": {
                "definitions": [
                    {"type": "function", "name": "main", "line": 1}
                ],
                "calls": [
                    {"name": "helper", "parent": "main", "line": 2}
                ],
                "imports": []
            }
        }
        
        graph_manager.update_file_structure(analysis1)
        graph_manager.update_file_structure(analysis2)
        graph_manager.link_calls_to_definitions()
        
        # Verify TARGETS relationship
        with graph_manager.driver.session() as session:
            result = session.run("""
                MATCH (c:Call {name: 'helper', project_id: $project_id})
                      -[:TARGETS]->(f:Function {name: 'helper'})
                RETURN f
            """, project_id="test-project")
            assert result.single() is not None
    
    def test_multi_project_isolation(self, graph_manager):
        """Test that different projects are isolated"""
        # Create node in test-project
        analysis = {
            "filename": "test.py",
            "data": {
                "definitions": [
                    {"type": "function", "name": "isolated_func", "line": 1}
                ],
                "calls": [],
                "imports": []
            }
        }
        graph_manager.update_file_structure(analysis)
        
        # Create another manager for different project
        other_manager = GraphManager(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
            "other-project"
        )
        
        # Verify function is not visible in other project
        with other_manager.driver.session() as session:
            result = session.run(
                "MATCH (f:Function {name: $name, project_id: $project_id}) RETURN f",
                name="isolated_func",
                project_id="other-project"
            )
            assert result.single() is None
        
        other_manager.close()
    
    def test_get_graph_data(self, graph_manager):
        """Test retrieving graph data for visualization"""
        analysis = {
            "filename": "test.py",
            "data": {
                "definitions": [
                    {"type": "function", "name": "test_func", "line": 1}
                ],
                "calls": [],
                "imports": []
            }
        }
        
        graph_manager.update_file_structure(analysis)
        data = graph_manager.get_graph_data()
        
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 2  # At least File and Function
        assert len(data["edges"]) >= 1  # At least CONTAINS relationship
