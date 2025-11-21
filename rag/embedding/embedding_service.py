"""Embedding service using Google Gemini API."""
from typing import List, Union
import google.generativeai as genai
from api.config.settings import settings


class EmbeddingService:
    """Service for generating embeddings using Gemini API."""
    
    def __init__(self, api_key: str = None):
        """Initialize embedding service.
        
        Args:
            api_key: Gemini API key. If None, uses settings.
        """
        self.api_key = api_key or settings.gemini_api_key
        genai.configure(api_key=self.api_key)
        self.model = "text-embedding-004"
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
        """
        try:
            result = genai.embed_content(
                model=self.model,
                content=text
            )
            # Handle different response formats
            if isinstance(result, dict):
                return result.get('embedding', [])
            elif hasattr(result, 'embedding'):
                embedding = result.embedding
                if hasattr(embedding, 'values'):
                    return list(embedding.values)
                elif isinstance(embedding, list):
                    return embedding
                else:
                    return list(embedding)
            else:
                return list(result) if result else []
        except Exception as e:
            raise Exception(f"Error generating embedding: {str(e)}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embeddings.append(self.embed(text))
        return embeddings
