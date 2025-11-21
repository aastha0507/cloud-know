"""Conversational agent for Google Drive query workflow using ADK."""
from typing import Dict, Any, List, Optional


class ConversationalAgent:
    """ADK Agent that handles Google Drive folder ingestion and querying."""
    
    def __init__(self):
        """Initialize the conversational agent."""
        # Lazy imports to avoid circular dependency
        from rag.ingestion.ingestion_service import IngestionService
        from rag.retrieval.retrieval_service import RetrievalService
        from cloudknow_tools.tools import SpannerTool
        
        self.ingestion_service = IngestionService()
        self.retrieval_service = RetrievalService()
        self.spanner_tool = SpannerTool()
    
    def process_folder_query(
        self,
        folder_id: str,
        query: str,
        limit: Optional[int] = None,
        min_score: float = 0.5
    ) -> Dict[str, Any]:
        """Process a folder and answer a query about its contents.
        
        This agent orchestrates:
        1. Ingestion of files from Google Drive folder
        2. Querying the ingested content
        3. Grouping results by file with brief descriptions
        
        Args:
            folder_id: Google Drive folder ID
            query: User's query/question
            limit: Maximum number of files to process (None for all)
            min_score: Minimum similarity score for results
            
        Returns:
            Dictionary with file names and brief descriptions
        """
        # Step 1: Ingest files from folder
        ingestion_result = self.ingestion_service.ingest_from_google_drive(
            folder_id=folder_id,
            limit=limit
        )
        
        if not ingestion_result.get("total_processed", 0) > 0:
            return {
                "success": False,
                "error": "No files were processed. Please check the folder ID and permissions.",
                "ingestion_result": ingestion_result
            }
        
        # Step 2: Query the ingested documents
        query_results = self.retrieval_service.retrieve(
            query=query,
            limit=50,  # Get more results to group by file
            source_filter="google_drive",
            min_score=min_score
        )
        
        if not query_results:
            return {
                "success": True,
                "query": query,
                "folder_id": folder_id,
                "files_processed": ingestion_result.get("total_processed", 0),
                "files_with_relevant_content": 0,
                "files": [],
                "message": "No relevant content found for your query. Try a different query or lower the min_score.",
                "ingestion_summary": {
                    "total_processed": ingestion_result.get("total_processed", 0),
                    "failed": len(ingestion_result.get("failed", []))
                }
            }
        
        # Step 3: Group results by file and format response
        file_results = self._group_results_by_file(query_results)
        
        return {
            "success": True,
            "query": query,
            "folder_id": folder_id,
            "files_processed": ingestion_result.get("total_processed", 0),
            "files_with_relevant_content": len(file_results),
            "files": file_results,
            "ingestion_summary": {
                "total_processed": ingestion_result.get("total_processed", 0),
                "failed": len(ingestion_result.get("failed", []))
            }
        }
    
    def _group_results_by_file(self, query_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group query results by file and create brief descriptions.
        
        Args:
            query_results: List of query results (chunks)
            
        Returns:
            List of files with brief descriptions, sorted by relevance
        """
        # Group chunks by document
        files_dict = {}
        
        # Cache for Google Drive file names (to avoid multiple API calls)
        drive_file_cache = {}
        
        for result in query_results:
            doc_info = result.get("document", {})
            chunk_metadata = result.get("chunk_metadata", {})
            
            # Try multiple sources for file name
            file_name = (
                doc_info.get("title") or
                chunk_metadata.get("file_name") or
                chunk_metadata.get("metadata", {}).get("file_name") if isinstance(chunk_metadata.get("metadata"), dict) else None
            )
            
            # If still no file name, try to get it from Google Drive using source_id
            if not file_name or file_name == "Unknown File":
                source_id = doc_info.get("source_id") or chunk_metadata.get("source_id")
                if source_id and (doc_info.get("source") == "google_drive" or chunk_metadata.get("source") == "google_drive"):
                    # Check cache first
                    if source_id in drive_file_cache:
                        file_name = drive_file_cache[source_id]
                    else:
                        # Try to get file name from Google Drive
                        try:
                            from cloudknow_tools.tools import GoogleDriveTool
                            drive_tool = GoogleDriveTool()
                            # Use the service to get file info (lightweight - just metadata)
                            file_info = drive_tool.service.files().get(
                                fileId=source_id,
                                fields="id,name,mimeType"
                            ).execute()
                            if file_info and file_info.get("name"):
                                file_name = file_info.get("name")
                                drive_file_cache[source_id] = file_name
                        except Exception:
                            pass  # If it fails, we'll use fallback
            
            # Final fallback
            if not file_name or file_name == "Unknown File":
                file_name = f"Document {result.get('document_id', 'unknown')[:8]}"
            
            document_id = result.get("document_id")
            similarity_score = result.get("similarity_score", 0.0)
            content_preview = result.get("content_preview", "")
            
            if document_id not in files_dict:
                files_dict[document_id] = {
                    "file_name": file_name,
                    "document_id": document_id,
                    "source_id": doc_info.get("source_id") or chunk_metadata.get("source_id"),
                    "content_type": doc_info.get("content_type") or chunk_metadata.get("mime_type"),
                    "web_view_link": doc_info.get("file_path") or doc_info.get("web_view_link"),
                    "summary": doc_info.get("summary"),
                    "key_points": doc_info.get("key_points", []),
                    "chunks": [],
                    "max_similarity": similarity_score,
                    "total_relevant_chunks": 0
                }
            
            # Add chunk information
            files_dict[document_id]["chunks"].append({
                "similarity_score": similarity_score,
                "content_preview": content_preview[:300]  # Brief preview
            })
            files_dict[document_id]["total_relevant_chunks"] += 1
            files_dict[document_id]["max_similarity"] = max(
                files_dict[document_id]["max_similarity"],
                similarity_score
            )
        
        # Format results with brief descriptions
        formatted_files = []
        for doc_id, file_data in files_dict.items():
            # Create brief description
            description = self._create_brief_description(file_data)
            
            formatted_files.append({
                "file_name": file_data["file_name"],
                "document_id": doc_id,
                "source_id": file_data.get("source_id"),
                "relevance_score": round(file_data["max_similarity"], 3),
                "relevant_chunks_found": file_data["total_relevant_chunks"],
                "brief_description": description,
                "summary": file_data.get("summary"),
                "key_points": file_data.get("key_points", [])[:3],  # Top 3 key points
                "content_type": file_data.get("content_type"),
                "web_view_link": file_data.get("web_view_link"),
                "top_content_preview": file_data["chunks"][0]["content_preview"] if file_data["chunks"] else ""
            })
        
        # Sort by relevance score (highest first)
        formatted_files.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return formatted_files
    
    def _create_brief_description(self, file_data: Dict[str, Any]) -> str:
        """Create a brief description for a file based on query results.
        
        Args:
            file_data: File data with chunks and metadata
            
        Returns:
            Brief description string (max 200 characters)
        """
        # Use summary if available
        if file_data.get("summary"):
            summary = file_data["summary"]
            # Truncate to 200 characters
            if len(summary) > 200:
                return summary[:200] + "..."
            return summary
        
        # Otherwise, use top chunk preview
        if file_data.get("chunks"):
            top_chunk = file_data["chunks"][0]
            preview = top_chunk.get("content_preview", "")
            if len(preview) > 200:
                return preview[:200] + "..."
            return preview
        
        # Fallback
        return f"Contains {file_data['total_relevant_chunks']} relevant section(s) about your query."

