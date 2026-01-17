"""
Centralized path normalization utility for consistent path handling across the system.
"""
from pathlib import Path
from typing import Union


class PathNormalizer:
    """Handles path normalization to ensure consistent relative paths"""
    
    def __init__(self, project_root: Union[str, Path]):
        """
        Initialize with a project root directory.
        
        Args:
            project_root: Absolute path to the project root directory
        """
        self.project_root = Path(project_root).resolve()
    
    def normalize(self, file_path: Union[str, Path]) -> str:
        """
        Convert any path format to relative path from project root.
        
        Args:
            file_path: Absolute or relative file path
            
        Returns:
            Relative path from project root with OS-specific separators
            
        Raises:
            ValueError: If path is outside project root
        """
        path = Path(file_path)
        
        # Handle absolute paths
        if path.is_absolute():
            try:
                relative = path.relative_to(self.project_root)
                # Use backslashes for Windows consistency with Neo4j storage
                return str(relative).replace('/', '\\')
            except ValueError:
                raise ValueError(
                    f"Path '{file_path}' is outside project root '{self.project_root}'"
                )
        
        # Handle relative paths (including those with ../)
        try:
            resolved = (self.project_root / path).resolve()
            relative = resolved.relative_to(self.project_root)
            return str(relative).replace('/', '\\')
        except ValueError:
            raise ValueError(
                f"Path '{file_path}' resolves outside project root '{self.project_root}'"
            )
    
    def to_absolute(self, relative_path: str) -> Path:
        """
        Convert relative path to absolute path.
        
        Args:
            relative_path: Relative path from project root
            
        Returns:
            Absolute Path object
        """
        return (self.project_root / relative_path).resolve()
    
    def exists(self, file_path: Union[str, Path]) -> bool:
        """
        Check if a file exists (handles both absolute and relative paths).
        
        Args:
            file_path: File path to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            normalized = self.normalize(file_path)
            absolute = self.to_absolute(normalized)
            return absolute.exists()
        except ValueError:
            return False
