"""Connector for Jira integration."""
from typing import List, Dict, Any, Optional
from jira import JIRA
from api.config.settings import settings


class JiraConnector:
    """Connector for interacting with Jira."""
    
    def __init__(
        self,
        server: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None
    ):
        """Initialize Jira connector.
        
        Args:
            server: Jira server URL
            email: Jira user email
            api_token: Jira API token
        """
        self.server = server or settings.jira_server
        self.email = email or settings.jira_email
        self.api_token = api_token or settings.jira_api_token
        
        if not all([self.server, self.email, self.api_token]):
            raise ValueError("Jira credentials not configured")
        
        self.client = JIRA(
            server=self.server,
            basic_auth=(self.email, self.api_token)
        )
    
    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get a Jira issue by key.
        
        Args:
            issue_key: Jira issue key (e.g., "PROJ-123")
            
        Returns:
            Dictionary with issue data
        """
        try:
            issue = self.client.issue(issue_key)
            
            # Extract comments
            comments = []
            for comment in issue.fields.comment.comments:
                comments.append({
                    "author": comment.author.displayName,
                    "body": comment.body,
                    "created": comment.created
                })
            
            # Build content
            content_parts = [
                f"Title: {issue.fields.summary}",
                f"Description: {issue.fields.description or 'No description'}",
                f"Status: {issue.fields.status.name}",
                f"Priority: {issue.fields.priority.name if issue.fields.priority else 'None'}",
                f"Assignee: {issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'}",
            ]
            
            if comments:
                content_parts.append("\nComments:")
                for comment in comments:
                    content_parts.append(f"\n{comment['author']} ({comment['created']}):")
                    content_parts.append(comment['body'])
            
            content = "\n".join(content_parts)
            
            return {
                "issue_key": issue_key,
                "summary": issue.fields.summary,
                "description": issue.fields.description,
                "status": issue.fields.status.name,
                "priority": issue.fields.priority.name if issue.fields.priority else None,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
                "reporter": issue.fields.reporter.displayName if issue.fields.reporter else None,
                "created": str(issue.fields.created),
                "updated": str(issue.fields.updated),
                "content": content,
                "url": f"{self.server}/browse/{issue_key}",
                "comments": comments
            }
        except Exception as e:
            raise Exception(f"Error getting Jira issue: {str(e)}")
    
    def search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for Jira issues using JQL.
        
        Args:
            jql: Jira Query Language query
            max_results: Maximum number of results
            
        Returns:
            List of issue dictionaries
        """
        try:
            issues = self.client.search_issues(jql, maxResults=max_results)
            
            results = []
            for issue in issues:
                results.append({
                    "issue_key": issue.key,
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name,
                    "url": f"{self.server}/browse/{issue.key}"
                })
            
            return results
        except Exception as e:
            raise Exception(f"Error searching Jira issues: {str(e)}")
    
    def get_project_issues(self, project_key: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all issues for a project.
        
        Args:
            project_key: Jira project key
            limit: Maximum number of issues
            
        Returns:
            List of issue dictionaries
        """
        jql = f"project = {project_key} ORDER BY updated DESC"
        return self.search_issues(jql, max_results=limit)

