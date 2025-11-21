"""Agent for generating summaries and insights from documents."""
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from api.config.settings import settings


class SummaryInsightAgent:
    """Agent responsible for generating summaries and insights."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the summary and insight agent.
        
        Args:
            api_key: Gemini API key. If None, uses settings.
        """
        self.api_key = api_key or settings.gemini_api_key
        genai.configure(api_key=self.api_key)
        # Use model from settings, with fallback
        model_name = getattr(settings, 'gemini_model_name', 'gemini-pro')
        try:
            self.model = genai.GenerativeModel(model_name)
        except Exception:
            # Fallback to gemini-pro if specified model doesn't work
            try:
                self.model = genai.GenerativeModel("gemini-pro")
            except Exception:
                # Last resort: try gemini-1.5-flash
                self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    def generate_summary(
        self,
        content: str,
        max_length: int = 200,
        include_key_points: bool = True
    ) -> Dict[str, Any]:
        """Generate a summary of the document.
        
        Args:
            content: Document content
            max_length: Maximum length of summary in words
            include_key_points: Whether to include key points
            
        Returns:
            Dictionary with summary and key points
        """
        try:
            prompt = f"""Please provide a concise summary of the following content in approximately {max_length} words.
            
Content:
{content[:5000]}  # Limit content to avoid token limits

Please provide:
1. A brief summary
2. Key points (if requested)
"""
            
            if not include_key_points:
                prompt += "\nFocus only on the summary."
            
            response = self.model.generate_content(prompt)
            
            summary_text = response.text
            
            result = {
                "summary": summary_text,
                "word_count": len(summary_text.split()),
                "generated_at": None  # Will be set by caller
            }
            
            if include_key_points:
                result["key_points"] = self._extract_key_points(summary_text)
            
            return result
        except Exception as e:
            return {
                "summary": f"[Error generating summary: {str(e)}]",
                "error": str(e)
            }
    
    def generate_insights(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate insights from document content.
        
        Args:
            content: Document content
            context: Optional context dictionary (metadata, relationships, etc.)
            
        Returns:
            Dictionary with insights
        """
        try:
            context_str = ""
            if context:
                context_str = f"\n\nContext:\n{self._format_context(context)}"
            
            prompt = f"""Analyze the following content and provide actionable insights.

Content:
{content[:5000]}{context_str}

Please provide:
1. Main themes and topics
2. Important relationships or connections
3. Action items or recommendations (if any)
4. Potential questions this content answers
"""
            
            response = self.model.generate_content(prompt)
            
            insights_text = response.text
            
            return {
                "insights": insights_text,
                "themes": self._extract_themes(insights_text),
                "action_items": self._extract_action_items(insights_text),
                "generated_at": None  # Will be set by caller
            }
        except Exception as e:
            return {
                "insights": f"[Error generating insights: {str(e)}]",
                "error": str(e)
            }
    
    def generate_citation(
        self,
        content: str,
        source: str,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a citation for the document.
        
        Args:
            content: Document content
            source: Source platform
            source_id: ID in source platform
            metadata: Optional metadata
            
        Returns:
            Citation dictionary
        """
        citation = {
            "source": source,
            "source_id": source_id,
            "title": metadata.get("title") if metadata else None,
            "url": metadata.get("web_view_link") or metadata.get("url") if metadata else None,
            "accessed_at": None  # Will be set by caller
        }
        
        # Format citation based on source
        if source == "google_drive":
            citation["formatted"] = self._format_drive_citation(citation)
        elif source == "jira":
            citation["formatted"] = self._format_jira_citation(citation)
        elif source == "slack":
            citation["formatted"] = self._format_slack_citation(citation)
        else:
            citation["formatted"] = f"{source}: {source_id}"
        
        return citation
    
    def _extract_key_points(self, summary: str) -> List[str]:
        """Extract key points from summary text."""
        # Simple extraction - look for numbered or bulleted lists
        import re
        key_points = []
        
        # Match numbered lists
        numbered = re.findall(r'\d+\.\s+([^\n]+)', summary)
        if numbered:
            key_points.extend(numbered)
        
        # Match bullet points
        bullets = re.findall(r'[-•]\s+([^\n]+)', summary)
        if bullets:
            key_points.extend(bullets)
        
        # If no structured list found, split by sentences
        if not key_points:
            sentences = summary.split('. ')
            key_points = [s.strip() for s in sentences[:5] if s.strip()]
        
        return key_points[:10]  # Limit to 10 key points
    
    def _extract_themes(self, insights: str) -> List[str]:
        """Extract main themes from insights."""
        # Simple keyword extraction for themes
        theme_keywords = ["theme", "topic", "subject", "focus", "area"]
        themes = []
        
        for keyword in theme_keywords:
            # Look for patterns like "Theme: X" or "Main topic: Y"
            pattern = rf'{keyword}[:\s]+([^\n,\.]+)'
            import re
            matches = re.findall(pattern, insights, re.IGNORECASE)
            themes.extend(matches)
        
        return themes[:5] if themes else []
    
    def _extract_action_items(self, insights: str) -> List[str]:
        """Extract action items from insights."""
        action_keywords = ["action", "recommend", "suggest", "should", "must", "need"]
        action_items = []
        
        import re
        for keyword in action_keywords:
            # Look for sentences containing action keywords
            pattern = rf'[^\.]*{keyword}[^\.]*\.'
            matches = re.findall(pattern, insights, re.IGNORECASE)
            action_items.extend(matches)
        
        return action_items[:5] if action_items else []
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as string."""
        lines = []
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"{key}: {value}")
            elif isinstance(value, list):
                lines.append(f"{key}: {', '.join(str(v) for v in value[:5])}")
            elif isinstance(value, dict):
                lines.append(f"{key}: {self._format_context(value)}")
        return "\n".join(lines)
    
    def _format_drive_citation(self, citation: Dict[str, Any]) -> str:
        """Format Google Drive citation."""
        title = citation.get("title", "Untitled Document")
        url = citation.get("url", "")
        if url:
            return f"{title} - Google Drive ({url})"
        return f"{title} - Google Drive"
    
    def _format_jira_citation(self, citation: Dict[str, Any]) -> str:
        """Format Jira citation."""
        title = citation.get("title", citation.get("source_id", "Jira Issue"))
        return f"Jira: {title} ({citation.get('source_id')})"
    
    def _format_slack_citation(self, citation: Dict[str, Any]) -> str:
        """Format Slack citation."""
        title = citation.get("title", "Slack Message")
        return f"Slack: {title}"

