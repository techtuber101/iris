import os
import base64
from typing import Any, Optional, List, Tuple
from datetime import datetime

from daytona_sdk import Daytona, DaytonaConfig, CreateSandboxBaseParams, Sandbox, SessionExecuteRequest
from dotenv import load_dotenv

from agentpress.tool import Tool
from utils.logger import logger
from utils.files_utils import clean_path

load_dotenv()

# ==============================================================================
# Daytona client bootstrap (handles server_url vs api_url differences)
# ==============================================================================

logger.debug("Initializing Daytona sandbox configuration")

_env_api_key   = os.getenv("DAYTONA_API_KEY")
_env_serverurl = os.getenv("DAYTONA_SERVER_URL")
_env_apiurl    = os.getenv("DAYTONA_API_URL") or _env_serverurl  # support both

_config: Optional[DaytonaConfig] = None
_cfg_errors: List[str] = []

# Try constructor with server_url first (older SDKs), then api_url (newer SDKs)
try:
    _config = DaytonaConfig(api_key=_env_api_key, server_url=_env_serverurl, target=os.getenv("DAYTONA_TARGET"))
    logger.debug("Constructed DaytonaConfig with server_url")
except Exception as e1:
    _cfg_errors.append(f"server_url ctor failed: {e1}")
    try:
        _config = DaytonaConfig(api_key=_env_api_key, api_url=_env_apiurl, target=os.getenv("DAYTONA_TARGET"))
        logger.debug("Constructed DaytonaConfig with api_url")
    except Exception as e2:
        _cfg_errors.append(f"api_url ctor failed: {e2}")
        raise RuntimeError("Failed to construct DaytonaConfig with both server_url and api_url") from e2

if _config.api_key:
    logger.debug("Daytona API key configured successfully")
else:
    logger.warning("No Daytona API key found in environment variables")

# Some SDKs expose server_url, some api_url – log whichever exists
_srv = getattr(_config, "server_url", None) or getattr(_config, "api_url", None)
if _srv:
    logger.debug(f"Daytona API endpoint: {_srv}")
else:
    logger.warning("No Daytona API endpoint found in DaytonaConfig")

if getattr(_config, "target", None):
    logger.debug(f"Daytona target: {_config.target}")
else:
    logger.warning("No Daytona target found in environment variables")

daytona = Daytona(_config)
logger.debug("Daytona client initialized")

# ==============================================================================
# Constants
# ==============================================================================

# Always operate under user home -> $HOME/workspace
WORKSPACE_REL = "workspace"  # SDK fs.* is relative to sandbox user home

# ==============================================================================
# Internal helpers (SDK drift adapters)
# ==============================================================================

def _call_first_available(obj: Any, candidates: List[Tuple[str, tuple, dict]]) -> Any:
    first_error: Optional[BaseException] = None
    for name, args, kwargs in candidates:
        if hasattr(obj, name):
            method = getattr(obj, name)
            try:
                return method(*args, **kwargs)
            except Exception as e:
                if first_error is None:
                    first_error = e
    if first_error:
        raise first_error
    raise AttributeError(f"None of the candidate methods exist: {[n for n,_,_ in candidates]}")

def _get_sandbox_by_id(sandbox_id: str) -> Sandbox:
    logger.debug(f"Attempting to fetch sandbox {sandbox_id}")
    # Try common places / names
    candidates = [
        ("get_sandbox", (sandbox_id,), {}),
        ("get", (sandbox_id,), {}),
        ("sandboxes", (), {}),  # handle namespaced client
    ]
    for name, args, kwargs in candidates:
        if name == "sandboxes" and hasattr(daytona, "sandboxes"):
            sandboxes_obj = getattr(daytona, "sandboxes")
            if hasattr(sandboxes_obj, "get"):
                try:
                    return sandboxes_obj.get(sandbox_id)
                except Exception as e:
                    logger.debug(f"daytona.sandboxes.get failed: {e}")
            continue
        if hasattr(daytona, name):
            try:
                return getattr(daytona, name)(*args, **kwargs)
            except Exception as e:
                logger.debug(f"daytona.{name} failed: {e}")
    # Legacy fallbacks
    legacy_candidates = [
        ("get_workspace", (sandbox_id,), {}),
        ("get_by_id", (sandbox_id,), {}),
    ]
    return _call_first_available(daytona, legacy_candidates)

def _list_sandboxes() -> list:
    logger.debug("Listing sandboxes (version-agnostic)")
    if hasattr(daytona, "list"):
        return daytona.list()
    if hasattr(daytona, "sandboxes") and hasattr(daytona.sandboxes, "list"):
        return daytona.sandboxes.list()
    if hasattr(daytona, "get_all"):
        return daytona.get_all()
    raise AttributeError("Cannot find a list method on Daytona client (tried: list, sandboxes.list, get_all).")

def _start_sandbox(sbx: Sandbox) -> None:
    logger.info(f"Starting sandbox {getattr(sbx, 'id', 'unknown')}")
    if hasattr(daytona, "start"):
        try:
            daytona.start(sbx)
            return
        except Exception as e:
            logger.debug(f"daytona.start failed: {e}")
    if hasattr(daytona, "sandboxes") and hasattr(daytona.sandboxes, "start"):
        try:
            daytona.sandboxes.start(getattr(sbx, "id"))
            return
        except Exception as e:
            logger.debug(f"daytona.sandboxes.start failed: {e}")
    if hasattr(sbx, "start"):
        sbx.start()
        return
    raise AttributeError("No available method to start sandbox (tried daytona.start, sandboxes.start, sbx.start).")

def _delete_sandbox_by_id(sandbox_id: str) -> None:
    logger.info(f"Deleting sandbox {sandbox_id}")
    if hasattr(daytona, "delete"):
        daytona.delete(sandbox_id)
        return
    if hasattr(daytona, "sandboxes") and hasattr(daytona.sandboxes, "delete"):
        daytona.sandboxes.delete(sandbox_id)
        return
    raise AttributeError("No available method to delete sandbox (tried daytona.delete, sandboxes.delete).")

def _get_state(sbx: Sandbox) -> str:
    state = None
    if hasattr(sbx, "instance") and getattr(sbx, "instance") is not None:
        state = getattr(sbx.instance, "state", None)
    if state is None:
        state = getattr(sbx, "state", None)
    if state is None:
        state = getattr(sbx, "status", None)
    if state is None:
        return "unknown"
    return str(state).lower()

def _get_timestamp(sbx: Sandbox) -> datetime:
    # Try multiple attribute names and ISO strings
    for attr in ("updated_at", "created_at", "updatedAt", "createdAt"):
        val = getattr(sbx, attr, None)
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except Exception:
                pass
    return datetime.utcnow()

def _fs_create_folder(sandbox: Sandbox, rel_path: str, perms: str = "777") -> None:
    """
    Create folder via SDK; rel_path is relative to user home (per Daytona docs).
    """
    if not hasattr(sandbox, "fs"):
        raise AttributeError("Sandbox has no fs attribute; SDK too old/new.")
    try:
        sandbox.fs.create_folder(rel_path, perms)
    except Exception as e:
        logger.debug(f"fs.create_folder failed for {rel_path}: {e}")
        raise

def _fs_upload_file(sandbox: Sandbox, rel_path: str, content: bytes) -> None:
    """
    Daytona SDKs differ on upload_file signature:
      - new: upload_file(content: bytes, destination: str)
      - old: upload_file(destination: str, content: bytes)
    Try both. If both fail, fallback to base64 + shell write.
    """
    if not hasattr(sandbox, "fs"):
        raise AttributeError("Sandbox has no fs attribute; SDK too old/new.")
    tried_errors: List[str] = []
    # New signature
    try:
        sandbox.fs.upload_file(content, rel_path)
        return
    except Exception as e1:
        tried_errors.append(f"new (content, path) failed: {e1}")
    # Old signature
    try:
        sandbox.fs.upload_file(rel_path, content)
        return
    except Exception as e2:
        tried_errors.append(f"old (path, content) failed: {e2}")
    # Fallback: shell write via base64 (safe for arbitrary bytes)
    try:
        encoded = base64.b64encode(content).decode("ascii")
        _shell_write_file(sandbox, rel_path, encoded)
        return
    except Exception as e3:
        tried_errors.append(f"shell write fallback failed: {e3}")
        raise RuntimeError("upload_file failed with all strategies:\n" + "\n".join(tried_errors))

def _shell_write_file(sandbox: Sandbox, rel_path: str, b64_ascii: str) -> None:
    """
    Write file using shell in $HOME using base64 decode.
    rel_path should be relative to $HOME (e.g., 'workspace/file.txt').
    """
    session = "iris-fs-fallback"
    try:
        # Ensure session exists
        try:
            sandbox.process.create_session(session)
        except Exception:
            pass
        # Ensure parent dir; write via base64
        cmd = (
            'bash -lc "set -euo pipefail; '
            f'DIR=$(dirname \\"$HOME/{rel_path}\\"); '
            'mkdir -p \\"$DIR\\"; '
            f'echo \\"{b64_ascii}\\" | base64 -d > \\"$HOME/{rel_path}\\"; '
            'chmod 664 \\"$HOME/{rel_path}\\""'
        )
        sandbox.process.execute_session_command(
            session,
            SessionExecuteRequest(command=cmd, var_async=True),
        )
    except Exception as e:
        raise RuntimeError(f"shell write failed for {rel_path}: {e}")

def _shell_cd_workspace(sandbox: Sandbox, extra_cmd: str) -> None:
    """
    Execute a shell command inside $HOME/workspace.
    """
    session = "iris-sh"
    try:
        try:
            sandbox.process.create_session(session)
        except Exception:
            pass
        cmd = f'bash -lc "set -e; mkdir -p \\"$HOME/{WORKSPACE_REL}\\"; cd \\"$HOME/{WORKSPACE_REL}\\"; {extra_cmd}"'
        sandbox.process.execute_session_command(
            session,
            SessionExecuteRequest(command=cmd, var_async=True),
        )
    except Exception as e:
        raise RuntimeError(f"shell exec failed in workspace: {e}")

# ==============================================================================
# Workspace bootstrap (SDK-first, shell fallback)
# ==============================================================================

def ensure_workspace_dir_sdk(sandbox: Sandbox) -> None:
    """
    Ensure the user-scoped workspace exists using Daytona SDK.
    WORKSPACE_REL ('workspace') maps to /home/<user>/workspace.
    Writes a tiny marker file to confirm.
    """
    try:
        _fs_create_folder(sandbox, WORKSPACE_REL, "777")
    except Exception as e:
        logger.warning(f"ensure_workspace_dir_sdk: create_folder failed: {e}; trying shell fallback")
        # Shell fallback: create workspace dir
        _shell_cd_workspace(sandbox, ":")  # no-op after mkdir -p

    # Write a ready marker
    try:
        _fs_upload_file(sandbox, f"{WORKSPACE_REL}/.iris_workspace_ready", b"ok\n")
    except Exception as e:
        logger.warning(f"ensure_workspace_dir_sdk: marker upload failed: {e}")

# ==============================================================================
# Public API
# ==============================================================================

async def get_or_start_sandbox(sandbox_id: str) -> Sandbox:
    """
    Retrieve a sandbox by ID; start if needed; ensure $HOME/workspace exists.
    Note: async signature kept for compatibility with callers (no awaits inside).
    """
    logger.info(f"Getting or starting sandbox with ID: {sandbox_id}")

    try:
        sandbox = _get_sandbox_by_id(sandbox_id)
    except Exception as e:
        logger.error(f"Error fetching sandbox {sandbox_id}: {e}")
        raise

    state = _get_state(sandbox)
    logger.info(f"Sandbox {sandbox_id} state: {state}")

    needs_start = state in {"archived", "stopped", "inactive", "shut_down", "terminated", "unknown"}
    if needs_start:
        logger.info(f"Sandbox {sandbox_id} not running — starting…")
        try:
            _start_sandbox(sandbox)
            sandbox = _get_sandbox_by_id(sandbox_id)  # refresh state
            start_supervisord_session(sandbox)
        except Exception as e:
            logger.error(f"Error starting sandbox {sandbox_id}: {e}")
            raise

    # Ensure workspace via SDK (with shell fallback inside)
    ensure_workspace_dir_sdk(sandbox)

    logger.info(f"Sandbox {sandbox_id} is ready")
    return sandbox

def start_supervisord_session(sandbox: Sandbox) -> None:
    """Start supervisord in a named session."""
    session_id = "supervisord-session"
    try:
        logger.info(f"Creating session {session_id} for supervisord")
        try:
            sandbox.process.create_session(session_id)
        except Exception:
            pass
        sandbox.process.execute_session_command(
            session_id,
            SessionExecuteRequest(
                command="exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf",
                var_async=True,
            ),
        )
        logger.info(f"Supervisord started in session {session_id}")
    except Exception as e:
        logger.error(f"Error starting supervisord session: {e}")
        raise

def create_sandbox(password: str) -> Sandbox:
    """
    Create a new sandbox with Iris defaults; start supervisord; ensure workspace.
    """
    logger.info("Creating new Daytona sandbox environment")

    sandbox = daytona.create(
        CreateSandboxBaseParams(
            image="adamcohenhillel/kortix-iris:0.0.20",
            public=False,
            env_vars={
                "CHROME_PERSISTENT_SESSION": "true",
                "RESOLUTION": "1024x768x24",
                "RESOLUTION_WIDTH": "1024",
                "RESOLUTION_HEIGHT": "768",
                "VNC_PASSWORD": password,
                "ANONYMIZED_TELEMETRY": "false",
                "CHROME_PATH": "",
                "CHROME_USER_DATA": "",
                "CHROME_DEBUGGING_PORT": "9222",
                "CHROME_DEBUGGING_HOST": "localhost",
                "CHROME_CDP": "",
            },
            ports=[
                6080,  # noVNC web
                5900,  # VNC
                5901,  # VNC
                9222,  # Chrome debug
                8080,  # HTTP site
                8002,  # browser API
            ],
            resources={
                "cpu": 2,
                "memory": 4,
                "disk": 5,
            },
        )
    )

    logger.info(f"Sandbox created with ID: {sandbox.id}")
    start_supervisord_session(sandbox)

    # Ensure workspace now
    ensure_workspace_dir_sdk(sandbox)

    logger.info("Sandbox environment successfully initialized")
    return sandbox

def enforce_sandbox_quota(max_count: int = 8) -> None:
    """
    Keep the newest `max_count` sandboxes; delete the rest (oldest first).
    """
    try:
        sandboxes = _list_sandboxes()
    except Exception as e:
        logger.error(f"Failed to list sandboxes for quota enforcement: {e}")
        return

    typed = [sb for sb in sandboxes if hasattr(sb, "id")]

    if len(typed) <= max_count:
        logger.info(f"Sandbox quota OK: {len(typed)}/{max_count}")
        return

    typed.sort(key=_get_timestamp, reverse=True)

    keep = typed[:max_count]
    delete = typed[max_count:]

    logger.info(
        f"Enforcing quota: keeping {len(keep)} newest, deleting {len(delete)} oldest (max={max_count})"
    )
    for sb in delete:
        sb_id = getattr(sb, "id", None)
        if not sb_id:
            continue
        try:
            _delete_sandbox_by_id(sb_id)
            logger.info(f"Deleted sandbox {sb_id}")
        except Exception as e:
            logger.error(f"Failed to delete sandbox {sb_id}: {e}")

class SandboxToolsBase(Tool):
    """
    Tool base that guarantees a writable workspace *in user home* and resolves
    all file paths under it. For Daytona fs.* calls use relative paths (WORKSPACE_REL).
    For shell, we cd into $HOME/workspace via helper.
    """

    _urls_printed = False  # Print preview URLs only once

    def __init__(self, sandbox: Sandbox):
        super().__init__()
        self.sandbox = sandbox
        self.daytona = daytona
        self.workspace_rel = WORKSPACE_REL          # e.g., "workspace"
        self.workspace_abs_for_shell = '$HOME/workspace'
        self.sandbox_id = sandbox.id

        try:
            logger.debug(f"Refreshing sandbox by ID: {self.sandbox_id}")
            self.sandbox = _get_sandbox_by_id(self.sandbox_id)
        except Exception as e:
            logger.error(f"Error retrieving sandbox: {e}", exc_info=True)
            raise

        # Make sure ~/workspace exists
        ensure_workspace_dir_sdk(self.sandbox)

        # Preview links (best-effort; SDKs vary)
        try:
            vnc_link = self.sandbox.get_preview_link(6080)
            site_link = self.sandbox.get_preview_link(8080)
            vnc_url  = getattr(vnc_link, "url", str(vnc_link))
            site_url = getattr(site_link, "url", str(site_link))
            logger.info(f"Sandbox VNC URL: {vnc_url}")
            logger.info(f"Sandbox Website URL: {site_url}")
            if not SandboxToolsBase._urls_printed:
                print("\033[95m***")
                print(vnc_url)
                print(site_url)
                print("***\033[0m")
                SandboxToolsBase._urls_printed = True
        except Exception as e:
            logger.debug(f"Preview link fetch failed: {e}")

    def clean_path(self, path: str) -> str:
        # NOTE: clean_path should not require a leading slash; we pass the relative root
        cleaned = clean_path(path, self.workspace_rel)
        logger.debug(f"Cleaned path: {path} -> {cleaned}")
        return cleaned

    # Optional: helper to run shell within workspace for subclasses
    def sh(self, command: str) -> None:
        _shell_cd_workspace(self.sandbox, command)
