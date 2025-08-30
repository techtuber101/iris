#!/bin/bash

# Iris AI Deployment Script for Google Compute Engine
# This script deploys the application using Docker Compose on GCE

set -e

echo "🚀 Starting Iris AI deployment to Google Compute Engine..."

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud CLI is not installed. Please install it first."
    exit 1
fi

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated with Google Cloud. Please run 'gcloud auth login' first."
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project)
echo "📁 Using Google Cloud project: $PROJECT_ID"

# Configuration
INSTANCE_NAME="iris-ai-instance"
ZONE="us-central1-a"
MACHINE_TYPE="e2-medium"  # 2 vCPU, 4 GB RAM
DISK_SIZE="20GB"

echo "🔧 Creating Google Compute Engine instance..."

# Create instance with Docker pre-installed
gcloud compute instances create $INSTANCE_NAME \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --image-family=debian-11 \
    --image-project=debian-cloud \
    --boot-disk-size=$DISK_SIZE \
    --tags=http-server,https-server \
    --metadata=startup-script='#! /bin/bash
        # Install Docker
        apt-get update
        apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
        curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
        # Install Docker Compose
        curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        
        # Create app directory
        mkdir -p /app
        chown -R $USER:$USER /app'

echo "⏳ Waiting for instance to be ready..."
sleep 60

echo "📁 Copying application files to instance..."
# Copy your application files to the instance
gcloud compute scp --recurse . $INSTANCE_NAME:/app --zone=$ZONE

echo "🔧 Setting up environment variables..."
# Copy production environment file
gcloud compute scp env.production $INSTANCE_NAME:/app/.env --zone=$ZONE

echo "🐳 Starting application with Docker Compose..."
# SSH into instance and start the application
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
    cd /app
    # Update docker-compose.yml with production URLs
    sed -i 's|http://localhost:8000|https://irisvision.ai|g' docker-compose.yml
    sed -i 's|http://localhost:3000|https://irisvision.ai|g' docker-compose.yml
    
    # Start the application with production compose file
    docker-compose -f docker-compose.production.yml up -d
"

echo "🌐 Setting up firewall rules..."
# Create firewall rule to allow HTTP/HTTPS traffic
gcloud compute firewall-rules create allow-iris-ai \
    --allow tcp:80,tcp:443,tcp:3000,tcp:8000 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server,https-server

# Get the external IP
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

echo "✅ Deployment completed successfully!"
echo ""
echo "🔗 Your application is now running at:"
echo "   Frontend: http://$EXTERNAL_IP:3000"
echo "   Backend:  http://$EXTERNAL_IP:8000"
echo ""
echo "📝 Next steps:"
echo "1. Point irisvision.ai DNS to: $EXTERNAL_IP"
echo "2. Set up SSL certificates (recommended)"
echo "3. Configure your domain registrar to point to this IP"
echo ""
echo "🔧 To manage your instance:"
echo "   SSH: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo "   Stop: gcloud compute instances stop $INSTANCE_NAME --zone=$ZONE"
echo "   Start: gcloud compute instances start $INSTANCE_NAME --zone=$ZONE"
echo "   Delete: gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE"
