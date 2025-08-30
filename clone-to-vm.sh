#!/bin/bash
echo "Cloning repository to VM..."
gcloud compute ssh instance-20250808-121222 --zone=us-central1-c --command="cd ~ && git clone https://github.com/techtuber101/iris.git iris-app"

