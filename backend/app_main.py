from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
from agentpress.thread_manager import ThreadManager
from services.supabase import DBConnection
from services.db import admin_client
from datetime import datetime, timezone
from dotenv import load_dotenv
import asyncio
from utils.logger import logger
import uuid

# Import the agent API module
from agent import api as agent_api
from sandbox import api as sandbox_api
from sandbox.pool import get_pool
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from api.share_routes import router as share_routes
from routes import diag

# Load environment variables
load_dotenv()

# Initialize managers
db = DBConnection()
thread_manager = None
instance_id = str(uuid.uuid4())[:8]  # Generate instance ID at module load time

def create_app():
    """Create and configure the FastAPI application."""
    app = FastAPI(lifespan=lifespan)
    
    app.add_middleware(
        CORSMiddleware,
        # Only allow the Iris domains plus localhost in development.
        allow_origins=[
            "https://www.irisai.vision",
            "https://irisai.vision",
            "https://staging.irisai.vision",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    
    # Include routers with prefix
    app.include_router(agent_api.router, prefix="/api")
    app.include_router(sandbox_api.router, prefix="/api")
    app.include_router(share_routes, prefix="/api")
    app.include_router(diag.router)  # Diagnostic routes (no prefix needed)

    # Add streaming alias route without /api prefix for frontend compatibility
    @app.get("/agent-run/{run_id}/stream")
    async def stream_agent_run_alias(run_id: str, token: Optional[str] = None, request: Request = None):
        """Alias for /api/agent-run/{run_id}/stream to support frontend expectations."""
        from agent import api as agent_api
        return await agent_api.stream_agent_run(run_id, token, request)
    
    @app.get("/api/health-check")
    async def health_check():
        """Health check endpoint to verify API is working."""
        logger.info("Health check endpoint called")
        return {
            "status": "ok", 
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "instance_id": instance_id
        }
    
    return app

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global thread_manager
    logger.info(f"Starting up FastAPI application with instance ID: {instance_id}")
    await db.initialize()

    # Optional hard check: require real Daytona client when configured
    import os
    require_daytona = os.getenv("IRIS_REQUIRE_DAYTONA", "true").lower() in ("1", "true", "yes")
    if require_daytona:
        try:
            from sandbox.sandbox import daytona as _daytona
            if getattr(_daytona, "is_mock", False):
                raise RuntimeError("Daytona mock client active while IRIS_REQUIRE_DAYTONA=true. Configure DAYTONA_* env vars and IRIS_SANDBOX_PROVIDER=daytona.")
        except Exception as e:
            logger.error(f"Daytona requirement failed: {e}")
            raise

    # Start warm sandbox pool (non-blocking)
    try:
        pool = get_pool()
        await pool.start()
    except Exception as e:
        logger.warning(f"Failed to start sandbox warm pool: {e}")

    # Validate Supabase schema configuration
    try:
        client = await admin_client()
        # This will throw if schema is wrong or table missing
        await client.table("threads").select("thread_id").limit(1).execute()
        logger.info("Supabase schema verified (public schema)")
    except Exception as e:
        logger.error(f"Supabase schema validation failed: {str(e)}")
        logger.error("This may cause PGRST205 errors. Check SUPABASE_DB_SCHEMA environment variable.")
        raise

    thread_manager = ThreadManager(db_connection=db)
    
    # Initialize the agent API with shared resources
    agent_api.initialize(
        thread_manager,
        db,
        instance_id  # Pass the instance_id to agent_api
    )
    
    # Initialize the sandbox API with shared resources
    sandbox_api.initialize(db)
    
    # Initialize Redis before restoring agent runs
    from services import redis
    await redis.initialize_async()
    
    asyncio.create_task(agent_api.restore_running_agent_runs())
    
    yield
    
    # Clean up agent resources (including Redis)
    logger.info("Cleaning up agent resources")
    await agent_api.cleanup()

    # Stop warm pool
    try:
        pool = get_pool()
        await pool.stop()
    except Exception:
        pass
    
    # Clean up database connection
    logger.info("Disconnecting from database")
    await db.disconnect()

app = create_app()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000) 
