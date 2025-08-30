import os, httpx, asyncio, time, logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Defaults for Daytona Cloud
DAYTONA_URL_DEFAULT = "https://app.daytona.io/api"
DAYTONA_TARGET_DEFAULT = "us"

# Provider selector env
PROVIDER_ENV = "IRIS_SANDBOX_PROVIDER"  # values: daytona|mock (default: daytona)


@dataclass
class DaytonaConfig:
    api_key: Optional[str] = None
    server_url: Optional[str] = None
    target: Optional[str] = None


@dataclass
class CreateSandboxBaseParams:
    image: str
    public: bool = False
    env_vars: Optional[Dict[str, str]] = None
    ports: Optional[List[int]] = None
    resources: Optional[Dict[str, Any]] = None


@dataclass
class PreviewLink:
    url: str
    token: Optional[str] = None

    def __str__(self):
        return self.url


class SessionExecuteRequest:
    def __init__(self, command: str = None, var_async: bool = False):
        self.command = command
        self.var_async = var_async


# ----- Mock fallback (lightweight, but minimally functional) -----------------

class _MockFileInfo:
    def __init__(self, name: str, is_dir: bool, size: int = 0, mod_time: Optional[str] = None, permissions: Optional[str] = None):
        import datetime
        self.name = name
        self.is_dir = is_dir
        self.size = size
        self.mod_time = mod_time or datetime.datetime.utcnow().isoformat()
        self.permissions = permissions or "644"


class MockFS:
    def __init__(self):
        # simple in-memory tree under 'workspace'
        self._files: Dict[str, bytes] = {}
        self._dirs: set[str] = {"workspace"}

    def create_folder(self, path: str, permissions: str = None):
        path = path.strip("/")
        parts = path.split("/") if path else []
        cur = []
        for p in parts:
            cur.append(p)
            self._dirs.add("/".join(cur).replace("//", "/"))

    def upload_file(self, destination: str, content: bytes):
        destination = destination.strip("/")
        parent = "/".join(destination.split("/")[:-1])
        if parent:
            self.create_folder(parent)
        if isinstance(content, str):
            content = content.encode("utf-8")
        self._files[destination] = bytes(content)

    def download_file(self, path: str) -> bytes:
        path = path.strip("/")
        return self._files.get(path, b"")

    def list_files(self, path: str) -> List[_MockFileInfo]:
        path = path.strip("/")
        base = path
        if base and base not in self._dirs and base not in self._files:
            return []
        # List direct children
        children = set()
        prefix = f"{base}/" if base else ""
        for d in self._dirs:
            if d.startswith(prefix):
                rest = d[len(prefix):]
                if rest and "/" not in rest:
                    children.add((rest, True))
        for f in self._files:
            if f.startswith(prefix):
                rest = f[len(prefix):]
                if rest and "/" not in rest:
                    children.add((rest, False))
        out = []
        for name, is_dir in sorted(children):
            size = len(self._files.get(f"{prefix}{name}", b"")) if not is_dir else 0
            out.append(_MockFileInfo(name=name, is_dir=is_dir, size=size))
        return out

    def delete_file(self, path: str):
        path = path.strip("/")
        self._files.pop(path, None)

    def set_file_permissions(self, path: str, permissions: str):
        # no-op in mock
        return

    def get_file_info(self, path: str):
        path = path.strip("/")
        if path in self._files:
            return _MockFileInfo(name=os.path.basename(path), is_dir=False, size=len(self._files[path]))
        if path in self._dirs:
            return _MockFileInfo(name=os.path.basename(path), is_dir=True)
        raise FileNotFoundError(path)


class MockProcess:
    def create_session(self, session_id: str):
        return None

    def execute_session_command(self, session_id: str, request: SessionExecuteRequest):
        class MockResponse:
            exit_code = 0
            result = ""
            cmd_id = f"cmd-{int(time.time()*1000)}"

        return MockResponse()

    def get_session_command_logs(self, session_id: str, command_id: str):
        return ""

    def delete_session(self, session_id: str):
        return None

    def exec(self, command: str, timeout: int = None):
        class MockResponse:
            exit_code = 0
            result = f"[mock] executed: {command}"

        return MockResponse()


class MockSandbox:
    def __init__(self, sandbox_id: str, client: 'Daytona'):
        self.id = sandbox_id
        self.client = client
        self.fs = MockFS()
        self.process = MockProcess()

    async def get_preview_link(self, port: int) -> PreviewLink:
        return PreviewLink(url=f"https://mock.daytona/{self.id}/{port}")

    def get_preview_link_sync(self, port: int) -> PreviewLink:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.get_preview_link(port))
        finally:
            loop.close()

    def __getattr__(self, name):
        if name == "get_preview_link":
            return self.get_preview_link_sync
        raise AttributeError(name)


# ----- Real Daytona adapter ---------------------------------------------------

def _build_real_client(config: Optional[DaytonaConfig]):
    """
    Construct a real Daytona SDK client, trying several constructor signatures
    to accommodate SDK version differences.
    """
    from daytona_sdk import Daytona as SDKDaytona
    last_err = None
    if config:
        # Try common permutations
        for kwargs in (
            {"api_key": config.api_key, "server_url": config.server_url, "target": config.target},
            {"api_key": config.api_key, "base_url": config.server_url, "target": config.target},
            {"api_key": config.api_key, "api_url": config.server_url, "target": config.target},
            {"api_key": config.api_key, "target": config.target},
        ):
            try:
                return SDKDaytona(**{k: v for k, v in kwargs.items() if v})
            except Exception as e:
                last_err = e
                continue
    # Final fallback: no-arg constructor (env-based)
    try:
        return SDKDaytona()
    except Exception as e:
        # Re-raise the last meaningful error if we had one
        raise last_err or e


class Daytona:
    """Selector that returns a real Daytona SDK client by default.

    Falls back to an internal mock only if IRIS_SANDBOX_PROVIDER=mock or
    if the real client cannot be constructed/used.
    """

    def __init__(self, config: Optional[DaytonaConfig] = None):
        self._provider = (os.getenv(PROVIDER_ENV, "daytona").strip() or "daytona").lower()
        self._real = None
        self._mock = None
        self.base = None
        self.headers: Dict[str, str] = {}

        if self._provider == "mock":
            self._mock = True
            self.base = os.getenv("DAYTONA_API_URL", DAYTONA_URL_DEFAULT)
            logging.warning("IRIS_SANDBOX_PROVIDER=mock set; using mock Daytona client")
            return

        # Try real SDK
        try:
            self._real = _build_real_client(config)
            # Expose some attributes for compatibility
            self.base = getattr(self._real, "base_url", os.getenv("DAYTONA_API_URL", DAYTONA_URL_DEFAULT))
            api_key = getattr(self._real, "api_key", os.getenv("DAYTONA_API_KEY"))
            if api_key:
                self.headers = {"Authorization": f"Bearer {api_key}"}
            logging.info("Daytona SDK client initialized (real)")
        except Exception as e:
            # Fallback to mock
            self._mock = True
            self.base = os.getenv("DAYTONA_API_URL", DAYTONA_URL_DEFAULT)
            logging.exception(f"Failed to initialize real Daytona client; falling back to mock: {e}")

    @property
    def is_mock(self) -> bool:
        return bool(self._mock) or not bool(self._real)

    # Provide a sandboxes namespace for SDK-compat access patterns
    class _Namespace:
        def __init__(self, outer: 'Daytona'):
            self._outer = outer
        def get(self, sandbox_id: str):
            return self._outer.get_sandbox(sandbox_id)
        def list(self):
            return self._outer.list()
        def start(self, sandbox_or_id):
            if isinstance(sandbox_or_id, str):
                sb = self._outer.get_sandbox(sandbox_or_id)
            else:
                sb = sandbox_or_id
            return self._outer.start(sb)
        def delete(self, sandbox_id: str):
            return self._outer.delete(sandbox_id)

    @property
    def sandboxes(self):  # accessor returns a namespace-like object
        if self._real and not self._mock and hasattr(self._real, "sandboxes"):
            return self._real.sandboxes
        return Daytona._Namespace(self)

    # Creation API
    def create(self, params: CreateSandboxBaseParams):
        if self._real and not self._mock:
            # Use the SDK's params object if available. If creation fails, re-raise
            # the underlying SDK error rather than attempting a kwargs fallback
            # that may not match the installed SDK signature.
            try:
                from daytona_sdk import CreateSandboxBaseParams as SDKParams  # type: ignore
                sdk_params = SDKParams(
                    image=params.image,
                    public=params.public,
                    env_vars=params.env_vars,
                    ports=params.ports,
                    resources=params.resources,
                )
                return self._real.create(sdk_params)
            except Exception:
                logging.exception("Daytona.create failed with SDK client; re-raising")
                raise
        # Mock path
        import uuid
        return MockSandbox(f"mock-{uuid.uuid4().hex[:8]}", self)

    # Compatibility shims used by sandbox.py
    def get_sandbox(self, sandbox_id: str):
        if self._real and not self._mock:
            return self._real.get_sandbox(sandbox_id)
        return MockSandbox(sandbox_id, self)

    def get(self, sandbox_id: str):
        if self._real and not self._mock:
            return self._real.get(sandbox_id)
        return MockSandbox(sandbox_id, self)

    # Namespace-style methods
    def list(self):
        if self._real and not self._mock:
            if hasattr(self._real, "list"):
                return self._real.list()
            if hasattr(self._real, "sandboxes") and hasattr(self._real.sandboxes, "list"):
                return self._real.sandboxes.list()
        return []

    def start(self, sandbox):
        if self._real and not self._mock:
            if hasattr(self._real, "start"):
                return self._real.start(sandbox)
            if hasattr(self._real, "sandboxes") and hasattr(self._real.sandboxes, "start"):
                return self._real.sandboxes.start(getattr(sandbox, "id"))
            if hasattr(sandbox, "start"):
                return sandbox.start()
        return None

    def delete(self, sandbox_id: str):
        if self._real and not self._mock:
            if hasattr(self._real, "delete"):
                return self._real.delete(sandbox_id)
            if hasattr(self._real, "sandboxes") and hasattr(self._real.sandboxes, "delete"):
                return self._real.sandboxes.delete(sandbox_id)
        return None

    # Convenience wrapper used by sandbox.py
    def get_workspace(self, workspace_id: str):
        return self.get_sandbox(workspace_id)

    def get_by_id(self, workspace_id: str):
        return self.get_sandbox(workspace_id)

# Export a Sandbox symbol for type compatibility
try:
    from daytona_sdk import Sandbox as Sandbox  # type: ignore
except Exception:
    Sandbox = MockSandbox  # type: ignore
