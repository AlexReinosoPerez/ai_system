"""
Router - System status reporting for AI System
"""

from shared.logger import setup_logger
from node_events.github_reader import GitHubProjectReader
from node_events.summarizer import ProjectSummarizer, SummarizationUnavailable
from node_events.gmail_reader import GmailReader, GmailUnavailable

logger = setup_logger(__name__)


class Router:
    """Provides system status information"""
    
    def __init__(self):
        """Initialize router"""
        logger.info("Router initialized")
        self._summarizer = None
        self._gmail_reader = None
    
    def get_system_status(self) -> str:
        """
        Get current system status
        
        Returns:
            Formatted status string
        """
        status = (
            "🧠 AI System Status\n\n"
            "• Interface node: ✅ running\n"
            "• Events node: ⏸️ not started\n"
            "• Programmer node: ⏸️ not started"
        )
        return status
    
    def project(self, name: str) -> str:
        """
        Get project information from GitHub
        
        Args:
            name: Project name
            
        Returns:
            Formatted project status
        """
        logger.info(f"Project query received: {name}")
        
        if name.lower() == "fitnessai":
            reader = GitHubProjectReader("AlexReinosoPerez", "FitnessAi")
            return reader.get_project_status()
        
        return "❌ Proyecto no reconocido"
    
    def project_summary(self, name: str) -> str:
        """
        Get summarized project information from GitHub
        
        Args:
            name: Project name
            
        Returns:
            Summarized project status
        """
        logger.info(f"Project summary query received: {name}")
        
        if name.lower() == "fitnessai":
            if self._summarizer is None:
                self._summarizer = ProjectSummarizer()
            
            reader = GitHubProjectReader("AlexReinosoPerez", "FitnessAi")
            raw_text = reader.get_project_status()
            
            if raw_text.startswith("❌"):
                return raw_text
            
            try:
                return self._summarizer.summarize(raw_text)
            except SummarizationUnavailable as e:
                logger.warning(f"Summarization unavailable: {e}")
                return (
                    "⚠️ Síntesis no disponible en este entorno.\n"
                    "Ejecuta el sistema en tu PC personal con dependencias completas."
                )
        
        return "❌ Proyecto no reconocido"
    
    def inbox(self, count: int = 10) -> str:
        """
        Get recent emails from Gmail inbox
        
        Args:
            count: Number of emails to retrieve
            
        Returns:
            Formatted email list
        """
        logger.info(f"Inbox query received: count={count}")
        
        if self._gmail_reader is None:
            self._gmail_reader = GmailReader()
        
        try:
            return self._gmail_reader.get_recent_emails(count)
        except GmailUnavailable as e:
            logger.warning(f"Gmail unavailable: {e}")
            return (
                "⚠️ Gmail no disponible.\n\n"
                "Posibles causas:\n"
                "• Falta archivo credentials.json\n"
                "• Librerías de Google no instaladas\n"
                "• Error de autenticación OAuth"
            )


router = Router()
