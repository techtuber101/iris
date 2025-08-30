try:
    from .tool_registry import extract_tool_calls, registry, strip_tools_from_text
    from .executors import register_all_tools
except ImportError:
    # Fallback for when running as standalone script
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from tool_registry import extract_tool_calls, registry, strip_tools_from_text
    from executors import register_all_tools

# Import new XML-based tool runtime
try:
    from .tool_runtime import get_tool_registry, get_xml_runner, ToolExecutionResult
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from tool_runtime import get_tool_registry, get_xml_runner, ToolExecutionResult

# Import sandbox health checks
try:
    from sandbox.health import assert_daytona_ready, ensure_workspace_ready, SandboxHealthError
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sandbox'))
    from health import assert_daytona_ready, ensure_workspace_ready, SandboxHealthError

try:
    from services.db import admin_client
except ImportError:
    # Fallback for when running as standalone script
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))
    from db import admin_client

import json, logging, asyncio

logger = logging.getLogger(__name__)
TOOLS_READY = False
HEALTH_CHECKED = False

async def ensure_tools():
    """Initialize and register all tools."""
    global TOOLS_READY
    if not TOOLS_READY:
        # Register legacy tools
        register_all_tools()

        # Register XML-based tools with the new registry
        tool_registry = get_tool_registry()

        # Import and register tools that have XML schemas
        try:
            from .tools import (
                MessageTool, SandboxFilesTool, WebSearchTool, SandboxShellTool,
                SandboxBrowserTool, DataProvidersTool, SandboxDeployTool, SandboxExposeTool
            )

            # Register tools that need sandbox instances
            # Note: Real sandbox instances should be passed when available
            tool_registry.register_tool(MessageTool())

            logger.info("Registered XML-based tools in tool registry")

        except ImportError as e:
            logger.warning(f"Could not import some tools for XML registry: {e}")

        TOOLS_READY = True

async def perform_health_checks(sandbox=None):
    """Perform Daytona sandbox health checks (opt-in via IRIS_ENABLE_SANDBOX_HEALTHCHECK)."""
    import os
    if os.getenv("IRIS_ENABLE_SANDBOX_HEALTHCHECK", "false").lower() not in ("1", "true", "yes"):  # disabled by default
        return
    global HEALTH_CHECKED
    if not HEALTH_CHECKED and sandbox:
        try:
            logger.info("Performing Daytona sandbox health checks...")
            health_results = await assert_daytona_ready(sandbox)
            logger.info(f"Health checks passed: {health_results.get('overall_status', 'unknown')}")
            HEALTH_CHECKED = True
        except SandboxHealthError as e:
            logger.error(f"Health checks failed: {e}")
            raise
        except Exception as e:
            logger.warning(f"Could not perform health checks: {e}")

async def handle_assistant_message(thread_id: str, content: str, meta: dict, sandbox=None):
    """
    Handle assistant message with enhanced XML tool execution.

    Args:
        thread_id: The thread ID for the conversation
        content: The message content that may contain XML tool calls
        meta: Additional metadata
        sandbox: Optional sandbox instance for tools that need it

    Returns:
        bool: True if tools were executed, False if no tools found
    """
    await ensure_tools()

    # Perform health checks if sandbox is available
    await perform_health_checks(sandbox)

    # If a sandbox is available, ensure XML tool registry has sandbox-backed tools
    try:
        if sandbox is not None:
            # Register sandbox tools once per sandbox id
            global _registered_sandbox_tools
            try:
                _registered_sandbox_tools
            except NameError:
                _registered_sandbox_tools = set()
            sid = getattr(sandbox, 'id', None)
            if sid and sid not in _registered_sandbox_tools:
                tool_registry = get_tool_registry()
                from .tools import (
                    SandboxFilesTool, SandboxShellTool, SandboxDeployTool, SandboxExposeTool
                )
                tool_registry.register_tool(SandboxFilesTool(sandbox))
                tool_registry.register_tool(SandboxShellTool(sandbox))
                tool_registry.register_tool(SandboxDeployTool(sandbox))
                tool_registry.register_tool(SandboxExposeTool(sandbox))
                _registered_sandbox_tools.add(sid)
    except Exception as e:
        logger.warning(f"Failed to register sandbox tools for XML runtime: {e}")

    # Try XML-based tool execution first
    xml_runner = get_xml_runner()

    # Execute all XML tools found in the content
    tool_results = await xml_runner.execute_all(content)

    if tool_results:
        # Save tool execution results
        for result in tool_results:
            if result.success:
                await save_message(thread_id, "tool_result", {
                    "tag": result.tag,
                    "result": result.data,
                    "success": True
                })
            else:
                await save_message(thread_id, "tool_error", {
                    "tag": result.tag,
                    "error": result.error or "Unknown error",
                    "success": False
                })

        return True  # XML tools were handled

    # Fallback to legacy tool execution for backward compatibility
    calls = extract_tool_calls(content)
    if not calls:
        return False  # no tools → let outer loop decide

    # Execute legacy tools sequentially
    for call in calls:
        spec = registry.get(call["tag"])
        if not spec:
            logger.warning("No tool registered: %s", call["tag"])
            await save_message(thread_id, "tool_error", {"tag": call["tag"], "error": "unregistered"})
            continue

        args = {"attrs": call["attrs"], "body": call["body"]}
        await save_message(thread_id, "tool_start", {"tag": spec.name, "attrs": call["attrs"]})

        try:
            result = await spec.executor(args)
            await save_message(thread_id, "tool_result", {
                "tag": spec.name, "result": result
            })
        except Exception as e:
            logger.exception("Tool %s failed", spec.name)
            await save_message(thread_id, "tool_error", {
                "tag": spec.name, "error": str(e)
            })

    return True  # legacy tools were handled

async def save_message(thread_id: str, msg_type: str, payload: dict):
    """Save a message to the database."""
    try:
        sb = await admin_client()
        await sb.table("messages").insert({
            "thread_id": thread_id,
            "type": msg_type,
            "is_llm_message": False,
            "content": json.dumps(payload),
        }).execute()
    except Exception as e:
        logger.error(f"Failed to save message: {e}")
