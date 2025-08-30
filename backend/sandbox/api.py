import os
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter, Form, Depends, Request
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

from utils.logger import logger
from utils.auth_utils import get_current_user_id, get_user_id_from_stream_auth, get_optional_user_id
from sandbox.sandbox import get_or_start_sandbox, upload_file_bytes
from services.supabase import DBConnection
try:
    from postgrest.exceptions import APIError as PostgrestAPIError  # type: ignore
except Exception:  # pragma: no cover
    PostgrestAPIError = Exception  # type: ignore
from sandbox.sandbox import daytona as _daytona_client

# TODO: ADD AUTHORIZATION TO ONLY HAVE ACCESS TO SANDBOXES OF PROJECTS U HAVE ACCESS TO

# Initialize shared resources
router = APIRouter(tags=["sandbox"])
db = None

def initialize(_db: DBConnection):
    """Initialize the sandbox API with resources from the main API."""
    global db
    db = _db
    logger.info("Initialized sandbox API with database connection")

class FileInfo(BaseModel):
    """Model for file information"""
    name: str
    path: str
    is_dir: bool
    size: int
    mod_time: str
    permissions: Optional[str] = None

def _normalize_sdk_path(path: str) -> str:
    """
    Normalize incoming paths for Daytona SDK which expects paths relative
    to the user home (e.g., 'workspace/dir/file').
    Accepts variants like '/workspace', '/workspace/file', 'workspace/file', or '/'.
    """
    if not path:
        return "workspace"
    p = path.strip()
    # Treat root as workspace root
    if p in ("/", ""):
        return "workspace"
    # Remove leading slash
    if p.startswith("/"):
        p = p[1:]
    # Ensure it is under workspace
    if p == "workspace" or p.startswith("workspace/"):
        return p
    # Map anything else into workspace subtree
    return f"workspace/{p}"

async def verify_sandbox_access(client, sandbox_id: str, user_id: Optional[str] = None):
    """
    Verify that a user has access to a specific sandbox based on account membership.
    
    Args:
        client: The Supabase client
        sandbox_id: The sandbox ID to check access for
        user_id: The user ID to check permissions for. Can be None for public resource access.
        
    Returns:
        dict: Project data containing sandbox information
        
    Raises:
        HTTPException: If the user doesn't have access to the sandbox or sandbox doesn't exist
    """
    # Find the project that owns this sandbox
    project_result = await client.table('projects').select('*').filter('sandbox->>id', 'eq', sandbox_id).execute()
    
    if not project_result.data or len(project_result.data) == 0:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    project_data = project_result.data[0]

    if project_data.get('is_public'):
        return project_data
    
    # For private projects, we must have a user_id
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required for this resource")
    
    account_id = project_data.get('account_id')
    
    # Verify account membership
    if account_id:
        try:
            account_user_result = await client.postgrest.table('basejump.account_user').select('account_role').eq('user_id', user_id).eq('account_id', account_id).execute()
            if account_user_result.data and len(account_user_result.data) > 0:
                return project_data
        except PostgrestAPIError as e:
            # Fallback for environments without basejump tables: allow if personal project (account_id == user_id)
            if user_id and account_id == user_id:
                logger.warning("basejump.account_user missing; allowing access for personal project owner")
                return project_data
            logger.error(f"Authorization lookup failed (basejump.account_user missing): {e}")
            raise HTTPException(status_code=403, detail="Authorization model unavailable. Access denied.")
    
    raise HTTPException(status_code=403, detail="Not authorized to access this sandbox")

@router.get("/sandboxes/{sandbox_id}/status")
async def get_sandbox_status(
    sandbox_id: str,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Return basic sandbox status, preview URLs and workspace readiness."""
    client = await db.get_client()

    # Verify access
    await verify_sandbox_access(client, sandbox_id, user_id)

    try:
        sb = await get_or_start_sandbox(sandbox_id)

        # Determine state as best effort
        state = "unknown"
        try:
            if getattr(sb, "instance", None) is not None:
                state = str(getattr(sb.instance, "state", "unknown")).lower()
            else:
                state = str(getattr(sb, "state", getattr(sb, "status", "unknown")).lower())
        except Exception:
            pass

        # Preview URLs (best effort; tolerate SDK differences)
        def _try_preview(port: int) -> Optional[str]:
            try:
                link = sb.get_preview_link(port)  # may be coroutine/str/obj
                import asyncio as _a
                if _a.iscoroutine(link):
                    loop = _a.new_event_loop()
                    _a.set_event_loop(loop)
                    try:
                        link = loop.run_until_complete(sb.get_preview_link(port))
                    finally:
                        loop.close()
                return getattr(link, "url", str(link))
            except Exception:
                return None

        preview = {
            "vnc": _try_preview(6080),
            "site": _try_preview(8080),
        }

        # Workspace readiness
        workspace_ready = False
        try:
            files = sb.fs.list_files("workspace")
            workspace_ready = True if files is not None else False
        except Exception:
            workspace_ready = False

        return {
            "id": sandbox_id,
            "state": state,
            "preview": preview,
            "workspace_ready": workspace_ready,
        }
    except Exception as e:
        logger.error(f"Error getting sandbox status for {sandbox_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sandbox/diagnostics")
async def sandbox_diagnostics(
    project_id: Optional[str] = None,
    sandbox_id: Optional[str] = None,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """
    Diagnostics for Daytona sandbox usage.
    - Reports provider, SDK version, env, and (optionally) tries to fetch preview links for a sandbox.
    """
    import os
    # Provider status
    provider_env = os.getenv("IRIS_SANDBOX_PROVIDER", "daytona")
    is_mock = getattr(_daytona_client, "is_mock", False)
    try:
        import daytona_sdk as _sdk
        sdk_version = getattr(_sdk, "__version__", "unknown")
    except Exception:
        sdk_version = None

    resp = {
        "provider_env": provider_env,
        "is_mock": bool(is_mock),
        "sdk_version": sdk_version,
        "server_url": os.getenv("DAYTONA_SERVER_URL"),
        "target": os.getenv("DAYTONA_TARGET"),
        "has_api_key": bool(os.getenv("DAYTONA_API_KEY")),
    }

    # Resolve sandbox id via project if provided
    try:
        if not sandbox_id and project_id:
            client = await db.get_client()
            pr = await client.table('projects').select('*').eq('project_id', project_id).single().execute()
            if pr.data and pr.data.get('sandbox', {}).get('id'):
                sandbox_id = pr.data['sandbox']['id']
    except Exception as e:
        resp["project_lookup_error"] = str(e)

    # Optionally test preview links/workspace
    if sandbox_id:
        try:
            sb = await get_or_start_sandbox(sandbox_id)
            def _try_preview(port: int):
                try:
                    link = sb.get_preview_link(port)
                    import asyncio as _a
                    if _a.iscoroutine(link):
                        loop = _a.new_event_loop()
                        _a.set_event_loop(loop)
                        try:
                            link = loop.run_until_complete(sb.get_preview_link(port))
                        finally:
                            loop.close()
                    return getattr(link, 'url', str(link))
                except Exception as _e:
                    return f"error: {_e}"
            resp["preview"] = {"vnc": _try_preview(6080), "site": _try_preview(8080)}
            try:
                files = sb.fs.list_files("workspace")
                resp["workspace_ok"] = bool(files is not None)
            except Exception as _e:
                resp["workspace_ok"] = False
                resp["workspace_error"] = str(_e)
        except Exception as e:
            resp["sandbox_error"] = str(e)

    return resp

@router.post("/sandboxes/{sandbox_id}/files")
async def create_file(
    sandbox_id: str, 
    path: str = Form(...),
    file: UploadFile = File(...),
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Create a file in the sandbox using direct file upload"""
    client = await db.get_client()
    
    # Verify the user has access to this sandbox
    await verify_sandbox_access(client, sandbox_id, user_id)
    
    try:
        import time
        t0 = time.time()
        # Get or start sandbox instance
        sandbox = await get_or_start_sandbox(sandbox_id)
        
        # Read file content directly from the uploaded file (bytes)
        content = await file.read()
        if isinstance(content, str):
            # Safety: ensure bytes for SDK
            content = content.encode('utf-8')
        
        # Normalize path for SDK and upload
        sdk_path = _normalize_sdk_path(path)
        upload_file_bytes(sandbox, sdk_path, content)
        duration_ms = int((time.time() - t0) * 1000)
        try:
            logger.info(
                f"ATTACHMENT_UPLOAD: {{'sandboxId': '{sandbox_id}', 'filename': '{os.path.basename(sdk_path)}', 'path': '{sdk_path}', 'bytesUploaded': {len(content)}, 'durationMs': {duration_ms}}}"
            )
        except Exception:
            pass
        
        return {"status": "success", "created": True, "path": path}
    except Exception as e:
        logger.error(f"Error creating file in sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# For backward compatibility, keep the JSON version too
@router.post("/sandboxes/{sandbox_id}/files/json")
async def create_file_json(
    sandbox_id: str, 
    file_request: dict,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Create a file in the sandbox using JSON (legacy support)"""
    client = await db.get_client()
    
    # Verify the user has access to this sandbox
    await verify_sandbox_access(client, sandbox_id, user_id)
    
    try:
        import time, os
        t0 = time.time()
        # Get or start sandbox instance
        sandbox = await get_or_start_sandbox(sandbox_id)
        
        # Get file path and content
        path = file_request.get("path")
        content = file_request.get("content", "")
        
        if not path:
            raise HTTPException(status_code=400, detail="File path is required")
        
        # Convert possible str content to bytes
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        # Create file
        sdk_path = _normalize_sdk_path(path)
        upload_file_bytes(sandbox, sdk_path, content)
        duration_ms = int((time.time() - t0) * 1000)
        try:
            logger.info(
                f"ATTACHMENT_UPLOAD: {{'sandboxId': '{sandbox_id}', 'filename': '{os.path.basename(sdk_path)}', 'path': '{sdk_path}', 'bytesUploaded': {len(content)}, 'durationMs': {duration_ms}}}"
            )
        except Exception:
            pass
        
        return {"status": "success", "created": True, "path": path}
    except Exception as e:
        logger.error(f"Error creating file in sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sandboxes/{sandbox_id}/files")
async def list_files(
    sandbox_id: str, 
    path: str,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """List files and directories at the specified path"""
    client = await db.get_client()
    
    # Verify the user has access to this sandbox
    await verify_sandbox_access(client, sandbox_id, user_id)
    
    try:
        # Get or start sandbox instance using the async function
        sandbox = await get_or_start_sandbox(sandbox_id)
        
        # List files from normalized path
        sdk_path = _normalize_sdk_path(path)
        files = sandbox.fs.list_files(sdk_path)
        result = []
        
        for file in files:
            # Convert file information to our model
            # Ensure forward slashes are used for paths, regardless of OS
            full_path = f"{sdk_path}/{file.name}"
            file_info = FileInfo(
                name=file.name,
                path=full_path,
                is_dir=file.is_dir,
                size=file.size,
                mod_time=str(file.mod_time),
                permissions=getattr(file, 'permissions', None)
            )
            result.append(file_info)
        
        return {"files": [file.dict() for file in result]}
    except Exception as e:
        logger.error(f"Error listing files in sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sandboxes/{sandbox_id}/files/content")
async def read_file(
    sandbox_id: str, 
    path: str,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Read a file from the sandbox"""
    client = await db.get_client()
    
    # Verify the user has access to this sandbox
    await verify_sandbox_access(client, sandbox_id, user_id)
    
    try:
        # Get or start sandbox instance using the async function
        sandbox = await get_or_start_sandbox(sandbox_id)
        
        # Read file
        sdk_path = _normalize_sdk_path(path)
        content = sandbox.fs.download_file(sdk_path)
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content

        # Heuristic content type and disposition for preview vs download
        media_type = "application/octet-stream"
        disposition = "attachment"
        try:
            name = os.path.basename(sdk_path).lower()
            if any(name.endswith(ext) for ext in [
                ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"
            ]):
                media_type = f"image/{'svg+xml' if name.endswith('.svg') else 'png' if name.endswith('.png') else 'jpeg' if name.endswith(('.jpg','.jpeg')) else 'gif' if name.endswith('.gif') else 'webp' if name.endswith('.webp') else 'bmp'}"
                disposition = "inline"
            elif name.endswith(".pdf"):
                media_type = "application/pdf"
                disposition = "inline"
            elif any(name.endswith(ext) for ext in [
                ".txt", ".md", ".json", ".csv", ".xml", ".html", ".css", ".js", ".ts", ".py"
            ]):
                media_type = "text/plain; charset=utf-8"
                disposition = "inline"
        except Exception:
            pass

        filename = os.path.basename(sdk_path)
        return Response(
            content=content_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f"{disposition}; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error reading file in sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/project/{project_id}/sandbox/ensure-active")
async def ensure_project_sandbox_active(
    project_id: str,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """
    Ensure that a project's sandbox is active and running.
    Checks the sandbox status and starts it if it's not running.
    """
    client = await db.get_client()
    
    # Find the project and sandbox information
    project_result = await client.table('projects').select('*').eq('project_id', project_id).execute()
    
    if not project_result.data or len(project_result.data) == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_data = project_result.data[0]
    
    # For public projects, no authentication is needed
    if not project_data.get('is_public'):
        # For private projects, we must have a user_id
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required for this resource")
            
        account_id = project_data.get('account_id')
        
        # Verify account membership
        if account_id:
            try:
                account_user_result = await client.postgrest.table('basejump.account_user').select('account_role').eq('user_id', user_id).eq('account_id', account_id).execute()
                if not (account_user_result.data and len(account_user_result.data) > 0):
                    raise HTTPException(status_code=403, detail="Not authorized to access this project")
            except PostgrestAPIError as e:
                if user_id and account_id == user_id:
                    logger.warning("basejump.account_user missing; allowing ensure-active for personal project owner")
                else:
                    logger.error(f"Authorization lookup failed (basejump.account_user missing): {e}")
                    raise HTTPException(status_code=403, detail="Authorization model unavailable. Access denied.")
    
    # Check if project has a sandbox
    sandbox_id = project_data.get('sandbox', {}).get('id')
    if not sandbox_id:
        raise HTTPException(status_code=404, detail="No sandbox found for this project")
    
    try:
        # Get or start sandbox instance
        logger.info(f"Ensuring sandbox {sandbox_id} is active for project {project_id}")
        sandbox = await get_or_start_sandbox(sandbox_id)
        
        return {
            "status": "success", 
            "sandbox_id": sandbox_id,
            "message": "Sandbox is active"
        }
    except Exception as e:
        logger.error(f"Error ensuring sandbox is active for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
