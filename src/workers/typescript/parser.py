import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser

class TypeScriptParser:
    def __init__(self):
        self.TS_LANGUAGE = Language(tstypescript.language_typescript())
        self.parser = Parser(self.TS_LANGUAGE)

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

        # Extract function/method definitions
        if node.type in ["function_declaration", "method_definition", "arrow_function"]:
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
        elif node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf8")
                results["definitions"].append({
                    "type": "class",
                    "name": name,
                    "line": node.start_point[0] + 1
                })
                current_symbol = name

        # Extract calls (e.g., axios.get)
        elif node.type == "call_expression":
            function_node = node.child_by_field_name("function")
            if function_node:
                results["calls"].append({
                    "name": function_node.text.decode("utf8"),
                    "parent": current_symbol,
                    "line": node.start_point[0] + 1
                })
        
        # Extract property access and identifiers (to catch renames like userId)
        elif node.type in ["identifier", "property_identifier"]:
            name = node.text.decode("utf8")
            if current_symbol:
                results["calls"].append({
                    "name": name,
                    "type": "reference",
                    "parent": current_symbol,
                    "line": node.start_point[0] + 1
                })

        # Extract imports
        elif node.type == "import_statement":
            results["imports"].append({
                "content": node.text.decode("utf8"),
                "line": node.start_point[0] + 1
            })

        for child in node.children:
            self._traverse(child, results, current_symbol)

if __name__ == "__main__":
    example_code = """
import axios from 'axios';

class UserService {
    async getUsers() {
        const response = await axios.get('/api/users');
        return response.data;
    }
}

function render() {
    const service = new UserService();
    service.getUsers();
}
"""
    parser = TypeScriptParser()
    print(parser.parse_code(example_code))
