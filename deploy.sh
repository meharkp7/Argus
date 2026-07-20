#!/bin/bash

# ARGUS Deployment Script
# This script builds and deploys the ARGUS application using Docker Compose

set -e  # Exit on error

echo "🚀 ARGUS Deployment Script"
echo "=========================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are installed"

# Stop existing containers
echo ""
echo "📦 Stopping existing containers..."
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
print_status "Existing containers stopped"

# Build images
echo ""
echo "🔨 Building Docker images..."
docker compose build || docker-compose build
print_status "Docker images built successfully"

# Start containers
echo ""
echo "🚀 Starting ARGUS containers..."
docker compose up -d || docker-compose up -d
print_status "Containers started"

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check backend health
echo ""
echo "🔍 Checking backend health..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -f http://localhost:8000/api/health &> /dev/null; then
        print_status "Backend is healthy"
        break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        print_error "Backend failed to start"
        docker compose logs backend || docker-compose logs backend
        exit 1
    fi
    sleep 2
done

# Check frontend health
echo ""
echo "🔍 Checking frontend health..."
if curl -f http://localhost:80 &> /dev/null; then
    print_status "Frontend is healthy"
else
    print_warning "Frontend may take a few more seconds to start"
fi

# Display status
echo ""
echo "=========================="
echo "✅ ARGUS Deployment Complete!"
echo "=========================="
echo ""
echo "🌐 Access the application:"
echo "   Frontend: http://localhost"
echo "   Backend API: http://localhost:8000"
echo "   API Health: http://localhost:8000/api/health"
echo ""
echo "📊 View logs:"
echo "   All services: docker compose logs -f"
echo "   Backend only: docker compose logs -f backend"
echo "   Frontend only: docker compose logs -f frontend"
echo ""
echo "🛑 Stop services:"
echo "   docker compose down"
echo ""
