"""
Gmail Reader - Read-only Gmail access via OAuth 2.0
"""

import os
from typing import List, Dict, Optional
from shared.logger import setup_logger

logger = setup_logger(__name__)


class GmailUnavailable(Exception):
    """Raised when Gmail access is not available"""
    pass


class GmailReader:
    """Reads emails from Gmail using OAuth 2.0 readonly scope"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None
    ):
        """
        Initialize Gmail reader with OAuth
        
        Args:
            credentials_path: Path to credentials.json (default: './credentials.json')
            token_path: Path to token.json (default: './token.json')
            
        Raises:
            GmailUnavailable: If dependencies missing or credentials not found
        """
        # Validate Google API libraries
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as e:
            raise GmailUnavailable(
                "Google API libraries not installed. "
                "Run: pip install google-auth google-auth-oauthlib google-api-python-client"
            ) from e
        
        # Set paths with explicit defaults
        self.credentials_path = credentials_path or 'credentials.json'
        self.token_path = token_path or 'token.json'
        
        logger.info(f"GmailReader initialized: credentials={self.credentials_path}, token={self.token_path}")
        
        # Validate credentials file exists
        if not os.path.exists(self.credentials_path):
            raise GmailUnavailable(
                f"Credentials file not found: {self.credentials_path}. "
                "Download from Google Cloud Console and mount as volume."
            )
        
        self._creds = None
        self._service = None
    
    def _authenticate(self):
        """
        Handle OAuth authentication flow
        
        Raises:
            GmailUnavailable: If authentication fails
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            pass
        
        logger.info("Starting OAuth authentication flow")
        
        # Load existing token if available
        if os.path.exists(self.token_path):
            logger.info(f"Loading existing token from {self.token_path}")
            self._creds = Credentials.from_authorized_user_file(
                self.token_path, self.SCOPES
            )
        
        # Refresh or obtain new credentials
        if not self._creds or not self._creds.valid:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                logger.info("Refreshing expired token")
                self._creds.refresh(Request())
            else:
                logger.info(f"Starting new OAuth flow with credentials from {self.credentials_path}")
                logger.info("OAuth flow using localhost redirect (OOB is deprecated by Google)")
                
                # Create flow
                # Google deprecated OOB (urn:ietf:wg:oauth:2.0:oob) in Oct 2022
                # Using localhost-based flow instead
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, 
                    self.SCOPES
                )
                
                # Run local server OAuth flow with state verification disabled
                # host="localhost" for compatibility with Google Cloud Console redirect URIs
                # port=8080 must be exposed in docker run (-p 8080:8080)
                # open_browser=False because container has no browser
                logger.info("Starting OAuth server on localhost:8080")
                
                self._creds = flow.run_local_server(
                    host="localhost",
                    port=8080,
                    open_browser=False
                )
            
            # Persist token for future use
            logger.info(f"Saving token to {self.token_path}")
            with open(self.token_path, 'w') as token:
                token.write(self._creds.to_json())
        
        from googleapiclient.discovery import build
        self._service = build('gmail', 'v1', credentials=self._creds)
        logger.info("Gmail service initialized successfully")
    
    def get_inbox(self, count: int = 5) -> List[Dict]:
        """
        Get recent emails from Gmail inbox
        
        Args:
            count: Number of emails to retrieve
            
        Returns:
            List of email dicts with from, subject, snippet, date
            
        Raises:
            GmailUnavailable: If Gmail access fails
        """
        if not self._service:
            self._authenticate()
        
        try:
            results = self._service.users().messages().list(
                userId='me',
                maxResults=count,
                labelIds=['INBOX']
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return []
            
            emails = []
            for msg in messages:
                msg_data = self._service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = msg_data.get('payload', {}).get('headers', [])
                snippet = msg_data.get('snippet', '')
                
                email = {
                    'from': '',
                    'subject': '',
                    'snippet': snippet,
                    'date': ''
                }
                
                for header in headers:
                    name = header.get('name', '').lower()
                    value = header.get('value', '')
                    
                    if name == 'from':
                        email['from'] = value
                    elif name == 'subject':
                        email['subject'] = value
                    elif name == 'date':
                        email['date'] = value
                
                emails.append(email)
            
            return emails
            
        except Exception as e:
            logger.error(f"Gmail API error: {e}")
            raise GmailUnavailable(f"Error accessing Gmail API: {str(e)}") from e
    
    def get_recent_emails(self, count: int = 10) -> str:
        """
        Get recent emails formatted as text (Router compatibility)
        
        Args:
            count: Number of emails to retrieve
            
        Returns:
            Formatted string with email list
            
        Raises:
            GmailUnavailable: If Gmail access fails
        """
        emails = self.get_inbox(count)
        
        if not emails:
            return "📭 No hay correos en la bandeja de entrada."
        
        output = f"📬 Últimos {len(emails)} correos:\n\n"
        
        for i, email in enumerate(emails, 1):
            from_addr = email.get('from', 'Desconocido')
            subject = email.get('subject', '(sin asunto)')
            snippet = email.get('snippet', '')
            date = email.get('date', '')
            
            # Truncate snippet
            if len(snippet) > 100:
                snippet = snippet[:100] + '...'
            
            output += f"{i}. **{from_addr}**\n"
            output += f"   Asunto: {subject}\n"
            output += f"   {snippet}\n"
            output += f"   Fecha: {date}\n\n"
        
        return output
