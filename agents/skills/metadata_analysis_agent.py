"""Agent for analyzing and extracting metadata from documents."""
from typing import Dict, Any, Optional, List
import re
from datetime import datetime


class MetadataAnalysisAgent:
    """Agent responsible for analyzing documents and extracting metadata."""
    
    def __init__(self):
        """Initialize the metadata analysis agent."""
        self.common_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "url": r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            "date": r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "jira_ticket": r'[A-Z]+-\d+',
            "github_issue": r'#[0-9]+',
        }
    
    def analyze(self, content: str, source: str, source_id: str, **kwargs) -> Dict[str, Any]:
        """Analyze document content and extract metadata.
        
        Args:
            content: Document content
            source: Source platform (e.g., "google_drive", "jira")
            source_id: ID in the source platform
            **kwargs: Additional context (file_name, mime_type, etc.)
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            "source": source,
            "source_id": source_id,
            "analyzed_at": datetime.utcnow().isoformat(),
            "content_length": len(content),
            "word_count": len(content.split()),
            "estimated_reading_time": self._estimate_reading_time(content),
        }
        
        # Extract patterns
        metadata["extracted_patterns"] = self._extract_patterns(content)
        
        # Extract topics/keywords
        metadata["keywords"] = self._extract_keywords(content)
        
        # Extract entities
        metadata["entities"] = self._extract_entities(content)
        
        # Source-specific analysis
        if source == "jira":
            metadata.update(self._analyze_jira_content(content))
        elif source == "slack":
            metadata.update(self._analyze_slack_content(content))
        elif source == "google_drive":
            metadata.update(self._analyze_drive_content(content, **kwargs))
        
        # Add any additional kwargs
        metadata.update({k: v for k, v in kwargs.items() if v is not None})
        
        return metadata
    
    def _extract_patterns(self, content: str) -> Dict[str, List[str]]:
        """Extract common patterns from content."""
        patterns = {}
        for pattern_name, pattern_regex in self.common_patterns.items():
            matches = re.findall(pattern_regex, content)
            if matches:
                patterns[pattern_name] = list(set(matches))  # Remove duplicates
        return patterns
    
    def _extract_keywords(self, content: str, top_n: int = 10) -> List[str]:
        """Extract top keywords from content."""
        # Simple keyword extraction based on frequency
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        
        # Common stop words to filter
        stop_words = {
            "the", "and", "for", "are", "but", "not", "you", "all", "can", "her",
            "was", "one", "our", "out", "day", "get", "has", "him", "his", "how",
            "its", "may", "new", "now", "old", "see", "two", "way", "who", "boy",
            "did", "has", "let", "put", "say", "she", "too", "use"
        }
        
        # Count word frequencies
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top N
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:top_n]]
    
    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract named entities from content."""
        # Simple entity extraction (can be enhanced with NER models)
        entities = {
            "people": [],
            "organizations": [],
            "locations": []
        }
        
        # Extract capitalized words/phrases (simple heuristic)
        capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        
        # This is a simplified version - in production, use proper NER
        for phrase in capitalized_phrases:
            if len(phrase.split()) == 1:
                # Single word - could be person or organization
                if phrase not in ["The", "This", "That", "These", "Those"]:
                    entities["people"].append(phrase)
            else:
                # Multi-word - likely organization
                entities["organizations"].append(phrase)
        
        return entities
    
    def _estimate_reading_time(self, content: str, words_per_minute: int = 200) -> int:
        """Estimate reading time in minutes."""
        word_count = len(content.split())
        return max(1, word_count // words_per_minute)
    
    def _analyze_jira_content(self, content: str) -> Dict[str, Any]:
        """Analyze Jira-specific content."""
        metadata = {}
        
        # Extract Jira ticket references
        ticket_refs = re.findall(r'[A-Z]+-\d+', content)
        if ticket_refs:
            metadata["referenced_tickets"] = list(set(ticket_refs))
        
        # Detect issue type keywords
        issue_keywords = {
            "bug": ["bug", "error", "crash", "broken", "fix"],
            "feature": ["feature", "enhancement", "improvement", "new"],
            "task": ["task", "work", "implement"],
        }
        
        content_lower = content.lower()
        detected_types = []
        for issue_type, keywords in issue_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_types.append(issue_type)
        
        if detected_types:
            metadata["detected_issue_types"] = detected_types
        
        return metadata
    
    def _analyze_slack_content(self, content: str) -> Dict[str, Any]:
        """Analyze Slack-specific content."""
        metadata = {}
        
        # Extract mentions
        mentions = re.findall(r'<@[A-Z0-9]+>', content)
        if mentions:
            metadata["mentions"] = list(set(mentions))
        
        # Extract channels
        channels = re.findall(r'<#[A-Z0-9]+\|[^>]+>', content)
        if channels:
            metadata["channel_references"] = channels
        
        # Extract links
        links = re.findall(r'<https?://[^>]+>', content)
        if links:
            metadata["links"] = links
        
        return metadata
    
    def _analyze_drive_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """Analyze Google Drive-specific content."""
        metadata = {}
        
        # Extract document structure
        if kwargs.get("mime_type") == "application/vnd.google-apps.document":
            # Count headings, lists, etc.
            heading_count = len(re.findall(r'^#+\s', content, re.MULTILINE))
            if heading_count > 0:
                metadata["has_headings"] = True
                metadata["heading_count"] = heading_count
        
        return metadata

