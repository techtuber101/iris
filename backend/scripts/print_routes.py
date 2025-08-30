#!/usr/bin/env python3
"""
Script to print all FastAPI routes at runtime.
Run this inside the backend container to see effective routes.
"""

import sys
import os

try:
    from fastapi.routing import APIRoute
    # Import the FastAPI app from the root app_main.py file by changing directory
    import importlib.util

    # Get the spec for the app_main.py file
    spec = importlib.util.spec_from_file_location("main_api", "/app/app_main.py")
    main_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_api)
    
    app = main_api.app
    
    print("=== FastAPI Routes ===")
    print(f"{'Method':<10} {'Path':<50} {'Name':<30}")
    print("-" * 90)
    
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ",".join(sorted(route.methods))
            path = route.path
            name = route.name or "unnamed"
            print(f"{methods:<10} {path:<50} {name:<30}")
    
    print(f"\nTotal routes: {len([r for r in app.routes if isinstance(r, APIRoute)])}")
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the backend container")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
