from fastapi import APIRouter, HTTPException, Depends, Request, Body
from fastapi.responses import StreamingResponse
import asyncio
import json
import traceback
from datetime import datetime, timezone
import uuid
from typing import Optional, List, Dict, Any
import jwt
from pydantic import BaseModel

from agentpress.thread_manager import ThreadManager
from services.supabase import DBConnection
from services import redis
from agent.run import run_agent
from agentpress.agent_orchestrator import AgentOrchestrator
from utils.auth_utils import get_current_user_id, get_user_id_from_stream_auth, verify_thread_access
from utils.logger import logger
from utils.billing import check_billing_status, get_account_id_from_thread
from utils.db import update_agent_run_status
from services.db import insert_and_return, admin_client
from sandbox.sandbox import create_sandbox, get_or_start_sandbox
from agent.adaptive_mode import should_use_adaptive_mode, analyze_query_complexity

# Initialize shared resources
router = APIRouter()
thread_manager = None
db = None 

# In-memory storage for active agent runs and their responses
active_agent_runs: Dict[str, List[Any]] = {}

# In the original Suna code multiple provider aliases were supported via
# `MODEL_NAME_ALIASES`.  Iris intentionally removes multi‑model support and
# restricts the agent to a single language model.  If a request includes a
# `model_name` it will be ignored in favour of this constant.  See
# `DEFAULT_MODEL_NAME` below.

# Define the sole supported large language model for Iris.  Gemini 2.5 Pro
# (direct) via LiteLLM. Multi‑model support has been removed entirely.
DEFAULT_MODEL_NAME = "gemini/gemini-2.5-pro"

class AgentStartRequest(BaseModel):
    # The requested model name.  This field is accepted for backwards
    # compatibility with clients but will be ignored.  Iris always uses
    # DEFAULT_MODEL_NAME defined above.
    model_name: Optional[str] = DEFAULT_MODEL_NAME
    enable_thinking: Optional[bool] = False
    reasoning_effort: Optional[str] = 'low'
    stream: Optional[bool] = True
    enable_context_manager: Optional[bool] = False

def initialize(
    _thread_manager: ThreadManager,
    _db: DBConnection,
    _instance_id: str = None
):
    """Initialize the agent API with resources from the main API."""
    global thread_manager, db, instance_id
    thread_manager = _thread_manager
    db = _db
    
    # Use provided instance_id or generate a new one
    if _instance_id:
        instance_id = _instance_id
    else:
        # Generate instance ID
        instance_id = str(uuid.uuid4())[:8]
    
    logger.info(f"Initialized agent API with instance ID: {instance_id}")
    
    # Note: Redis will be initialized in the lifespan function in app_main.py

async def cleanup():
    """Clean up resources and stop running agents on shutdown."""
    logger.info("Starting cleanup of agent API resources")
    
    # Use the instance_id to find and clean up this instance's keys
    try:
        running_keys = await redis.keys(f"active_run:{instance_id}:*")
        logger.info(f"Found {len(running_keys)} running agent runs to clean up")
        
        for key in running_keys:
            agent_run_id = key.split(":")[-1]
            await stop_agent_run(agent_run_id)
    except Exception as e:
        logger.error(f"Failed to clean up running agent runs: {str(e)}")
    
    # Close Redis connection
    await redis.close()
    logger.info("Completed cleanup of agent API resources")

async def check_resources_initialized():
    """Check if the agent API resources are properly initialized."""
    if db is None or thread_manager is None:
        raise HTTPException(status_code=503, detail="Agent API not yet initialized")
    return True

async def update_agent_run_status(
    client,
    agent_run_id: str,
    status: str,
    error: Optional[str] = None,
    responses: Optional[List[Any]] = None
) -> bool:
    """
    Centralized function to update agent run status.
    Returns True if update was successful.
    """
    try:
        update_data = {
            "status": status,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        
        if error:
            update_data["error"] = error
            
        # Retry up to 3 times
        for retry in range(3):
            try:
                update_result = await client.table("agent_runs").update(update_data).eq("id", agent_run_id).execute()
                
                if hasattr(update_result, "data") and update_result.data:
                    logger.info(f"Successfully updated agent run status to \'{status}\' (retry {retry}): {agent_run_id}")
                    
                    # Verify the update
                    verify_result = await client.table("agent_runs").select("status", "completed_at").eq("id", agent_run_id).execute()
                    if verify_result.data:
                        actual_status = verify_result.data[0].get("status")
                        completed_at = verify_result.data[0].get("completed_at")
                        logger.info(f"Verified agent run update: status={actual_status}, completed_at={completed_at}")
                    return True
                else:
                    logger.warning(f"Database update returned no data on retry {retry}: {update_result}")
                    if retry == 2:  # Last retry
                        logger.error(f"Failed to update agent run status after all retries: {agent_run_id}")
                        return False
            except Exception as db_error:
                logger.error(f"Database error on retry {retry} updating status: {str(db_error)}")
                if retry < 2:  # Not the last retry yet
                    await asyncio.sleep(0.5 * (2 ** retry))  # Exponential backoff
                else:
                    logger.error(f"Failed to update agent run status after all retries: {agent_run_id}", exc_info=True)
                    return False
    except Exception as e:
        logger.error(f"Unexpected error updating agent run status: {str(e)}", exc_info=True)
        return False
    
    return False

async def stop_agent_run(agent_run_id: str, error_message: Optional[str] = None):
    """Update database and publish stop signal to Redis."""
    logger.info(f"Stopping agent run: {agent_run_id}")
    client = await admin_client()
    
    # Update the agent run status
    status = "failed" if error_message else "stopped"
    await update_agent_run_status(client, agent_run_id, status, error=error_message)
    
    # Send stop signal to global channel
    try:
        await redis.publish(f"agent_run:{agent_run_id}:control", "STOP")
        logger.debug(f"Published STOP signal to global channel for agent run {agent_run_id}")
    except Exception as e:
        logger.error(f"Failed to publish STOP signal to global channel: {str(e)}")
    
    # Find all instances handling this agent run
    try:
        instance_keys = await redis.keys(f"active_run:*:{agent_run_id}")
        logger.debug(f"Found {len(instance_keys)} active instances for agent run {agent_run_id}")
        
        for key in instance_keys:
            # Extract instance ID from the key pattern: active_run:{instance_id}:{agent_run_id}
            parts = key.split(":")
            if len(parts) >= 3:
                instance_id = parts[1]
                try:
                    # Send stop signal to instance-specific channel
                    await redis.publish(f"agent_run:{agent_run_id}:control:{instance_id}", "STOP")
                    logger.debug(f"Published STOP signal to instance {instance_id} for agent run {agent_run_id}")
                except Exception as e:
                    logger.warning(f"Failed to publish STOP signal to instance {instance_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to find or signal active instances: {str(e)}")
    
    logger.info(f"Successfully initiated stop process for agent run: {agent_run_id}")

async def restore_running_agent_runs():
    """Restore any agent runs that were still marked as running in the database."""
    logger.info("Restoring running agent runs after server restart")
    try:
        client = await admin_client()
        running_agent_runs = await client.table('agent_runs').select('*').eq("status", "running").execute()

        for run in running_agent_runs.data:
            logger.warning(f"Found running agent run {run['id']} from before server restart")
            await client.table('agent_runs').update({
                "status": "failed", 
                "error": "Server restarted while agent was running",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", run['id']).execute()
    except Exception as e:
        logger.warning(f"Failed to restore running agent runs (database connection issue): {str(e)}")
        logger.info("Continuing startup without restoring agent runs - this is non-critical")

async def check_for_active_project_agent_run(client, project_id: str):
    """
    Check if there is an active agent run for any thread in the given project.
    If found, returns the ID of the active run, otherwise returns None.
    
    Args:
        client: The Supabase client
        project_id: The project ID to check
        
    Returns:
        str or None: The ID of the active agent run if found, None otherwise
    """
    # Get all threads from this project
    project_threads = await client.table('threads').select('thread_id').eq('project_id', project_id).execute()
    project_thread_ids = [t['thread_id'] for t in project_threads.data]
    
    # Check if there are any active agent runs for any thread in this project
    if project_thread_ids:
        active_runs = await client.table('agent_runs').select('id').in_('thread_id', project_thread_ids).eq('status', 'running').execute()
        
        if active_runs.data and len(active_runs.data) > 0:
            return active_runs.data[0]['id']
    
    return None

async def get_agent_run_with_access_check(client, agent_run_id: str, user_id: str):
    """
    Get an agent run's data after verifying the user has access to it through account membership.
    
    Args:
        client: The Supabase client
        agent_run_id: The agent run ID to check access for
        user_id: The user ID to check permissions for
        
    Returns:
        dict: The agent run data if access is granted
        
    Raises:
        HTTPException: If the user doesn't have access or the agent run doesn't exist
    """
    agent_run = await client.table('agent_runs').select('*').eq('id', agent_run_id).execute()
    
    if not agent_run.data or len(agent_run.data) == 0:
        raise HTTPException(status_code=404, detail="Agent run not found")
        
    agent_run_data = agent_run.data[0]
    thread_id = agent_run_data['thread_id']
    
    # Verify user has access to this thread using the updated verify_thread_access function
    await verify_thread_access(client, thread_id, user_id)
    
    return agent_run_data

async def _cleanup_agent_run(agent_run_id: str):
    """Clean up Redis keys when an agent run is done."""
    logger.debug(f"Cleaning up Redis keys for agent run: {agent_run_id}")
    try:
        await redis.delete(f"active_run:{instance_id}:{agent_run_id}")
        logger.debug(f"Successfully cleaned up Redis keys for agent run: {agent_run_id}")
    except Exception as e:
        logger.warning(f"Failed to clean up Redis keys for agent run {agent_run_id}: {str(e)}")
        # Non-fatal error, can continue

# Canonical handler for starting an agent
@router.post("/thread/{thread_id}/agent/start")
async def start_agent(
    thread_id: str,
    body: AgentStartRequest = Body(...), # Accept request body
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(check_resources_initialized)
):
    """Start an agent for a specific thread in the background."""
    logger.info(f"HTTP matched: /thread/{thread_id}/agent/start -> {thread_id}")
    logger.info(f"Starting new agent for thread: {thread_id} with config: model={body.model_name}, thinking={body.enable_thinking}, effort={body.reasoning_effort}, stream={body.stream}, context_manager={body.enable_context_manager}")
    client = await admin_client()
    
    # Verify user has access to this thread
    await verify_thread_access(client, thread_id, user_id)
    
    # Get the project_id and account_id for this thread
    thread_result = await client.table('threads').select('project_id', 'account_id').eq('thread_id', thread_id).execute()
    if not thread_result.data:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    thread_data = thread_result.data[0]
    project_id = thread_data.get('project_id')
    account_id = thread_data.get('account_id')
    
    # Check billing status
    can_run, message, subscription = await check_billing_status(client, account_id)
    if not can_run:
        raise HTTPException(status_code=402, detail={
            "message": message,
            "subscription": subscription
        })
    
    # Check if there is already an active agent run for this project
    active_run_id = await check_for_active_project_agent_run(client, project_id)
    
    # If there's an active run, stop it first
    if active_run_id:
        logger.info(f"Stopping existing agent run {active_run_id} before starting new one")
        await stop_agent_run(active_run_id)

    # Adaptive sandbox: don't start or create here. The agent will lazily
    # create/start a sandbox if and when a tool is actually invoked.
    sandbox = None
    
    agent_run = await client.table('agent_runs').insert({
        "thread_id": thread_id,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat()
    }).execute()
    
    agent_run_id = agent_run.data[0]['id']
    logger.info(f"Created new agent run: {agent_run_id}")
    
    # Initialize in-memory storage for this agent run
    active_agent_runs[agent_run_id] = []
    
    # Register this run in Redis with TTL
    try:
        await redis.set(
            f"active_run:{instance_id}:{agent_run_id}", 
            "running", 
            ex=redis.REDIS_KEY_TTL
        )
    except Exception as e:
        logger.warning(f"Failed to register agent run in Redis, continuing without Redis tracking: {str(e)}")
    
    # Run the agent in the background
    task = asyncio.create_task(
        run_agent_background(
            agent_run_id=agent_run_id,
            thread_id=thread_id,
            instance_id=instance_id,
            project_id=project_id,
            sandbox=sandbox,
            # Iris uses a single model for all runs.  Ignore any requested model
            # name in the body and always pass DEFAULT_MODEL_NAME.
            model_name=DEFAULT_MODEL_NAME,
            enable_thinking=body.enable_thinking,
            reasoning_effort=body.reasoning_effort,
            stream=body.stream,
            enable_context_manager=body.enable_context_manager
        )
    )
    
    # Set a callback to clean up when task is done
    task.add_done_callback(
        lambda _: asyncio.create_task(
            _cleanup_agent_run(agent_run_id)
        )
    )
    
    return {"agent_run_id": agent_run_id, "status": "running"}

# Backward-compatible alias for plural form (remove after 60 days once clients migrate)
@router.post("/threads/{thread_id}/agent/start")
async def start_agent_alias(
    thread_id: str,
    body: AgentStartRequest = Body(...), # Accept request body
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(check_resources_initialized)
):
    """Backward-compatible alias for /thread/{thread_id}/agent/start. Use /thread/{thread_id}/agent/start instead."""
    logger.info(f"HTTP matched: /threads/{thread_id}/agent/start -> {thread_id} (alias)")
    return await start_agent(thread_id, body, user_id, _)

# Thread creation request model
class CreateThreadRequest(BaseModel):
    project_id: str

# Thread creation endpoint
@router.post("/threads")
async def create_thread(
    request: CreateThreadRequest,
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(check_resources_initialized)
):
    """Create a new thread for a project."""
    logger.info(f"Creating new thread for project: {request.project_id}")
    client = await db.get_client()
    
    try:
        # Insert the new thread using helper function (admin client - bypasses RLS)
        # TODO: Revert to RLS (Option B) after unblock - use user client with proper policies
        thread_data = await insert_and_return('threads', {
            "project_id": request.project_id,
            "account_id": user_id,
            "is_public": False
        })
        logger.info(f"Created new thread: {thread_data['thread_id']}")
        
        return {
            "thread_id": thread_data['thread_id'],
            "project_id": thread_data['project_id'],
            "account_id": thread_data['account_id'],
            "created_at": thread_data['created_at']
        }
        
    except Exception as e:
        logger.error(f"Error creating thread: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create thread: {str(e)}")

@router.post("/agent-run/{agent_run_id}/stop")
async def stop_agent(
    agent_run_id: str, 
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(check_resources_initialized)
):
    """Stop a running agent."""
    logger.info(f"Stopping agent run: {agent_run_id}")
    client = await db.get_client()
    
    # Verify user has access to the agent run
    await get_agent_run_with_access_check(client, agent_run_id, user_id)
    
    # Stop the agent run
    await stop_agent_run(agent_run_id)
    
    return {"status": "stopped"}

@router.get("/thread/{thread_id}/agent-runs")
async def get_agent_runs(
    thread_id: str,
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(check_resources_initialized)
):
    """Get all agent runs for a thread."""
    logger.info(f"Fetching agent runs for thread: {thread_id}")
    client = await admin_client()
    
    # Verify user has access to this thread
    await verify_thread_access(client, thread_id, user_id)
    
    agent_runs = await client.table('agent_runs').select('*').eq("thread_id", thread_id).execute()
    logger.debug(f"Found {len(agent_runs.data)} agent runs for thread: {thread_id}")
    return {"agent_runs": agent_runs.data}

@router.get("/agent-run/{agent_run_id}")
async def get_agent_run(
    agent_run_id: str,
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(check_resources_initialized)
):
    """Get agent run status and responses."""
    logger.info(f"Fetching agent run details: {agent_run_id}")
    client = await admin_client()
    
    agent_run_data = await get_agent_run_with_access_check(client, agent_run_id, user_id)
    
    return {
        "id": agent_run_data['id'],
        "threadId": agent_run_data['thread_id'],
        "status": agent_run_data['status'],
        "startedAt": agent_run_data['started_at'],
        "completedAt": agent_run_data['completed_at'],
        "error": agent_run_data['error']
    }

@router.get("/agent-run/{agent_run_id}/stream")
async def stream_agent_run(
    agent_run_id: str, 
    token: Optional[str] = None,
    request: Request = None,
    _: bool = Depends(check_resources_initialized)
):
    """Stream the responses of an agent run from in-memory storage or reconnect to ongoing run."""
    logger.info(f"Starting stream for agent run: {agent_run_id}")
    client = await db.get_client()
    
    # Get user ID using the streaming auth function
    user_id = await get_user_id_from_stream_auth(request, token)
    
    # Verify user has access to the agent run and get run data
    agent_run_data = await get_agent_run_with_access_check(client, agent_run_id, user_id)
    
    # Define a streaming generator that uses in-memory responses
    async def stream_generator():
        logger.debug(f"Streaming responses for agent run: {agent_run_id}")
        
        # Recommend client auto-retry interval for SSE reconnects
        yield "retry: 1000\n\n"

        last_ping_time = datetime.now(timezone.utc)

        # Check if this is an active run with stored responses
        if agent_run_id in active_agent_runs:
            # First, send all existing responses
            stored_responses = active_agent_runs[agent_run_id]
            logger.debug(f"Sending {len(stored_responses)} existing responses for agent run: {agent_run_id}")
            
            for response in stored_responses:
                yield f"data: {json.dumps(response)}\n\n"
            
            # If the run is still active (status is running), set up to stream new responses
            if agent_run_data['status'] == 'running':
                # Get the current length to know where to start watching for new responses
                current_length = len(stored_responses)
                
                # Keep checking for new responses
                while agent_run_id in active_agent_runs:
                    # Check if there are new responses
                    if len(active_agent_runs[agent_run_id]) > current_length:
                        # Send all new responses
                        for i in range(current_length, len(active_agent_runs[agent_run_id])):
                            response = active_agent_runs[agent_run_id][i]
                            yield f"data: {json.dumps(response)}\n\n"
                        
                        # Update current length
                        current_length = len(active_agent_runs[agent_run_id])
                    
                    # Send a heartbeat ping every ~10s to keep connections alive through proxies
                    now = datetime.now(timezone.utc)
                    if (now - last_ping_time).total_seconds() >= 10:
                        try:
                            yield "data: {\"type\":\"ping\"}\n\n"
                        except Exception:
                            # If client disconnected, just allow generator to end naturally
                            break
                        last_ping_time = now
                    
                    # Brief pause before checking again
                    await asyncio.sleep(0.1)
        else:
            # If the run is not active or we don't have stored responses,
            # send a message indicating the run is not available for streaming
            logger.warning(f"Agent run {agent_run_id} not found in active runs")
            yield f"data: {json.dumps({'type': 'status', 'status': agent_run_data['status'], 'message': 'Run data not available for streaming'})}\n\n"
        
        # Always send a completion status at the end
        yield f"data: {json.dumps({'type': 'status', 'status': 'completed'})}\n\n"
        logger.debug(f"Streaming complete for agent run: {agent_run_id}")
    
    # Return a streaming response
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive", 
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*"
        }
    )

async def run_agent_background(
    agent_run_id: str,
    thread_id: str,
    instance_id: str,
    project_id: str,
    sandbox,
    model_name: str,
    enable_thinking: Optional[bool],
    reasoning_effort: Optional[str],
    stream: bool,
    enable_context_manager: bool
):
    """Run the agent in the background and handle status updates."""
    logger.info(f"Starting background agent run: {agent_run_id} for thread: {thread_id} (instance: {instance_id}) with model={model_name}, thinking={enable_thinking}, effort={reasoning_effort}, stream={stream}, context_manager={enable_context_manager}")
    client = await db.get_client()
    
    # Tracking variables
    total_responses = 0
    start_time = datetime.now(timezone.utc)
    
    # ADAPTIVE MODE: Check if we should use simple response
    if should_use_adaptive_mode():
        logger.info(f"Adaptive mode enabled, analyzing query complexity for thread: {thread_id}")
        
        try:
            # Get the latest user message to analyze
            messages_result = await client.table('messages').select('*').eq('thread_id', thread_id).eq('type', 'user').order('created_at', desc=True).limit(1).execute()
            
            if messages_result.data:
                latest_message = messages_result.data[0]
                content = latest_message.get('content', {})
                
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except:
                        pass
                
                user_query = ""
                if isinstance(content, dict):
                    user_query = content.get('content', '')
                elif isinstance(content, str):
                    user_query = content
                
                if user_query:
                    # Analyze query complexity
                    mode, reasoning, metadata = await analyze_query_complexity(user_query)
                    logger.info(f"Query analysis result: mode={mode}, reasoning={reasoning}")
                    
                    if mode == "simple":
                        logger.info(f"Using simple response mode for thread: {thread_id}")
                        
                        # Handle with simple response
                        from agent.simple_response import handle_simple_response
                        await handle_simple_response(
                            thread_id=thread_id,
                            query=user_query,
                            agent_run_id=agent_run_id,
                            client=client,
                            thread_manager=thread_manager
                        )
                        
                        # Add completion message to active runs for streaming
                        completion_message = {
                            "type": "status",
                            "status": "completed",
                            "message": "Simple response completed",
                            "mode": "simple"
                        }
                        if agent_run_id in active_agent_runs:
                            active_agent_runs[agent_run_id].append(completion_message)
                        
                        logger.info(f"Simple response completed for thread: {thread_id}")
                        return
                    
                    logger.info(f"Using full agentic mode for thread: {thread_id}")
        
        except Exception as e:
            logger.warning(f"Error in adaptive mode analysis: {str(e)}, falling back to full agentic mode")
    
    # FULL AGENTIC MODE: Continue with original logic
    logger.info(f"Starting full agentic mode for thread: {thread_id}")
    
    # Create a pubsub to listen for control messages
    pubsub = None
    try:
        pubsub = await redis.create_pubsub()
        
        # Use instance-specific control channel to avoid cross-talk between instances
        control_channel = f"agent_run:{agent_run_id}:control:{instance_id}"
        # Use backoff retry pattern for pubsub connection
        retry_count = 0
        while retry_count < 3:
            try:
                await pubsub.subscribe(control_channel)
                logger.debug(f"Subscribed to control channel: {control_channel}")
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= 3:
                    logger.error(f"Failed to subscribe to control channel after 3 attempts: {str(e)}")
                    raise
                wait_time = 0.5 * (2 ** (retry_count - 1))
                logger.warning(f"Failed to subscribe to control channel (attempt {retry_count}/3): {str(e)}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        # Also subscribe to the global control channel for cross-instance control
        global_control_channel = f"agent_run:{agent_run_id}:control"
        retry_count = 0
        while retry_count < 3:
            try:
                await pubsub.subscribe(global_control_channel)
                logger.debug(f"Subscribed to global control channel: {global_control_channel}")
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= 3:
                    logger.error(f"Failed to subscribe to global control channel after 3 attempts: {str(e)}")
                    # We can continue with just the instance-specific channel
                    break
                wait_time = 0.5 * (2 ** (retry_count - 1))
                logger.warning(f"Failed to subscribe to global control channel (attempt {retry_count}/3): {str(e)}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
    except Exception as e:
        logger.error(f"Failed to initialize Redis pubsub: {str(e)}")
        pubsub = None
    
    # Keep Redis key up-to-date with TTL refresh
    try:
        # Extend TTL on the active run key to prevent expiration during long runs
        await redis.set(
            f"active_run:{instance_id}:{agent_run_id}", 
            "running", 
            ex=redis.REDIS_KEY_TTL
        )
    except Exception as e:
        logger.warning(f"Failed to refresh active run key TTL: {str(e)}")
    
    # Start a background task to check for stop signals
    stop_signal_received = False
    stop_checker = None
    
    async def check_for_stop_signal():
        nonlocal stop_signal_received
        if not pubsub:
            logger.warning("Stop signal checker not started - pubsub not available")
            return
            
        try:
            while True:
                try:
                    message = await pubsub.get_message(timeout=0.5)
                    if message and message["type"] == "message":
                        stop_signal = "STOP"
                        if message["data"] == stop_signal or message["data"] == stop_signal.encode('utf-8'):
                            logger.info(f"Received stop signal for agent run: {agent_run_id} (instance: {instance_id})")
                            stop_signal_received = True
                            break
                except Exception as e:
                    logger.warning(f"Error checking for stop signals: {str(e)}")
                    # Brief pause before retry
                    await asyncio.sleep(1)
                    
                # Check if we should stop naturally
                if stop_signal_received:
                    break
                    
                # Periodically refresh the active run key's TTL
                try:
                    if total_responses % 100 == 0:
                        await redis.set(
                            f"active_run:{instance_id}:{agent_run_id}", 
                            "running", 
                            ex=redis.REDIS_KEY_TTL
                        )
                except Exception as e:
                    logger.warning(f"Failed to refresh active run key TTL: {str(e)}")
                
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.info(f"Stop signal checker task cancelled (instance: {instance_id})")
        except Exception as e:
            logger.error(f"Unexpected error in stop signal checker: {str(e)}", exc_info=True)
    
    # Start the stop signal checker if pubsub is available
    if pubsub:
        stop_checker = asyncio.create_task(check_for_stop_signal())
        logger.debug(f"Started stop signal checker for agent run: {agent_run_id} (instance: {instance_id})")
    else:
        logger.warning(f"No stop signal checker for agent run: {agent_run_id} - pubsub unavailable")
    
    try:
        # Run the agent
        logger.debug(f"Initializing agent generator for thread: {thread_id} (instance: {instance_id})")
        agent_gen = run_agent(
            thread_id=thread_id,
            project_id=project_id,
            stream=stream,
            thread_manager=thread_manager,
            sandbox=sandbox,
            model_name=model_name,
            enable_thinking=enable_thinking,
            reasoning_effort=reasoning_effort,
            enable_context_manager=enable_context_manager
        )
        
        # Collect all responses to save to database
        all_responses = []
        
        async for response in agent_gen:
            # Check if stop signal received
            if stop_signal_received:
                logger.info(f"Agent run stopped due to stop signal: {agent_run_id} (instance: {instance_id})")
                await update_agent_run_status(client, agent_run_id, "stopped", responses=all_responses)
                break
                
            # Check for billing error status
            if response.get('type') == 'status' and response.get('status') == 'error':
                error_msg = response.get('message', '')
                logger.info(f"Agent run failed with error: {error_msg} (instance: {instance_id})")
                await update_agent_run_status(client, agent_run_id, "failed", error=error_msg, responses=all_responses)
                break
                
            # Store response in memory
            if agent_run_id in active_agent_runs:
                active_agent_runs[agent_run_id].append(response)
                all_responses.append(response)
                total_responses += 1
        
        # Signal all done if we weren't stopped
        if not stop_signal_received:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Thread Run Response completed successfully: {agent_run_id} (duration: {duration:.2f}s, total responses: {total_responses}, instance: {instance_id})")
            
            # Add completion message to the stream
            completion_message = {
                "type": "status",
                "status": "completed",
                "message": "Agent run completed successfully"
            }
            if agent_run_id in active_agent_runs:
                active_agent_runs[agent_run_id].append(completion_message)
                all_responses.append(completion_message)
            
            # Update the agent run status
            await update_agent_run_status(client, agent_run_id, "completed", responses=all_responses)
            
            # Notify any clients monitoring the control channels that we're done
            try:
                if pubsub:
                    await redis.publish(f"agent_run:{agent_run_id}:control:{instance_id}", "END_STREAM")
                    await redis.publish(f"agent_run:{agent_run_id}:control", "END_STREAM")
                    logger.debug(f"Sent END_STREAM signals for agent run: {agent_run_id} (instance: {instance_id})")
            except Exception as e:
                logger.warning(f"Failed to publish END_STREAM signals: {str(e)}")
            
    except Exception as e:
        # Log the error and update the agent run
        error_message = str(e)
        traceback_str = traceback.format_exc()
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.error(f"Error in agent run {agent_run_id} after {duration:.2f}s: {error_message}\n{traceback_str} (instance: {instance_id})")
        
        # Add error message to the stream
        error_response = {
            "type": "status",
            "status": "error",
            "message": error_message
        }
        if agent_run_id in active_agent_runs:
            active_agent_runs[agent_run_id].append(error_response)
            if 'all_responses' in locals():
                all_responses.append(error_response)
            else:
                all_responses = [error_response]
        
        # Update the agent run with the error
        await update_agent_run_status(
            client, 
            agent_run_id, 
            "failed", 
            error=f"{error_message}\n{traceback_str}",
            responses=all_responses
        )
        
        # Notify any clients of the error
        try:
            if pubsub:
                await redis.publish(f"agent_run:{agent_run_id}:control:{instance_id}", "ERROR")
                await redis.publish(f"agent_run:{agent_run_id}:control", "ERROR")
                logger.debug(f"Sent ERROR signals for agent run: {agent_run_id} (instance: {instance_id})")
        except Exception as e:
            logger.warning(f"Failed to publish ERROR signals: {str(e)}")
            
    finally:
        # Ensure we always clean up the pubsub and stop checker
        if stop_checker:
            try:
                stop_checker.cancel()
                logger.debug(f"Cancelled stop signal checker task for agent run: {agent_run_id} (instance: {instance_id})")
            except Exception as e:
                logger.warning(f"Error cancelling stop checker: {str(e)}")
                
        if pubsub:
            try:
                await pubsub.unsubscribe()
                logger.debug(f"Successfully unsubscribed from pubsub for agent run: {agent_run_id} (instance: {instance_id})")
            except Exception as e:
                logger.warning(f"Error unsubscribing from pubsub: {str(e)}")
        
        # Clean up the Redis key
        try:
            await redis.delete(f"active_run:{instance_id}:{agent_run_id}")
            logger.debug(f"Deleted active run key for agent run: {agent_run_id} (instance: {instance_id})")
        except Exception as e:
            logger.warning(f"Error deleting active run key: {str(e)}")
                
        logger.info(f"Agent run background task fully completed for: {agent_run_id} (instance: {instance_id})")