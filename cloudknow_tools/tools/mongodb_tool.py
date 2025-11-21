"""MCP Tool for MongoDB Atlas Vector Database operations."""
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
import numpy as np
from api.config.settings import settings


class MongoDBAtlasTool:
    """MCP Tool for interacting with MongoDB Atlas Vector Database."""
    
    def __init__(self, connection_uri: Optional[str] = None):
        """Initialize MongoDB Atlas tool.
        
        Args:
            connection_uri: MongoDB Atlas connection URI.
                          If None, uses settings.mongodb_atlas_uri
        """
        self.connection_uri = connection_uri or settings.mongodb_atlas_uri
        self.client = MongoClient(self.connection_uri)
        self.database = self.client[settings.mongodb_database_name]
        self.collection = self.database[settings.mongodb_collection_name]
        
        # Create vector search index if it doesn't exist
        self._ensure_vector_index()
    
    def _ensure_vector_index(self):
        """Ensure vector search index exists for semantic search."""
        try:
            # Check if index already exists
            indexes = self.collection.list_indexes()
            index_names = [idx["name"] for idx in indexes]
            
            if "vector_index" not in index_names:
                # Create vector search index
                self.database.command({
                    "createSearchIndexes": self.collection.name,
                    "indexes": [{
                        "name": "vector_index",
                        "definition": {
                            "mappings": {
                                "dynamic": True,
                                "fields": {
                                    "embedding": {
                                        "type": "knnVector",
                                        "dimensions": 768,  # Adjust based on your embedding model
                                        "similarity": "cosine"
                                    }
                                }
                            }
                        }
                    }]
                })
        except Exception as e:
            # Index might already exist or creation might fail
            # This is okay for now
            pass
    
    def insert_document(
        self,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        source: str = "unknown"
    ) -> str:
        """Insert or update a document with its embedding into MongoDB Atlas.
        
        Uses upsert to handle duplicate documents gracefully - if the document
        already exists, it will be updated with the new content and embedding.
        
        Args:
            document_id: Unique document identifier
            content: Document text content
            embedding: Vector embedding of the document
            metadata: Additional metadata dictionary
            source: Source of the document (e.g., "google_drive", "jira")
            
        Returns:
            Document ID
        """
        try:
            from datetime import datetime
            
            document = {
                "_id": document_id,
                "content": content,
                "embedding": embedding,
                "metadata": {
                    **metadata,
                    "source": source
                },
                "updated_at": datetime.utcnow()
            }
            
            # Preserve created_at if it exists, otherwise set it now
            if "created_at" not in metadata or not metadata.get("created_at"):
                document["created_at"] = datetime.utcnow()
            else:
                document["created_at"] = metadata.get("created_at")
            
            # Use replace_one with upsert=True to handle duplicates
            # This will insert if new, or update if exists
            result = self.collection.replace_one(
                {"_id": document_id},
                document,
                upsert=True
            )
            return document_id
        except Exception as e:
            raise Exception(f"Error inserting document: {str(e)}")
    
    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity.
        
        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results to return
            filter_dict: Optional MongoDB filter dictionary
            
        Returns:
            List of similar documents with scores
        """
        try:
            # Build aggregation pipeline for vector search
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": limit * 10,
                        "limit": limit
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "content": 1,
                        "metadata": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]
            
            # Add filter if provided
            if filter_dict:
                pipeline.insert(1, {"$match": filter_dict})
            
            results = list(self.collection.aggregate(pipeline))
            return results
        except Exception as e:
            # Fallback to cosine similarity if vector search fails
            return self._fallback_search(query_embedding, limit, filter_dict)
    
    def _fallback_search(
        self,
        query_embedding: List[float],
        limit: int,
        filter_dict: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fallback search using cosine similarity."""
        query_vec = np.array(query_embedding)
        
        # Build filter
        filter_query = filter_dict or {}
        
        # Get all documents matching filter
        documents = list(self.collection.find(filter_query))
        
        # Calculate cosine similarity
        results = []
        for doc in documents:
            if "embedding" in doc:
                doc_vec = np.array(doc["embedding"])
                similarity = np.dot(query_vec, doc_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)
                )
                results.append({
                    "_id": doc["_id"],
                    "content": doc.get("content"),
                    "metadata": doc.get("metadata", {}),
                    "score": float(similarity)
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document dictionary or None if not found
        """
        return self.collection.find_one({"_id": document_id})
    
    def update_document(
        self,
        document_id: str,
        content: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update an existing document.
        
        Args:
            document_id: Document ID
            content: Updated content (optional)
            embedding: Updated embedding (optional)
            metadata: Updated metadata (optional)
            
        Returns:
            True if document was updated, False otherwise
        """
        update_dict = {}
        if content:
            update_dict["content"] = content
        if embedding:
            update_dict["embedding"] = embedding
        if metadata:
            update_dict["metadata"] = metadata
        
        if not update_dict:
            return False
        
        result = self.collection.update_one(
            {"_id": document_id},
            {"$set": update_dict}
        )
        return result.modified_count > 0
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            True if document was deleted, False otherwise
        """
        result = self.collection.delete_one({"_id": document_id})
        return result.deleted_count > 0

