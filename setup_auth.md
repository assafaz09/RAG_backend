# Authentication System Setup Guide

This guide will help you set up and configure the authentication system for your RAG AI System.

## Prerequisites

1. **PostgreSQL Database**: Make sure you have PostgreSQL installed and running
2. **Google OAuth Credentials**: Create a Google OAuth 2.0 client ID and secret
3. **Python Dependencies**: All required packages are listed in requirements.txt

## Setup Steps

### 1. Database Setup

```bash
# Create PostgreSQL database
createdb rag_ai_db

# Run database migrations
python -m alembic upgrade head
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure the following variables:

```bash
# Database
DATABASE_URL=postgresql://username:password@localhost/rag_ai_db

# Google OAuth (get these from Google Cloud Console)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# JWT Security (change these in production!)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:8000/auth/google/callback`
5. Copy Client ID and Client Secret to your `.env` file

### 4. Start the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Authentication Endpoints

- `GET /auth/google` - Redirect to Google OAuth
- `GET /auth/google/callback` - OAuth callback (returns JWT token)
- `GET /auth/me` - Get current user info (requires authentication)
- `POST /auth/logout` - Logout user
- `POST /auth/refresh` - Refresh JWT token

### User Management

- `GET /users/profile` - Get user profile
- `PUT /users/profile` - Update user profile
- `DELETE /users/account` - Delete user account

### Protected RAG Endpoints

All existing RAG endpoints now require authentication:

- `POST /ingest` - Ingest documents
- `POST /upload` - Upload files
- `GET /documents` - List documents
- `POST /query` - Query documents
- `GET /dashboard/stats` - Dashboard statistics
- `GET /dashboard/activity` - Recent activity

## Usage Example

### 1. Login with Google OAuth

```bash
# Get OAuth URL
curl "http://localhost:8000/auth/google"
# This will redirect to Google for authentication
```

### 2. After OAuth Callback

You'll receive a JWT token:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 3. Use Protected Endpoints

```bash
# Get current user
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     "http://localhost:8000/auth/me"

# Upload a file
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -F "file=@document.pdf" \
     "http://localhost:8000/upload"
```

## Frontend Integration

For frontend integration, you'll need to:

1. Store the JWT token securely (e.g., localStorage, httpOnly cookies)
2. Include the token in Authorization headers: `Bearer <token>`
3. Handle token refresh before expiration
4. Redirect to login when token is invalid

## Security Notes

- **JWT Secret Key**: Change the default JWT secret key in production
- **HTTPS**: Use HTTPS in production for OAuth callbacks
- **Token Expiration**: Set appropriate token expiration times
- **Database Security**: Use strong database credentials
- **OAuth Credentials**: Keep Google OAuth credentials secure

## Troubleshooting

### Common Issues

1. **Database Connection Error**: Check DATABASE_URL format and PostgreSQL status
2. **OAuth Error**: Verify Google OAuth configuration and redirect URI
3. **JWT Token Error**: Check JWT secret key configuration
4. **Import Errors**: Run `pip install -r requirements.txt`

### Debug Mode

Set environment variable for debugging:

```bash
export PYTHON_ENV=development
```

This will enable more detailed logging for troubleshooting.
