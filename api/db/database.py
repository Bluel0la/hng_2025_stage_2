from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv(".env.config")


def get_db_engine():
    if os.getenv("DB_TYPE") == "sqlite":
        DATABASE_URL = os.getenv("DB_URL", "sqlite:///./test.db")
        db_engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            pool_size=32,
            max_overflow=64,
        )
    else:
        DATABASE_URL = os.getenv("DB_URL")
        db_engine = create_engine(DATABASE_URL, pool_size=32, max_overflow=64)

    return db_engine


# Call get_db_engine to create the engine
db_engine = get_db_engine()

# Session and Base declaration
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
Base = declarative_base()


def create_database():
    return Base.metadata.create_all(bind=db_engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
