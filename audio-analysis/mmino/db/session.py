"""
Database session management
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging
from typing import Generator

from mmino.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
try:
    engine = create_engine(
        str(settings.DATABASE_URL),
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,   # Recycle connections after 1 hour
        pool_size=20,        # Maximum number of connections in pool
        max_overflow=40,     # Maximum number of connections beyond pool_size
        echo=settings.DEBUG, # Log SQL queries in debug mode
        future=True          # Use SQLAlchemy 2.0 style
    )
    
    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Database connection established successfully")
    
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# Create SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    expire_on_commit=False
)

# Create declarative base
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Yields a session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Useful for non-FastAPI contexts.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables() -> None:
    """
    Create all tables in the database.
    Only for development/testing. Use migrations for production.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise


def drop_tables() -> None:
    """
    Drop all tables in the database.
    Only for development/testing.
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        raise


def check_db_connection() -> bool:
    """
    Check if database connection is working.
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_db_stats() -> dict:
    """
    Get database statistics.
    """
    stats = {}
    try:
        with engine.connect() as conn:
            # Get table counts
            for table in Base.metadata.tables.values():
                result = conn.execute(f"SELECT COUNT(*) FROM {table.name}")
                count = result.scalar()
                stats[table.name] = count
            
            # Get database size
            if engine.dialect.name == "postgresql":
                result = conn.execute(
                    "SELECT pg_database_size(current_database())"
                )
                stats["database_size_bytes"] = result.scalar()
                
                result = conn.execute(
                    "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'"
                )
                stats["active_connections"] = result.scalar()
            
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
    
    return stats