"""
Simple Response Handler for Adaptive Mode

Handles simple queries that don't require full agentic mode.
"""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from agent.adaptive_mode import handle_simple_query
from utils.logger import logger

async def handle_simple_response(
    thread_id: str,
    query: str,
    agent_run_id: str,
    client,
    thread_manager
) -> None:
    """
    Handle a simple query with direct LLM response and save to thread.
    
    Args:
        thread_id: The thread ID
        query: The user's query
        agent_run_id: The agent run ID
        client: Database client
        thread_manager: Thread manager instance
    """
    
    try:
        logger.info(f"Handling simple response for thread {thread_id}")
        
        # Get thread history for context
        thread_history = []
        try:
            messages_result = await client.table('messages').select('*').eq('thread_id', thread_id).order('created_at').execute()
            if messages_result.data:
                for msg in messages_result.data[-10:]:  # Last 10 messages for context
                    if msg.get('is_llm_message', True):
                        content = msg.get('content', {})
                        if isinstance(content, str):
                            try:
                                content = json.loads(content)
                            except:
                                pass
                        
                        if isinstance(content, dict) and content.get('role') and content.get('content'):
                            thread_history.append({
                                'role': content['role'],
                                'content': content['content']
                            })
        except Exception as e:
            logger.warning(f"Could not fetch thread history: {str(e)}")
        
        # Generate simple response
        response = await handle_simple_query(query, thread_history)
        
        # Create assistant message
        assistant_message = {
            "role": "assistant",
            "content": response
        }
        
        # Save assistant response to thread
        await thread_manager.add_message(
            thread_id=thread_id,
            message_type="assistant",
            content=assistant_message,
            is_llm_message=True
        )
        
        # Update agent run status to completed
        await client.table('agent_runs').update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", agent_run_id).execute()
        
        logger.info(f"Simple response completed for thread {thread_id}")
        
    except Exception as e:
        logger.error(f"Error in simple response handling: {str(e)}")
        
        # Save error message
        error_message = {
            "role": "assistant",
            "content": "I'm sorry, I encountered an error processing your request. Please try again."
        }
        
        try:
            await thread_manager.add_message(
                thread_id=thread_id,
                message_type="assistant",
                content=error_message,
                is_llm_message=True
            )
        except:
            pass
        
        # Update agent run status to failed
        try:
            await client.table('agent_runs').update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", agent_run_id).execute()
        except:
            pass

