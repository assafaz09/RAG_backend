# Authentication and Persistence Setup Guide

This guide explains how to set up the complete authentication and conversation persistence system for the RAG AI application.

## Overview

The system now includes:
- **Supabase Authentication** with Google OAuth
- **User-specific conversation persistence** using LangGraph PostgresSaver
- **Row Level Security (RLS)** for data isolation
- **Protected API endpoints** with JWT verification
- **Frontend authentication** with automatic token management

## Setup Instructions

### 1. Supabase Project Setup

1. **Create a Supabase Project**
   - Go to [supabase.com](https://supabase.com)
   - Create a new project
   - Note your project URL and anon key

2. **Configure Google OAuth**
   - In Supabase Dashboard → Authentication → Providers
   - Enable Google provider
   - Add your Google Client ID and Secret
   - Set redirect URL: `http://localhost:3000/auth/callback`

3. **Run Database Migrations**
   ```bash
   # Apply the schema to your Supabase project
   psql -h [host] -U [user] -d [database] -f supabase/migrations/001_initial_schema.sql
   psql -h [host] -U [user] -d [database] -f supabase/rls_policies.sql
   ```

### 2. Backend Configuration

1. **Environment Variables**
   ```bash
   cp .env.example .env
   ```
   
   Fill in your `.env` file:
   ```env
   # Supabase Configuration
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   SUPABASE_DB_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres
   SUPABASE_JWT_SECRET=your-jwt-secret
   
   # OpenAI API Key
   OPENAI_API_KEY=your-openai-key
   ```

2. **Install Dependencies**
   ```bash
   pip install supabase langgraph-checkpoint-postgres
   ```

3. **Start the Backend**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### 3. Frontend Configuration

1. **Environment Variables**
   ```bash
   cp frontend/env.local.example frontend/.env.local
   ```
   
   Fill in your `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

2. **Start the Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

## Key Features

### Authentication Flow
1. User clicks "Sign in with Google"
2. Redirected to Google OAuth
3. Redirected back to `/auth/callback`
4. JWT token stored and managed automatically
5. User redirected to dashboard

### Conversation Persistence
- Each conversation has a unique `thread_id`
- LangGraph state is persisted using PostgresSaver
- Conversations are isolated per user
- Full conversation history is maintained

### Security Features
- **Row Level Security (RLS)**: Users can only access their own data
- **JWT Verification**: All API endpoints verify Supabase JWT tokens
- **User Isolation**: Filesystem and data are isolated per user
- **Protected Routes**: Middleware protects sensitive routes

### API Endpoints

#### Authentication
- `GET /auth/me` - Get current user info
- `POST /auth/logout` - Logout user

#### Conversations
- `GET /conversations` - List user conversations
- `GET /conversations/{thread_id}` - Get conversation with messages
- `DELETE /conversations/{thread_id}` - Delete conversation
- `POST /chat` - Send message (creates/continues conversation)

#### MCP (Model Context Protocol)
- `POST /deploy-mcp` - Deploy MCP server configuration
- `GET /mcp-servers` - List configured MCP servers

## Database Schema

### Users Table
```sql
- id (UUID, primary key)
- email (unique)
- name
- profile_picture_url
- auth_provider ('supabase')
- auth_provider_id (Supabase user ID)
- created_at, updated_at
```

### Conversations Table
```sql
- id (UUID, primary key)
- user_id (foreign key)
- title
- thread_id (unique, for LangGraph)
- created_at
```

### Messages Table
```sql
- id (UUID, primary key)
- conversation_id (foreign key)
- role ('user' | 'assistant')
- content
- created_at
```

### Checkpoints Table
```sql
- id (UUID, primary key)
- thread_id (unique)
- checkpoint (JSONB)
- metadata (JSONB)
- created_at, updated_at
```

## Testing the System

1. **Start both services**
   ```bash
   # Backend
   uvicorn app.main:app --reload --port 8000
   
   # Frontend
   cd frontend && npm run dev
   ```

2. **Test Authentication**
   - Navigate to `http://localhost:3000/login`
   - Click "Continue with Google"
   - Complete OAuth flow
   - Should redirect to dashboard

3. **Test Conversation Persistence**
   - Start a chat conversation
   - Refresh the page
   - Conversation should be preserved
   - Check database for persisted data

4. **Test User Isolation**
   - Create conversations with different users
   - Verify users can only see their own conversations
   - Test RLS policies are working

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Ensure backend allows frontend origin
   - Check Supabase CORS settings

2. **JWT Verification Errors**
   - Verify SUPABASE_JWT_SECRET is correct
   - Check token format and expiration

3. **Database Connection Issues**
   - Verify database URL format
   - Check network connectivity
   - Ensure database user has proper permissions

4. **OAuth Redirect Issues**
   - Verify redirect URL in Google Console
   - Check Supabase auth configuration
   - Ensure callback route exists

### Debug Tips

1. **Check Browser Console** for JavaScript errors
2. **Check Network Tab** for failed API requests
3. **Check Backend Logs** for authentication errors
4. **Check Supabase Logs** for database issues

## Migration from Legacy System

If migrating from the previous JWT-only system:

1. **Update Environment Variables** with Supabase credentials
2. **Run Database Migrations** to add new tables
3. **Update Frontend** to use new auth context
4. **Test All Endpoints** with new authentication
5. **Update API Clients** to include auth headers

## Production Considerations

1. **Environment Variables**: Never commit secrets to git
2. **Database Security**: Use strong passwords and SSL
3. **JWT Secrets**: Use long, random secrets
4. **Rate Limiting**: Implement API rate limiting
5. **Monitoring**: Set up error tracking and monitoring
6. **Backups**: Regular database backups

## Support

For issues:
1. Check the troubleshooting section above
2. Review Supabase documentation
3. Check LangGraph documentation for checkpoint issues
4. Create an issue with detailed error logs
