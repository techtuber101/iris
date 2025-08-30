"""
LLM API interface — Gemini only (via LiteLLM).

- Direct calls to Google Gemini through LiteLLM
- Streaming/tool calls supported
- Retries + logging
- OpenRouter/Bedrock/Anthropic paths are ignored/mapped away
"""

from typing import Union, Dict, Any, Optional, AsyncGenerator, List
import os
import json
import asyncio
import litellm
from utils.logger import logger

# LiteLLM tweaks
# litellm.set_verbose = True
litellm.modify_params = True

# Constants
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 30
RETRY_DELAY = 5

# Env-configured defaults
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_DEFAULT_MODEL = os.getenv("MODEL_TO_USE", "gemini/gemini-2.5-pro")

class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass

class LLMRetryError(LLMError):
    """Exception raised when retries are exhausted."""
    pass

def setup_api_keys() -> None:
    """Ensure Gemini API key is present; warn otherwise."""
    if GEMINI_API_KEY:
        logger.debug("GEMINI_API_KEY detected.")
        # LiteLLM will pick it from env automatically, but we also pass it explicitly.
        os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
    else:
        logger.warning("GEMINI_API_KEY not set — Gemini calls will fail.")

def _normalize_model_name(in_name: Optional[str]) -> str:
    """
    Normalize incoming model names to direct Gemini.
    - Maps OpenRouter Gemini aliases to 'gemini/...'
    - Falls back to GEMINI_DEFAULT_MODEL if empty.
    """
    name = (in_name or "").strip()
    if not name:
        return GEMINI_DEFAULT_MODEL

    # Map common OpenRouter Gemini variants to direct Gemini
    if name.startswith("openrouter/google/"):
        tail = name.split("openrouter/google/", 1)[1]
        # Normalize common ordering variants
        if tail == "gemini-pro-2.5":
            tail = "gemini-2.5-pro"
        return f"gemini/{tail}"

    if name.startswith("openrouter/"):
        logger.warning(f"OpenRouter model '{name}' provided, but OpenRouter is disabled. "
                       f"Using direct Gemini '{GEMINI_DEFAULT_MODEL}'.")
        return GEMINI_DEFAULT_MODEL

    return name

async def handle_error(error: Exception, attempt: int, max_attempts: int) -> None:
    """Handle API errors with appropriate delays and logging."""
    delay = RATE_LIMIT_DELAY if isinstance(error, litellm.exceptions.RateLimitError) else RETRY_DELAY
    logger.warning(f"Error on attempt {attempt + 1}/{max_attempts}: {str(error)}")
    logger.debug(f"Waiting {delay} seconds before retry...")
    await asyncio.sleep(delay)

def prepare_params(
    messages: List[Dict[str, Any]],
    model_name: str,
    temperature: float = 0,
    max_tokens: Optional[int] = None,
    response_format: Optional[Any] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto",
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,  # Ignored for Gemini
    stream: bool = False,
    top_p: Optional[float] = None,
    model_id: Optional[str] = None,  # Ignored for Gemini
    enable_thinking: Optional[bool] = False,  # Not used by Gemini
    reasoning_effort: Optional[str] = 'low'    # Not used by Gemini
) -> Dict[str, Any]:
    """Prepare parameters for a Gemini API call via LiteLLM."""
    effective_model = _normalize_model_name(model_name)

    params: Dict[str, Any] = {
        "model": effective_model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "stream": stream,
        # LiteLLM will ignore response_format if unsupported by provider.
        "response_format": response_format,
        # Pass the key explicitly (in addition to env) for clarity.
        "api_key": api_key or GEMINI_API_KEY,
    }

    # Token limit (LiteLLM expects 'max_tokens' for Gemini)
    if max_tokens is not None:
        params["max_tokens"] = max_tokens

    # Tools / function calling
    if tools:
        params["tools"] = tools
        params["tool_choice"] = tool_choice

    # Soft notices if Anthropic-style options are passed
    if enable_thinking:
        logger.info("`enable_thinking` requested, but Gemini doesn't use this parameter. Ignoring.")
    if reasoning_effort and reasoning_effort != 'low':
        logger.info("`reasoning_effort` requested, but Gemini doesn't use this parameter. Ignoring.")

    return params

async def make_llm_api_call(
    messages: List[Dict[str, Any]],
    model_name: str,
    response_format: Optional[Any] = None,
    temperature: float = 0,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto",
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    stream: bool = False,
    top_p: Optional[float] = None,
    model_id: Optional[str] = None,
    enable_thinking: Optional[bool] = False,
    reasoning_effort: Optional[str] = 'low'
) -> Union[Dict[str, Any], AsyncGenerator]:
    """
    Make an API call to Gemini via LiteLLM.

    Returns:
        Dict response or AsyncGenerator (if stream=True)
    """
    effective_model_logged = _normalize_model_name(model_name)
    logger.debug(
        f"LLM call → model: {effective_model_logged} | "
        f"thinking={enable_thinking} | effort={reasoning_effort} | stream={stream}"
    )

    params = prepare_params(
        messages=messages,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
        tools=tools,
        tool_choice=tool_choice,
        api_key=api_key,
        api_base=api_base,
        stream=stream,
        top_p=top_p,
        model_id=model_id,
        enable_thinking=enable_thinking,
        reasoning_effort=reasoning_effort
    )

    last_error: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"Attempt {attempt + 1}/{MAX_RETRIES}")
            response = await litellm.acompletion(**params)
            logger.debug("Received response from Gemini successfully.")
            return response

        except (litellm.exceptions.RateLimitError,
                litellm.exceptions.APIConnectionError,
                litellm.exceptions.AuthenticationError,
                json.JSONDecodeError) as e:
            last_error = e
            await handle_error(e, attempt, MAX_RETRIES)

        except Exception as e:
            logger.error(f"Unexpected error during API call: {str(e)}", exc_info=True)
            raise LLMError(f"API call failed: {str(e)}")

    error_msg = f"Failed to make API call after {MAX_RETRIES} attempts"
    if last_error:
        error_msg += f". Last error: {str(last_error)}"
    logger.error(error_msg, exc_info=True)
    raise LLMRetryError(error_msg)

# Initialize on import
setup_api_keys()
