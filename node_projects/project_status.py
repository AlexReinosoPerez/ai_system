"""
Project Status - Format project information for display
"""

from node_projects.project_registry import ProjectRegistry
from shared.logger import setup_logger

logger = setup_logger(__name__)


class ProjectStatus:
    """Formats project data for user display"""
    
    def __init__(self, registry: ProjectRegistry):
        """
        Initialize project status formatter
        
        Args:
            registry: ProjectRegistry instance
        """
        self.registry = registry
        logger.info("Project status formatter initialized")
    
    def summarize_all(self) -> str:
        """
        Summarize all projects
        
        Returns:
            Formatted project list
        """
        projects = self.registry.list_projects()
        
        if not projects:
            return "📂 No hay proyectos registrados"
        
        lines = [f"📂 Proyectos registrados ({len(projects)})\n"]
        
        for key, project in projects.items():
            name = project.get('name', key)
            status = project.get('status', 'unknown')
            priority = project.get('priority', 'normal')
            
            status_icon = "✅" if status == "active" else "⏸️"
            priority_icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
            
            lines.append(f"\n{status_icon} {name}")
            lines.append(f"   Estado: {status}")
            lines.append(f"   Prioridad: {priority_icon} {priority}")
        
        logger.info(f"Summarized {len(projects)} projects")
        return "\n".join(lines)
    
    def summarize_one(self, name: str) -> str:
        """
        Summarize specific project
        
        Args:
            name: Project name
            
        Returns:
            Formatted project details
        """
        project = self.registry.get_project(name)
        
        if not project:
            return f"❌ Proyecto '{name}' no encontrado"
        
        project_name = project.get('name', name)
        status = project.get('status', 'unknown')
        phase = project.get('phase', 'unknown')
        priority = project.get('priority', 'normal')
        description = project.get('description', 'Sin descripción')
        
        status_icon = "✅" if status == "active" else "⏸️"
        
        lines = [
            f"{status_icon} {project_name}\n",
            f"Estado: {status}",
            f"Fase: {phase}",
            f"Prioridad: {priority}",
            f"\nDescripción:",
            description
        ]
        
        logger.info(f"Summarized project: {name}")
        return "\n".join(lines)
