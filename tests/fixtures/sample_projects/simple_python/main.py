"""
Simple Python project for testing.

This is a minimal Python project used as a fixture for integration tests.
"""

def helper_function(x, y):
    """Helper function that adds two numbers"""
    return x + y


def main():
    """Main function that uses the helper"""
    result = helper_function(5, 10)
    print(f"Result: {result}")
    return result


if __name__ == "__main__":
    main()
