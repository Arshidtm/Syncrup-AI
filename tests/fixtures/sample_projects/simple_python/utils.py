"""
Utility functions for the sample project.
"""

def calculate(a, b, operation="add"):
    """Perform a calculation"""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        return a / b if b != 0 else None
    return None


def format_result(value):
    """Format a result for display"""
    return f"Result: {value}"
