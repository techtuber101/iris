"""
Agent Orchestrator for AgentPress.

This module orchestrates the flow between direct LLM responses and agentic tool-based processing.
It integrates the decision router to determine the appropriate response mode and handles
the execution flow accordingly.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime, timezone
from litellm import acompletion

from agentpress.decision_router import DecisionRouter
from agentpress.response_processor import ResponseProcessor
from agentpress.thread_manager import ThreadManager
from utils.logger import logger


class AgentOrchestrator:
    """
    Orchestrates the flow between direct LLM responses and agentic processing.
    """
    
    def __init__(self, thread_manager: ThreadManager):
        self.thread_manager = thread_manager
        self.decision_router = DecisionRouter()
        self.response_processor = ResponseProcessor()
        
    async def process_user_input(
        self,
        thread_id: str,
        user_input: str,
        context: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process user input with adaptive routing between direct and agentic modes.
        
        Args:
            thread_id: The thread identifier
            user_input: The user's input text
            context: Optional context from recent messages
            **kwargs: Additional parameters for processing
            
        Yields:
            Stream of response events
        """
        try:
            # Emit initial status
            yield {
                "type": "status",
                "status_type": "thread_run_start",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Make routing decision
            decision = self.decision_router.classify_input(user_input, context)
            
            logger.info(f"Routing decision for thread {thread_id}: {decision.mode} - {decision.reason}")
            
            # Emit routing decision status
            yield {
                "type": "status", 
                "status_type": "routing_decision",
                "mode": decision.mode,
                "reason": decision.reason,
                "confidence": decision.confidence,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if decision.mode == "direct":
                # Handle with direct LLM response
                async for event in self._handle_direct_mode(thread_id, user_input, context, **kwargs):
                    yield event
            else:
                # Handle with agentic mode (tools + agent)
                async for event in self._handle_agentic_mode(thread_id, user_input, context, **kwargs):
                    yield event
                    
        except Exception as e:
            logger.error(f"Error in agent orchestrator: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        finally:
            # Emit completion status
            yield {
                "type": "status",
                "status_type": "thread_run_end", 
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _handle_direct_mode(
        self,
        thread_id: str,
        user_input: str,
        context: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle direct mode with immediate LLM response.
        """
        try:
            # Emit intro response immediately for fast perceived feedback
            intro_response = await self._generate_intro_response(user_input)
            
            yield {
                "type": "assistant",
                "content": intro_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Build conversation context
            messages = await self._build_conversation_context(thread_id, context)
            messages.append({"role": "user", "content": user_input})
            
            # Generate main response
            response = await acompletion(
                model=kwargs.get("model", "gemini/gemini-2.5-pro"),
                messages=messages,
                max_tokens=kwargs.get("max_tokens", 1000),
                temperature=kwargs.get("temperature", 0.7),
                stream=False
            )
            
            content = response.choices[0].message.content
            if content is None:
                main_content = "I'm sorry, I couldn't generate a response."
            else:
                main_content = content.strip()
            
            # Only yield main content if it's different from intro
            if main_content.lower() != intro_response.lower():
                yield {
                    "type": "assistant",
                    "content": main_content,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error in direct mode: {e}")
            yield {
                "type": "assistant",
                "content": "I apologize, but I encountered an error processing your request. Please try again.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _handle_agentic_mode(
        self,
        thread_id: str,
        user_input: str,
        context: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle agentic mode with tools and agent processing.
        """
        try:
            # Emit intro response immediately for fast perceived feedback
            intro_response = await self._generate_intro_response(user_input)
            
            yield {
                "type": "assistant",
                "content": intro_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Emit progressive status updates
            yield {
                "type": "status",
                "status_type": "assistant_response_start",
                "message": "Computer is starting...",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Small delay for perceived responsiveness
            await asyncio.sleep(0.5)
            
            yield {
                "type": "status", 
                "status_type": "agent_working",
                "message": "Iris is now working on your request...",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Delegate to existing agent processing logic
            # This would integrate with the existing run_agent function
            from agent.run import run_agent
            
            async for event in run_agent(
                thread_id=thread_id,
                **kwargs
            ):
                yield event
                
        except Exception as e:
            logger.error(f"Error in agentic mode: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _generate_intro_response(self, user_input: str) -> str:
        """
        Generate a quick intro response for immediate feedback.
        """
        try:
            # Simple heuristics for intro responses
            if any(word in user_input.lower() for word in ['create', 'make', 'build', 'generate']):
                return "Hi! I'm on it — I'll help you create what you need and get started now."
            elif any(word in user_input.lower() for word in ['search', 'find', 'lookup', 'research']):
                return "Hi! I'm on it — I'll search for that information and get started now."
            elif any(word in user_input.lower() for word in ['analyze', 'process', 'calculate']):
                return "Hi! I'm on it — I'll analyze that for you and get started now."
            elif any(word in user_input.lower() for word in ['write', 'code', 'develop']):
                return "Hi! I'm on it — I'll help you write that and get started now."
            else:
                return "Hi! I'm on it — I'll help you with that and get started now."
                
        except Exception as e:
            logger.error(f"Error generating intro response: {e}")
            return "Hi! I'm working on your request now."
    
    async def _build_conversation_context(
        self,
        thread_id: str,
        context: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, str]]:
        """
        Build conversation context for LLM calls.
        """
        messages = []
        
        # Add system prompt
        system_prompt = """You are Iris, a helpful AI assistant. You're in direct conversation mode.
Provide friendly, helpful responses to questions and conversations.
Keep responses concise but informative. Be conversational and engaging."""
        
        messages.append({"role": "system", "content": system_prompt})
        
        # Add context from recent messages
        if context:
            for msg in context[-5:]:  # Last 5 messages for context
                if isinstance(msg, dict) and msg.get('content'):
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    if role in ['user', 'assistant'] and content:
                        messages.append({"role": role, "content": content})
        
        return messages

