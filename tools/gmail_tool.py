import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config.settings import settings
from .base_tool import BaseTool, ToolResult


SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]


class GmailTool(BaseTool):
    name = "gmail"
    description = "Read and send emails via Gmail"
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.token_path = settings.BASE_DIR / "token.json"
        self.credentials_path = settings.BASE_DIR / "credentials.json"
    
    def _authenticate(self) -> bool:
        """Authenticate with Gmail API"""
        try:
            if self.token_path.exists():
                self.creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not self.credentials_path.exists():
                        return False
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())
            
            self.service = build('gmail', 'v1', credentials=self.creds)
            return True
        except Exception as e:
            print(f"Gmail auth error: {e}")
            return False
    
    def get_function_schemas(self) -> list[dict]:
        return [
            self._make_schema(
                name="read_emails",
                description="Read recent emails from inbox",
                parameters={
                    "max_results": {"type": "integer", "description": "Maximum emails to retrieve (default 10)"},
                    "query": {"type": "string", "description": "Gmail search query (e.g., 'from:someone@email.com', 'is:unread')"},
                    "include_body": {"type": "boolean", "description": "Include full email body (default false for preview)"}
                },
                required=[]
            ),
            self._make_schema(
                name="send_email",
                description="Send an email",
                parameters={
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body (plain text or HTML)"},
                    "html": {"type": "boolean", "description": "If true, body is HTML"}
                },
                required=["to", "subject", "body"]
            ),
            self._make_schema(
                name="get_email",
                description="Get a specific email by ID",
                parameters={
                    "email_id": {"type": "string", "description": "Email ID to retrieve"}
                },
                required=["email_id"]
            ),
            self._make_schema(
                name="mark_as_read",
                description="Mark an email as read",
                parameters={
                    "email_id": {"type": "string", "description": "Email ID to mark as read"}
                },
                required=["email_id"]
            )
        ]
    
    async def execute(self, function_name: str, arguments: dict) -> ToolResult:
        if not self._authenticate():
            return ToolResult(
                success=False,
                error="Gmail not configured. Please add credentials.json and complete OAuth setup."
            )
        
        try:
            if function_name == "read_emails":
                return await self._read_emails(**arguments)
            elif function_name == "send_email":
                return await self._send_email(**arguments)
            elif function_name == "get_email":
                return await self._get_email(**arguments)
            elif function_name == "mark_as_read":
                return await self._mark_as_read(**arguments)
            else:
                return ToolResult(success=False, error=f"Unknown function: {function_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _read_emails(
        self,
        max_results: int = 10,
        query: str = None,
        include_body: bool = False
    ) -> ToolResult:
        try:
            query_str = query or "in:inbox"
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query_str
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                email_data = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata' if not include_body else 'full',
                    metadataHeaders=['From', 'To', 'Subject', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in email_data.get('payload', {}).get('headers', [])}
                
                email_info = {
                    "id": msg['id'],
                    "from": headers.get('From', ''),
                    "to": headers.get('To', ''),
                    "subject": headers.get('Subject', ''),
                    "date": headers.get('Date', ''),
                    "snippet": email_data.get('snippet', ''),
                    "is_unread": 'UNREAD' in email_data.get('labelIds', [])
                }
                
                if include_body:
                    body = self._get_body(email_data.get('payload', {}))
                    email_info['body'] = body
                
                emails.append(email_info)
            
            return ToolResult(success=True, data=emails)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def _get_body(self, payload: dict) -> str:
        """Extract email body from payload"""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part.get('body', {}):
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    if 'data' in part.get('body', {}):
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        
        return ""
    
    async def _send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> ToolResult:
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            if html:
                msg_body = MIMEText(body, 'html')
            else:
                msg_body = MIMEText(body, 'plain')
            
            message.attach(msg_body)
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            sent = self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            return ToolResult(success=True, data={
                "message": f"Email sent to {to}",
                "id": sent['id']
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _get_email(self, email_id: str) -> ToolResult:
        try:
            email_data = self.service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()
            
            headers = {h['name']: h['value'] for h in email_data.get('payload', {}).get('headers', [])}
            body = self._get_body(email_data.get('payload', {}))
            
            return ToolResult(success=True, data={
                "id": email_id,
                "from": headers.get('From', ''),
                "to": headers.get('To', ''),
                "subject": headers.get('Subject', ''),
                "date": headers.get('Date', ''),
                "body": body,
                "labels": email_data.get('labelIds', [])
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _mark_as_read(self, email_id: str) -> ToolResult:
        try:
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return ToolResult(success=True, data=f"Email {email_id} marked as read")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
