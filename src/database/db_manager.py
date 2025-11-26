from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base
import os

class DBManager:
    def __init__(self, db_path="local_data.db"):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def init_db(self):
        """Initialize Database Tables"""
        Base.metadata.create_all(self.engine)
        
    def get_session(self) -> Session:
        return self.SessionLocal()

# Singleton instance
db_manager = DBManager()

