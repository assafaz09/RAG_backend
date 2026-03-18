-- Row Level Security (RLS) Policies for RAG AI System
-- These policies ensure users can only access their own data

-- Drop existing policies if they exist (for idempotency)
DROP POLICY IF EXISTS "Users can view their own profile" ON users;
DROP POLICY IF EXISTS "Users can update their own profile" ON users;
DROP POLICY IF EXISTS "Users can view their own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can create their own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can update their own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can delete their own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can view messages in their conversations" ON messages;
DROP POLICY IF EXISTS "Users can create messages in their conversations" ON messages;
DROP POLICY IF EXISTS "Users can view their own checkpoints" ON checkpoints;
DROP POLICY IF EXISTS "Users can create their own checkpoints" ON checkpoints;
DROP POLICY IF EXISTS "Users can update their own checkpoints" ON checkpoints;

-- Users table policies
CREATE POLICY "Users can view their own profile" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile" ON users
    FOR UPDATE USING (auth.uid() = id);

-- Conversations table policies
CREATE POLICY "Users can view their own conversations" ON conversations
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own conversations" ON conversations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own conversations" ON conversations
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own conversations" ON conversations
    FOR DELETE USING (auth.uid() = user_id);

-- Messages table policies
CREATE POLICY "Users can view messages in their conversations" ON messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM conversations 
            WHERE conversations.id = messages.conversation_id 
            AND conversations.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create messages in their conversations" ON messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM conversations 
            WHERE conversations.id = messages.conversation_id 
            AND conversations.user_id = auth.uid()
        )
    );

-- Checkpoints table policies (for LangGraph persistence)
CREATE POLICY "Users can view their own checkpoints" ON checkpoints
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM conversations 
            WHERE conversations.thread_id = checkpoints.thread_id 
            AND conversations.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create their own checkpoints" ON checkpoints
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM conversations 
            WHERE conversations.thread_id = checkpoints.thread_id 
            AND conversations.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update their own checkpoints" ON checkpoints
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM conversations 
            WHERE conversations.thread_id = checkpoints.thread_id 
            AND conversations.user_id = auth.uid()
        )
    );

-- Admin policies (for service operations)
-- These allow the service role key to bypass RLS
CREATE POLICY "Service role can manage all users" ON users
    FOR ALL USING (current_setting('request.jwt.claims', true)::jsonb->>'role' = 'service_role');

CREATE POLICY "Service role can manage all conversations" ON conversations
    FOR ALL USING (current_setting('request.jwt.claims', true)::jsonb->>'role' = 'service_role');

CREATE POLICY "Service role can manage all messages" ON messages
    FOR ALL USING (current_setting('request.jwt.claims', true)::jsonb->>'role' = 'service_role');

CREATE POLICY "Service role can manage all checkpoints" ON checkpoints
    FOR ALL USING (current_setting('request.jwt.claims', true)::jsonb->>'role' = 'service_role');
