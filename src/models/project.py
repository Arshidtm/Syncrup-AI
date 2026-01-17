"""
Project management and multi-project support.
"""
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Optional
from src.utils.path_normalizer import PathNormalizer
from src.exceptions import ProjectNotFoundError


class Project(BaseModel):
    """Represents a project in the system"""
    
    id: str
    name: str
    root_path: str
    
    class Config:
        arbitrary_types_allowed = True


class ProjectRegistry:
    """
    Manages multiple projects and their path normalizers.
    Provides a centralized registry for all active projects.
    """
    
    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self._normalizers: Dict[str, PathNormalizer] = {}
    
    def register(self, project_id: str, name: str, root_path: str) -> Project:
        """
        Register a new project in the registry.
        
        Args:
            project_id: Unique project identifier
            name: Human-readable project name
            root_path: Absolute path to project root directory
            
        Returns:
            Created Project instance
        """
        project = Project(id=project_id, name=name, root_path=root_path)
        self.projects[project_id] = project
        self._normalizers[project_id] = PathNormalizer(root_path)
        return project
    
    def get(self, project_id: str) -> Optional[Project]:
        """
        Get a project by ID.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Project instance or None if not found
        """
        return self.projects.get(project_id)
    
    def get_normalizer(self, project_id: str) -> PathNormalizer:
        """
        Get the path normalizer for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            PathNormalizer instance for the project
            
        Raises:
            ProjectNotFoundError: If project not found
        """
        if project_id not in self._normalizers:
            raise ProjectNotFoundError(project_id)
        return self._normalizers[project_id]
    
    def list_projects(self) -> list[Project]:
        """
        List all registered projects.
        
        Returns:
            List of all Project instances
        """
        return list(self.projects.values())
    
    def remove(self, project_id: str) -> bool:
        """
        Remove a project from the registry.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if project was removed, False if not found
        """
        if project_id in self.projects:
            del self.projects[project_id]
            del self._normalizers[project_id]
            return True
        return False


# Global project registry instance
project_registry = ProjectRegistry()
