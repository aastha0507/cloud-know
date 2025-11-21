"""CloudKnow ADK Agent - Interactive agent for document querying and ingestion."""
from typing import Dict, Any, List, Optional
import sys
import os

# Add project root to path to import CloudKnow modules
# Get the absolute path to the project root (go up from agents_dir/cloudknow_agent)
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)  # agents_dir/cloudknow_agent
_agents_dir = os.path.dirname(_current_dir)    # agents_dir
_project_root = os.path.dirname(_agents_dir)   # project root

# Ensure project root is in Python path (at the beginning for priority)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Also ensure current directory is in path
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from google.adk.agents import Agent
from rag.retrieval.retrieval_service import RetrievalService
from rag.ingestion.ingestion_service import IngestionService
from agents.workflows.conversational_agent import ConversationalAgent


def query_documents(
    query: str,
    limit: int = 10,
    source_filter: Optional[str] = None,
    min_score: float = 0.7
) -> Dict[str, Any]:
    """Query the knowledge base to find relevant documents.
    
    Args:
        query (str): The search query or question.
        limit (int): Maximum number of results to return (default: 10).
        source_filter (str, optional): Filter by source platform (e.g., "google_drive", "jira").
        min_score (float): Minimum similarity score (0.0 to 1.0, default: 0.7).
    
    Returns:
        dict: Query results with relevant documents, scores, and content previews.
    """
    try:
        # Initialize services with error handling
        try:
            retrieval_service = RetrievalService()
        except Exception as init_error:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error initializing RetrievalService: {str(init_error)}")
            print(f"Traceback: {error_trace}")
            
            return {
                "status": "error",
                "message": f"Failed to initialize retrieval service: {str(init_error)}",
                "error_type": "initialization_error",
                "suggestion": "Please check: 1) MongoDB connection, 2) Spanner connection, 3) Environment variables"
            }
        
        try:
            results = retrieval_service.retrieve(
                query=query,
                limit=limit,
                source_filter=source_filter,
                min_score=min_score
            )
        except Exception as retrieve_error:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error retrieving documents: {str(retrieve_error)}")
            print(f"Traceback: {error_trace}")
            
            return {
                "status": "error",
                "message": f"Error retrieving documents: {str(retrieve_error)}",
                "error_type": "retrieval_error",
                "suggestion": "Please check: 1) MongoDB connection, 2) That documents have been ingested, 3) Embedding service"
            }
        
        if not results:
            return {
                "status": "no_results",
                "message": f"No documents found matching '{query}'. Try a different query or lower the min_score (currently {min_score}).",
                "results": [],
                "query": query
            }
        
        # Format results for better readability
        formatted_results = []
        for result in results:
            doc_info = result.get("document", {})
            formatted_results.append({
                "title": doc_info.get("title", "Unknown"),
                "source": doc_info.get("source", "unknown"),
                "relevance_score": result.get("similarity_score", 0.0),
                "content_preview": result.get("content_preview", "")[:300],
                "document_id": result.get("document_id")
            })
        
        return {
            "status": "success",
            "query": query,
            "total_results": len(results),
            "results": formatted_results,
            "message": f"Found {len(results)} relevant document(s) for '{query}'"
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Unexpected error in query_documents: {str(e)}")
        print(f"Traceback: {error_trace}")
        
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unexpected_error",
            "suggestion": "Please try again or contact support if the issue persists"
        }


def ingest_google_drive_folder(
    folder_id: str,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """Ingest documents from a Google Drive folder into the knowledge base.
    
    Args:
        folder_id (str): The Google Drive folder ID to ingest from.
        limit (int, optional): Maximum number of files to process (None for all).
    
    Returns:
        dict: Ingestion results with processed files, failed files, and statistics.
    """
    try:
        ingestion_service = IngestionService()
        result = ingestion_service.ingest_from_google_drive(
            folder_id=folder_id,
            limit=limit
        )
        
        if result.get("total_processed", 0) > 0:
            return {
                "status": "success",
                "message": f"Successfully processed {result.get('total_processed', 0)} file(s) from Google Drive.",
                "files_processed": result.get("total_processed", 0),
                "files_found": result.get("files_found", 0),
                "processed_files": result.get("processed", []),
                "failed_files": result.get("failed", [])
            }
        else:
            return {
                "status": "error",
                "error_message": "No files were processed. Please check the folder ID and permissions.",
                "details": result
            }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error ingesting from Google Drive: {str(e)}"
        }


def query_folder_with_context(
    folder_id: str,
    query: str,
    limit: Optional[int] = None,
    min_score: float = 0.7
) -> Dict[str, Any]:
    """Query documents in a specific Google Drive folder and get contextual answers.
    
    This function:
    1. Ingests files from the folder (if not already ingested)
    2. Queries the ingested content
    3. Returns file names with brief descriptions
    
    Args:
        folder_id (str): Google Drive folder ID.
        query (str): Your question or query about the files.
        limit (int, optional): Maximum number of files to process.
        min_score (float): Minimum similarity score (default: 0.7).
    
    Returns:
        dict: Files with relevant content, descriptions, and relevance scores.
    """
    try:
        agent = ConversationalAgent()
        result = agent.process_folder_query(
            folder_id=folder_id,
            query=query,
            limit=limit,
            min_score=min_score
        )
        
        if result.get("success"):
            files = result.get("files", [])
            return {
                "status": "success",
                "query": query,
                "files_processed": result.get("files_processed", 0),
                "files_with_relevant_content": result.get("files_with_relevant_content", 0),
                "files": [
                    {
                        "file_name": f.get("file_name", "Unknown"),
                        "relevance_score": f.get("relevance_score", 0.0),
                        "brief_description": f.get("brief_description", ""),
                        "relevant_chunks_found": f.get("relevant_chunks_found", 0)
                    }
                    for f in files
                ]
            }
        else:
            return {
                "status": "error",
                "error_message": result.get("error", "Unknown error occurred"),
                "details": result
            }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error processing folder query: {str(e)}"
        }


# Create the CloudKnow agent
# ADK expects the variable to be named 'root_agent'
root_agent = Agent(
    name="cloudknow_agent",
    model="gemini-2.0-flash",
    description=(
        "CloudKnow is an intelligent knowledge assistant that helps you find information "
        "from your documents stored in Google Drive, Jira, and Slack. It can query documents, "
        "ingest files from Google Drive, and provide contextual answers about your knowledge base."
    ),
    instruction=(
        "You are CloudKnow, a helpful knowledge assistant. You help users:\n"
        "- Query and search through their document knowledge base\n"
        "- Ingest documents from Google Drive folders\n"
        "- Find relevant information and provide contextual answers\n"
        "- Understand compliance rules and regulations\n\n"
        "Always be helpful, provide clear answers, and cite sources when possible. "
        "If a query doesn't return results, suggest alternative queries or lower similarity thresholds."
    ),
    tools=[
        query_documents,
        ingest_google_drive_folder,
        query_folder_with_context
    ],
)

# Also export as cloudknow_agent for backward compatibility
cloudknow_agent = root_agent


