"""
Python Code Parser using Tree-sitter

This module implements a Tree-sitter based parser for Python code that extracts:
- Function definitions
- Class definitions
- Function calls
- Import statements

Tree-sitter Advantages:
    - Error-tolerant: Handles syntax errors gracefully
    - Fast: Incremental parsing for large files
    - Accurate: Precise line numbers and positions
    - Consistent: Same API across all languages

Parsing Strategy:
    1. Parse code into concrete syntax tree (CST)
    2. Traverse tree recursively
    3. Extract relevant nodes (functions, classes, calls)
    4. Track parent symbols for call attribution
    5. Return structured data with line numbers

Parent Symbol Tracking:
    When traversing the tree, the parser tracks the current function or class
    context. This allows calls to be attributed to their parent symbol, which
    is crucial for building accurate dependency graphs.

Output Format:
    {
        "definitions": [
            {"type": "function", "name": "foo", "line": 10},
            {"type": "class", "name": "Bar", "line": 20}
        ],
        "calls": [
            {"name": "baz", "parent": "foo", "line": 12}
        ],
        "imports": [
            {"content": "import os", "line": 1}
        ]
    }

Node Types Extracted:
    - function_definition: Function definitions
    - class_definition: Class definitions
    - call: Function/method invocations
    - import_from_statement, import_statement: Imports

Example:
    parser = PythonParser()
    result = parser.parse_code("def foo():\\n    bar()")
    # Returns: {"definitions": [...], "calls": [...], "imports": [...]}
"""
import tree_sitter_python as tspython

from tree_sitter import Language, Parser

class PythonParser:
    def __init__(self):
        self.PY_LANGUAGE = Language(tspython.language())
        self.parser = Parser(self.PY_LANGUAGE)

    def parse_code(self, code: str):
        tree = self.parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        
        results = {
            "definitions": [],
            "calls": [],
            "imports": []
        }
        
        self._traverse(root_node, results)
        return results

    def _traverse(self, node, results, parent_symbol=None):
        current_symbol = parent_symbol
        
        # Extract function definitions
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf8")
                results["definitions"].append({
                    "type": "function",
                    "name": name,
                    "line": node.start_point[0] + 1
                })
                current_symbol = name
        
        # Extract class definitions
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf8")
                results["definitions"].append({
                    "type": "class",
                    "name": name,
                    "line": node.start_point[0] + 1
                })
                current_symbol = name

        # Extract calls
        elif node.type == "call":
            function_node = node.child_by_field_name("function")
            if function_node:
                results["calls"].append({
                    "name": function_node.text.decode("utf8"),
                    "parent": current_symbol,
                    "line": node.start_point[0] + 1
                })

        # Extract imports
        elif node.type in ["import_from_statement", "import_statement"]:
            results["imports"].append({
                "content": node.text.decode("utf8"),
                "line": node.start_point[0] + 1
            })

        for child in node.children:
            self._traverse(child, results, current_symbol)

if __name__ == "__main__":
    example_code = """
import os
from math import sqrt

class Calculator:
    def add(self, a, b):
        return a + b

def calculate():
    calc = Calculator()
    result = calc.add(5, 10)
    print(result)
    return sqrt(result)
"""
    parser = PythonParser()
    print(parser.parse_code(example_code))
