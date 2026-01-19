"""
Unit tests for Python parser.

Tests the Tree-sitter based Python parser's ability to extract:
- Function definitions
- Class definitions
- Function calls
- Import statements
"""
import pytest
from src.workers.python.parser import PythonParser


class TestPythonParser:
    """Test suite for PythonParser"""
    
    @pytest.fixture
    def parser(self):
        """Fixture to create a parser instance"""
        return PythonParser()
    
    def test_parse_function_definition(self, parser):
        """Test parsing a simple function definition"""
        code = """
def hello_world():
    print("Hello, World!")
"""
        result = parser.parse_code(code)
        
        assert len(result["definitions"]) == 1
        assert result["definitions"][0]["type"] == "function"
        assert result["definitions"][0]["name"] == "hello_world"
        assert result["definitions"][0]["line"] == 2
    
    def test_parse_class_definition(self, parser):
        """Test parsing a class definition"""
        code = """
class Calculator:
    def add(self, a, b):
        return a + b
"""
        result = parser.parse_code(code)
        
        # Should find both class and method
        assert len(result["definitions"]) == 2
        class_def = next(d for d in result["definitions"] if d["type"] == "class")
        assert class_def["name"] == "Calculator"
        assert class_def["line"] == 2
    
    def test_parse_function_calls(self, parser):
        """Test parsing function calls"""
        code = """
def main():
    result = calculate(5, 10)
    print(result)
"""
        result = parser.parse_code(code)
        
        assert len(result["calls"]) >= 2
        call_names = [call["name"] for call in result["calls"]]
        assert "calculate" in call_names
        assert "print" in call_names
    
    def test_parse_imports(self, parser):
        """Test parsing import statements"""
        code = """
import os
from pathlib import Path
from typing import Dict, List
"""
        result = parser.parse_code(code)
        
        assert len(result["imports"]) == 3
        assert any("import os" in imp["content"] for imp in result["imports"])
    
    def test_parent_symbol_tracking(self, parser):
        """Test that calls are attributed to their parent function"""
        code = """
def outer_function():
    inner_call()
"""
        result = parser.parse_code(code)
        
        call = next(c for c in result["calls"] if c["name"] == "inner_call")
        assert call["parent"] == "outer_function"
    
    def test_empty_code(self, parser):
        """Test parsing empty code"""
        result = parser.parse_code("")
        
        assert result["definitions"] == []
        assert result["calls"] == []
        assert result["imports"] == []
    
    def test_syntax_error_tolerance(self, parser):
        """Test that parser handles syntax errors gracefully"""
        code = """
def broken_function(
    # Missing closing parenthesis
    print("This has a syntax error")
"""
        # Should not raise an exception
        result = parser.parse_code(code)
        assert isinstance(result, dict)
