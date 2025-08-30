# from daytona_sdk import SessionExecuteRequest

# Stub class to prevent import errors
class SessionExecuteRequest:
    def __init__(self, command=None, var_async=False):
        self.command = command
        self.var_async = var_async
from typing import Optional

from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.sandbox import SandboxToolsBase, Sandbox, upload_file_bytes, atomic_write_file_bytes
from utils.files_utils import EXCLUDED_FILES, EXCLUDED_DIRS, EXCLUDED_EXT, should_exclude_file, clean_path
from utils.logger import logger

class SandboxFilesTool(SandboxToolsBase):
    """File operations via Daytona SDK under user workspace (~/<user>/workspace)."""

    def __init__(self, sandbox: Sandbox):
        super().__init__(sandbox)
        self.SNIPPET_LINES = 4
        # Use relative root per Daytona SDK
        self.workspace_rel = "workspace"
        # Ensure workspace directory exists
        self._ensure_workspace_directory()

    def _ensure_workspace_directory(self):
        """Ensure the workspace directory exists in the sandbox."""
        try:
            # Try to create the workspace directory if it doesn't exist
            self.sandbox.fs.create_folder(self.workspace_rel)
            logger.debug("Workspace directory ensured at ~/workspace")
        except Exception:
            # Directory might already exist, which is fine
            try:
                # Verify it exists by listing it
                self.sandbox.fs.list_files(self.workspace_rel)
                logger.debug("Workspace directory already exists at ~/workspace")
            except Exception as list_error:
                logger.warning(f"Could not ensure workspace directory: {str(list_error)}")

    def clean_path(self, path: str) -> str:
        return clean_path(path, self.workspace_rel)

    def _should_exclude_file(self, rel_path: str) -> bool:
        return should_exclude_file(rel_path)

    def _file_exists(self, rel_path: str) -> bool:
        try:
            self.sandbox.fs.get_file_info(rel_path)
            return True
        except Exception:
            return False

    async def get_workspace_state(self) -> dict:
        files_state = {}
        try:
            files = self.sandbox.fs.list_files(self.workspace_rel)
            for file_info in files:
                rel_path = file_info.name
                if self._should_exclude_file(rel_path) or file_info.is_dir:
                    continue
                try:
                    content = self.sandbox.fs.download_file(f"{self.workspace_rel}/{rel_path}").decode()
                    files_state[rel_path] = {
                        "content": content,
                        "is_dir": file_info.is_dir,
                        "size": file_info.size,
                        "modified": file_info.mod_time
                    }
                except UnicodeDecodeError:
                    pass
                except Exception:
                    pass
            return files_state
        except Exception:
            return {}

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a file under ~/workspace (SDK path: 'workspace/...').",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "file_contents": {"type": "string"},
                    "permissions": {"type": "string", "default": "644"}
                },
                "required": ["file_path", "file_contents"]
            }
        }
    })
    @xml_schema(
        tag_name="create-file",
        mappings=[
            {"param_name": "file_path", "node_type": "attribute", "path": "file_path"},
            {"param_name": "file_contents", "node_type": "content", "path": "."}
        ],
        example="""
        <create-file file_path="src/main.py">print('hi')</create-file>
        """
    )
    async def create_file(self, file_path: str, file_contents: str, permissions: str = "644") -> ToolResult:
        rel_path = self.clean_path(file_path)
        # clean_path already returns a path under workspace_rel (e.g., 'workspace/...')
        full_rel = rel_path
        try:
            if self._file_exists(full_rel):
                return self.fail_response(f"File '{rel_path}' already exists.")
            parent = "/".join(full_rel.split("/")[:-1])
            if parent:
                self.sandbox.fs.create_folder(parent, "755")
            # Daytona FS may expect bytes; accept either bytes or str
            data = file_contents if isinstance(file_contents, (bytes, bytearray)) else file_contents.encode()
            upload_file_bytes(self.sandbox, full_rel, data)
            self.sandbox.fs.set_file_permissions(full_rel, permissions)
            display_path = f"/{full_rel}" if not full_rel.startswith("/") else full_rel
            return self.success_response(f"File '{rel_path}' created. [Uploaded File: {display_path}]")
        except Exception as e:
            return self.fail_response(f"Error creating file: {str(e)}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "str_replace",
            "description": "Replace a unique string in a file under workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "old_str": {"type": "string"},
                    "new_str": {"type": "string"}
                },
                "required": ["file_path", "old_str", "new_str"]
            }
        }
    })
    @xml_schema(
        tag_name="str-replace",
        mappings=[
            {"param_name": "file_path", "node_type": "attribute", "path": "file_path"},
            {"param_name": "old_str", "node_type": "element", "path": "old_str"},
            {"param_name": "new_str", "node_type": "element", "path": "new_str"}
        ]
    )
    async def str_replace(self, file_path: str, old_str: str, new_str: str) -> ToolResult:
        try:
            rel_path = self.clean_path(file_path)
            full_rel = rel_path
            if not self._file_exists(full_rel):
                return self.fail_response(f"File '{rel_path}' does not exist")

            content_bytes = self.sandbox.fs.download_file(full_rel)
            content = content_bytes.decode(errors='replace') if isinstance(content_bytes, (bytes, bytearray)) else str(content_bytes)
            old_str = old_str.expandtabs()
            new_str = new_str.expandtabs()

            occurrences = content.count(old_str)
            if occurrences == 0:
                return self.fail_response(f"String not found")
            if occurrences > 1:
                return self.fail_response("Multiple occurrences found; ensure uniqueness")

            new_content = content.replace(old_str, new_str)
            upload_file_bytes(self.sandbox, full_rel, new_content.encode())
            return self.success_response("Replacement successful.")
        except Exception as e:
            return self.fail_response(f"Error replacing string: {str(e)}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "full_file_rewrite",
            "description": "Rewrite a file under workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "file_contents": {"type": "string"},
                    "permissions": {"type": "string", "default": "644"}
                },
                "required": ["file_path", "file_contents"]
            }
        }
    })
    @xml_schema(
        tag_name="full-file-rewrite",
        mappings=[
            {"param_name": "file_path", "node_type": "attribute", "path": "file_path"},
            {"param_name": "file_contents", "node_type": "content", "path": "."}
        ]
    )
    async def full_file_rewrite(self, file_path: str, file_contents: str, permissions: str = "644") -> ToolResult:
        try:
            rel_path = self.clean_path(file_path)
            full_rel = rel_path
            if not self._file_exists(full_rel):
                return self.fail_response(f"File '{rel_path}' does not exist")
            data = file_contents if isinstance(file_contents, (bytes, bytearray)) else file_contents.encode()
            # Atomic rewrite to prevent partial reads and race conditions
            atomic_write_file_bytes(self.sandbox, full_rel, data)
            self.sandbox.fs.set_file_permissions(full_rel, permissions)
            display_path = f"/{full_rel}" if not full_rel.startswith("/") else full_rel
            return self.success_response(f"File '{rel_path}' rewritten. [Uploaded File: {display_path}]")
        except Exception as e:
            return self.fail_response(f"Error rewriting file: {str(e)}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file under workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                },
                "required": ["file_path"]
            }
        }
    })
    @xml_schema(
        tag_name="delete-file",
        mappings=[
            {"param_name": "file_path", "node_type": "attribute", "path": "file_path"}
        ]
    )
    async def delete_file(self, file_path: str) -> ToolResult:
        try:
            rel_path = self.clean_path(file_path)
            full_rel = rel_path
            if not self._file_exists(full_rel):
                return self.fail_response(f"File '{rel_path}' does not exist")
            self.sandbox.fs.delete_file(full_rel)
            return self.success_response(f"File '{rel_path}' deleted.")
        except Exception as e:
            return self.fail_response(f"Error deleting file: {str(e)}")
