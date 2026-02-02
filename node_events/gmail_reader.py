"""
Gmail Reader - Read-only Gmail access via OAuth 2.0
"""

import os
from datetime import datetime
from shared.logger import setup_logger

logger = setup_logger(__name__)


class GmailUnavailable(Exception):
    """Raised when Gmail access is not available"""
    pass


class GmailReader:
    """Reads emails from Gmail using OAuth 2.0 readonly scope"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    TOKEN_FILE = 'token.json'
    CREDENTIALS_FILE = 'credentials.json'
    
    def __init__(self):
        """Initialize Gmail reader"""
        logger.info("Gmail reader initialized")
    
    def get_recent_emails(self, max_results: int = 10) -> str:
        """
        Get recent emails from Gmail inbox
        
        Args:
            max_results: Maximum number of emails to retrieve
            
        Returns:
            Formatted email list
            
        Raises:
            GmailUnavailable: If Gmail access is not available
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as e:
            logger.error("Google API libraries not available")
            raise GmailUnavailable("Google API libraries not installed") from e
        
        if not os.path.exists(self.CREDENTIALS_FILE):
            logger.error(f"Credentials file not found: {self.CREDENTIALS_FILE}")
            raise GmailUnavailable(
                f"Archivo {self.CREDENTIALS_FILE} no encontrado.\n"
                "Descarga las credenciales desde Google Cloud Console."
            )
        
        try:
            creds = None
            
            if os.path.exists(self.TOKEN_FILE):
                logger.info("Loading existing token")
                creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing expired token")
                    creds.refresh(Request())
                else:
                    logger.info("Starting OAuth flow")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.CREDENTIALS_FILE, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                logger.info("Saving token")
                with open(self.TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            
            logger.info("Building Gmail service")
            service = build('gmail', 'v1', credentials=creds)
            
            logger.info(f"Fetching {max_results} recent emails")
            results = service.users().messages().list(
                userId='me',
                maxResults=max_results,
                labelIds=['INBOX']
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return "📭 No hay mensajes en la bandeja de entrada"
            
            email_list = []
            email_list.append(f"📧 Últimos {len(messages)} correos\n")
            
            for msg in messages:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = msg_data.get('payload', {}).get('headers', [])
                
                from_addr = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconocido')
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(sin asunto)')
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                snippet = msg_data.get('snippet', '')[:100]
                
                email_list.append(f"\n---")
                email_list.append(f"De: {from_addr}")
                email_list.append(f"Asunto: {subject}")
                email_list.append(f"Fecha: {date_str}")
                if snippet:
                    email_list.append(f"Vista previa: {snippet}...")
            
            logger.info(f"Successfully fetched {len(messages)} emails")
            return "\n".join(email_list)
            
        except Exception as e:
            logger.error(f"Gmail access error: {e}")
            raise GmailUnavailable(f"Error accediendo a Gmail: {str(e)}") from e
