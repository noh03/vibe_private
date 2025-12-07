"""
attachments_fs.py - Local filesystem helpers for issue attachments.

Responsibilities:
- Define a stable root directory for attachments relative to main.py
- Provide per-issue attachment directory helpers
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def get_attachments_root() -> Path:
    """
    Return the root directory for all attachments.

    By design this is:
        <rtm_local_manager>/attachments
    where <rtm_local_manager>/main.py also lives.
    """
    # This file lives in <rtm_local_manager>/backend
    pkg_root = Path(__file__).resolve().parent.parent
    root = pkg_root / "attachments"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_issue_attachments_dir(issue_type: str, issue_id: int, root: Optional[Path] = None) -> Path:
    """
    Return the directory for attachments of a specific local issue.

    Layout (requested by spec):
        attachments/<ISSUE_TYPE>/<ISSUE_ID>/
    """
    if root is None:
        root = get_attachments_root()
    safe_type = (issue_type or "UNKNOWN").upper()
    d = root / safe_type / str(issue_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


