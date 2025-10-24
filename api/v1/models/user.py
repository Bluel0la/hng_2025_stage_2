from sqlalchemy import Column, String, Boolean, Enum, UUID
from sqlalchemy.orm import relationship
import uuid

from api.db.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    username = Column(String(255), unique=True, nullable=False)
    gender = Column(Enum("Male", "Female", "Other", name="gender_enum"))
    is_active = Column(Boolean, default=True)

    
