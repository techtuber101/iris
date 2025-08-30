#!/bin/bash

# Iris AI VM Deployment Script
# This script copies your code to the VM and deploys it automatically

echo "🚀 Deploying Iris AI to Google Cloud VM..."
echo "=========================================="

# Check if we have changes to commit
if [[ -n $(git status --porcelain) ]]; then
    echo "📝 Committing local changes..."
    git add .
    git commit -m "Auto-deploy: $(date)"
fi

# Push to GitHub first
echo "📤 Pushing to GitHub..."
git push origin master

# Copy files to VM
echo "📁 Copying files to VM..."
gcloud compute scp --recurse . instance-20250808-121222:~/iris-app --zone=us-central1-c

# Deploy on VM
echo "🐳 Deploying on VM..."
gcloud compute ssh instance-20250808-121222 --zone=us-central1-c --command="
    cd ~/iris-app
    echo '🌍 Switching to production mode...'
    ./switch-env.sh production
    
    echo '🛑 Stopping existing containers...'
    docker compose -f docker-compose.production.yml down 2>/dev/null || true
    
    echo '🏗️ Building and starting application...'
    docker compose -f docker-compose.production.yml up -d --build
    
    echo '⏳ Waiting for services to start...'
    sleep 15
    
    echo '🔍 Checking service status...'
    docker compose -f docker-compose.production.yml ps
    
    echo '📋 Recent logs:'
    docker compose -f docker-compose.production.yml logs --tail=10
"

echo ""
echo "✅ Deployment completed!"
echo "🌐 Your app should now be running at: https://irisvision.ai"
echo ""
echo "📋 To check status on VM:"
echo "   gcloud compute ssh instance-20250808-121222 --zone=us-central1-c"
echo "   cd ~/iris-app"
echo "   docker compose -f docker-compose.production.yml ps"
echo ""
echo "📋 To view logs:"
echo "   docker compose -f docker-compose.production.yml logs -f"
