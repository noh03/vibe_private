import json
import os
from typing import Dict


def _default_path() -> str:
    """excel_mapping.json 기본 경로 (backend 디렉터리 옆)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "excel_mapping.json")


def load_mapping(path: str | None = None) -> Dict[str, Dict[str, str]]:
    """
    Excel 컬럼 매핑 설정을 JSON 파일에서 읽어온다.

    반환 형태:
        {
          "Issues": {
              "jira_key": "JIRA Key",
              "summary": "Summary",
              ...
          },
          "TestcaseSteps": {
              "issue_id": "TC ID",
              ...
          },
          ...
        }

    - 파일이 없거나, 포맷이 잘못된 경우에는 빈 dict 를 반환한다.
    - 매핑이 없는 필드는 기본적으로 "논리 이름 == 엑셀 헤더 이름" 으로 취급된다.
    """
    if path is None:
        path = _default_path()
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        mapping: Dict[str, Dict[str, str]] = {}
        for sheet, sheet_map in data.items():
            if not isinstance(sheet_map, dict):
                continue
            sheet_name = str(sheet)
            inner: Dict[str, str] = {}
            for logical, header in sheet_map.items():
                if header is None:
                    continue
                inner[str(logical)] = str(header)
            if inner:
                mapping[sheet_name] = inner
        return mapping
    except Exception:
        # 매핑 로드 실패 시에도 앱이 죽지 않도록 빈 매핑 반환
        return {}


def save_mapping(mapping: Dict[str, Dict[str, str]], path: str | None = None) -> None:
    """Excel 컬럼 매핑 설정을 JSON 파일로 저장한다."""
    if path is None:
        path = _default_path()
    try:
        # 중첩 dict 가 아닌 값은 모두 무시하고, 문자열로 serialize
        serializable: Dict[str, Dict[str, str]] = {}
        for sheet, sheet_map in mapping.items():
            if not isinstance(sheet_map, dict):
                continue
            inner: Dict[str, str] = {}
            for logical, header in sheet_map.items():
                if header is None:
                    continue
                header_str = str(header).strip()
                if not header_str:
                    continue
                inner[str(logical)] = header_str
            if inner:
                serializable[str(sheet)] = inner
        with open(path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
    except Exception:
        # 저장 실패해도 앱 전체에 영향이 가지 않도록 예외는 무시
        pass





