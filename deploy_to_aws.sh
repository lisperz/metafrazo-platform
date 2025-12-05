#!/bin/bash

# AWS Deployment Script for Video Text Inpainting Service
# This script helps you deploy to AWS Elastic Beanstalk

set -e  # Exit on error

echo "🚀 AWS Elastic Beanstalk Deployment Helper"
echo "=========================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed."
    echo "   Install it with: brew install awscli"
    exit 1
fi

# Check if EB CLI is installed
if ! command -v eb &> /dev/null; then
    echo "❌ Elastic Beanstalk CLI is not installed."
    echo "   Install it with: pip install awsebcli --upgrade --user"
    exit 1
fi

echo "✅ AWS CLI and EB CLI are installed"
echo ""

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials are not configured."
    echo "   Run: aws configure"
    exit 1
fi

echo "✅ AWS credentials are configured"
echo ""

# Check if .elasticbeanstalk directory exists (EB initialized)
if [ ! -d ".elasticbeanstalk" ]; then
    echo "📋 Elastic Beanstalk is not initialized yet."
    echo ""
    read -p "Do you want to initialize EB now? (y/n): " init_eb

    if [ "$init_eb" = "y" ]; then
        echo ""
        echo "🔧 Initializing Elastic Beanstalk application..."
        echo "   Please follow the prompts:"
        echo "   - Select region (e.g., us-east-1)"
        echo "   - Application name: video-text-inpainting"
        echo "   - Platform: Docker (Multi-container)"
        echo "   - Set up SSH: Yes (recommended for debugging)"
        echo ""
        eb init

        echo ""
        echo "✅ EB initialized!"
    else
        echo "❌ Deployment cancelled. Please run 'eb init' manually first."
        exit 1
    fi
fi

echo "✅ Elastic Beanstalk is initialized"
echo ""

# Check if environment exists
if ! eb status &> /dev/null; then
    echo "📋 No EB environment exists yet."
    echo ""
    read -p "Do you want to create a new environment? (y/n): " create_env

    if [ "$create_env" = "y" ]; then
        echo ""
        read -p "Enter environment name (e.g., video-inpainting-prod): " env_name
        read -p "Enter database password: " db_password

        echo ""
        echo "🔧 Creating EB environment with RDS database..."
        echo "   This will take 10-15 minutes..."
        echo ""

        eb create $env_name \
            --database.engine postgres \
            --database.username vti_user \
            --database.password $db_password \
            --instance-type t3.medium

        echo ""
        echo "✅ Environment created!"
        echo ""
        echo "⚠️  IMPORTANT: You need to set environment variables!"
        echo "   Run: eb setenv KEY=VALUE KEY2=VALUE2 ..."
        echo "   See .env.production.example for all required variables"
        exit 0
    else
        echo "❌ Deployment cancelled."
        exit 1
    fi
fi

echo "✅ EB environment exists"
echo ""

# Deploy
echo "🚀 Deploying application..."
echo ""
eb deploy

echo ""
echo "✅ Deployment complete!"
echo ""

# Show status
echo "📊 Environment status:"
eb status

echo ""
echo "🌐 Your application URL:"
eb status | grep "CNAME" | awk '{print "   https://"$2}'

echo ""
echo "📋 Next steps:"
echo "   1. Test your deployment: eb open"
echo "   2. View logs: eb logs"
echo "   3. Monitor health: eb health"
echo "   4. Share URL with company developer"
echo ""
