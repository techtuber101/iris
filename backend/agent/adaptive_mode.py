"""
Adaptive Mode Implementation for Iris AI

This module determines whether a user query requires simple LLM response
or full agentic mode with sandbox execution.
"""

import os
import re
from typing import Dict, Any, Optional, Tuple
from litellm import acompletion
from utils.logger import logger

# Get model configuration
MODEL_TO_USE = os.getenv("MODEL_TO_USE", "gemini/gemini-2.5-pro")

# Simple patterns that indicate basic conversation
SIMPLE_PATTERNS = [
    r'^(hi|hello|hey|good morning|good afternoon|good evening)[\s\.,!]*$',
    r'^(how are you|what\'s up|how\'s it going)[\s\.,!?]*$',
    r'^(thanks?|thank you|thx)[\s\.,!]*$',
    r'^(bye|goodbye|see you|farewell)[\s\.,!]*$',
    r'^(yes|no|ok|okay|sure|alright)[\s\.,!]*$',
    r'^(what is|what are|define|explain) [a-zA-Z\s]{1,20}[\s\.,!?]*$',
    r'^(who is|who are) [a-zA-Z\s]{1,30}[\s\.,!?]*$',
]

# Complex patterns that definitely need agentic mode
COMPLEX_PATTERNS = [
    r'(create|generate|build|make|develop|write|code|program)',
    r'(file|folder|directory|project|website|app|application)',
    r'(analyze|research|find|search|scrape|crawl|browse)',
    r'(install|setup|configure|deploy|run|execute)',
    r'(pdf|csv|json|html|css|javascript|python|code)',
    r'(download|upload|save|export|import)',
    r'(automation|workflow|script|tool|utility)',
]

def normalize_text_input(text) -> str:
    """
    Defensively normalize text input to handle None, empty, and non-string types.

    Args:
        text: Input text that might be None, empty, or non-string

    Returns:
        str: Normalized text, guaranteed to be a non-empty string after stripping
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return text.strip()

async def analyze_query_complexity(query: str, thread_history: Optional[list] = None) -> Tuple[str, str, Dict[str, Any]]:
    """
    Analyze if a query needs simple response or full agentic mode.

    Args:
        query: The user's query
        thread_history: Previous conversation context

    Returns:
        Tuple of (mode, reasoning, metadata)
        - mode: "simple" or "agentic"
        - reasoning: Explanation of the decision
        - metadata: Additional context for the decision
    """

    query_lower = normalize_text_input(query)

    # Handle empty query after normalization
    if not query_lower:
        return "simple", "Empty or whitespace-only query", {"empty_query": True}

    # Quick pattern matching for obvious cases
    for pattern in SIMPLE_PATTERNS:
        if re.match(pattern, query_lower, re.IGNORECASE):
            return "simple", f"Matched simple pattern: {pattern}", {"pattern_matched": True}
    
    for pattern in COMPLEX_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return "agentic", f"Matched complex pattern: {pattern}", {"pattern_matched": True}
    
    # For ambiguous cases, use LLM to decide
    try:
        decision_prompt = f"""
You are an AI assistant that determines if a user query requires:
1. SIMPLE: Just a conversational response (greetings, basic questions, explanations)
2. AGENTIC: Tool usage, file operations, coding, research, or complex tasks

Query: "{query}"

Context from previous messages: {thread_history[-3:] if thread_history else "None"}

Respond with exactly one word: SIMPLE or AGENTIC

Then on a new line, provide a brief reason (max 50 words).
"""

        response = await acompletion(
            model=MODEL_TO_USE,
            messages=[{"role": "user", "content": decision_prompt}],
            max_tokens=100,
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        if content is None:
            return "agentic", "Error in analysis, defaulting to agentic mode", {"error": True}

        content = content.strip()
        lines = content.split('\n', 1)
        
        decision = lines[0].strip().upper()
        reasoning = lines[1].strip() if len(lines) > 1 else "LLM analysis"
        
        if decision == "SIMPLE":
            return "simple", reasoning, {"llm_decision": True}
        elif decision == "AGENTIC":
            return "agentic", reasoning, {"llm_decision": True}
        else:
            # Fallback: if unclear, default to agentic for safety
            return "agentic", "Unclear decision, defaulting to agentic mode", {"fallback": True}
            
    except Exception as e:
        logger.warning(f"Error in LLM decision making: {str(e)}")
        # Fallback: default to agentic mode for safety
        return "agentic", "Error in analysis, defaulting to agentic mode", {"error": True}

async def handle_simple_query(query: str, thread_history: Optional[list] = None) -> str:
    """
    Handle simple queries with direct LLM response.

    Args:
        query: The user's query
        thread_history: Previous conversation context

    Returns:
        Direct response string
    """

    try:
        # Normalize the query input to handle None/empty cases
        normalized_query = normalize_text_input(query)

        # Handle empty query
        if not normalized_query:
            return "Hi! How can I help you today?"

        # Build context from thread history
        messages = []

        if thread_history:
            # Add recent context (last 5 messages)
            for msg in thread_history[-5:]:
                if isinstance(msg, dict):
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    if content and role in ['user', 'assistant']:
                        messages.append({"role": role, "content": content})

        # Add current query (using normalized version)
        messages.append({"role": "user", "content": normalized_query})
        
        # System prompt for simple mode
        system_prompt = """You are Iris, a helpful AI assistant. You're in simple conversation mode.
Provide friendly, helpful responses to basic questions and conversations.
Keep responses concise but informative. Be conversational and engaging."""
        
        # Insert system message at the beginning
        messages.insert(0, {"role": "system", "content": system_prompt})
        
        response = await acompletion(
            model=MODEL_TO_USE,
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )

        content = response.choices[0].message.content
        if content is None:
            return "I'm sorry, I couldn't generate a response. Please try again."

        return content.strip()
        
    except Exception as e:
        logger.error(f"Error in simple query handling: {str(e)}")
        return "I'm sorry, I encountered an error processing your request. Please try again."

def should_use_adaptive_mode() -> bool:
    """
    Check if adaptive mode is enabled via environment variable.
    
    Returns:
        True if adaptive mode should be used
    """
    return os.getenv("ENABLE_ADAPTIVE_MODE", "true").lower() in ["true", "1", "yes", "on"]

