"""
Integration tests for API endpoints.

Tests the FastAPI endpoints with real database and worker interactions.
"""
import pytest
from fastapi.testclient import TestClient
from src.api_server import app
from src.config.settings import settings


@pytest.fixture
def client():
    """Fixture to create a test client"""
    return TestClient(app)


@pytest.fixture
def test_project_id():
    """Fixture to provide a consistent test project ID"""
    return "test-api-project"


@pytest.fixture(autouse=True)
def cleanup_test_data(test_project_id):
    """Automatically clean up test data after each test"""
    yield
    # Cleanup after test
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    with driver.session() as session:
        session.run(
            "MATCH (n {project_id: $project_id}) DETACH DELETE n",
            project_id=test_project_id
        )
    driver.close()


class TestInitializeGraph:
    """Test suite for /initialize-graph endpoint"""
    
    def test_initialize_graph_success(self, client, test_project_id):
        """Test successful graph initialization"""
        response = client.post(
            "/initialize-graph",
            json={
                "project_id": test_project_id,
                "project_path": "tests/fixtures/sample_projects/simple_python"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["project_id"] == test_project_id
        assert "files_processed" in data
        assert "nodes_created" in data
    
    def test_initialize_graph_invalid_path(self, client, test_project_id):
        """Test initialization with invalid path"""
        response = client.post(
            "/initialize-graph",
            json={
                "project_id": test_project_id,
                "project_path": "/nonexistent/path"
            }
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 404, 500]
    
    def test_initialize_graph_missing_project_id(self, client):
        """Test initialization without project_id"""
        response = client.post(
            "/initialize-graph",
            json={
                "project_path": "."
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestCheckImpact:
    """Test suite for /check-impact endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup_graph(self, client, test_project_id):
        """Set up a test graph before impact checks"""
        client.post(
            "/initialize-graph",
            json={
                "project_id": test_project_id,
                "project_path": "tests/fixtures/sample_projects/simple_python"
            }
        )
    
    def test_check_impact_success(self, client, test_project_id):
        """Test successful impact analysis"""
        response = client.post(
            "/check-impact",
            json={
                "project_id": test_project_id,
                "filename": "utils.py",
                "changes": "Modified helper function"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "impact_level" in data
        assert "affected_items" in data
        assert "recommendations" in data
    
    def test_check_impact_nonexistent_file(self, client, test_project_id):
        """Test impact check for nonexistent file"""
        response = client.post(
            "/check-impact",
            json={
                "project_id": test_project_id,
                "filename": "nonexistent.py"
            }
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 404]
    
    def test_check_impact_empty_filename(self, client, test_project_id):
        """Test impact check with empty filename"""
        response = client.post(
            "/check-impact",
            json={
                "project_id": test_project_id,
                "filename": ""
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestGraphData:
    """Test suite for /graph-data endpoint"""
    
    def test_get_graph_data(self, client, test_project_id):
        """Test retrieving graph data"""
        # First initialize a graph
        client.post(
            "/initialize-graph",
            json={
                "project_id": test_project_id,
                "project_path": "tests/fixtures/sample_projects/simple_python"
            }
        )
        
        # Then get graph data
        response = client.get(f"/graph-data?project_id={test_project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
    
    def test_get_graph_data_empty_project(self, client):
        """Test getting graph data for empty project"""
        response = client.get("/graph-data?project_id=nonexistent-project")
        
        assert response.status_code == 200
        data = response.json()
        assert data["nodes"] == []
        assert data["edges"] == []


class TestClearGraph:
    """Test suite for /clear-graph endpoint"""
    
    def test_clear_specific_project(self, client, test_project_id):
        """Test clearing a specific project"""
        # First create some data
        client.post(
            "/initialize-graph",
            json={
                "project_id": test_project_id,
                "project_path": "tests/fixtures/sample_projects/simple_python"
            }
        )
        
        # Then clear it
        response = client.delete(f"/clear-graph?project_id={test_project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "nodes_deleted" in data
    
    def test_clear_nonexistent_project(self, client):
        """Test clearing a project that doesn't exist"""
        response = client.delete("/clear-graph?project_id=nonexistent")
        
        assert response.status_code == 200
        # Should succeed even if nothing to delete


class TestAddRepository:
    """Test suite for /add-repository endpoint"""
    
    @pytest.mark.skip(reason="Requires network access and valid Git repository")
    def test_add_repository_success(self, client, test_project_id):
        """Test adding a GitHub repository"""
        response = client.post(
            "/add-repository",
            json={
                "project_id": test_project_id,
                "repo_url": "https://github.com/test/small-repo.git"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_add_repository_invalid_url(self, client, test_project_id):
        """Test adding repository with invalid URL"""
        response = client.post(
            "/add-repository",
            json={
                "project_id": test_project_id,
                "repo_url": "not-a-valid-url"
            }
        )
        
        # Should fail gracefully
        assert response.status_code in [400, 500]
