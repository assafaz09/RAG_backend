"""
User MCP Configuration Service
Manages user-specific MCP configurations in a thread-safe manner
"""
from typing import Dict, Any, Optional
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class UserMCPService:
    """Thread-safe service for managing user MCP configurations"""
    
    def __init__(self):
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        logger.info("UserMCPService initialized with thread-safe storage")
    
    def set_config(self, user_id: str, config: Dict[str, Any]) -> None:
        """Set MCP configuration for a user"""
        with self._lock:
            self._configs[user_id] = config
            logger.info(f"Set MCP config for user {user_id}")
    
    def get_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get MCP configuration for a user"""
        with self._lock:
            return self._configs.get(user_id)
    
    def set_tools(self, user_id: str, tools: Dict[str, Any]) -> None:
        """Set MCP tools for a user"""
        with self._lock:
            self._tools[user_id] = tools
            logger.info(f"Set MCP tools for user {user_id}")
    
    def get_tools(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get MCP tools for a user"""
        with self._lock:
            return self._tools.get(user_id)
    
    def clear_user_data(self, user_id: str) -> None:
        """Clear all data for a user"""
        with self._lock:
            self._configs.pop(user_id, None)
            self._tools.pop(user_id, None)
            logger.info(f"Cleared MCP data for user {user_id}")
    
    def get_all_users(self) -> list[str]:
        """Get all user IDs with data"""
        with self._lock:
            return list(set(self._configs.keys()) | set(self._tools.keys()))

# Global instance
user_mcp_service = UserMCPService()
