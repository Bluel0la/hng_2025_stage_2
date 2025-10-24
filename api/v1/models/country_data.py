from sqlalchemy import Column, String, UUID, Float, Integer, DateTime
from api.db.database import Base
from sqlalchemy.sql import func
from datetime import datetime
import uuid

class CountryData(Base):
    __tablename__ = "country_data"

    country_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_name = Column(String, nullable=False)
    capital = Column(String, nullable=True)
    region = Column(String, nullable=True)
    population = Column(Integer, nullable=False)
    currency_code = Column(String, nullable=True)
    exchange_rate = Column(Float, nullable=True)
    estimated_gdp = Column(Float, nullable=True)
    flag_url = Column(String, nullable=True)    
    last_refreshed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
