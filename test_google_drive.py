#!/usr/bin/env python3
"""Test script for Google Drive connection."""
import sys
from cloudknow_tools.tools.google_drive_tool import GoogleDriveTool
from api.config.settings import settings

def test_google_drive():
    """Test Google Drive connection and list files."""
    print("Testing Google Drive Connection...")
    print("=" * 50)
    
    # Check if folder ID is set
    folder_id = settings.google_drive_folder_id
    if not folder_id:
        print("❌ Error: GOOGLE_DRIVE_FOLDER_ID not set in .env file")
        print("\nPlease add to your .env file:")
        print("GOOGLE_DRIVE_FOLDER_ID=your-folder-id")
        return False
    
    print(f"Folder ID: {folder_id}")
    print()
    
    try:
        # Initialize Google Drive tool
        print("Initializing Google Drive tool...")
        drive_tool = GoogleDriveTool()
        print("✅ Google Drive tool initialized")
        print()
        
        # List files
        print(f"Listing files in folder {folder_id}...")
        files = drive_tool.list_files(folder_id, page_size=10)
        
        if not files:
            print("⚠️  No files found in this folder")
            print("   Make sure:")
            print("   1. The folder ID is correct")
            print("   2. The folder is shared with your account/service account")
            print("   3. The folder contains files")
            return False
        
        print(f"✅ Found {len(files)} file(s):")
        print()
        for i, file_info in enumerate(files[:10], 1):
            print(f"{i}. {file_info.get('name', 'Unknown')}")
            print(f"   ID: {file_info.get('id')}")
            print(f"   Type: {file_info.get('mimeType', 'Unknown')}")
            print()
        
        # Test getting file content for first file
        if files:
            first_file = files[0]
            print(f"Testing content extraction for: {first_file.get('name')}")
            try:
                file_data = drive_tool.get_file_content(first_file['id'])
                content_preview = file_data.get('content', '')
                if isinstance(content_preview, str):
                    preview = content_preview[:200] + "..." if len(content_preview) > 200 else content_preview
                    print(f"✅ Content extracted ({len(content_preview)} characters)")
                    print(f"   Preview: {preview}")
                else:
                    print(f"✅ File retrieved (binary content, {len(content_preview)} bytes)")
            except Exception as e:
                print(f"⚠️  Could not extract content: {str(e)}")
                print("   This is okay for binary files")
        
        print()
        print("=" * 50)
        print("✅ Google Drive connection test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()
        print("Troubleshooting:")
        print("1. Make sure Google Drive API is enabled:")
        print("   gcloud services enable drive.googleapis.com")
        print()
        print("2. Authenticate with Google:")
        print("   gcloud auth application-default login")
        print()
        print("3. For service accounts, make sure:")
        print("   - Service account key file exists")
        print("   - Folder is shared with service account email")
        print()
        return False

if __name__ == "__main__":
    success = test_google_drive()
    sys.exit(0 if success else 1)

