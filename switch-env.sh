#!/bin/bash

# Iris AI Environment Switcher
# This script allows you to easily switch between local and production environments

if [ "$1" = "local" ]; then
    echo "🔄 Switching to LOCAL environment..."
    sed -i '' 's/ENV_MODE=production/ENV_MODE=local/' env.config.master
    python3 generate-env.py
    echo "✅ Switched to LOCAL environment"
    echo "🌐 URLs: http://localhost:3000 (frontend), http://localhost:8000 (backend)"
    
elif [ "$1" = "production" ]; then
    echo "🔄 Switching to PRODUCTION environment..."
    sed -i '' 's/ENV_MODE=local/ENV_MODE=production/' env.config.master
    python3 generate-env.py
    echo "✅ Switched to PRODUCTION environment"
    echo "🌐 URLs: https://irisvision.ai (frontend), https://irisvision.ai/api (backend)"
    
elif [ "$1" = "status" ]; then
    current_env=$(grep "ENV_MODE=" env.config.master | cut -d'=' -f2)
    echo "📋 Current Environment: $current_env"
    if [ "$current_env" = "production" ]; then
        echo "🌐 URLs: https://irisvision.ai (frontend), https://irisvision.ai/api (backend)"
    else
        echo "🌐 URLs: http://localhost:3000 (frontend), http://localhost:8000 (backend)"
    fi
    
else
    echo "🚀 Iris AI Environment Switcher"
    echo "Usage: $0 [local|production|status]"
    echo ""
    echo "Commands:"
    echo "  local      - Switch to local development environment"
    echo "  production - Switch to production environment"
    echo "  status     - Show current environment status"
    echo ""
    echo "Examples:"
    echo "  $0 local      # Switch to localhost URLs"
    echo "  $0 production # Switch to irisvision.ai URLs"
    echo "  $0 status     # Check current environment"
fi
