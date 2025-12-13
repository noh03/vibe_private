"""
공통 로깅 유틸리티.

- 콘솔(LOG_LEVEL: INFO) + 파일 로그(rtm_local_manager.log, LOG_LEVEL: DEBUG)
- 모듈별 로거 이름 사용: get_logger(__name__)
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_LOGGER_INITIALIZED = False


def _init_root_logger() -> None:
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return

    # 기본값을 DEBUG 으로 두어, 별도 환경 변수 없이도 상세 로그(특히 JIRA 요청/응답)를
    # 콘솔에서 바로 확인할 수 있게 한다.
    # 필요 시 사용자가 RTM_LOG_LEVEL=INFO 등으로 다시 줄여서 실행 가능.
    log_level = os.environ.get("RTM_LOG_LEVEL", "DEBUG").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    logger = logging.getLogger("rtm")
    logger.setLevel(logging.DEBUG)  # 핸들러에서 레벨 필터링

    # 포맷
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 콘솔 핸들러
    ch = logging.StreamHandler()
    ch.setLevel(numeric_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # 파일 핸들러 (현재 작업 디렉터리에 생성)
    log_path = os.environ.get("RTM_LOG_FILE", "rtm_local_manager.log")
    try:
        fh = RotatingFileHandler(log_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception:
        # 파일 생성 실패해도 콘솔 로그만이라도 동작하게
        logger.warning("Failed to initialize file log handler", exc_info=True)

    _LOGGER_INITIALIZED = True


def get_logger(name: str = "rtm"):
    _init_root_logger()
    return logging.getLogger(f"rtm.{name}")
