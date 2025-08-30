from typing import Optional, Dict, List
from uuid import uuid4

from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.sandbox import SandboxToolsBase, Sandbox

"""
We pass plain dict payloads to Daytona SDK's execute_session_command to satisfy
its Pydantic validation (expects dict or SDK SessionExecuteRequest). This keeps
compatibility with both real SDK and mock.
"""

class SandboxShellTool(SandboxToolsBase):
    """
    Run shell commands inside the Daytona sandbox.
    IMPORTANT: We cd into $HOME/workspace and ensure it exists.
    """

    def __init__(self, sandbox: Sandbox):
        super().__init__(sandbox)
        self._sessions: Dict[str, str] = {}  # Maps session names to session IDs
        # Ensure workspace directory exists on initialization
        self._ensure_workspace_directory()

    def _ensure_workspace_directory(self):
        """Ensure the workspace directory exists in the sandbox."""
        try:
            # Create workspace directory if it doesn't exist
            session_id = str(uuid4())
            self.sandbox.process.create_session(session_id)
            
            payload = {
                "command": "mkdir -p $HOME/workspace && cd $HOME/workspace && pwd",
                "var_async": False,
            }
            
            # Call execute_session_command with broad compatibility across SDKs/mocks
            try:
                # Prefer passing timeout to avoid hangs
                response = self._exec_with_timeout(session_id, payload, timeout=10)
            except TypeError:
                try:
                    response = self.sandbox.process.execute_session_command(session_id=session_id, session_execute_request=payload)
                except TypeError:
                    response = self.sandbox.process.execute_session_command(session_id=session_id, request=payload)
            
            # Clean up the temporary session
            try:
                self.sandbox.process.delete_session(session_id)
            except:
                pass  # Ignore cleanup errors
                
            if response.exit_code != 0:
                print(f"Warning: Failed to create workspace directory: {response.exit_code}")
            else:
                print("Workspace directory ensured at $HOME/workspace")
                
        except Exception as e:
            print(f"Warning: Could not ensure workspace directory: {str(e)}")

    async def _ensure_session(self, session_name: str = "default") -> str:
        if session_name not in self._sessions:
            session_id = str(uuid4())
            try:
                self.sandbox.process.create_session(session_id)
                self._sessions[session_name] = session_id
            except Exception as e:
                raise RuntimeError(f"Failed to create session: {str(e)}")
        return self._sessions[session_name]

    async def _cleanup_session(self, session_name: str):
        if session_name in self._sessions:
            try:
                self.sandbox.process.delete_session(self._sessions[session_name])
                del self._sessions[session_name]
            except Exception as e:
                print(f"Warning: Failed to cleanup session {session_name}: {str(e)}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a shell command under $HOME/workspace. Use named sessions to maintain state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run"},
                    "folder": {"type": "string", "description": "Optional subfolder of workspace"},
                    "session_name": {"type": "string", "default": "default"},
                    "timeout": {"type": "integer", "default": 60}
                },
                "required": ["command"]
            }
        }
    })
    @xml_schema(
        tag_name="execute-command",
        mappings=[
            {"param_name": "command", "node_type": "content", "path": "."},
            {"param_name": "folder", "node_type": "attribute", "path": ".", "required": False},
            {"param_name": "session_name", "node_type": "attribute", "path": ".", "required": False},
            {"param_name": "timeout", "node_type": "attribute", "path": ".", "required": False}
        ],
        example="""
        <execute-command>ls -la</execute-command>
        """
    )
    async def execute_command(
        self,
        command: str,
        folder: Optional[str] = None,
        session_name: str = "default",
        timeout: int = 60
    ) -> ToolResult:
        try:
            session_id = await self._ensure_session(session_name)

            # Build 'cd' into $HOME/workspace (and optional subfolder)
            if folder:
                # Normalize folder to be relative to workspace (strip leading slashes and optional 'workspace/' prefix)
                folder = folder.strip("/")
                if folder.startswith("workspace/"):
                    folder = folder[len("workspace/"):]
                cd_prefix = f'cd {self.workspace_abs_for_shell}/{folder}'
            else:
                cd_prefix = f'cd {self.workspace_abs_for_shell}'

            full_cmd = f'{cd_prefix} && {command}'

            payload = {"command": full_cmd, "var_async": False}

            try:
                response = self._exec_with_timeout(session_id, payload, timeout=timeout)
            except TypeError:
                try:
                    response = self.sandbox.process.execute_session_command(session_id=session_id, session_execute_request=payload)
                except TypeError:
                    response = self.sandbox.process.execute_session_command(session_id=session_id, request=payload)

            logs = self.sandbox.process.get_session_command_logs(
                session_id=session_id,
                command_id=response.cmd_id
            )

            if response.exit_code == 0:
                return self.success_response({
                    "output": logs,
                    "exit_code": response.exit_code
                })
            else:
                return self.fail_response(f"Command failed with exit code {response.exit_code}: {logs or ''}")

        except Exception as e:
            return self.fail_response(f"Error executing command: {str(e)}")

    async def cleanup(self):
        for session_name in list(self._sessions.keys()):
            await self._cleanup_session(session_name)

    # Internal helper to execute with timeout across SDK signatures
    def _exec_with_timeout(self, session_id: str, payload: dict, timeout: int):
        try:
            # Positional timeout
            return self.sandbox.process.execute_session_command(session_id, payload, timeout)
        except TypeError:
            pass
        try:
            # Keyword timeout
            return self.sandbox.process.execute_session_command(session_id, payload, timeout=timeout)
        except TypeError:
            pass
        try:
            # Keywords style
            return self.sandbox.process.execute_session_command(session_id=session_id, session_execute_request=payload, timeout=timeout)
        except TypeError:
            pass
        # Fallback without timeout (last resort)
        return self.sandbox.process.execute_session_command(session_id, payload)
