"""Agent for chunking documents into smaller pieces for embedding."""
from typing import List, Dict, Any, Optional, Tuple
import re


class ChunkingAgent:
    """Agent responsible for splitting documents into chunks."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None
    ):
        """Initialize the chunking agent.
        
        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            separators: List of separators to use for splitting (in order of preference)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentence endings
            " ",     # Word breaks
            ""       # Character breaks (fallback)
        ]
    
    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Split text into chunks.
        
        Args:
            text: Text content to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries with content and metadata
        """
        if not text or len(text.strip()) == 0:
            return []
        
        chunks = []
        current_text = text
        chunk_index = 0
        
        while len(current_text) > 0:
            # Try to find the best split point
            chunk_text, remaining_text = self._split_text(current_text)
            
            if chunk_text:
                chunk = {
                    "chunk_id": f"{metadata.get('document_id', 'doc')}_chunk_{chunk_index}",
                    "content": chunk_text.strip(),
                    "chunk_index": chunk_index,
                    "metadata": {
                        **(metadata or {}),
                        "chunk_size": len(chunk_text),
                        "total_chunks": None  # Will be updated later
                    }
                }
                chunks.append(chunk)
                chunk_index += 1
            
            current_text = remaining_text
            
            # Safety check to prevent infinite loops
            if len(remaining_text) == len(current_text):
                # No progress made, force a split
                if len(current_text) > self.chunk_size:
                    chunk_text = current_text[:self.chunk_size]
                    current_text = current_text[self.chunk_size - self.chunk_overlap:]
                else:
                    # Last chunk
                    if current_text.strip():
                        chunk = {
                            "chunk_id": f"{metadata.get('document_id', 'doc')}_chunk_{chunk_index}",
                            "content": current_text.strip(),
                            "chunk_index": chunk_index,
                            "metadata": {
                                **(metadata or {}),
                                "chunk_size": len(current_text),
                                "total_chunks": None
                            }
                        }
                        chunks.append(chunk)
                    break
        
        # Update total_chunks in metadata
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = len(chunks)
        
        return chunks
    
    def _split_text(self, text: str) -> Tuple[str, str]:
        """Split text at the best separator.
        
        Args:
            text: Text to split
            
        Returns:
            Tuple of (chunk_text, remaining_text)
        """
        # If text is smaller than chunk size, return it all
        if len(text) <= self.chunk_size:
            return text, ""
        
        # Try each separator in order
        for separator in self.separators:
            if separator == "":
                # Character-level split (fallback)
                chunk_text = text[:self.chunk_size]
                remaining_text = text[self.chunk_size - self.chunk_overlap:]
                return chunk_text, remaining_text
            
            # Find the last occurrence of separator before chunk_size
            search_text = text[:self.chunk_size + len(separator)]
            last_index = search_text.rfind(separator)
            
            if last_index != -1:
                # Found a good split point
                chunk_text = text[:last_index + len(separator)]
                remaining_text = text[last_index + len(separator) - self.chunk_overlap:]
                return chunk_text, remaining_text
        
        # Fallback: split at chunk_size
        chunk_text = text[:self.chunk_size]
        remaining_text = text[self.chunk_size - self.chunk_overlap:]
        return chunk_text, remaining_text
    
    def chunk_by_sentences(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Chunk text by sentences, grouping them to fit chunk_size.
        
        Args:
            text: Text content to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries
        """
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunk = {
                    "chunk_id": f"{metadata.get('document_id', 'doc')}_chunk_{chunk_index}",
                    "content": chunk_text,
                    "chunk_index": chunk_index,
                    "metadata": {
                        **(metadata or {}),
                        "chunk_size": len(chunk_text),
                        "total_chunks": None
                    }
                }
                chunks.append(chunk)
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_sentences = current_chunk[-self._get_overlap_sentence_count():]
                current_chunk = overlap_sentences + [sentence]
                current_size = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk = {
                "chunk_id": f"{metadata.get('document_id', 'doc')}_chunk_{chunk_index}",
                "content": chunk_text,
                "chunk_index": chunk_index,
                "metadata": {
                    **(metadata or {}),
                    "chunk_size": len(chunk_text),
                    "total_chunks": None
                }
            }
            chunks.append(chunk)
        
        # Update total_chunks
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = len(chunks)
        
        return chunks
    
    def _get_overlap_sentence_count(self) -> int:
        """Calculate how many sentences to include in overlap."""
        # Rough estimate: assume average sentence length of 50 chars
        avg_sentence_length = 50
        return max(1, self.chunk_overlap // avg_sentence_length)

