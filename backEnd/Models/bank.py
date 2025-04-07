from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime

from Access.database import Base

class Bank(Base):
    """SQLAlchemy модель банка для базы данных"""
    __tablename__ = "Banks"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(255), nullable=False)
    Code = Column(String(50), unique=True, nullable=False)
    IsActive = Column(Boolean, default=True)
    CreateDate = Column(DateTime, default=datetime.now)
    DeleteDate = Column(DateTime, nullable=True)

    # Отношения
    statements = relationship("StatementFile", back_populates="bank")


# Pydantic модели для валидации API запросов и ответов

class BankBase(BaseModel):
    """Базовая модель банка"""
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)

    @validator('code')
    def code_must_be_uppercase(cls, v):
        return v.upper()


class BankCreate(BankBase):
    """Модель для создания банка"""
    is_active: bool = True


class BankUpdate(BaseModel):
    """Модель для обновления банка"""
    name: Optional[str] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None

    @validator('code')
    def code_must_be_uppercase(cls, v):
        if v is None:
            return v
        return v.upper()


class BankResponse(BankBase):
    """Модель для ответа с информацией о банке"""
    id: int
    is_active: bool
    create_date: datetime
    delete_date: Optional[datetime] = None

    class Config:
        orm_mode = True


class BankList(BaseModel):
    """Модель для списка банков"""
    banks: List[BankResponse]
    total: int