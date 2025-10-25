from sqlalchemy import Column, String, UUID, Float, Integer, DateTime
from sqlalchemy.dialects.mysql import CHAR

from api.db.database import Base
from sqlalchemy.sql import func
from datetime import datetime
import uuid

class CountryData(Base):
    __tablename__ = "country_data"

    country_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    country_name = Column(String(255), nullable=False)
    capital = Column(String(255), nullable=True)
    region = Column(String(255), nullable=True)
    population = Column(Integer, nullable=False)
    currency_code = Column(String(10), nullable=True)
    exchange_rate = Column(Float, nullable=True)
    estimated_gdp = Column(Float, nullable=True)
    flag_url = Column(String(512), nullable=True)    
    last_refreshed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
