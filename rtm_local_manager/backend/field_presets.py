import json
import os
from typing import Dict, List

DEFAULT_PRESETS: Dict[str, List[str]] = {
    "rtm_environment": ["DEV", "QA", "STAGE", "PROD"],
    "status": [],
    "priority": [],
    "components": [],
    "versions": [],
    "relation_types": [],
}


def _default_path() -> str:
    """Return default presets file path (field_presets.json next to this module)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "field_presets.json")


def load_presets(path: str | None = None) -> Dict[str, List[str]]:
    """Load field presets from JSON file. Returns defaults if file is missing/invalid."""
    if path is None:
        path = _default_path()
    try:
        if not os.path.exists(path):
            return dict(DEFAULT_PRESETS)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return dict(DEFAULT_PRESETS)
        # ensure all values are list[str]
        presets: Dict[str, List[str]] = {}
        for k, v in data.items():
            if isinstance(v, list):
                presets[str(k)] = [str(x) for x in v]
        # merge defaults for missing keys
        for k, v in DEFAULT_PRESETS.items():
            presets.setdefault(k, list(v))
        return presets
    except Exception:
        return dict(DEFAULT_PRESETS)


def save_presets(presets: Dict[str, List[str]], path: str | None = None) -> None:
    """Save field presets to JSON file."""
    if path is None:
        path = _default_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(presets, f, ensure_ascii=False, indent=2)
    except Exception:
        # 실패해도 앱이 죽지 않도록 예외는 상위로 올리지 않는다.
        pass

{
  "cells": [],
  "metadata": {
    "language_info": {
      "name": "python"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 2
}