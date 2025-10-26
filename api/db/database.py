import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Load environment variables
load_dotenv(".env.config")


# ==========================================================
# 1️⃣  Synchronous Engine (Optional Fallback / Migrations)
# ==========================================================
def get_db_engine():
    """
    Create a SQLAlchemy synchronous engine for MySQL or SQLite.
    Useful for migrations or synchronous tasks.
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

        database_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"

        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=False,  # set True for debugging
        )

    return engine


db_engine = get_db_engine()
SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
Base = declarative_base()


def create_database():
    """Initialize all tables synchronously."""
    Base.metadata.create_all(bind=db_engine)


def get_db():
    """Dependency to provide a synchronous DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================================
# 2️⃣  Asynchronous Engine (Primary for FastAPI Endpoints)
# ==========================================================
def get_async_engine():
    """
    Create an asynchronous SQLAlchemy engine for MySQL using aiomysql.
    """
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "countries_db")

    database_url = f"mysql+aiomysql://{user}:{password}@{host}:{port}/{db_name}"

    return create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


# Instantiate global async engine and session factory
async_engine = get_async_engine()
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_async_db():
    """
    Dependency that yields an asynchronous database session.
    Automatically handles cleanup and connection return to the pool.
    """
    async with AsyncSessionLocal() as session:
        yield session
