"""SQLAlchemy engine, session lifecycle, and safe schema initialization."""
import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session


is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
database_url = os.getenv("DATABASE_URL", "").strip()
if is_serverless and not database_url:
    raise RuntimeError("Set DATABASE_URL to a persistent PostgreSQL database for Vercel. SQLite files are ephemeral in serverless functions.")
if is_serverless and not database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
    raise RuntimeError("DATABASE_URL must use PostgreSQL in serverless deployments; SQLite is not persistent there.")

if database_url:
    # Providers may supply either postgres:// or postgresql:// URLs. Use the
    # psycopg 3 driver installed by backend/requirements.txt.
    if database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    elif database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    engine = create_engine(database_url, pool_pre_ping=True, pool_size=1, max_overflow=0)
else:
    database_path = os.getenv("SENTINEL_DB_PATH", os.path.join(os.path.dirname(__file__), "sentineltext.db"))
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False, "timeout": 30})

SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Importing registers every model with Base before create_all runs.
    from backend import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
