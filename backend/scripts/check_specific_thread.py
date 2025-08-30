#!/usr/bin/env python3
"""
Script to check if a specific thread ID exists in the database.
"""

import asyncio
import sys
import os

try:
    from services.supabase import DBConnection
    from utils.logger import logger
    
    async def check_specific_thread():
        """Check if a specific thread ID exists in the database."""
        db = DBConnection()
        await db.initialize()
        client = await db.get_client()
        
        # Check the most recent thread ID from the logs that's causing 404
        thread_id = "94a05fbe-c3c8-4bfb-b58a-5e218ac4b6d0"
        
        try:
            result = await client.table('threads').select('*').eq('thread_id', thread_id).execute()
            print(f'Thread {thread_id} found: {len(result.data) > 0}')
            
            if result.data:
                print(f'Thread data: {result.data[0]}')
            else:
                print(f'Thread {thread_id} not found in database')
                
        except Exception as e:
            print(f'Error querying database: {e}')
        finally:
            await db.disconnect()
    
    # Run the async function
    asyncio.run(check_specific_thread())
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the backend container")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
