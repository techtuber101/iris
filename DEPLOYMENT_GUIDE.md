# 🚀 Iris AI Deployment Guide for Google Cloud

## Overview
This guide will help you deploy your Iris AI application to Google Cloud using Docker Compose, just like your local setup.

## 🎯 What We're Deploying
- **Backend**: FastAPI application (port 8000)
- **Frontend**: Next.js application (port 3000)  
- **Redis**: Cache and session storage (port 6379)
- **Caddy**: Reverse proxy and automatic SSL (ports 80, 443)

## 📋 Prerequisites
- ✅ Google Cloud CLI installed (`gcloud`)
- ✅ Authenticated with Google Cloud (`gcloud auth login`)
- ✅ Project selected (`gcloud config set project YOUR_PROJECT_ID`)
- ✅ Domain `irisvision.ai` (you'll need to point DNS to the deployed IP)

## 🚀 Quick Deploy (Recommended)

### Option 1: Automated Deployment
```bash
./deploy-gce.sh
```

This script will:
1. Create a Google Compute Engine instance
2. Install Docker and Docker Compose
3. Copy your application files
4. Start the application with Docker Compose
5. Set up firewall rules
6. Give you the external IP address

### Option 2: Manual Step-by-Step

#### Step 1: Create Compute Engine Instance
```bash
gcloud compute instances create iris-ai-instance \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=debian-11 \
    --image-project=debian-cloud \
    --boot-disk-size=20GB \
    --tags=http-server,https-server
```

#### Step 2: Install Docker (SSH into instance)
```bash
gcloud compute ssh iris-ai-instance --zone=us-central1-a
```

Then run these commands inside the instance:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### Step 3: Copy Application Files
```bash
# From your local machine
gcloud compute scp --recurse . iris-ai-instance:/app --zone=us-central1-a
```

#### Step 4: Start Application
```bash
# SSH into instance
gcloud compute ssh iris-ai-instance --zone=us-central1-a

# Navigate to app directory and start
cd /app
docker-compose -f docker-compose.production.yml up -d
```

#### Step 5: Set Up Firewall
```bash
gcloud compute firewall-rules create allow-iris-ai \
    --allow tcp:80,tcp:443,tcp:3000,tcp:8000 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server,https-server
```

## 🌐 Domain Configuration

### 1. Get Your Instance IP
```bash
gcloud compute instances describe iris-ai-instance --zone=us-central1-a --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
```

### 2. Update DNS Records
Point `irisvision.ai` and `www.irisvision.ai` to the IP address you got above.

### 3. SSL Certificates (Automatic with Caddy!)
Caddy automatically handles SSL certificates for you! No manual setup needed.

```bash
# Caddy will automatically:
# - Request Let's Encrypt certificates
# - Renew them before expiration
# - Handle HTTP to HTTPS redirects
# - Provide modern TLS configuration
```

## 🔧 Management Commands

### Start/Stop Instance
```bash
# Stop instance
gcloud compute instances stop iris-ai-instance --zone=us-central1-a

# Start instance  
gcloud compute instances start iris-ai-instance --zone=us-central1-a
```

### SSH into Instance
```bash
gcloud compute ssh iris-ai-instance --zone=us-central1-a
```

### View Logs
```bash
# SSH into instance first, then:
docker-compose -f docker-compose.production.yml logs -f
```

### Restart Services
```bash
# SSH into instance first, then:
docker-compose -f docker-compose.production.yml restart
```

## 💰 Cost Estimation
- **e2-medium instance**: ~$25-30/month
- **Network egress**: ~$5-10/month (depending on traffic)
- **Total estimated cost**: ~$30-40/month

## 🆘 Troubleshooting

### Instance won't start
```bash
gcloud compute instances describe iris-ai-instance --zone=us-central1-a
```

### Docker services not running
```bash
# SSH into instance
docker ps
docker-compose -f docker-compose.production.yml ps
```

### Port access issues
```bash
# Check firewall rules
gcloud compute firewall-rules list
```

## 🎉 Success!
Once deployed, your application will be available at:
- **Frontend**: https://irisvision.ai
- **Backend API**: https://irisvision.ai/api
- **Health Check**: https://irisvision.ai/health

## 📞 Support
If you encounter issues:
1. Check the logs: `docker-compose logs -f`
2. Verify firewall rules are set correctly
3. Ensure DNS is pointing to the correct IP
4. Check that all required ports are open (80, 443, 3000, 8000)
