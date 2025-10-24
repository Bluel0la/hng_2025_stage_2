# api/v1/models/system_meta.py
from sqlalchemy import Column, DateTime, String
from api.db.database import Base
from datetime import datetime


class SystemMeta(Base):
    __tablename__ = "system_meta"

    key = Column(String, primary_key=True)
    value = Column(String)
    last_refreshed_at = Column(DateTime, default=datetime.utcnow)
