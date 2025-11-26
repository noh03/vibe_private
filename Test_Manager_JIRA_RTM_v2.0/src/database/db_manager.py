from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from .models import Base


class DBManager:
    def __init__(self, db_path: str = "local_data_v2.db") -> None:
        # v2.0용 별도 DB 파일 사용
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def init_db(self) -> None:
        """
        데이터베이스 테이블 초기화 + 간단한 스키마 마이그레이션.

        이미 생성된 DB에 새로운 컬럼(sync_status, last_synced_at 등)을
        추가하기 위해 SQLite ALTER TABLE을 수행한다.
        """
        # 기본 테이블 생성 (없는 경우에만)
        Base.metadata.create_all(self.engine)

        # 간단 마이그레이션 처리
        inspector = inspect(self.engine)
        with self.engine.begin() as conn:
            for table in ["requirements", "test_cases", "test_plans", "test_executions", "defects"]:
                if not inspector.has_table(table):
                    continue

                cols = {c["name"] for c in inspector.get_columns(table)}

                if "sync_status" not in cols:
                    try:
                        conn.execute(
                            text(f'ALTER TABLE {table} ADD COLUMN sync_status VARCHAR(20)')
                        )
                    except Exception:
                        # 이미 존재하거나 실패해도 애플리케이션 동작에는 치명적이지 않으므로 무시
                        pass

                if "last_synced_at" not in cols:
                    try:
                        conn.execute(
                            text(f'ALTER TABLE {table} ADD COLUMN last_synced_at DATETIME')
                        )
                    except Exception:
                        pass

    def get_session(self) -> Session:
        return self.SessionLocal()


# Singleton instance
db_manager = DBManager()
