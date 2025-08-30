#!/usr/bin/env python3
"""
GitHub Webhook Server for Iris AI Auto-Deployment
This server runs on the VM and receives webhooks from GitHub to trigger deployments
"""

import http.server
import socketserver
import json
import subprocess
import os
import hmac
import hashlib
import logging
from urllib.parse import parse_qs, urlparse

# Configuration
WEBHOOK_SECRET = "iris-ai-deploy-secret-2025"  # Change this to something secure
GITHUB_REPO = "techtuber101/iris"
WORKING_DIR = "/home/ishaantheman/iris-app"
LOG_FILE = "/home/ishaantheman/webhook.log"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Get the request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            # Verify GitHub webhook signature
            signature = self.headers.get('X-Hub-Signature-256', '')
            if not self.verify_signature(body, signature):
                logging.warning("Invalid webhook signature")
                self.send_response(401)
                self.end_headers()
                return
            
            # Parse the webhook payload
            payload = json.loads(body.decode('utf-8'))
            event_type = self.headers.get('X-GitHub-Event', '')
            
            logging.info(f"Received {event_type} event from {payload.get('repository', {}).get('full_name', 'unknown')}")
            
            # Only deploy on push to main/master branch
            if event_type == 'push' and payload.get('ref') == 'refs/heads/master':
                logging.info("Push to master detected, starting deployment...")
                
                # Send immediate response
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Deployment started")
                
                # Start deployment in background
                self.deploy_application()
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Event ignored")
                
        except Exception as e:
            logging.error(f"Error processing webhook: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal server error")
    
    def verify_signature(self, body, signature):
        """Verify GitHub webhook signature"""
        if not signature:
            return False
        
        expected_signature = 'sha256=' + hmac.new(
            WEBHOOK_SECRET.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def deploy_application(self):
        """Deploy the application from GitHub"""
        try:
            logging.info("🚀 Starting deployment...")
            
            # Navigate to working directory
            os.chdir(WORKING_DIR)
            
            # Pull latest code from GitHub
            logging.info("📥 Pulling latest code from GitHub...")
            subprocess.run(['git', 'pull', 'origin', 'master'], check=True, capture_output=True)
            
            # Switch to production mode
            logging.info("🌍 Switching to production mode...")
            subprocess.run(['./switch-env.sh', 'production'], check=True, capture_output=True)
            
            # Stop existing containers
            logging.info("🛑 Stopping existing containers...")
            subprocess.run(['docker', 'compose', '-f', 'docker-compose.production.yml', 'down'], 
                         capture_output=True)
            
            # Build and start new containers
            logging.info("🏗️ Building and starting new containers...")
            result = subprocess.run(['docker', 'compose', '-f', 'docker-compose.production.yml', 'up', '-d', '--build'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logging.info("✅ Deployment completed successfully!")
                
                # Check service status
                status_result = subprocess.run(['docker', 'compose', '-f', 'docker-compose.production.yml', 'ps'], 
                                            capture_output=True, text=True)
                logging.info(f"Service status:\n{status_result.stdout}")
            else:
                logging.error(f"❌ Deployment failed: {result.stderr}")
                
        except Exception as e:
            logging.error(f"❌ Deployment error: {e}")
    
    def log_message(self, format, *args):
        """Override to use our logging"""
        logging.info(format % args)

def run_webhook_server():
    """Run the webhook server"""
    PORT = 8080
    
    with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
        logging.info(f"🚀 Webhook server started on port {PORT}")
        logging.info(f"📡 Ready to receive GitHub webhooks")
        logging.info(f"🔗 GitHub will call: http://34.133.150.110:8080/webhook")
        logging.info(f"📝 Logs saved to: {LOG_FILE}")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down webhook server...")
            httpd.shutdown()

if __name__ == "__main__":
    run_webhook_server()
