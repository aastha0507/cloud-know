"""Connector for Slack integration."""
from typing import List, Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from api.config.settings import settings


class SlackConnector:
    """Connector for interacting with Slack."""
    
    def __init__(
        self,
        bot_token: Optional[str] = None
    ):
        """Initialize Slack connector.
        
        Args:
            bot_token: Slack bot token
        """
        self.bot_token = bot_token or settings.slack_bot_token
        
        if not self.bot_token:
            raise ValueError("Slack bot token not configured")
        
        self.client = WebClient(token=self.bot_token)
    
    def get_channel_messages(
        self,
        channel_id: str,
        limit: int = 100,
        oldest: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get messages from a Slack channel.
        
        Args:
            channel_id: Slack channel ID
            limit: Maximum number of messages
            oldest: Optional timestamp to get messages after
            
        Returns:
            List of message dictionaries
        """
        try:
            result = self.client.conversations_history(
                channel=channel_id,
                limit=limit,
                oldest=oldest
            )
            
            messages = []
            for msg in result["messages"]:
                # Get user info if available
                user_name = "Unknown"
                if "user" in msg:
                    try:
                        user_info = self.client.users_info(user=msg["user"])
                        user_name = user_info["user"]["real_name"] or user_info["user"]["name"]
                    except:
                        pass
                
                messages.append({
                    "ts": msg["ts"],
                    "user": user_name,
                    "text": msg.get("text", ""),
                    "thread_ts": msg.get("thread_ts"),
                    "replies": msg.get("reply_count", 0)
                })
            
            return messages
        except SlackApiError as e:
            raise Exception(f"Slack API error: {str(e)}")
    
    def get_thread_messages(
        self,
        channel_id: str,
        thread_ts: str
    ) -> List[Dict[str, Any]]:
        """Get messages in a thread.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            
        Returns:
            List of thread message dictionaries
        """
        try:
            result = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )
            
            messages = []
            for msg in result["messages"]:
                user_name = "Unknown"
                if "user" in msg:
                    try:
                        user_info = self.client.users_info(user=msg["user"])
                        user_name = user_info["user"]["real_name"] or user_info["user"]["name"]
                    except:
                        pass
                
                messages.append({
                    "ts": msg["ts"],
                    "user": user_name,
                    "text": msg.get("text", "")
                })
            
            return messages
        except SlackApiError as e:
            raise Exception(f"Slack API error: {str(e)}")
    
    def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get information about a channel.
        
        Args:
            channel_id: Slack channel ID
            
        Returns:
            Channel information dictionary
        """
        try:
            result = self.client.conversations_info(channel=channel_id)
            channel = result["channel"]
            
            return {
                "id": channel["id"],
                "name": channel["name"],
                "topic": channel.get("topic", {}).get("value", ""),
                "purpose": channel.get("purpose", {}).get("value", ""),
                "created": channel.get("created"),
                "num_members": channel.get("num_members", 0)
            }
        except SlackApiError as e:
            raise Exception(f"Slack API error: {str(e)}")
    
    def format_conversation_content(
        self,
        messages: List[Dict[str, Any]],
        channel_name: Optional[str] = None
    ) -> str:
        """Format Slack messages into a single text content.
        
        Args:
            messages: List of message dictionaries
            channel_name: Optional channel name for context
            
        Returns:
            Formatted conversation text
        """
        content_parts = []
        
        if channel_name:
            content_parts.append(f"Channel: {channel_name}\n")
        
        for msg in messages:
            user = msg.get("user", "Unknown")
            text = msg.get("text", "")
            content_parts.append(f"{user}: {text}")
        
        return "\n".join(content_parts)

