"""
Integration tests for worker communication.

Tests the communication between the main server and language workers.
"""
import pytest
import requests
from src.config.settings import settings


class TestPythonWorker:
    """Test suite for Python worker communication"""
    
    def test_python_worker_health(self):
        """Test that Python worker is running"""
        try:
            response = requests.get(settings.python_worker_url, timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("Python worker not running")
    
    def test_python_worker_parse_simple_code(self):
        """Test parsing simple Python code"""
        code = """
def hello():
    print("Hello, World!")
"""
        
        try:
            response = requests.post(
                f"{settings.python_worker_url}/parse",
                json={"code": code, "filename": "test.py"},
                timeout=10
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "definitions" in data["data"]
            assert len(data["data"]["definitions"]) == 1
            assert data["data"]["definitions"][0]["name"] == "hello"
        except requests.exceptions.ConnectionError:
            pytest.skip("Python worker not running")
    
    def test_python_worker_parse_with_calls(self):
        """Test parsing code with function calls"""
        code = """
def main():
    helper()
    
def helper():
    pass
"""
        
        try:
            response = requests.post(
                f"{settings.python_worker_url}/parse",
                json={"code": code, "filename": "test.py"},
                timeout=10
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]["definitions"]) == 2
            assert len(data["data"]["calls"]) >= 1
        except requests.exceptions.ConnectionError:
            pytest.skip("Python worker not running")
    
    def test_python_worker_parse_with_imports(self):
        """Test parsing code with imports"""
        code = """
import os
from pathlib import Path

def main():
    pass
"""
        
        try:
            response = requests.post(
                f"{settings.python_worker_url}/parse",
                json={"code": code, "filename": "test.py"},
                timeout=10
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]["imports"]) == 2
        except requests.exceptions.ConnectionError:
            pytest.skip("Python worker not running")


class TestTypeScriptWorker:
    """Test suite for TypeScript worker communication"""
    
    def test_typescript_worker_health(self):
        """Test that TypeScript worker is running"""
        try:
            response = requests.get(settings.typescript_worker_url, timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("TypeScript worker not running")
    
    def test_typescript_worker_parse_simple_code(self):
        """Test parsing simple TypeScript code"""
        code = """
function hello(): void {
    console.log("Hello, World!");
}
"""
        
        try:
            response = requests.post(
                f"{settings.typescript_worker_url}/parse",
                json={"code": code, "filename": "test.ts"},
                timeout=10
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "definitions" in data["data"]
        except requests.exceptions.ConnectionError:
            pytest.skip("TypeScript worker not running")
    
    def test_typescript_worker_parse_arrow_function(self):
        """Test parsing arrow functions"""
        code = """
const greet = (name: string) => {
    console.log(`Hello, ${name}!`);
};
"""
        
        try:
            response = requests.post(
                f"{settings.typescript_worker_url}/parse",
                json={"code": code, "filename": "test.ts"},
                timeout=10
            )
            
            assert response.status_code == 200
            data = response.json()
            # Should detect the arrow function
            assert "data" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("TypeScript worker not running")


class TestWorkerErrorHandling:
    """Test suite for worker error handling"""
    
    def test_python_worker_invalid_json(self):
        """Test Python worker with invalid JSON"""
        try:
            response = requests.post(
                f"{settings.python_worker_url}/parse",
                data="invalid json",
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            # Should return error status
            assert response.status_code in [400, 422]
        except requests.exceptions.ConnectionError:
            pytest.skip("Python worker not running")
    
    def test_python_worker_missing_fields(self):
        """Test Python worker with missing required fields"""
        try:
            response = requests.post(
                f"{settings.python_worker_url}/parse",
                json={"code": "def foo(): pass"},  # Missing filename
                timeout=10
            )
            
            # Should return validation error
            assert response.status_code == 422
        except requests.exceptions.ConnectionError:
            pytest.skip("Python worker not running")
    
    def test_worker_timeout_handling(self):
        """Test handling of worker timeouts"""
        # This test would require a mock worker or very large code
        # For now, just verify the timeout parameter works
        try:
            response = requests.post(
                f"{settings.python_worker_url}/parse",
                json={"code": "def foo(): pass", "filename": "test.py"},
                timeout=0.001  # Very short timeout
            )
            pytest.fail("Should have timed out")
        except requests.exceptions.Timeout:
            # Expected behavior
            pass
        except requests.exceptions.ConnectionError:
            pytest.skip("Python worker not running")
