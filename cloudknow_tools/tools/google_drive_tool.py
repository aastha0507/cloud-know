"""MCP Tool for Google Drive operations."""
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth import default
import io
from connectors.google_drive.drive_connector import GoogleDriveConnector


class GoogleDriveTool:
    """MCP Tool for interacting with Google Drive."""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """Initialize Google Drive tool.
        
        Args:
            credentials_path: Optional path to service account credentials.
                             If None, uses default credentials.
        """
        import os
        
        # Check if credentials_path is provided and file exists
        if credentials_path and os.path.exists(credentials_path):
            self.creds = service_account.Credentials.from_service_account_file(
                credentials_path
            )
        else:
            # Use default credentials (ADC)
            # This will use:
            # 1. GOOGLE_APPLICATION_CREDENTIALS env var if set and file exists
            # 2. gcloud auth application-default login credentials
            # 3. GCE/Cloud Run service account (in cloud environments)
            self.creds, _ = default()
        
        self.service = build("drive", "v3", credentials=self.creds)
        self.connector = GoogleDriveConnector()
    
    def list_files(self, folder_id: str, page_size: int = 100) -> List[Dict[str, Any]]:
        """List files in a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            page_size: Maximum number of files to return
            
        Returns:
            List of file metadata dictionaries
        """
        try:
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id, name, mimeType, modifiedTime, size, webViewLink)",
                pageSize=page_size,
                orderBy="modifiedTime desc"
            ).execute()
            
            return results.get("files", [])
        except Exception as e:
            raise Exception(f"Error listing files: {str(e)}")
    
    def get_file_content(self, file_id: str) -> Dict[str, Any]:
        """Download and extract content from a Google Drive file.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Dictionary with file content and metadata
        """
        try:
            # Get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, modifiedTime, size, webViewLink, owners"
            ).execute()
            
            content = None
            mime_type = file_metadata.get("mimeType", "")
            
            # Handle different file types
            if "text" in mime_type or mime_type == "application/json":
                # Download text files
                request = self.service.files().get_media(fileId=file_id)
                content = request.execute().decode("utf-8")
            elif mime_type == "application/vnd.google-apps.document":
                # Google Docs - export as text
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType="text/plain"
                )
                content = request.execute().decode("utf-8")
            elif mime_type == "application/vnd.google-apps.spreadsheet":
                # Google Sheets - export as CSV
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType="text/csv"
                )
                content = request.execute().decode("utf-8")
            elif mime_type == "application/vnd.google-apps.presentation":
                # Google Slides - export as text
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType="text/plain"
                )
                content = request.execute().decode("utf-8")
            else:
                # For other types, try to download as binary
                request = self.service.files().get_media(fileId=file_id)
                content = request.execute()
            
            return {
                "file_id": file_id,
                "name": file_metadata.get("name"),
                "mime_type": mime_type,
                "content": content,
                "metadata": file_metadata,
                "modified_time": file_metadata.get("modifiedTime"),
                "web_view_link": file_metadata.get("webViewLink")
            }
        except Exception as e:
            raise Exception(f"Error getting file content: {str(e)}")
    
    def search_files(self, query: str, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for files in Google Drive.
        
        Args:
            query: Search query string
            folder_id: Optional folder ID to limit search
            
        Returns:
            List of matching file metadata dictionaries
        """
        try:
            search_query = f"name contains '{query}' and trashed=false"
            if folder_id:
                search_query += f" and '{folder_id}' in parents"
            
            results = self.service.files().list(
                q=search_query,
                fields="files(id, name, mimeType, modifiedTime, size, webViewLink)",
                pageSize=50
            ).execute()
            
            return results.get("files", [])
        except Exception as e:
            raise Exception(f"Error searching files: {str(e)}")

