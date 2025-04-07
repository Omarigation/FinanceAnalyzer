from fastapi import Depends
from sqlalchemy.orm import Session
from Access.database import SessionLocal

def get_db():
    """
    Dependency that provides a database session
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()