"""
Project Summarizer - Local text summarization using HuggingFace
"""

from shared.logger import setup_logger

logger = setup_logger(__name__)


class SummarizationUnavailable(Exception):
    """Raised when summarization dependencies are not available"""
    pass


class ProjectSummarizer:
    """Summarizes project information using local HuggingFace model"""
    
    MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
    
    def __init__(self):
        """Initialize summarizer"""
        logger.info("Summarizer initialized")
    
    def summarize(self, text: str) -> str:
        """
        Summarize project text
        
        Args:
            text: Raw project information text
            
        Returns:
            Structured summary
            
        Raises:
            SummarizationUnavailable: If transformers library is not available
        """
        try:
            from transformers import pipeline
        except ImportError as e:
            logger.error("Transformers library not available")
            raise SummarizationUnavailable("Transformers library not installed") from e
        
        try:
            logger.info("Loading summarization model")
            summarizer_pipeline = pipeline(
                "summarization",
                model=self.MODEL_NAME,
                device=-1
            )
            
            logger.info("Generating summary")
            summary_result = summarizer_pipeline(
                text,
                max_length=130,
                min_length=30,
                do_sample=False
            )
            
            summary_text = summary_result[0]['summary_text']
            formatted_summary = self._format_summary(text, summary_text)
            logger.info("Summary generated successfully")
            
            return formatted_summary
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            raise SummarizationUnavailable(f"Model loading or inference failed: {str(e)}") from e
    
    def _format_summary(self, original_text: str, summary: str) -> str:
        """
        Format summary as structured output
        
        Args:
            original_text: Original project text
            summary: Generated summary
            
        Returns:
            Formatted summary
        """
        project_name = "Desconocido"
        language = "No detectado"
        issues = "0"
        
        for line in original_text.split('\n'):
            if "Proyecto:" in line:
                project_name = line.split("Proyecto:")[-1].strip()
            elif "Lenguaje principal:" in line:
                language = line.split("Lenguaje principal:")[-1].strip()
            elif "Issues abiertas:" in line:
                issues = line.split("Issues abiertas:")[-1].strip()
        
        estado = "activo" if "commit" in original_text.lower() else "inactivo"
        actividad = "reciente" if "2026" in original_text or "2025" in original_text else "antigua"
        
        formatted = (
            f"📝 Resumen del proyecto: {project_name}\n\n"
            f"Estado general: {estado}\n"
            f"Última actividad: {actividad}\n"
            f"Issues abiertas: {issues}\n"
            f"Lenguaje principal: {language}"
        )
        
        return formatted
