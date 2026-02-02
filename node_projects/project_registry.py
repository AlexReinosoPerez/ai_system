"""
Project Registry - Read project data from JSON
"""

import json
import os
from shared.logger import setup_logger

logger = setup_logger(__name__)


class ProjectRegistryError(Exception):
    """Raised when project registry cannot be accessed"""
    pass


class ProjectRegistry:
    """Manages project data from JSON file"""
    
    PROJECTS_FILE = "node_projects/projects.json"
    
    def __init__(self):
        """Initialize project registry"""
        logger.info("Project registry initialized")
    
    def list_projects(self) -> dict:
        """
        List all projects from registry
        
        Returns:
            Dictionary of projects
            
        Raises:
            ProjectRegistryError: If JSON cannot be parsed
        """
        if not os.path.exists(self.PROJECTS_FILE):
            logger.warning(f"Projects file not found: {self.PROJECTS_FILE}")
            return {}
        
        try:
            with open(self.PROJECTS_FILE, 'r') as f:
                data = json.load(f)
            
            projects = data.get('projects', {})
            logger.info(f"Loaded {len(projects)} projects from registry")
            return projects
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse projects.json: {e}")
            raise ProjectRegistryError(f"Invalid JSON format: {str(e)}") from e
        except Exception as e:
            logger.error(f"Failed to read projects: {e}")
            raise ProjectRegistryError(f"Error reading registry: {str(e)}") from e
    
    def get_project(self, name: str) -> dict | None:
        """
        Get specific project by name
        
        Args:
            name: Project name (case-insensitive)
            
        Returns:
            Project dict or None if not found
        """
        projects = self.list_projects()
        
        name_lower = name.lower()
        for project_key, project_data in projects.items():
            if project_key.lower() == name_lower:
                logger.info(f"Found project: {project_key}")
                return project_data
        
        logger.info(f"Project not found: {name}")
        return None
