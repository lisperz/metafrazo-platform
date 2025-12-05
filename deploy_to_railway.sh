#!/bin/bash

# Railway Deployment Script for Video Text Inpainting Service
# This script automates deployment to Railway.app

set -e  # Exit on error

echo "🚂 Railway Deployment Helper"
echo "============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${RED}❌ Railway CLI is not installed.${NC}"
    echo ""
    echo "Install it with one of these commands:"
    echo "  npm install -g @railway/cli"
    echo "  OR"
    echo "  brew install railway"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Railway CLI is installed${NC}"
echo ""

# Check if logged in to Railway
if ! railway whoami &> /dev/null; then
    echo -e "${YELLOW}📋 Not logged in to Railway${NC}"
    echo ""
    read -p "Do you want to login now? (y/n): " do_login

    if [ "$do_login" = "y" ]; then
        echo ""
        echo "🔐 Opening browser for Railway login..."
        railway login
        echo ""
        echo -e "${GREEN}✅ Logged in to Railway!${NC}"
    else
        echo -e "${RED}❌ Deployment cancelled. Please run 'railway login' first.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Logged in to Railway as: $(railway whoami)${NC}"
echo ""

# Check if project is initialized
if [ ! -f ".railway.json" ] && ! railway status &> /dev/null; then
    echo -e "${YELLOW}📋 Railway project not initialized${NC}"
    echo ""
    read -p "Do you want to create a new Railway project? (y/n): " create_project

    if [ "$create_project" = "y" ]; then
        echo ""
        read -p "Enter project name (e.g., video-text-inpainting): " project_name

        echo ""
        echo "🔧 Creating Railway project..."
        railway init --name "$project_name"

        echo ""
        echo -e "${GREEN}✅ Project created!${NC}"
    else
        echo -e "${RED}❌ Deployment cancelled.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Railway project exists${NC}"
echo ""

# Check if PostgreSQL is added
echo "🔍 Checking for PostgreSQL database..."
if ! railway variables | grep -q "DATABASE_URL"; then
    echo -e "${YELLOW}📋 PostgreSQL not found${NC}"
    echo ""
    read -p "Do you want to add PostgreSQL database? (y/n): " add_postgres

    if [ "$add_postgres" = "y" ]; then
        echo ""
        echo "🔧 Adding PostgreSQL..."
        railway add --database postgres
        echo ""
        echo -e "${GREEN}✅ PostgreSQL added!${NC}"
    fi
else
    echo -e "${GREEN}✅ PostgreSQL database exists${NC}"
fi
echo ""

# Check if Redis is added
echo "🔍 Checking for Redis cache..."
if ! railway variables | grep -q "REDIS_URL"; then
    echo -e "${YELLOW}📋 Redis not found${NC}"
    echo ""
    read -p "Do you want to add Redis cache? (y/n): " add_redis

    if [ "$add_redis" = "y" ]; then
        echo ""
        echo "🔧 Adding Redis..."
        railway add --database redis
        echo ""
        echo -e "${GREEN}✅ Redis added!${NC}"
    fi
else
    echo -e "${GREEN}✅ Redis cache exists${NC}"
fi
echo ""

# Check if environment variables are set
echo "🔍 Checking environment variables..."
required_vars=("JWT_SECRET_KEY" "GHOSTCUT_API_KEY" "SYNC_API_KEY" "AWS_ACCESS_KEY_ID" "AWS_S3_BUCKET")
missing_vars=()

for var in "${required_vars[@]}"; do
    if ! railway variables | grep -q "$var"; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Missing environment variables:${NC}"
    for var in "${missing_vars[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Set them with:"
    echo "  railway variables set $var=your-value"
    echo ""
    echo "Or use the Railway dashboard: https://railway.app/dashboard"
    echo ""
    read -p "Continue deployment anyway? (y/n): " continue_deploy

    if [ "$continue_deploy" != "y" ]; then
        echo -e "${RED}❌ Deployment cancelled. Please set environment variables first.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ All required environment variables set${NC}"
fi
echo ""

# Deploy backend
echo "🚀 Deploying backend service..."
echo ""
read -p "Deploy backend now? (y/n): " deploy_backend

if [ "$deploy_backend" = "y" ]; then
    echo ""
    echo "🔧 Building and deploying backend..."
    echo "   This may take 3-5 minutes..."
    echo ""

    railway up --detach

    echo ""
    echo -e "${GREEN}✅ Backend deployed!${NC}"
    echo ""

    # Get the URL
    echo "🌐 Your backend URL:"
    railway domain || echo "   Run 'railway domain' to generate a public URL"
fi

echo ""
echo "================================"
echo -e "${GREEN}🎉 Railway Deployment Complete!${NC}"
echo "================================"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Get your backend URL:"
echo "   railway domain"
echo ""
echo "2. View logs:"
echo "   railway logs"
echo ""
echo "3. Check status:"
echo "   railway status"
echo ""
echo "4. Open Railway dashboard:"
echo "   railway open"
echo ""
echo "5. Test your API:"
echo "   curl https://your-backend-url.up.railway.app/health"
echo ""
echo "6. Share with company developer:"
echo "   - Backend URL: https://your-backend-url.up.railway.app"
echo "   - API Docs: https://your-backend-url.up.railway.app/docs"
echo ""
echo -e "${GREEN}🚂 Happy deploying!${NC}"
echo ""
