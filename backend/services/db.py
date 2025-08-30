import os
from typing import Union, Optional
from supabase import create_async_client, AsyncClient
from utils.logger import logger

SUPABASE_URL = os.environ["SUPABASE_URL"]
ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_SERVICE_KEY"]
DB_SCHEMA = os.environ.get("SUPABASE_DB_SCHEMA", "public")

# Cache clients for performance
_user_clients: dict[str, AsyncClient] = {}
_admin_client: Optional[AsyncClient] = None

async def client_for_user(token: Optional[str] = None) -> AsyncClient:
    """Get user client with proper schema configuration"""
    # Use token as cache key, or "anon" for anonymous access
    cache_key = token or "anon"

    if cache_key not in _user_clients:
        sb = await create_async_client(SUPABASE_URL, ANON_KEY)
        # Set schema directly after client creation - this is mandatory
        # We need to explicitly set the schema for the client
        if token:
            sb.postgrest.auth(token)
        if hasattr(sb.postgrest, 'headers'):
            sb.postgrest.headers["apikey"] = ANON_KEY
        # Note: postgrest schema setting is handled by the SUPABASE_DB_SCHEMA environment variable
        # We don't need to explicitly set it here as the client respects the environment variable
        _user_clients[cache_key] = sb

    return _user_clients[cache_key]

async def admin_client() -> AsyncClient:
    """Get admin client (bypasses RLS) - server-only for mutations"""
    global _admin_client
    if _admin_client is None:
        sb = await create_async_client(SUPABASE_URL, SERVICE_KEY)
        # Set schema directly after client creation - this is mandatory
        # We need to explicitly set the schema for the client
        sb.postgrest.auth(SERVICE_KEY)
        if hasattr(sb.postgrest, 'headers'):
            sb.postgrest.headers["apikey"] = SERVICE_KEY
        # Note: postgrest schema setting is handled by the SUPABASE_DB_SCHEMA environment variable
        # We don't need to explicitly set it here as the client respects the environment variable
        _admin_client = sb
    return _admin_client

async def insert_and_return(table: str, payload: dict) -> dict:
    """Insert using admin client (bypasses RLS) - for server mutations"""
    client = await admin_client()
    resp = await client.table(table).insert(payload, returning="representation").execute()
    if resp.data:
        return resp.data[0]
    raise RuntimeError(f"Insert failed: {getattr(resp, 'error', None)}")

# Backward compatibility alias
async def sb() -> AsyncClient:
    """Legacy alias for backward compatibility - use client_for_user instead"""
    return await client_for_user()

def ensure_public_schema(client) -> None:
    """Safeguard helper to ensure client uses public schema"""
    if not hasattr(client, 'postgrest') or not hasattr(client.postgrest, 'schema'):
        raise RuntimeError("Supabase client misconfigured - missing postgrest.schema method")
    # Re-apply schema configuration as safeguard
    client.postgrest = client.postgrest.schema(DB_SCHEMA)
