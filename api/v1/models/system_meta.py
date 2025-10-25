# api/v1/models/system_meta.py
from sqlalchemy import Column, DateTime, String
from api.db.database import Base
from datetime import datetime


class SystemMeta(Base):
    __tablename__ = "system_meta"

    key = Column(String(255), primary_key=True)
    value = Column(String(255))
    last_refreshed_at = Column(DateTime, default=datetime.utcnow)
