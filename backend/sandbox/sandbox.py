import os
from typing import Any, Optional, List, Tuple, Dict
from datetime import datetime

# Import the real Daytona client
from .daytona_client import Daytona, DaytonaConfig, CreateSandboxBaseParams, Sandbox
from dotenv import load_dotenv

from agentpress.tool import Tool
from utils.logger import logger
from utils.files_utils import clean_path

load_dotenv()

# ----- Daytona client bootstrap ------------------------------------------------

logger.info("Initializing Daytona sandbox configuration")
_config = DaytonaConfig(
    api_key=os.getenv("DAYTONA_API_KEY"),
    server_url=os.getenv("DAYTONA_SERVER_URL"),
    target=os.getenv("DAYTONA_TARGET"),
)

if _config.api_key:
    logger.info("Daytona API key configured successfully")
else:
    logger.warning("No Daytona API key found in environment variables")

if _config.server_url:
    logger.info(f"Daytona server URL: {_config.server_url}")
else:
    logger.warning("No Daytona server URL found in environment variables")

if _config.target:
    logger.info(f"Daytona target: {_config.target}")
else:
    logger.warning("No Daytona target found in environment variables")

daytona = Daytona(_config)
try:
    # Our adapter exposes is_mock; real SDK won't, but our Daytona class does.
    if getattr(daytona, "is_mock", False):
        logger.warning("Using MOCK Daytona client (check daytona_sdk install and env vars)")
    else:
        logger.info("Using REAL Daytona client")
except Exception:
    logger.info("Daytona client initialized")

# Use SDK-recommended relative workspace root (maps to /home/<user>/workspace)
WORKSPACE_REL = "workspace"

# Cache preview links briefly to avoid repeated network calls
_preview_cache: Dict[tuple, str] = {}
_PREVIEW_TTL = 30  # seconds

# ----- FS helpers (handle SDK signature drift + safe fallbacks) --------------


def _fs_upload_file(sandbox: Sandbox, rel_path: str, content: bytes) -> None:
    """
    Upload a file into the sandbox user home using Daytona SDK, handling
    signature drift across SDK versions. Falls back to a shell write if needed.
    rel_path is relative to user home (e.g., 'workspace/file.txt').
    """
    # Newer SDKs: upload_file(content: bytes, destination: str)
    try:
        sandbox.fs.upload_file(content, rel_path)  # type: ignore[arg-type]
        return
    except Exception:
        pass

    # Older SDKs: upload_file(destination: str, content: bytes)
    try:
        sandbox.fs.upload_file(rel_path, content)  # type: ignore[arg-type]
        return
    except Exception:
        pass

    # Fallback via shell write using base64
    import base64

    session = "iris-fs-fallback"
    try:
        try:
            sandbox.process.create_session(session)
        except Exception:
            pass

        b64_ascii = base64.b64encode(content).decode("ascii")
        cmd = (
            'bash -lc "set -euo pipefail; '
            f'DIR=$(dirname \"$HOME/{rel_path}\"); '
            'mkdir -p \"$DIR\"; '
            f'echo \"{b64_ascii}\" | base64 -d > \"$HOME/{rel_path}\"; '
            'chmod 664 \"$HOME/{rel_path}\""'
        )
        sandbox.process.execute_session_command(
            session,
            SessionExecuteRequest(command=cmd, var_async=True),
        )
    except Exception as e:
        raise RuntimeError(f"upload_file fallback failed for {rel_path}: {e}")


def upload_file_bytes(sandbox: Sandbox, rel_path: str, content: bytes) -> None:
    """
    Public helper for other modules to upload bytes reliably to the sandbox.
    rel_path is relative to user home (e.g., 'workspace/file.txt').
    """
    _fs_upload_file(sandbox, rel_path, content)

def atomic_write_file_bytes(sandbox: Sandbox, rel_path: str, content: bytes) -> None:
    """
    Write a file atomically: upload to a temp path in the same directory, then rename.
    Attempts to fsync via shell to avoid partial reads by listeners.
    """
    import secrets
    import posixpath

    # Ensure parent directory exists via shell (safer across SDK variants)
    temp_name = f".{posixpath.basename(rel_path)}.iris.tmp.{secrets.token_hex(4)}"
    parent = posixpath.dirname(rel_path)
    tmp_path = posixpath.join(parent, temp_name) if parent else temp_name

    # 1) Upload content to temp path
    _fs_upload_file(sandbox, tmp_path, content)

    # 2) Atomically move temp into place (same filesystem) with a best-effort sync
    session_id = f"iris-atomic-{secrets.token_hex(3)}"
    try:
        sandbox.process.create_session(session_id)
    except Exception:
        pass

    # Compose shell script: sync temp file, then mv over target
    sh = (
        'bash -lc "set -euo pipefail; '
        f'TARGET=\"$HOME/{rel_path}\"; TMP=\"$HOME/{tmp_path}\"; '
        'mkdir -p \"$(dirname \"$TARGET\")\"; '
        'sync \"$TMP\" || true; '
        'mv -f \"$TMP\" \"$TARGET\"; '
        'sync \"$TARGET\" || true;"'
    )

    payload = {"command": sh, "var_async": False}
    try:
        try:
            resp = sandbox.process.execute_session_command(session_id, payload, 20)
        except TypeError:
            try:
                resp = sandbox.process.execute_session_command(session_id, payload, timeout=20)
            except TypeError:
                resp = sandbox.process.execute_session_command(session_id=session_id, session_execute_request=payload, timeout=20)
        if getattr(resp, 'exit_code', 0) != 0:
            raise RuntimeError(f"atomic mv failed (exit {getattr(resp,'exit_code',-1)})")
    finally:
        try:
            sandbox.process.delete_session(session_id)
        except Exception:
            pass

# ----- Helpers to adapt to SDK changes ----------------------------------------


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
    candidates = [
        ("get_sandbox", (sandbox_id,), {}),
        ("get", (sandbox_id,), {}),
        ("sandboxes", (), {}),
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

# ----- Bootstrap helpers: ensure ~/workspace exists via SDK --------------------


def ensure_workspace_dir_sdk(sandbox: Sandbox) -> None:
    """
    Ensure the user-scoped workspace exists using Daytona SDK.
    WORKSPACE_REL ('workspace') maps to /home/<user>/workspace.
    """
    try:
        # Create if missing; open perms to avoid ownership pains across processes
        sandbox.fs.create_folder(WORKSPACE_REL, "777")
        # Drop a ready marker
        try:
            _fs_upload_file(sandbox, f"{WORKSPACE_REL}/.iris_workspace_ready", b"ok\n")
        except Exception:
            pass
        logger.info("Ensured user workspace exists via SDK")
    except Exception as e:
        logger.warning(f"ensure_workspace_dir_sdk: {e}")


# ----- Public API --------------------------------------------------------------


async def get_or_start_sandbox(sandbox_id: str) -> Sandbox:
    """
    Retrieve a sandbox by ID, and start it if needed.
    Always ensures ~/workspace is ready (SDK way).
    """
    logger.info(f"Getting or starting sandbox with ID: {sandbox_id}")

    # Enforce real Daytona if configured
    import os as _os
    allow_mock = _os.getenv("IRIS_ALLOW_MOCK", "false").lower() in ("1", "true", "yes")
    if getattr(daytona, "is_mock", False) and not allow_mock:
        raise RuntimeError(
            "Daytona mock client is active but IRIS_ALLOW_MOCK is false. "
            "Set IRIS_SANDBOX_PROVIDER=daytona and provide DAYTONA_API_KEY/DAYTONA_SERVER_URL."
        )

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

    # Ensure workspace (SDK, not absolute /workspace)
    ensure_workspace_dir_sdk(sandbox)

    logger.info(f"Sandbox {sandbox_id} is ready")
    return sandbox


def start_supervisord_session(sandbox: Sandbox) -> None:
    """Start supervisord in a named session."""
    session_id = "supervisord-session"
    try:
        logger.info(f"Creating session {session_id} for supervisord")
        sandbox.process.create_session(session_id)

        payload = {
            "command": "exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf",
            "var_async": True,
        }
        try:
            sandbox.process.execute_session_command(session_id, payload)
        except TypeError:
            try:
                sandbox.process.execute_session_command(session_id=session_id, session_execute_request=payload)
            except TypeError:
                sandbox.process.execute_session_command(session_id=session_id, request=payload)
        logger.info(f"Supervisord started in session {session_id}")
    except Exception as e:
        logger.error(f"Error starting supervisord session: {e}")
        raise


def create_sandbox(password: str) -> Sandbox:
    """
    Create a new sandbox with Iris defaults and start supervisord.
    Also ensures ~/workspace is ready immediately (SDK way).
    """
    logger.info("Creating new Daytona sandbox environment")

    # Allow image/resources/env overrides via environment variables
    image = os.getenv("IRIS_SANDBOX_IMAGE", "kortix/suna:0.1.3.5")
    cpu = int(os.getenv("IRIS_SANDBOX_CPU", "1"))
    memory = int(os.getenv("IRIS_SANDBOX_MEMORY_GB", "1"))
    disk = int(os.getenv("IRIS_SANDBOX_DISK_GB", "3"))

    # Merge extra env vars if provided as JSON
    extra_env = {}
    try:
        if os.getenv("IRIS_SANDBOX_EXTRA_ENV_JSON"):
            import json as _json
            extra_env = _json.loads(os.getenv("IRIS_SANDBOX_EXTRA_ENV_JSON", "{}"))
    except Exception:
        pass

    sandbox = daytona.create(
        CreateSandboxBaseParams(
            image=image,
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
                **extra_env,
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
                "cpu": cpu,
                "memory": memory,
                "disk": disk,
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
    For shell, cd into $HOME/workspace.
    """

    _urls_printed = False  # Print preview URLs only once
    _workspace_ensured: set = set()  # Track sandboxes already ensured

    def __init__(self, sandbox: Sandbox):
        super().__init__()
        self.sandbox = sandbox
        self.daytona = daytona
        self.workspace_rel = WORKSPACE_REL          # e.g. "workspace"
        self.workspace_abs_for_shell = '$HOME/workspace'
        self.sandbox_id = sandbox.id

        try:
            logger.debug(f"Refreshing sandbox by ID: {self.sandbox_id}")
            self.sandbox = _get_sandbox_by_id(self.sandbox_id)
        except Exception as e:
            logger.error(f"Error retrieving sandbox: {e}", exc_info=True)
            raise

        # Make sure ~/workspace exists only once per sandbox
        try:
            if self.sandbox_id not in SandboxToolsBase._workspace_ensured:
                ensure_workspace_dir_sdk(self.sandbox)
                SandboxToolsBase._workspace_ensured.add(self.sandbox_id)
        except Exception:
            pass

        # Preview links (tolerate async/sync variants)
        def _preview(port: int) -> str:
            try:
                import time
                key = (self.sandbox_id, port)
                ts_key = (self.sandbox_id, port, 'ts')
                now = time.time()
                ts = _preview_cache.get(ts_key, 0)
                if now - ts < _PREVIEW_TTL and key in _preview_cache:
                    return _preview_cache[key]
                link = self.sandbox.get_preview_link(port)
                import asyncio as _a
                if _a.iscoroutine(link):
                    loop = _a.new_event_loop()
                    _a.set_event_loop(loop)
                    try:
                        link = loop.run_until_complete(self.sandbox.get_preview_link(port))
                    finally:
                        loop.close()
                url = getattr(link, "url", str(link))
                _preview_cache[key] = url
                _preview_cache[ts_key] = now
                return url
            except Exception:
                return ""

        vnc_url = _preview(6080)
        site_url = _preview(8080)

        logger.info(f"Sandbox VNC URL: {vnc_url}")
        logger.info(f"Sandbox Website URL: {site_url}")

        if not SandboxToolsBase._urls_printed:
            print("\033[95m***")
            print(vnc_url)
            print(site_url)
            print("***\033[0m")
            SandboxToolsBase._urls_printed = True

    def clean_path(self, path: str) -> str:
        # NOTE: clean_path should not require a leading slash; we pass the relative root
        cleaned = clean_path(path, self.workspace_rel)
        logger.debug(f"Cleaned path: {path} -> {cleaned}")
        return cleaned
