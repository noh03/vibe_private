import json
import os
from typing import Any, Dict


DEFAULT_LOCAL_SETTINGS: Dict[str, Any] = {
    "activity": {
        # 로컬 Activity 추가 시 자동으로 타임스탬프를 앞에 붙일지 여부
        "append_timestamp_on_add": True,
        # datetime.strftime 포맷 문자열
        "timestamp_format": "%Y-%m-%d %H:%M",
    },
    "attachments": {
        # 첨부 루트 디렉터리 (빈 문자열이면 기본값: rtm_local_manager/attachments)
        "root_dir": "",
        # Pull from JIRA 시 서버 첨부파일을 자동으로 다운로드할지 여부
        "auto_download_on_pull": True,
        # Push to JIRA 시 로컬 첨부파일을 자동으로 업로드할지 여부
        "auto_upload_on_push": True,
    },
}


def _default_path() -> str:
    """Return default settings file path (local_settings.json next to this module)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "local_settings.json")


def _deep_merge(defaults: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow+nested dict merge: defaults ∪ user, with user taking precedence."""
    result: Dict[str, Any] = {}
    for k, v in defaults.items():
        if isinstance(v, dict):
            uv = user.get(k)
            if isinstance(uv, dict):
                result[k] = _deep_merge(v, uv)
            else:
                result[k] = dict(v)
        else:
            result[k] = v
    for k, v in user.items():
        if k not in result:
            result[k] = v
    return result


def load_local_settings(path: str | None = None) -> Dict[str, Any]:
    """Load local Activity/Attachments settings from JSON. Returns defaults on error."""
    if path is None:
        path = _default_path()
    try:
        if not os.path.exists(path):
            return dict(DEFAULT_LOCAL_SETTINGS)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return dict(DEFAULT_LOCAL_SETTINGS)
        # deep-merge with defaults so 신규 옵션도 기본값으로 채워진다.
        return _deep_merge(DEFAULT_LOCAL_SETTINGS, data)
    except Exception:
        return dict(DEFAULT_LOCAL_SETTINGS)


def save_local_settings(settings: Dict[str, Any], path: str | None = None) -> None:
    """Save local Activity/Attachments settings to JSON file."""
    if path is None:
        path = _default_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        # 설정 저장 실패는 앱 동작에 치명적이지 않으므로 예외를 전파하지 않는다.
        pass




