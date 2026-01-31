"""Workflow for processing documents through the agent pipeline."""
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

from agents.skills import (
    FileExtractionAgent,
    ChunkingAgent,
    MetadataAnalysisAgent,
    SummaryInsightAgent
)
from rag.embedding.embedding_service import EmbeddingService
from cloudknow_tools.tools import MongoDBAtlasTool, SpannerTool


class DocumentProcessingWorkflow:
    """Orchestrates the complete document processing pipeline."""
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        mongodb_tool: Optional[MongoDBAtlasTool] = None,
        spanner_tool: Optional[SpannerTool] = None
    ):
        """Initialize the document processing workflow.
        
        Args:
            embedding_service: Embedding service instance
            mongodb_tool: MongoDB Atlas tool instance
            spanner_tool: Spanner tool instance
        """
        # Initialize agents
        self.extraction_agent = FileExtractionAgent()
        self.chunking_agent = ChunkingAgent()
        self.metadata_agent = MetadataAnalysisAgent()
        self.summary_agent = SummaryInsightAgent()
        
        # Initialize services
        self.embedding_service = embedding_service or EmbeddingService()
        self.mongodb_tool = mongodb_tool or MongoDBAtlasTool()
        self.spanner_tool = spanner_tool or SpannerTool()
    
    def process_document(
        self,
        file_content: bytes,
        source: str,
        source_id: str,
        mime_type: str,
        file_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        skip_metadata_and_summary: bool = False,
    ) -> Dict[str, Any]:
        """Process a document through the complete pipeline.
        
        Args:
            file_content: File content as bytes
            source: Source platform (e.g., "google_drive", "jira")
            source_id: ID in the source platform
            mime_type: MIME type of the file
            file_name: Optional file name
            metadata: Optional additional metadata
            skip_metadata_and_summary: If True, only chunk+embed+store in MongoDB (no Spanner/Gemini); cheaper and more resilient.
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Step 1: Extract content
            extraction_result = self.extraction_agent.extract(
                file_content, mime_type, file_name
            )
            content = extraction_result["content"]
            
            if not content or extraction_result.get("extraction_method") == "error":
                return {
                    "success": False,
                    "error": "Failed to extract content",
                    "extraction_result": extraction_result
                }
            
            if skip_metadata_and_summary:
                analysis_metadata = {"title": file_name}
                summary_result = {}
                insights_result = {}
            else:
                # Step 2: Analyze metadata
                analysis_metadata = self.metadata_agent.analyze(
                    content=content,
                    source=source,
                    source_id=source_id,
                    file_name=file_name,
                    mime_type=mime_type,
                    **(metadata or {})
                )
                # Step 3: Generate summary and insights
                summary_result = self.summary_agent.generate_summary(
                    content, max_length=200, include_key_points=True
                )
                insights_result = self.summary_agent.generate_insights(
                    content, context=analysis_metadata
                )
            
            # Step 4: Chunk the document
            chunk_metadata = {
                "document_id": self._generate_document_id(source, source_id),
                "source": source,
                "source_id": source_id,
                "file_name": file_name,
                "mime_type": mime_type,
                **analysis_metadata
            }
            chunks = self.chunking_agent.chunk(content, chunk_metadata)
            
            # Step 5: Generate embeddings and store (batch when possible for cost)
            document_id = self._generate_document_id(source, source_id)
            stored_chunks = []
            batch_size = 20
            embed_batch_available = hasattr(self.embedding_service, "embed_batch")
            
            if skip_metadata_and_summary and embed_batch_available and chunks:
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i : i + batch_size]
                    texts = [c["content"] for c in batch]
                    embeddings = self.embedding_service.embed_batch(texts)
                    for chunk, embedding in zip(batch, embeddings):
                        chunk_id = chunk["chunk_id"]
                        self.mongodb_tool.insert_document(
                            document_id=chunk_id,
                            content=chunk["content"],
                            embedding=embedding,
                            metadata=chunk["metadata"],
                            source=source
                        )
                        stored_chunks.append(chunk_id)
            else:
                for chunk in chunks:
                    embedding = self.embedding_service.embed(chunk["content"])
                    chunk_id = chunk["chunk_id"]
                    self.mongodb_tool.insert_document(
                        document_id=chunk_id,
                        content=chunk["content"],
                        embedding=embedding,
                        metadata=chunk["metadata"],
                        source=source
                    )
                    stored_chunks.append(chunk_id)
            
            if not skip_metadata_and_summary:
                # Step 6: Store metadata in Spanner
                self.spanner_tool.store_document_metadata(
                    document_id=document_id,
                    source=source,
                    source_id=source_id,
                    title=file_name or analysis_metadata.get("title"),
                    content_type=mime_type,
                    file_size=len(file_content),
                    owner=analysis_metadata.get("owner"),
                    tags=analysis_metadata.get("keywords", [])[:10],
                    metadata={
                        "summary": summary_result.get("summary"),
                        "key_points": summary_result.get("key_points", []),
                        "insights": insights_result.get("insights"),
                        "themes": insights_result.get("themes", []),
                        "word_count": analysis_metadata.get("word_count"),
                        "chunk_count": len(chunks)
                    }
                )
                # Step 7: Generate citation
                citation = self.summary_agent.generate_citation(
                    content=content,
                    source=source,
                    source_id=source_id,
                    metadata={
                        "title": file_name,
                        "web_view_link": metadata.get("web_view_link") if metadata else None
                    }
                )
            else:
                citation = None
            
            return {
                "success": True,
                "document_id": document_id,
                "source": source,
                "source_id": source_id,
                "chunks_created": len(chunks),
                "chunks_stored": stored_chunks,
                "summary": summary_result if not skip_metadata_and_summary else {},
                "insights": insights_result if not skip_metadata_and_summary else {},
                "metadata": analysis_metadata,
                "citation": citation,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def process_text_document(
        self,
        text_content: str,
        source: str,
        source_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        minimal: bool = False,
    ) -> Dict[str, Any]:
        """Process a text document (already extracted).
        
        Args:
            text_content: Text content
            source: Source platform
            source_id: ID in source platform
            title: Optional document title
            metadata: Optional additional metadata
            minimal: If True, only chunk+embed+store in MongoDB (no Spanner/Gemini); cheaper.
            
        Returns:
            Dictionary with processing results
        """
        file_content = text_content.encode("utf-8")
        return self.process_document(
            file_content=file_content,
            source=source,
            source_id=source_id,
            mime_type="text/plain",
            file_name=title,
            metadata=metadata,
            skip_metadata_and_summary=minimal,
        )
    
    def _generate_document_id(self, source: str, source_id: str) -> str:
        """Generate a unique document ID."""
        combined = f"{source}:{source_id}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

