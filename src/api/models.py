"""
API request and response models using Pydantic for validation.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum


class ImpactLevel(str, Enum):
    """Impact severity levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ERROR = "error"


class InitRequest(BaseModel):
    """Request model for project initialization"""
    project_id: str = Field(..., description="Unique project identifier")
    project_path: str = Field(default="project_demo", description="Path to project directory")


class ImpactCheckRequest(BaseModel):
    """Request model for impact analysis"""
    project_id: str = Field(..., description="Project identifier")
    filename: str = Field(..., description="File path (absolute or relative)")
    changes: Optional[str] = Field(None, description="Description of changes made")
    
    @validator('filename')
    def validate_filename(cls, v):
        if not v or v.strip() == "":
            raise ValueError("filename cannot be empty")
        return v


class AffectedItem(BaseModel):
    """Model for an affected code item"""
    file: str = Field(..., description="File containing the affected symbol")
    symbol: str = Field(..., description="Name of the affected symbol")
    symbol_type: str = Field(..., description="Type of symbol (function, class, etc.)")
    line_number: Optional[int] = Field(None, description="Line number where symbol is defined")
    depends_on: str = Field(..., description="Symbol this depends on")
    impact_reason: str = Field(..., description="Explanation of why this is affected")
    breaking: bool = Field(..., description="Whether this is a breaking change")


class ImpactCheckResponse(BaseModel):
    """Response model for impact analysis"""
    status: str = Field(default="success", description="Request status")
    impact_level: ImpactLevel = Field(..., description="Overall impact severity")
    summary: str = Field(..., description="Brief summary of the impact")
    changed_file: str = Field(..., description="File that was changed")
    affected_items: List[AffectedItem] = Field(default_factory=list, description="List of affected code items")
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions")
    blast_zone_size: int = Field(..., description="Number of affected items")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "impact_level": "high",
                "summary": "Function signature change affects 3 callers",
                "changed_file": "src\\auth\\login.py",
                "affected_items": [
                    {
                        "file": "src\\api\\routes.py",
                        "symbol": "login_endpoint",
                        "symbol_type": "function",
                        "line_number": 45,
                        "depends_on": "authenticate_user",
                        "impact_reason": "Function signature changed",
                        "breaking": True
                    }
                ],
                "recommendations": ["Update all callers to match new signature"],
                "blast_zone_size": 3
            }
        }


class RepoRequest(BaseModel):
    """Request model for adding a repository"""
    project_id: str = Field(..., description="Project identifier")
    repo_url: str = Field(..., description="GitHub repository URL")
