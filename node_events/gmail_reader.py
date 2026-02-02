"""
Gmail Reader - Read-only Gmail access via OAuth 2.0
"""

import os
from typing import List, Dict


class GmailUnavailable(Exception):
    """Raised when Gmail access is not available"""
    pass


class GmailReader:
    """Reads emails from Gmail using OAuth 2.0 readonly scope"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    TOKEN_FILE = 'token.json'
    CREDENTIALS_FILE = 'credentials.json'
    
    def __init__(self):
        """Initialize Gmail reader with OAuth"""
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
        
        if not os.path.exists(self.CREDENTIALS_FILE):
            raise GmailUnavailable(
                f"Archivo {self.CREDENTIALS_FILE} no encontrado. "
                "Descarga las credenciales desde Google Cloud Console."
            )
        
        self._creds = None
        self._service = None
    
    def _authenticate(self):
        """Handle OAuth authentication"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            pass
        
        if os.path.exists(self.TOKEN_FILE):
            self._creds = Credentials.from_authorized_user_file(
                self.TOKEN_FILE, self.SCOPES
            )
        
        if not self._creds or not self._creds.valid:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                self._creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDENTIALS_FILE, self.SCOPES
                )
                self._creds = flow.run_local_server(port=0)
            
            with open(self.TOKEN_FILE, 'w') as token:
                token.write(self._creds.to_json())
        
        from googleapiclient.discovery import build
        self._service = build('gmail', 'v1', credentials=self._creds)
    
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
            raise GmailUnavailable(f"Error accessing Gmail API: {str(e)}") from e
