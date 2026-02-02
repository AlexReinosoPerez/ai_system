"""
Router - System status reporting for AI System
"""

from shared.logger import setup_logger

logger = setup_logger(__name__)


class Router:
    """Provides system status information"""
    
    def __init__(self):
        """Initialize router"""
        logger.info("Router initialized")
    
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


router = Router()
