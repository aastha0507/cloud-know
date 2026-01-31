"""Retrieval service for RAG pipeline."""
from typing import List, Dict, Any, Optional
from rag.embedding.embedding_service import EmbeddingService
from rag.vectorstore.vector_store import VectorStore
from cloudknow_tools.tools import SpannerTool


class RetrievalService:
    """Service for retrieving relevant documents using RAG."""
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
        spanner_tool: Optional[SpannerTool] = None
    ):
        """Initialize retrieval service.
        
        Args:
            embedding_service: Embedding service instance
            vector_store: Vector store instance
            spanner_tool: Spanner tool for metadata queries
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()
        self.spanner_tool = spanner_tool or SpannerTool()
    
    def retrieve(
        self,
        query: str,
        limit: int = 10,
        source_filter: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            source_filter: Optional source platform filter
            min_score: Minimum similarity score threshold
            
        Returns:
            List of retrieved documents with content, metadata, and scores
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed(query)
        
        # Build filter
        filter_dict = None
        if source_filter:
            filter_dict = {"metadata.source": source_filter}
        
        # Search vector store
        results = self.vector_store.search(
            query_embedding=query_embedding,
            limit=limit * 2,  # Get more results for filtering
            filter_dict=filter_dict
        )
        
        # Filter by minimum score
        filtered_results = [
            r for r in results
            if r.get("score", 0.0) >= min_score
        ]
        
        # Enrich with metadata from Spanner
        enriched_results = []
        for result in filtered_results[:limit]:
            chunk_id = result.get("_id", "")
            content = result.get("content", "")
            score = result.get("score", 0.0)
            chunk_metadata = result.get("metadata", {})
            
            # Extract document ID from chunk ID (format: document_id_chunk_N)
            document_id = chunk_id.rsplit("_chunk_", 1)[0] if "_chunk_" in chunk_id else chunk_id
            
            # Get file name from chunk metadata (stored in MongoDB)
            chunk_file_name = chunk_metadata.get("file_name")
            chunk_source_id = chunk_metadata.get("source_id")
            chunk_mime_type = chunk_metadata.get("mime_type")
            
            # Get full document metadata from Spanner
            doc_metadata = None
            try:
                doc_metadata = self.spanner_tool.get_document_metadata(document_id)
            except Exception as e:
                # If lookup fails, we'll use chunk metadata as fallback
                pass
            
            # Format result with structured information
            formatted_result = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "similarity_score": round(score, 4),
                "content": content,
                "content_preview": content[:500] + "..." if len(content) > 500 else content,
                "content_length": len(content),
                "chunk_metadata": {
                    "chunk_index": chunk_metadata.get("chunk_index"),
                    "total_chunks": chunk_metadata.get("total_chunks"),
                    "source": chunk_metadata.get("source", "unknown"),
                    "file_name": chunk_file_name,  # Include in chunk metadata
                    "source_id": chunk_source_id,
                    "mime_type": chunk_mime_type
                }
            }
            
            # Add document-level metadata if available
            if doc_metadata:
                formatted_result["document"] = {
                    "title": doc_metadata.get("title") or chunk_file_name,  # Fallback to chunk metadata
                    "source": doc_metadata.get("source"),
                    "source_id": doc_metadata.get("source_id") or chunk_source_id,
                    "content_type": doc_metadata.get("content_type") or chunk_mime_type,
                    "file_path": doc_metadata.get("file_path"),
                    "created_at": doc_metadata.get("created_at"),
                    "updated_at": doc_metadata.get("updated_at"),
                    "owner": doc_metadata.get("owner"),
                    "tags": doc_metadata.get("tags", []),
                    "summary": doc_metadata.get("metadata", {}).get("summary") if isinstance(doc_metadata.get("metadata"), dict) else None,
                    "key_points": doc_metadata.get("metadata", {}).get("key_points", []) if isinstance(doc_metadata.get("metadata"), dict) else []
                }
            elif chunk_file_name or chunk_source_id:
                # If Spanner lookup failed, use chunk metadata
                formatted_result["document"] = {
                    "title": chunk_file_name,
                    "source": chunk_metadata.get("source", "unknown"),
                    "source_id": chunk_source_id,
                    "content_type": chunk_mime_type
                }
            
            enriched_results.append(formatted_result)
        
        return enriched_results
    
    def retrieve_with_context(
        self,
        query: str,
        limit: int = 10,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """Retrieve documents with relationship context.
        
        Args:
            query: Search query
            limit: Maximum number of results
            include_relationships: Whether to include related documents
            
        Returns:
            Dictionary with results and relationships
        """
        # Get initial results
        results = self.retrieve(query, limit=limit)
        
        response = {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
        if include_relationships:
            # Get relationships for top results
            relationships = []
            for result in results[:5]:  # Limit to top 5 for relationships
                doc_id = result.get("_id")
                if doc_id:
                    doc_relationships = self.spanner_tool.get_document_relationships(doc_id)
                    relationships.extend(doc_relationships)
            
            response["relationships"] = relationships
        
        return response

