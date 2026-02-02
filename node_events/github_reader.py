"""
GitHub Project Reader - Fetches public repository information
"""

import requests
from typing import Optional
from datetime import datetime

from shared.logger import setup_logger

logger = setup_logger(__name__)


class GitHubProjectReader:
    """Reads public information from GitHub repositories"""
    
    BASE_URL = "https://api.github.com"
    TIMEOUT = 10
    
    def __init__(self, owner: str, repo: str):
        """
        Initialize GitHub reader
        
        Args:
            owner: Repository owner
            repo: Repository name
        """
        self.owner = owner
        self.repo = repo
        logger.info(f"Initialized GitHub reader for {owner}/{repo}")
    
    def get_project_status(self) -> str:
        """
        Get current project status from GitHub
        
        Returns:
            Formatted status string
        """
        try:
            repo_info = self._get_repo_info()
            if not repo_info:
                return "❌ Error: No se pudo obtener información del repositorio"
            
            latest_commit = self._get_latest_commit()
            open_issues = self._get_open_issues_count()
            
            status = self._format_status(repo_info, latest_commit, open_issues)
            logger.info(f"Successfully fetched status for {self.owner}/{self.repo}")
            return status
            
        except requests.RequestException as e:
            error_msg = f"❌ Error de red: {str(e)}"
            logger.error(f"Network error fetching GitHub data: {e}")
            return error_msg
        except Exception as e:
            error_msg = f"❌ Error inesperado: {str(e)}"
            logger.error(f"Unexpected error: {e}")
            return error_msg
    
    def _get_repo_info(self) -> Optional[dict]:
        """Get repository basic information"""
        url = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}"
        response = requests.get(url, timeout=self.TIMEOUT)
        
        if response.status_code == 404:
            logger.error(f"Repository {self.owner}/{self.repo} not found")
            return None
        
        response.raise_for_status()
        return response.json()
    
    def _get_latest_commit(self) -> Optional[dict]:
        """Get latest commit information"""
        url = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/commits"
        response = requests.get(url, timeout=self.TIMEOUT)
        
        if response.status_code != 200:
            logger.warning(f"Could not fetch commits: {response.status_code}")
            return None
        
        commits = response.json()
        return commits[0] if commits else None
    
    def _get_open_issues_count(self) -> int:
        """Get count of open issues"""
        url = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/issues"
        params = {"state": "open"}
        response = requests.get(url, params=params, timeout=self.TIMEOUT)
        
        if response.status_code != 200:
            logger.warning(f"Could not fetch issues: {response.status_code}")
            return 0
        
        issues = response.json()
        return len(issues)
    
    def _format_status(self, repo_info: dict, latest_commit: Optional[dict], open_issues: int) -> str:
        """Format status information"""
        repo_name = repo_info.get("name", "Unknown")
        language = repo_info.get("language", "No detectado")
        
        status_lines = [
            f"📦 Proyecto: {repo_name}",
            ""
        ]
        
        if latest_commit:
            commit_msg = latest_commit.get("commit", {}).get("message", "N/A")
            commit_date_str = latest_commit.get("commit", {}).get("author", {}).get("date", "")
            
            if commit_date_str:
                try:
                    commit_date = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
                    formatted_date = commit_date.strftime("%Y-%m-%d")
                except:
                    formatted_date = commit_date_str[:10]
            else:
                formatted_date = "N/A"
            
            status_lines.extend([
                "Último commit:",
                f"- Mensaje: \"{commit_msg}\"",
                f"- Fecha: {formatted_date}",
                ""
            ])
        else:
            status_lines.extend([
                "Último commit: No disponible",
                ""
            ])
        
        status_lines.append(f"Issues abiertas: {open_issues}")
        status_lines.append(f"Lenguaje principal: {language}")
        
        return "\n".join(status_lines)
