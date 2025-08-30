"""
Centralized database connection management for Suna using Supabase.
"""

import os
from typing import Optional
from supabase import create_async_client, AsyncClient
from utils.logger import logger

class DBConnection:
    """Singleton database connection manager using Supabase."""
    
    _instance: Optional['DBConnection'] = None
    _initialized = False
    _client: Optional[AsyncClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """No initialization needed in __init__ as it's handled in __new__"""
        pass

    async def initialize(self):
        """Initialize the database connection."""
        if self._initialized:
            return self._client

        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not supabase_url or not supabase_key:
                raise ValueError("Missing Supabase environment variables")
            
            self._client = create_async_client(supabase_url, supabase_key)
            self._initialized = True
            logger.info("Supabase initialized with SERVICE_ROLE_KEY")
            
            return self._client
        except Exception as e:
            logger.error(f"Failed to initialize Supabase connection: {str(e)}")
            raise

    async def get_client(self):
        """Get the Supabase client, initializing if necessary."""
        if not self._initialized:
            await self.initialize()
        return self._client

# Global instance
db = DBConnection()
