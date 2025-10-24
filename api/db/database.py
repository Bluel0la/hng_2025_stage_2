from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.config")


def get_db_engine():
    """
    Dynamically create a SQLAlchemy engine for MySQL or SQLite (for fallback/testing).
    Ensures optimal connection pooling and safe thread handling.
    """
    db_type = os.getenv("DB_TYPE", "mysql").lower()

    if db_type == "sqlite":
        # Local fallback option
        database_url = os.getenv("DB_URL", "sqlite:///./test.db")
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            pool_size=5,
            max_overflow=10,
        )
    else:
        # Default: MySQL configuration
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "3306")
        db_name = os.getenv("DB_NAME", "countries_db")

        # Recommended MySQL URL format
        database_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"

        engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Avoid stale connections
            pool_size=10,  # Reasonable pool size
            max_overflow=20,  # Allow limited overflow under load
            echo=False,  # Set True for debugging SQL
        )

    return engine


# --- Create Engine and Session ---
db_engine = get_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
Base = declarative_base()


def create_database():
    """Initialize all tables in the database."""
    Base.metadata.create_all(bind=db_engine)


def get_db():
    """Dependency to get a DB session for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
