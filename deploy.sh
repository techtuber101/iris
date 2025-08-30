#!/bin/bash

# Iris AI Deployment Script
# This script pushes your code to the VM and triggers automatic deployment

echo "🚀 Deploying Iris AI to Google Cloud VM..."
echo "=========================================="

# Check if we have changes to commit
if [[ -n $(git status --porcelain) ]]; then
    echo "📝 Committing local changes..."
    git add .
    git commit -m "Auto-deploy: $(date)"
fi

# Push to production VM
echo "📤 Pushing to production VM..."
git push production master

echo ""
echo "✅ Deployment triggered!"
echo "🌐 Your app will be available at: https://irisvision.ai"
echo ""
echo "📋 To check deployment status on VM:"
echo "   gcloud compute ssh instance-20250808-121222 --zone=us-central1-c"
echo "   cd ~/iris-app-working"
echo "   docker compose -f docker-compose.production.yml ps"
echo ""
echo "📋 To view logs:"
echo "   docker compose -f docker-compose.production.yml logs -f"
