"""
Database configuration and connection management.
Uses lazy initialization to ensure environment variables are loaded before engine creation.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import logging

logger = logging.getLogger(__name__)

# Base class for models (can be created at import time)
Base = declarative_base()

# Lazy-initialized globals
_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """Get database URL from environment with fallback for local development."""
    url = os.getenv("DATABASE_URL")
    if not url:
        url = "postgresql://user:password@localhost:5432/video_inpainting"
        logger.warning("DATABASE_URL not set, using local fallback!")
    return url


def get_engine():
    """Lazy initialization of database engine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        logger.info(f"Creating database engine...")

        # Log connection info (hide password)
        if '@' in database_url:
            host_part = database_url.split('@')[1].split('/')[0]
            logger.info(f"Connecting to database host: {host_part}")

        if database_url.startswith("sqlite"):
            _engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=True
            )
        else:
            _engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=0,
                pool_pre_ping=True,
                echo=False
            )

        # Register event listeners
        _register_event_listeners(_engine)
        logger.info("Database engine created successfully")

    return _engine


def _register_event_listeners(engine):
    """Register SQLAlchemy event listeners for the engine."""
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if "sqlite" in str(dbapi_connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    @event.listens_for(engine, "connect")
    def set_postgresql_extensions(dbapi_connection, connection_record):
        if "postgresql" in str(dbapi_connection):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
                cursor.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
                dbapi_connection.commit()
            except Exception as e:
                logger.warning(f"Could not create PostgreSQL extensions: {e}")
            finally:
                cursor.close()


def get_session_local():
    """Get or create SessionLocal factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_database():
    """Dependency to get database session."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initialize database tables."""
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


# Backwards compatibility: Create a wrapper class for lazy SessionLocal access
class _LazySessionLocal:
    """Wrapper that creates sessions using lazy-initialized engine."""
    def __call__(self):
        return get_session_local()()


# Export for backwards compatibility
SessionLocal = _LazySessionLocal()