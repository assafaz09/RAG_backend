#!/bin/bash

# Multi-Agent Orchestration System Deployment Script
# This script deploys the system to production

set -e

echo "🚀 Starting Multi-Agent Orchestration System Deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it with the required environment variables."
    exit 1
fi

# Load environment variables
source .env

# Check required environment variables
required_vars=("OPENAI_API_KEY" "POSTGRES_PASSWORD" "DOMAIN_NAME")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Create necessary directories
mkdir -p nginx/ssl
mkdir -p logs

# Generate SSL certificate (self-signed for demo, replace with real cert in production)
if [ ! -f nginx/ssl/cert.pem ]; then
    echo "🔐 Generating SSL certificate..."
    openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 -nodes \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=${DOMAIN_NAME}"
fi

# Create nginx configuration
cat > nginx/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server app:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;
        server_name ${DOMAIN_NAME};
        return 301 https://\$server_name\$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name ${DOMAIN_NAME};

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # Backend API
        location /api/ {
            proxy_pass http://backend/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # WebSocket connections
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # Health check
        location /health {
            proxy_pass http://backend/health;
        }
    }
}
EOF

echo "✅ Nginx configuration created"

# Pull latest images
echo "📦 Pulling Docker images..."
docker-compose -f docker-compose.prod.yml pull

# Build and start services
echo "🔨 Building and starting services..."
docker-compose -f docker-compose.prod.yml up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# Check service health
echo "🏥 Checking service health..."
for service in app postgres qdrant redis nginx; do
    if docker-compose -f docker-compose.prod.yml ps $service | grep -q "Up (healthy)"; then
        echo "✅ $service is healthy"
    else
        echo "❌ $service is not healthy"
        docker-compose -f docker-compose.prod.yml logs $service
    fi
done

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "🌐 Access your application at:"
echo "   HTTP: http://${DOMAIN_NAME}"
echo "   HTTPS: https://${DOMAIN_NAME}"
echo ""
echo "📊 Service URLs:"
echo "   Frontend: https://${DOMAIN_NAME}"
echo "   Backend API: https://${DOMAIN_NAME}/api"
echo "   Health Check: https://${DOMAIN_NAME}/health"
echo ""
echo "🔧 Management commands:"
echo "   View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "   Stop services: docker-compose -f docker-compose.prod.yml down"
echo "   Update: docker-compose -f docker-compose.prod.yml pull && docker-compose -f docker-compose.prod.yml up --build -d"
echo ""
echo "📝 Next steps:"
echo "   1. Configure your SSL certificate with a real certificate"
echo "   2. Set up monitoring and logging"
echo "   3. Configure backup strategies"
echo "   4. Set up CI/CD pipeline"
