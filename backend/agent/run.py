import os
import json
import re
from uuid import uuid4
from typing import Optional

from agent.tools.message_tool import MessageTool
from agent.tools.sb_deploy_tool import SandboxDeployTool
from agent.tools.sb_expose_tool import SandboxExposeTool
from agent.tools.web_search_tool import WebSearchTool
from dotenv import load_dotenv

from agentpress.thread_manager import ThreadManager
from agentpress.response_processor import ProcessorConfig
from agent.tools.sb_shell_tool import SandboxShellTool
from agent.tools.sb_files_tool import SandboxFilesTool
from agent.tools.sb_browser_tool import SandboxBrowserTool
from agent.tools.data_providers_tool import DataProvidersTool
from agent.prompt import get_system_prompt
from sandbox.sandbox import create_sandbox, get_or_start_sandbox
from utils.billing import check_billing_status, get_account_id_from_thread
from .runner import handle_assistant_message, ensure_tools

load_dotenv()

# --- New: read model from env, default to Gemini 2.5 Pro ---
MODEL_TO_USE = os.getenv("MODEL_TO_USE", "gemini/gemini-2.5-pro")

async def run_agent(
    thread_id: str,
    project_id: str,
    sandbox,
    stream: bool,
    thread_manager: Optional[ThreadManager] = None,
    native_max_auto_continues: int = 25,
    max_iterations: int = 150,
    model_name: str = MODEL_TO_USE,  # was anthropic/claude-3-7-sonnet-latest
    enable_thinking: Optional[bool] = False,
    reasoning_effort: Optional[str] = 'low',
    enable_context_manager: bool = True
):
    """Run the development agent with specified configuration."""

    # Initialize our agentic tools
    await ensure_tools()

    if not thread_manager:
        # Create ThreadManager with a new DBConnection (will be initialized on first use)
        thread_manager = ThreadManager()
    client = await thread_manager.db.get_client()

    # Get account ID from thread for billing checks
    account_id = await get_account_id_from_thread(client, thread_id)
    if not account_id:
        raise ValueError("Could not determine account ID for thread")

    # Tools
    # Register non-sandbox tools immediately.
    # Sandbox tools will be registered lazily on first detected tool call.
    sandbox_registered = False
    async def ensure_sandbox_ready() -> None:
        nonlocal sandbox, sandbox_registered
        if sandbox_registered:
            return
        # Prefer warm pool acquisition
        from sandbox.pool import get_pool
        pool = get_pool()
        client = await thread_manager.db.get_client()
        project = await client.table('projects').select('*').eq('project_id', project_id).execute()
        pr_data = project.data[0] if project.data else None
        sbx_id = pr_data.get('sandbox', {}).get('id') if pr_data else None
        if sbx_id:
            sandbox = await get_or_start_sandbox(sbx_id)
        else:
            # Acquire pre-warmed or create on demand
            sandbox = await pool.acquire()
            vnc_link = sandbox.get_preview_link(6080)
            website_link = sandbox.get_preview_link(8080)
            vnc_url = vnc_link.url if hasattr(vnc_link, 'url') else str(vnc_link)
            website_url = website_link.url if hasattr(website_link, 'url') else str(website_link)
            token = getattr(vnc_link, 'token', None)
            await client.table('projects').update({
                'sandbox': {
                    'id': sandbox.id,
                    'pass': '',
                    'vnc_preview': vnc_url,
                    'sandbox_url': website_url,
                    'token': token
                }
            }).eq('project_id', project_id).execute()
        thread_manager.add_tool(SandboxShellTool, sandbox=sandbox)
        thread_manager.add_tool(SandboxFilesTool, sandbox=sandbox)
        thread_manager.add_tool(SandboxBrowserTool, sandbox=sandbox, thread_id=thread_id, thread_manager=thread_manager)
        thread_manager.add_tool(SandboxDeployTool, sandbox=sandbox)
        thread_manager.add_tool(SandboxExposeTool, sandbox=sandbox)
        sandbox_registered = True
    thread_manager.add_tool(MessageTool)  # used by prompt (no direct tool call needed)

    if os.getenv("TAVILY_API_KEY"):
        thread_manager.add_tool(WebSearchTool)
    else:
        print("TAVILY_API_KEY not found, WebSearchTool will not be available.")

    if os.getenv("RAPID_API_KEY"):
        thread_manager.add_tool(DataProvidersTool)

    system_message = {"role": "system", "content": get_system_prompt()}

    # Wire lazy sandbox start into response processor
    async def pre_tool():
        await ensure_sandbox_ready()
    thread_manager.response_processor.pre_tool_hook = pre_tool

    iteration_count = 0
    continue_execution = True

    while continue_execution and iteration_count < max_iterations:
        iteration_count += 1
        if iteration_count == 1:
            print(f"[Agent] Model: {model_name}")
        # Reduce console noise in hot path
        if iteration_count <= 2:
            print(f"Running iteration {iteration_count}...")

        # Billing check on each iteration
        can_run, message, subscription = await check_billing_status(client, account_id)
        if not can_run:
            error_msg = f"Billing limit reached: {message}"
            # Yield a special message to indicate billing limit reached
            yield {
                "type": "status",
                "status": "stopped",
                "message": error_msg
            }
            break

            # Check for tool execution in assistant messages
        latest_message = await client.table('messages') \
            .select('*') \
            .eq('thread_id', thread_id) \
            .in_('type', ['assistant', 'tool', 'user', 'tool_start', 'tool_result', 'tool_error']) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()

        if latest_message.data and len(latest_message.data) > 0:
            message_type = latest_message.data[0].get('type')
            if message_type == 'assistant':
                # Check if this assistant message contains tools to execute
                content = latest_message.data[0].get('content', '')
                if isinstance(content, str):
                    try:
                        content_json = json.loads(content)
                        assistant_text = content_json.get('content', '')
                    except json.JSONDecodeError:
                        assistant_text = content
                else:
                    assistant_text = str(content)

                # Ensure sandbox is ready before executing tools, then handle XML tools with sandbox
                await ensure_sandbox_ready()
                handled_tools = await handle_assistant_message(thread_id, assistant_text, {}, sandbox=sandbox)
                if handled_tools:
                    print(f"Executed tools from assistant message, continuing...")
                    continue  # Continue the loop to process tool results

                print(f"Last message was from assistant with no tools, stopping execution")
                continue_execution = False
                break

        # Attach latest browser state (image + JSON) as temporary user message
        latest_browser_state = await client.table('messages') \
            .select('*') \
            .eq('thread_id', thread_id) \
            .eq('type', 'browser_state') \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()

        temporary_message = None
        if latest_browser_state.data and len(latest_browser_state.data) > 0:
            try:
                content = json.loads(latest_browser_state.data[0]["content"])
                screenshot_base64 = content.get("screenshot_base64")
                # Copy without big fields
                browser_state = content.copy()
                browser_state.pop('screenshot_base64', None)
                browser_state.pop('screenshot_url', None)
                browser_state.pop('screenshot_url_base64', None)

                temporary_message = {"role": "user", "content": []}
                if browser_state:
                    temporary_message["content"].append({
                        "type": "text",
                        "text": f"The following is the current state of the browser:\n{browser_state}"
                    })
                if screenshot_base64:
                    temporary_message["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screenshot_base64}",
                        }
                    })
                else:
                    print("@@@@@ THIS TIME NO SCREENSHOT!!")
            except Exception as e:
                print(f"Error parsing browser state: {e}")

        # Token handling: leave None for Gemini (LiteLLM default).
        is_sonnet = "sonnet" in model_name.lower()
        max_tokens = 64000 if is_sonnet else None

        response = await thread_manager.run_thread(
            thread_id=thread_id,
            system_prompt=system_message,
            stream=stream,
            llm_model=model_name,
            llm_temperature=0,
            llm_max_tokens=max_tokens,
            tool_choice="auto",
            max_xml_tool_calls=1,
            temporary_message=temporary_message,
            processor_config=ProcessorConfig(
                xml_tool_calling=True,
                native_tool_calling=False,
                execute_tools=True,
                execute_on_stream=True,
                tool_execution_strategy="parallel",
                xml_adding_strategy="user_message",
            ),
            native_max_auto_continues=native_max_auto_continues,
            include_xml_examples=True,
            enable_thinking=enable_thinking,
            reasoning_effort=reasoning_effort,
            enable_context_manager=enable_context_manager
        )

        if isinstance(response, dict) and "status" in response and response["status"] == "error":
            yield response
            break

        # Track if we saw <ask> or <complete> to decide whether to stop
        last_tool_call = None

        async for chunk in response:
            # Detect XML tool usage in assistant chunks
            if chunk.get('type') == 'assistant' and 'content' in chunk:
                try:
                    content = chunk.get('content', '{}')
                    assistant_content_json = json.loads(content) if isinstance(content, str) else content
                    assistant_text = assistant_content_json.get('content', '')
                    if isinstance(assistant_text, str):
                        # Lazy sandbox start detection:
                        # If the assistant intends to use any tool tags (other than ask/complete),
                        # ensure the sandbox is started and tools are registered, and inform user.
                        if '<execute-command' in assistant_text or '<create-file' in assistant_text or '<delete-file' in assistant_text or '<full-file-rewrite' in assistant_text or '<browser-' in assistant_text or '<deploy' in assistant_text or '<expose-port' in assistant_text:
                            if not sandbox_registered:
                                # Yield a quick narrative before starting sandbox
                                plan_msg = {"role": "assistant", "content": "I’ll start Iris’s Computer to carry this out and then proceed."}
                                yield {"type": "assistant", "is_llm_message": True, "content": json.dumps(plan_msg)}
                                await ensure_sandbox_ready()
                        if '</ask>' in assistant_text or '</complete>' in assistant_text:
                            xml_tool = 'ask' if '</ask>' in assistant_text else 'complete'
                            last_tool_call = xml_tool
                            print(f"Agent used XML tool: {xml_tool}")
                except json.JSONDecodeError:
                    # non-JSON streaming deltas are fine
                    pass
                except Exception as e:
                    print(f"Error processing assistant chunk: {e}")

            yield chunk

        if last_tool_call in ['ask', 'complete']:
            print(f"Agent decided to stop with tool: {last_tool_call}")
            continue_execution = False


# -----------------------
# TESTING (CLI harness)
# -----------------------

async def test_agent():
    """Test function to run the agent with a sample query"""
    from agentpress.thread_manager import ThreadManager
    from services.supabase import DBConnection

    # Initialize ThreadManager
    thread_manager = ThreadManager()

    # Create a test thread directly with Postgres function
    client = await DBConnection().get_client()

    try:
        # Get user's personal account (RPC is project-specific; hardcoded fallback used below)
        account_result = await client.rpc('get_personal_account').execute()

        # Replace with your account ID as needed
        account_id = "a5fe9cb6-4812-407e-a61c-fe95b7320c59"
        if not account_id:
            print("Error: Could not get account ID")
            return

        # Find or create a test project
        project_result = await client.table('projects').select('*').eq('name', 'test11').eq('account_id', account_id).execute()
        if project_result.data and len(project_result.data) > 0:
            project_id = project_result.data[0]['project_id']
            print(f"\n🔄 Using existing test project: {project_id}")
        else:
            project_result = await client.table('projects').insert({
                "name": "test11",
                "account_id": account_id
            }).execute()
            project_id = project_result.data[0]['project_id']
            print(f"\n✨ Created new test project: {project_id}")

        # Create a thread for this project
        thread_result = await client.table('threads').insert({
            'project_id': project_id,
            'account_id': account_id
        }).execute()
        thread_data = thread_result.data[0] if thread_result.data else None

        if not thread_data:
            print("Error: No thread data returned")
            return

        thread_id = thread_data['thread_id']
    except Exception as e:
        print(f"Error setting up thread: {str(e)}")
        return

    print(f"\n🤖 Agent Thread Created: {thread_id}\n")

    # Interactive message input loop
    while True:
        user_message = input("\n💬 Enter your message (or 'exit' to quit): ")
        if user_message.lower() == 'exit':
            break

        if not user_message.strip():
            print("\n🔄 Running agent...\n")
            await process_agent_response(thread_id, project_id, thread_manager)
            continue

        # Add the user message to the thread
        await thread_manager.add_message(
            thread_id=thread_id,
            type="user",
            content={
                "role": "user",
                "content": user_message
            },
            is_llm_message=True
        )

        print("\n🔄 Running agent...\n")
        await process_agent_response(thread_id, project_id, thread_manager)

    print("\n👋 Test completed. Goodbye!")


async def process_agent_response(
    thread_id: str,
    project_id: str,
    thread_manager: ThreadManager,
    stream: bool = True,
    model_name: str = MODEL_TO_USE,  # was anthropic/claude-3-7-sonnet-latest
    enable_thinking: Optional[bool] = False,
    reasoning_effort: Optional[str] = 'low',
    enable_context_manager: bool = True
):
    """Process the streaming response from the agent."""
    chunk_counter = 0
    current_response = ""
    tool_usage_counter = 0

    # Create a test sandbox for processing
    sandbox_pass = str(uuid4())
    sandbox = create_sandbox(sandbox_pass)
    print(f"\033[91mTest sandbox created: {str(sandbox.get_preview_link(6080))}/vnc_lite.html?password={sandbox_pass}\033[0m")

    async for chunk in run_agent(
        thread_id=thread_id,
        project_id=project_id,
        sandbox=sandbox,
        stream=stream,
        thread_manager=thread_manager,
        native_max_auto_continues=25,
        model_name=model_name,
        enable_thinking=enable_thinking,
        reasoning_effort=reasoning_effort,
        enable_context_manager=enable_context_manager
    ):
        chunk_counter += 1

        if chunk.get('type') == 'assistant':
            try:
                content = chunk.get('content', '{}')
                content_json = json.loads(content) if isinstance(content, str) else content
                actual_content = content_json.get('content', '')
                if actual_content:
                    if '<' in actual_content and '>' in actual_content:
                        if len(actual_content) < 500:
                            print(actual_content, end='', flush=True)
                        else:
                            if '</ask>' in actual_content:
                                print("<ask>...</ask>", end='', flush=True)
                            elif '</complete>' in actual_content:
                                print("<complete>...</complete>", end='', flush=True)
                            else:
                                print("<tool_call>...</tool_call>", end='', flush=True)
                    else:
                        print(actual_content, end='', flush=True)
                    current_response += actual_content
            except json.JSONDecodeError:
                raw_content = chunk.get('content', '')
                print(raw_content, end='', flush=True)
                current_response += raw_content
            except Exception as e:
                print(f"\nError processing assistant chunk: {e}\n")

        elif chunk.get('type') == 'tool':
            tool_name = "UnknownTool"
            result_content = "No content"

            metadata = chunk.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}

            parsing_details = metadata.get('parsing_details')
            if parsing_details:
                tool_name = parsing_details.get('xml_tag_name', 'UnknownTool')

            try:
                content = chunk.get('content', '{}')
                content_json = json.loads(content) if isinstance(content, str) else content
                tool_result_str = content_json.get('content', '')

                match = re.search(rf'<{tool_name}>(.*?)</{tool_name}>', tool_result_str, re.DOTALL)
                if match:
                    result_content = match.group(1).strip()
                    try:
                        result_obj = json.loads(result_content)
                        result_content = json.dumps(result_obj, indent=2)
                    except json.JSONDecodeError:
                        pass
                else:
                    result_content = tool_result_str
            except json.JSONDecodeError:
                result_content = chunk.get('content', 'Error parsing tool content')
            except Exception as e:
                result_content = f"Error processing tool chunk: {e}"

            print(f"\n\n🛠️  TOOL RESULT [{tool_name}] → {result_content}")

        elif chunk.get('type') == 'status':
            try:
                status_content = chunk.get('content', '{}')
                status_content = json.loads(status_content) if isinstance(status_content, str) else status_content

                status_type = status_content.get('status_type')
                function_name = status_content.get('function_name', '')
                xml_tag_name = status_content.get('xml_tag_name', '')
                tool_name = xml_tag_name or function_name

                if status_type == 'tool_started' and tool_name:
                    tool_usage_counter += 1
                    print(f"\n⏳ TOOL STARTING #{tool_usage_counter} [{tool_name}]")
                    print("  " + "-" * 40)
                    if current_response:
                        print("\nContinuing response:", flush=True)
                        print(current_response, end='', flush=True)
                elif status_type == 'tool_completed' and tool_name:
                    print(f"\n✅ TOOL COMPLETED: {tool_name}")
                elif status_type == 'finish':
                    finish_reason = status_content.get('finish_reason', '')
                    if finish_reason:
                        print(f"\n📌 Finished: {finish_reason}")

            except json.JSONDecodeError:
                print(f"\nWarning: Could not parse status content JSON: {chunk.get('content')}")
            except Exception as e:
                print(f"\nError processing status chunk: {e}")

    print(f"\n\n✅ Agent run completed with {tool_usage_counter} tool executions")


if __name__ == "__main__":
    import asyncio
    load_dotenv()
    asyncio.run(test_agent())
