"""
Custom exceptions for the Nexus AI Engine.
"""


class NexusException(Exception):
    """Base exception for all Nexus-related errors"""
    pass


class ProjectNotFoundError(NexusException):
    """Raised when a project is not found in the registry"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        super().__init__(f"Project '{project_id}' not found in registry")


class PathNormalizationError(NexusException):
    """Raised when path normalization fails"""
    
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to normalize path '{path}': {reason}")


class GraphQueryError(NexusException):
    """Raised when a Neo4j graph query fails"""
    
    def __init__(self, query: str, error: str):
        self.query = query
        self.error = error
        super().__init__(f"Graph query failed: {error}")


class LLMAnalysisError(NexusException):
    """Raised when LLM analysis fails"""
    
    def __init__(self, error: str):
        self.error = error
        super().__init__(f"LLM analysis failed: {error}")


class WorkerConnectionError(NexusException):
    """Raised when unable to connect to a parser worker"""
    
    def __init__(self, worker_url: str, error: str):
        self.worker_url = worker_url
        self.error = error
        super().__init__(f"Failed to connect to worker at {worker_url}: {error}")
