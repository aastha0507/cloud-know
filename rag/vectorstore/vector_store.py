"""Vector store interface - delegates to MongoDB Atlas."""
from typing import List, Dict, Any, Optional
from cloudknow_tools.tools.mongodb_tool import MongoDBAtlasTool


class VectorStore:
    """Vector store wrapper around MongoDB Atlas."""
    
    def __init__(self, mongodb_tool: Optional[MongoDBAtlasTool] = None):
        """Initialize vector store.
        
        Args:
            mongodb_tool: MongoDB Atlas tool instance. If None, creates new instance.
        """
        self.mongodb_tool = mongodb_tool or MongoDBAtlasTool()
    
    def add(self, doc_id: str, embedding: List[float], metadata: Dict[str, Any]):
        """Add a document to the vector store.
        
        Args:
            doc_id: Document ID
            embedding: Document embedding vector
            metadata: Document metadata
        """
        self.mongodb_tool.insert_document(
            document_id=doc_id,
            content=metadata.get("content", ""),
            embedding=embedding,
            metadata=metadata,
            source=metadata.get("source", "unknown")
        )
    
    def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            filter_dict: Optional MongoDB filter
            
        Returns:
            List of similar documents with scores
        """
        return self.mongodb_tool.search_similar(
            query_embedding=query_embedding,
            limit=limit,
            filter_dict=filter_dict
        )
