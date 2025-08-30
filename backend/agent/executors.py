import os, asyncio, json, pathlib, subprocess, shlex
try:
    from .tool_registry import ToolSpec, registry
except ImportError:
    # Fallback for when running as standalone script
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from tool_registry import ToolSpec, registry
try:
    from ..sandbox.daytona_client import Daytona
except ImportError:
    # Fallback for when running as standalone script
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sandbox'))
    from daytona_client import Daytona

BASE_DIR = pathlib.Path(os.getenv("WORKSPACE_DIR", "/tmp/iris-workspaces"))
BASE_DIR.mkdir(parents=True, exist_ok=True)

async def exec_file_write(args):
    path = args.get("path") or args.get("attrs", {}).get("path") or "output.txt"
    content = args.get("body", "")
    full_path = BASE_DIR / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(full_path)}

async def exec_execute_python(args):
    code = args.get("body", "")
    # Run in Daytona if configured, else local
    if os.getenv("DAYTONA_API_KEY"):
        d = Daytona()
        ws = await d.ensure_workspace(args.get("workspace", "iris-python"))
        logs = await d.run(ws, cmd="python - <<'PY'\n" + code + "\nPY")
        return {"ok": True, "mode": "daytona", "logs": logs}
    # local fallback (short-running only)
    p = subprocess.Popen(["python","-c", code],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out, _ = p.communicate(timeout=120)
    return {"ok": p.returncode==0, "mode": "local", "logs": out, "rc": p.returncode}

async def exec_web_search(args):
    q = (args.get("attrs", {}).get("query") or args.get("body","")).strip()
    # stub: return placeholder; integrate your web.run later
    return {"ok": True, "query": q, "results": []}

async def exec_daytona_run(args):
    d = Daytona()
    ws = await d.ensure_workspace(args.get("attrs", {}).get("workspace","iris-app"))
    cmd = args.get("attrs", {}).get("cmd") or args.get("body", "")
    logs = await d.run(ws, cmd=cmd)
    return {"ok": True, "workspace": ws, "logs": logs}

def register_all_tools():
    registry.register(ToolSpec("file-write", exec_file_write, parse_body_as="text"))
    registry.register(ToolSpec("execute-python", exec_execute_python, parse_body_as="code"))
    registry.register(ToolSpec("web-search", exec_web_search, parse_body_as="text"))
    registry.register(ToolSpec("daytona-run", exec_daytona_run, parse_body_as="text"))
