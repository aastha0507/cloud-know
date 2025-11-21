"""Google Drive connector."""
from typing import List, Dict, Any
import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth import default


class GoogleDriveConnector:
    """Connector for interacting with Google Drive."""
    
    def __init__(self, credentials_path: str = None):
        """Initialize Google Drive connector.
        
        Args:
            credentials_path: Optional path to service account credentials.
                             If None, uses default credentials.
        """
        # Check if credentials_path is provided and file exists
        if credentials_path and os.path.exists(credentials_path):
            self.creds = service_account.Credentials.from_service_account_file(
                credentials_path
            )
        else:
            self.creds, _ = default()
        
        self.service = build("drive", "v3", credentials=self.creds)
    
    def list_files(self, folder_id: str) -> List[Dict[str, Any]]:
        """List files in a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            List of file metadata dictionaries
        """
        results = self.service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType)"
        ).execute()
        
        return results.get("files", [])
