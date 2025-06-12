# File: /app/db/init_db.py
from sqlalchemy.orm import Session
from app.db.database import engine
from app.models.models import Base
import logging

logger = logging.getLogger(__name__)

def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def init_db():
    """Initialize the database"""
    create_tables()
    logger.info("Database initialization completed")

if __name__ == "__main__":
    # Run this script to create tables
    init_db()