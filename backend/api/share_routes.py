"""
Share Routes for Iris Backend

This module handles sharing functionality for threads, allowing users to create
public share links and manage shared thread access.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from services.supabase import DBConnection
from utils.auth_utils import get_current_user_id
from utils.logger import logger

router = APIRouter()
db = DBConnection()


class ShareRequest(BaseModel):
    """Request model for creating a share."""
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = True
    allow_comments: bool = False
    expires_at: Optional[str] = None


class ShareResponse(BaseModel):
    """Response model for share creation."""
    public_id: str
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: bool
    allow_comments: bool
    expires_at: Optional[str] = None
    created_at: str


@router.post("/thread/{thread_id}/share")
async def create_share(
    thread_id: str,
    share_request: ShareRequest,
    user_id: str = Depends(get_current_user_id)
) -> ShareResponse:
    """
    Create a share link for a thread.
    
    Args:
        thread_id: The thread to share
        share_request: Share configuration
        user_id: Current user ID
        
    Returns:
        Share response with public URL
    """
    try:
        client = await db.get_client()
        
        # Verify user has access to this thread
        thread_result = await client.table('threads').select('*').eq('thread_id', thread_id).execute()
        if not thread_result.data:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        thread_data = thread_result.data[0]
        
        # Check if user owns this thread or has access
        if thread_data.get('account_id') != user_id:
            # TODO: Add proper access control for shared threads
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Generate unique public ID
        public_id = str(uuid.uuid4())
        
        # Check if share already exists for this thread
        existing_share = await client.table('thread_shares').select('*').eq('thread_id', thread_id).execute()
        
        share_data = {
            'thread_id': thread_id,
            'public_id': public_id,
            'title': share_request.title,
            'description': share_request.description,
            'is_public': share_request.is_public,
            'allow_comments': share_request.allow_comments,
            'expires_at': share_request.expires_at,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        if existing_share.data:
            # Update existing share
            result = await client.table('thread_shares').update(share_data).eq('thread_id', thread_id).execute()
            public_id = existing_share.data[0]['public_id']  # Keep existing public_id
        else:
            # Create new share
            result = await client.table('thread_shares').insert(share_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create share")
        
        # Generate share URL
        base_url = "http://localhost:3000"  # TODO: Get from environment
        share_url = f"{base_url}/share/{public_id}"
        
        return ShareResponse(
            public_id=public_id,
            url=share_url,
            title=share_request.title,
            description=share_request.description,
            is_public=share_request.is_public,
            allow_comments=share_request.allow_comments,
            expires_at=share_request.expires_at,
            created_at=share_data['created_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating share: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        try:
            logger.info(
                f"SHARE_ACTION: {{'runId': '{thread_id}', 'visibility': '{'public' if share_request.is_public else 'unlisted'}', 'linkId': '{locals().get('public_id','')}'}}"
            )
        except Exception:
            pass


@router.get("/share/{public_id}")
async def get_shared_thread(public_id: str) -> Dict[str, Any]:
    """
    Get a shared thread by public ID.
    
    Args:
        public_id: Public share ID
        
    Returns:
        Thread data and messages for public viewing
    """
    try:
        client = await db.get_client()
        
        # Get share record
        share_result = await client.table('thread_shares').select('*').eq('public_id', public_id).execute()
        if not share_result.data:
            raise HTTPException(status_code=404, detail="Shared thread not found")
        
        share_data = share_result.data[0]
        
        # Check if share is expired
        if share_data.get('expires_at'):
            expires_at = datetime.fromisoformat(share_data['expires_at'].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_at:
                raise HTTPException(status_code=410, detail="Share link has expired")
        
        # Check if share is public
        if not share_data.get('is_public', True):
            raise HTTPException(status_code=403, detail="This thread is not publicly accessible")
        
        thread_id = share_data['thread_id']
        
        # Get thread data
        thread_result = await client.table('threads').select('*').eq('thread_id', thread_id).execute()
        if not thread_result.data:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        thread_data = thread_result.data[0]
        
        # Get messages
        messages_result = await client.table('messages').select('*').eq('thread_id', thread_id).order('created_at').execute()
        messages = messages_result.data or []
        
        # Get project data if available
        project_data = None
        if thread_data.get('project_id'):
            project_result = await client.table('projects').select('*').eq('id', thread_data['project_id']).execute()
            if project_result.data:
                project_data = project_result.data[0]
        
        return {
            'share': {
                'public_id': public_id,
                'title': share_data.get('title'),
                'description': share_data.get('description'),
                'is_public': share_data.get('is_public', True),
                'allow_comments': share_data.get('allow_comments', False),
                'created_at': share_data.get('created_at'),
                'expires_at': share_data.get('expires_at')
            },
            'thread': thread_data,
            'messages': messages,
            'project': project_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shared thread: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/thread/{thread_id}/share")
async def delete_share(
    thread_id: str,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, str]:
    """
    Delete a share for a thread.
    
    Args:
        thread_id: The thread to unshare
        user_id: Current user ID
        
    Returns:
        Success message
    """
    try:
        client = await db.get_client()
        
        # Verify user has access to this thread
        thread_result = await client.table('threads').select('*').eq('thread_id', thread_id).execute()
        if not thread_result.data:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        thread_data = thread_result.data[0]
        
        # Check if user owns this thread
        if thread_data.get('account_id') != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete share
        result = await client.table('thread_shares').delete().eq('thread_id', thread_id).execute()
        
        return {"message": "Share deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting share: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/thread/{thread_id}/share")
async def get_thread_share(
    thread_id: str,
    user_id: str = Depends(get_current_user_id)
) -> Optional[ShareResponse]:
    """
    Get existing share for a thread.
    
    Args:
        thread_id: The thread ID
        user_id: Current user ID
        
    Returns:
        Share data if exists, None otherwise
    """
    try:
        client = await db.get_client()
        
        # Verify user has access to this thread
        thread_result = await client.table('threads').select('*').eq('thread_id', thread_id).execute()
        if not thread_result.data:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        thread_data = thread_result.data[0]
        
        # Check if user owns this thread
        if thread_data.get('account_id') != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get share
        share_result = await client.table('thread_shares').select('*').eq('thread_id', thread_id).execute()
        if not share_result.data:
            return None
        
        share_data = share_result.data[0]
        
        # Generate share URL
        base_url = "http://localhost:3000"  # TODO: Get from environment
        share_url = f"{base_url}/share/{share_data['public_id']}"
        
        return ShareResponse(
            public_id=share_data['public_id'],
            url=share_url,
            title=share_data.get('title'),
            description=share_data.get('description'),
            is_public=share_data.get('is_public', True),
            allow_comments=share_data.get('allow_comments', False),
            expires_at=share_data.get('expires_at'),
            created_at=share_data['created_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thread share: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
