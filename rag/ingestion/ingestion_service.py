"""Ingestion service for processing documents from various sources."""
import io
from typing import Dict, Any, List, Optional
from agents.workflows.document_processing_workflow import DocumentProcessingWorkflow
from cloudknow_tools.tools import GoogleDriveTool, MongoDBAtlasTool, SpannerTool
from connectors.github.github_connector import GitHubConnector


def _extract_text_from_pdf(content_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyPDF2."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts).strip() if parts else ""
    except Exception:
        return ""


class IngestionService:
    """Service for ingesting documents from various sources."""
    
    def __init__(
        self,
        workflow: Optional[DocumentProcessingWorkflow] = None,
        drive_tool: Optional[GoogleDriveTool] = None
    ):
        """Initialize ingestion service.
        
        Args:
            workflow: Document processing workflow instance
            drive_tool: Google Drive tool instance
        """
        self.workflow = workflow or DocumentProcessingWorkflow()
        self.drive_tool = drive_tool or GoogleDriveTool()
    
    def ingest_from_google_drive(
        self,
        folder_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Ingest documents from a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            limit: Maximum number of files to process (None for all)
            
        Returns:
            Dictionary with ingestion results
        """
        try:
            # List files in folder
            files = self.drive_tool.list_files(folder_id, page_size=limit or 100)
            
            results = {
                "source": "google_drive",
                "folder_id": folder_id,
                "files_found": len(files),
                "processed": [],
                "failed": [],
                "total_processed": 0
            }
            
            # Process each file
            for file_info in files[:limit] if limit else files:
                try:
                    # Get file content
                    file_data = self.drive_tool.get_file_content(file_info["id"])
                    
                    # Process document
                    process_result = self.workflow.process_document(
                        file_content=file_data["content"].encode("utf-8")
                        if isinstance(file_data["content"], str)
                        else file_data["content"],
                        source="google_drive",
                        source_id=file_info["id"],
                        mime_type=file_info.get("mimeType", "application/octet-stream"),
                        file_name=file_info.get("name"),
                        metadata={
                            "web_view_link": file_info.get("webViewLink"),
                            "modified_time": file_info.get("modifiedTime")
                        }
                    )
                    
                    if process_result.get("success"):
                        results["processed"].append({
                            "file_id": file_info["id"],
                            "file_name": file_info.get("name"),
                            "document_id": process_result.get("document_id")
                        })
                        results["total_processed"] += 1
                    else:
                        results["failed"].append({
                            "file_id": file_info["id"],
                            "file_name": file_info.get("name"),
                            "error": process_result.get("error")
                        })
                except Exception as e:
                    results["failed"].append({
                        "file_id": file_info.get("id", "unknown"),
                        "error": str(e)
                    })
            
            return results
            
        except Exception as e:
            return {
                "source": "google_drive",
                "folder_id": folder_id,
                "error": str(e),
                "success": False
            }
    
    def ingest_text(
        self,
        text: str,
        source: str,
        source_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Ingest a text document.
        
        Args:
            text: Text content
            source: Source platform
            source_id: ID in source platform
            title: Optional document title
            metadata: Optional additional metadata
            
        Returns:
            Processing result dictionary
        """
        return self.workflow.process_text_document(
            text_content=text,
            source=source,
            source_id=source_id,
            title=title,
            metadata=metadata
        )

    def ingest_from_github(
        self,
        owner: str,
        repo: str,
        path: str = "",
        ref: str = "main",
        limit: Optional[int] = None,
        github_token: Optional[str] = None,
        minimal: bool = False,
    ) -> Dict[str, Any]:
        """Ingest documents from a GitHub repository path (e.g. novatech-kb).
        
        Args:
            owner: Repository owner (e.g. Rapid-Claim)
            repo: Repository name (e.g. hackathon-ps)
            path: Path inside repo (e.g. novatech-kb); empty = root
            ref: Branch or ref (e.g. dev)
            limit: Max files to process (None = all)
            github_token: Optional GitHub token for private repos / higher rate limits
            minimal: If True, only chunk+embed+store in MongoDB (no Spanner/Gemini); cheaper and avoids 500 if Spanner/Gemini unavailable.
            
        Returns:
            Dictionary with processed, failed, total_processed, source=github
        """
        connector = GitHubConnector(token=github_token)
        path = path.strip("/") or "."
        try:
            files = connector.list_files_recursive(owner=owner, repo=repo, path=path, ref=ref, limit=limit)
        except Exception as e:
            return {
                "source": "github",
                "owner": owner,
                "repo": repo,
                "path": path,
                "ref": ref,
                "error": str(e),
                "files_found": 0,
                "processed": [],
                "failed": [],
                "total_processed": 0,
            }
        results = {
            "source": "github",
            "owner": owner,
            "repo": repo,
            "path": path,
            "ref": ref,
            "files_found": len(files),
            "processed": [],
            "failed": [],
            "total_processed": 0,
        }
        for item in files:
            file_path = item.get("path", "")
            name = item.get("name", "")
            try:
                content_res = connector.get_file_content(owner=owner, repo=repo, path=file_path, ref=ref)
                # PDF from GitHub: extract text from raw bytes
                if content_res.get("content_bytes") and (name.lower().endswith(".pdf") or file_path.lower().endswith(".pdf")):
                    text = _extract_text_from_pdf(content_res["content_bytes"])
                else:
                    text = content_res.get("content", "")
                if not text or not text.strip():
                    results["failed"].append({"path": file_path, "error": "Empty or unreadable content"})
                    continue
                source_id = f"{owner}/{repo}/{file_path}@{ref}"
                process_result = self.workflow.process_text_document(
                    text_content=text,
                    source="github",
                    source_id=source_id,
                    title=name,
                    metadata={
                        "repo": repo,
                        "owner": owner,
                        "path": file_path,
                        "ref": ref,
                        "html_url": item.get("html_url"),
                    },
                    minimal=minimal,
                )
                if process_result.get("success"):
                    results["processed"].append({
                        "path": file_path,
                        "name": name,
                        "document_id": process_result.get("document_id"),
                    })
                    results["total_processed"] += 1
                else:
                    results["failed"].append({"path": file_path, "error": process_result.get("error", "Unknown")})
            except Exception as e:
                results["failed"].append({"path": file_path, "error": str(e)})
        return results

