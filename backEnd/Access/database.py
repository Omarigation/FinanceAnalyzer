from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from fastapi import Depends
from sqlalchemy.orm import Session
import pyodbc
import logging

from config import DATABASE_URL

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание движка SQLAlchemy с подключением к SQL Server
try:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={"timeout": 30}
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# Создание сессии для работы с базой данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей SQLAlchemy
Base = declarative_base()

def get_db():
    """
    Функция-зависимость для получения сессии базы данных.
    Используется с FastAPI Depends для инъекции зависимостей.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Инициализация базы данных, создание всех таблиц.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def check_db_connection():
    """
    Проверка соединения с базой данных.
    Возвращает True, если соединение успешно установлено, иначе False.
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return False

def test_specific_db_connection():
    """
    Тестирование подключения к базе данных с использованием pyodbc напрямую.
    Полезно для отладки проблем с подключением.
    """
    try:
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DATABASE_URL.split('@')[1].split('/')[0]};DATABASE={DATABASE_URL.split('/')[3].split('?')[0]};UID={DATABASE_URL.split('://')[1].split(':')[0]};PWD={DATABASE_URL.split(':')[2].split('@')[0]}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        logger.info(f"Direct pyodbc connection successful: {row}")
        return True
    except Exception as e:
        logger.error(f"Direct pyodbc connection error: {e}")
        return False