from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from Access.database import Base

class EventType(Base):
    """SQLAlchemy модель типа события для базы данных"""
    __tablename__ = "EventTypes"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(100), unique=True, nullable=False)
    Description = Column(String(255), nullable=True)

    # Отношения
    events = relationship("EventLogItem", back_populates="event_type")


class EventStatus(Base):
    """SQLAlchemy модель статуса события для базы данных"""
    __tablename__ = "EventStatuses"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(50), unique=True, nullable=False)
    Description = Column(String(255), nullable=True)

    # Отношения
    events = relationship("EventLogItem", back_populates="event_status")


class EventLogItem(Base):
    """SQLAlchemy модель записи лога событий для базы данных"""
    __tablename__ = "EventLogItems"

    Id = Column(Integer, primary_key=True, index=True)
    UserId = Column(Integer, ForeignKey("Users.Id"), nullable=True)
    EventTypeId = Column(Integer, ForeignKey("EventTypes.Id"), nullable=False)
    EventStatusId = Column(Integer, ForeignKey("EventStatuses.Id"), nullable=False)
    EventDate = Column(DateTime, default=datetime.now)
    Description = Column(Text, nullable=True)
    IPAddress = Column(String(50), nullable=True)
    UserAgent = Column(String(500), nullable=True)

    # Отношения
    user = relationship("User", back_populates="events")
    event_type = relationship("EventType", back_populates="events")
    event_status = relationship("EventStatus", back_populates="events")


# Pydantic модели для валидации API запросов и ответов

class EventTypeEnum(str, Enum):
    """Перечисление для типов событий"""
    LOGIN = "Login"
    REGISTER = "Register"
    GET_ANALYSIS = "GetAnalysis"
    UPLOAD_FILE = "UploadFile"
    DOWNLOAD_REPORT = "DownloadReport"
    UPDATE_PROFILE = "UpdateProfile"
    CHANGE_PASSWORD = "ChangePassword"
    ADMIN_ACTION = "AdminAction"


class EventStatusEnum(str, Enum):
    """Перечисление для статусов событий"""
    SUCCESS = "Success"
    FAILED = "Failed"


class EventLogCreate(BaseModel):
    """Модель для создания записи лога событий"""
    user_id: Optional[int] = None
    event_type: EventTypeEnum
    event_status: EventStatusEnum
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class EventTypeResponse(BaseModel):
    """Модель для ответа с информацией о типе события"""
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        orm_mode = True


class EventStatusResponse(BaseModel):
    """Модель для ответа с информацией о статусе события"""
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        orm_mode = True


class UserBasicInfo(BaseModel):
    """Базовая информация о пользователе для включения в ответ"""
    id: int
    full_name: str
    login: str

    class Config:
        orm_mode = True


class EventLogResponse(BaseModel):
    """Модель для ответа с информацией о записи лога событий"""
    id: int
    user: Optional[UserBasicInfo] = None
    event_type: EventTypeResponse
    event_status: EventStatusResponse
    event_date: datetime
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    class Config:
        orm_mode = True


class EventLogList(BaseModel):
    """Модель для списка записей лога событий"""
    events: List[EventLogResponse]
    total: int
    page: int
    page_size: int


# Функция для создания новой записи в логе событий
def log_event(db, event_data: EventLogCreate):
    """
    Функция для логирования события в базу данных
    
    :param db: Сессия базы данных
    :param event_data: Данные о событии
    :return: Созданная запись лога
    """
    from Access.database import SessionLocal
    
    # Если сессия не передана, создаем новую
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        # Получаем ID типа события
        event_type = db.query(EventType).filter(EventType.Name == event_data.event_type).first()
        if not event_type:
            # Если тип события не найден, создаем его
            event_type = EventType(Name=event_data.event_type)
            db.add(event_type)
            db.flush()
        
        # Получаем ID статуса события
        event_status = db.query(EventStatus).filter(EventStatus.Name == event_data.event_status).first()
        if not event_status:
            # Если статус события не найден, создаем его
            event_status = EventStatus(Name=event_data.event_status)
            db.add(event_status)
            db.flush()
        
        # Создаем запись лога
        log_item = EventLogItem(
            UserId=event_data.user_id,
            EventTypeId=event_type.Id,
            EventStatusId=event_status.Id,
            Description=event_data.description,
            IPAddress=event_data.ip_address,
            UserAgent=event_data.user_agent
        )
        
        db.add(log_item)
        db.commit()
        
        return log_item
    
    except Exception as e:
        db.rollback()
        raise e
    
    finally:
        if close_db:
            db.close()