# utils/files_utils.py

import os
import re
from typing import Iterable

# Filenames to ignore entirely (exact matches)
EXCLUDED_FILES: set[str] = {
    ".DS_Store",
    ".gitignore",
    ".gitattributes",
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "Thumbs.db",
}

# Directory names to ignore (folder basenames)
EXCLUDED_DIRS: set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    ".next",
    "build",
    "dist",
    ".cache",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".coverage",
}

# File extensions to ignore (lowercased; include the leading dot)
EXCLUDED_EXT: set[str] = {
    ".lock",
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".bin",
    ".pack",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".iso",
    ".svgz",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".ico",
    ".mp4",
    ".mov",
    ".mkv",
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".pdf",
    ".log",
}

# Optional: patterns for very large/generated stuff
EXCLUDED_REGEX: list[re.Pattern] = [
    re.compile(r"\.coverage.*$"),
    re.compile(r".*\.min\.(js|css)$", re.IGNORECASE),
]

def _is_under_excluded_dir(parts: Iterable[str]) -> bool:
    """Return True if any path component is an excluded directory."""
    for p in parts:
        if p in EXCLUDED_DIRS:
            return True
    return False

def should_exclude_file(path: str) -> bool:
    """
    Decide if a file should be excluded from listings/uploads.
    Excludes by filename, extension, containing directory and regex patterns.
    """
    # Normalize and split into parts
    norm = os.path.normpath(path)
    base = os.path.basename(norm)
    name, ext = os.path.splitext(base)
    ext = ext.lower()

    # Exact filename exclusions
    if base in EXCLUDED_FILES:
        return True

    # Directory exclusion
    if _is_under_excluded_dir(norm.split(os.sep)):
        return True

    # Extension exclusion
    if ext in EXCLUDED_EXT:
        return True

    # Regex patterns
    for rx in EXCLUDED_REGEX:
        if rx.match(base) or rx.match(norm):
            return True

    return False

def clean_path(path: str, workspace_root: str = "workspace") -> str:
    """
    Resolve a possibly-relative path safely under the workspace root.
    
    FIXED: Now properly handles relative workspace root for Daytona SDK.
    
    - If `path` is absolute, we strip leading '/' and join with workspace_root
    - If `path` is relative, we join it under workspace_root
    - Collapse '..' and '.' safely
    - Ensure we never escape the workspace root
    - Return path relative to user home (for Daytona SDK)

    Args:
        path: The input path to clean
        workspace_root: The workspace root (default: "workspace" for ~/workspace)
    
    Returns:
        A normalized path under workspace_root (e.g., "workspace/file.txt")
    """
    if not path or path == ".":
        return workspace_root

    # Strip any protocol-like junk and whitespace
    path = str(path).strip().replace("\x00", "")
    
    # Remove leading slash if present to make it relative
    if path.startswith("/"):
        path = path.lstrip("/")
    
    # If path is just workspace_root, return it
    if path == workspace_root:
        return workspace_root
    
    # If path already starts with workspace_root/, return it normalized
    if path.startswith(f"{workspace_root}/"):
        candidate = os.path.normpath(path)
    else:
        # Join with workspace root
        candidate = os.path.normpath(os.path.join(workspace_root, path))

    # Ensure the result starts with workspace_root and doesn't escape
    if not candidate.startswith(workspace_root):
        # If somehow we escaped, snap back to workspace root
        return workspace_root
    
    # Additional safety: ensure no parent directory traversal escapes workspace
    parts = candidate.split(os.sep)
    clean_parts = []
    workspace_depth = len(workspace_root.split(os.sep))
    
    for part in parts:
        if part == "..":
            # Only allow going up if we're deeper than workspace root
            if len(clean_parts) > workspace_depth:
                clean_parts.pop()
        elif part and part != ".":
            clean_parts.append(part)
    
    result = os.sep.join(clean_parts) if clean_parts else workspace_root
    
    # Final safety check
    if not result.startswith(workspace_root):
        return workspace_root
        
    return result
