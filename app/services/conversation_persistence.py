"""
Conversation Persistence Service using LangGraph
Handles persistent conversation state with Supabase PostgreSQL
"""
import sys

from typing import Optional, Dict, Any
import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.db.models import User, Conversation
import logging

# For now, we'll use a simpler approach without PostgresSaver
# TODO: Re-enable PostgresSaver once psycopg issues are resolved

logger = logging.getLogger(__name__)

class ConversationPersistenceService:
    """Service for managing conversation persistence with LangGraph"""
    
    def __init__(self):
        # For now, disable checkpoint saver until psycopg issues are resolved
        self.checkpoint_saver = None
        logger.info("ConversationPersistenceService initialized (PostgresSaver disabled)")
    
    def _initialize_checkpointer(self):
        """Initialize PostgresSaver with Supabase connection"""
        # Disabled for now - TODO: Re-enable once psycopg issues are resolved
        pass
    
    def get_or_create_conversation(
        self, 
        db: Session, 
        user: User, 
        thread_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Conversation:
        """
        Get existing conversation or create new one
        """
        if thread_id:
            # Try to get existing conversation by thread_id
            conv = db.query(Conversation).filter(
                Conversation.thread_id == thread_id,
                Conversation.user_id == user.id
            ).first()
            
            if conv:
                return conv
        
        # Create new conversation
        if not thread_id:
            thread_id = str(uuid.uuid4())
        
        if not title:
            title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        conv = Conversation(
            user_id=user.id,
            title=title,
            thread_id=thread_id
        )
        
        db.add(conv)
        db.commit()
        db.refresh(conv)
        
        logger.info(f"Created conversation {conv.id} for user {user.id}")
        return conv
    
    def save_checkpoint(
        self, 
        thread_id: str, 
        checkpoint: Dict[str, Any], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save LangGraph checkpoint to database
        """
        if not self.checkpoint_saver:
            logger.error("Checkpoint saver not initialized")
            return False
        
        try:
            # Use LangGraph's checkpoint saver
            config = {"thread_id": thread_id}
            self.checkpoint_saver.put(config, checkpoint, metadata)
            return True
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False
    
    def load_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Load LangGraph checkpoint from database
        """
        if not self.checkpoint_saver:
            logger.error("Checkpoint saver not initialized")
            return None
        
        try:
            config = {"thread_id": thread_id}
            checkpoint_tuple = self.checkpoint_saver.get(config)
            
            if checkpoint_tuple:
                checkpoint, metadata = checkpoint_tuple
                return {
                    "checkpoint": checkpoint,
                    "metadata": metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def list_user_conversations(self, db: Session, user: User) -> list[Conversation]:
        """
        List all conversations for a user
        """
        return db.query(Conversation).filter(
            Conversation.user_id == user.id
        ).order_by(Conversation.created_at.desc()).all()
    
    def delete_conversation(self, db: Session, user: User, conversation_id: str) -> bool:
        """
        Delete a conversation and all its data
        """
        try:
            conv = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id
            ).first()
            
            if not conv:
                return False
            
            # Delete checkpoint
            if self.checkpoint_saver:
                try:
                    config = {"thread_id": conv.thread_id}
                    self.checkpoint_saver.delete(config)
                except Exception as e:
                    logger.warning(f"Failed to delete checkpoint: {e}")
            
            # Delete conversation (cascade will delete messages)
            db.delete(conv)
            db.commit()
            
            logger.info(f"Deleted conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            db.rollback()
            return False
    
    def get_user_filesystem_root(self, user: User) -> str:
        """
        Get user-specific filesystem root for data isolation
        """
        return f"user_data/{user.id}"
    
    def validate_user_access(self, user: User, thread_id: str) -> bool:
        """
        Validate that user has access to the given thread/conversation
        """
        from app.db.database import get_db
        
        with get_db() as db:
            conv = db.query(Conversation).filter(
                Conversation.thread_id == thread_id,
                Conversation.user_id == user.id
            ).first()
            
            return conv is not None

# Global instance
conversation_persistence = ConversationPersistenceService()
