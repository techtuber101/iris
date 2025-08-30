#!/usr/bin/env python3
"""
Script to check the database for existing threads.
"""

import asyncio
import sys
import os

try:
    from services.supabase import DBConnection
    from utils.logger import logger
    
    async def check_db():
        """Check the database for existing threads."""
        db = DBConnection()
        await db.initialize()
        client = await db.get_client()
        
        try:
            # Check threads table
            result = await client.table('threads').select('*').limit(5).execute()
            print(f'Found {len(result.data)} threads in database')
            
            if result.data:
                for thread in result.data:
                    print(f'Thread: {thread}')
            else:
                print('No threads found in database')
                
            # Check projects table
            project_result = await client.table('projects').select('*').limit(5).execute()
            print(f'\nFound {len(project_result.data)} projects in database')
            
            if project_result.data:
                for project in project_result.data:
                    print(f'Project: {project}')
            else:
                print('No projects found in database')
                
        except Exception as e:
            print(f'Error querying database: {e}')
        finally:
            await db.disconnect()
    
    # Run the async function
    asyncio.run(check_db())
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the backend container")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
