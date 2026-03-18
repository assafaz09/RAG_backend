"""
Database indexes for performance optimization
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_performance_indexes'
down_revision = '791b3732410e'
branch_labels = None
depends_on = None

def upgrade():
    """Add performance indexes"""
    # Index for user conversations lookup
    op.create_index('idx_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('idx_conversations_thread_id', 'conversations', ['thread_id'])
    
    # Index for message queries
    op.create_index('idx_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('idx_messages_created_at', 'messages', ['created_at'])
    
    # Composite index for user conversation queries
    op.create_index('idx_conversations_user_created', 'conversations', ['user_id', 'created_at'])
    
    # Index for auth provider lookups
    op.create_index('idx_users_auth_provider_id', 'users', ['auth_provider_id'])
    op.create_index('idx_users_auth_provider', 'users', ['auth_provider'])

def downgrade():
    """Remove performance indexes"""
    op.drop_index('idx_users_auth_provider', table_name='users')
    op.drop_index('idx_users_auth_provider_id', table_name='users')
    op.drop_index('idx_conversations_user_created', table_name='conversations')
    op.drop_index('idx_messages_created_at', table_name='messages')
    op.drop_index('idx_messages_conversation_id', table_name='messages')
    op.drop_index('idx_conversations_thread_id', table_name='conversations')
    op.drop_index('idx_conversations_user_id', table_name='conversations')
