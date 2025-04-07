from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, DECIMAL, Boolean, BigInteger
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import os

from Access.database import Base
from config import ALLOWED_FILE_EXTENSIONS

class StatementFile(Base):
    """SQLAlchemy модель файла выписки для базы данных"""
    __tablename__ = "StatementFiles"

    Id = Column(Integer, primary_key=True, index=True)
    UserId = Column(Integer, ForeignKey("Users.Id"), nullable=False)
    BankId = Column(Integer, ForeignKey("Banks.Id"), nullable=False)
    FileName = Column(String(255), nullable=False)
    FileSize = Column(BigInteger, nullable=False)
    FilePath = Column(String(500), nullable=False)
    UploadDate = Column(DateTime, default=datetime.now)
    ProcessingStatus = Column(String(50), default="Pending")
    ProcessingDate = Column(DateTime, nullable=True)

    # Отношения
    user = relationship("User", back_populates="statements")
    bank = relationship("Bank", back_populates="statements")
    transactions = relationship("Transaction", back_populates="statement_file")
    analysis_result = relationship("AnalysisResult", back_populates="statement_file", uselist=False)


class Transaction(Base):
    """SQLAlchemy модель транзакции для базы данных"""
    __tablename__ = "Transactions"

    Id = Column(Integer, primary_key=True, index=True)
    StatementFileId = Column(Integer, ForeignKey("StatementFiles.Id"), nullable=False)
    TransactionDate = Column(DateTime, nullable=False)
    Amount = Column(DECIMAL(18, 2), nullable=False)
    Description = Column(String(500), nullable=True)
    CategoryId = Column(Integer, ForeignKey("TransactionCategories.Id"), nullable=True)
    IsIncome = Column(Boolean, nullable=False)
    Reference = Column(String(255), nullable=True)

    # Отношения
    statement_file = relationship("StatementFile", back_populates="transactions")
    category = relationship("TransactionCategory", back_populates="transactions")


class TransactionCategory(Base):
    """SQLAlchemy модель категории транзакции для базы данных"""
    __tablename__ = "TransactionCategories"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(255), nullable=False)
    Type = Column(String(50), nullable=False)  # 'Income' или 'Expense'
    IsDefault = Column(Boolean, default=False)
    IsActive = Column(Boolean, default=True)
    CreateDate = Column(DateTime, default=datetime.now)
    DeleteDate = Column(DateTime, nullable=True)

    # Отношения
    transactions = relationship("Transaction", back_populates="category")


# Pydantic модели для валидации API запросов и ответов

class ProcessingStatusEnum(str, Enum):
    """Перечисление для статусов обработки"""
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


class StatementUpload(BaseModel):
    """Модель для загрузки файла выписки"""
    bank_id: int
    file_name: str

    @validator('file_name')
    def validate_file_extension(cls, v):
        ext = v.split('.')[-1].lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            raise ValueError(f"Неподдерживаемый формат файла. Допустимые форматы: {', '.join(ALLOWED_FILE_EXTENSIONS)}")
        return v


class BankInfo(BaseModel):
    """Краткая информация о банке"""
    id: int
    name: str
    code: str

    class Config:
        orm_mode = True


class StatementFileResponse(BaseModel):
    """Модель для ответа с информацией о файле выписки"""
    id: int
    user_id: int
    bank: BankInfo
    file_name: str
    file_size: int
    upload_date: datetime
    processing_status: str
    processing_date: Optional[datetime] = None

    class Config:
        orm_mode = True


class StatementFileList(BaseModel):
    """Модель для списка файлов выписок"""
    statements: List[StatementFileResponse]
    total: int
    page: int
    page_size: int


class TransactionCategoryBase(BaseModel):
    """Базовая модель категории транзакции"""
    name: str
    type: str  # 'Income' или 'Expense'
    is_default: bool = False
    is_active: bool = True


class TransactionCategoryCreate(TransactionCategoryBase):
    """Модель для создания категории транзакции"""
    pass


class TransactionCategoryUpdate(BaseModel):
    """Модель для обновления категории транзакции"""
    name: Optional[str] = None
    type: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class TransactionCategoryResponse(TransactionCategoryBase):
    """Модель для ответа с информацией о категории транзакции"""
    id: int
    create_date: datetime
    delete_date: Optional[datetime] = None

    class Config:
        orm_mode = True


class TransactionBase(BaseModel):
    """Базовая модель транзакции"""
    transaction_date: datetime
    amount: float
    description: Optional[str] = None
    category_id: Optional[int] = None
    is_income: bool
    reference: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Модель для создания транзакции"""
    statement_file_id: int


class TransactionUpdate(BaseModel):
    """Модель для обновления транзакции"""
    transaction_date: Optional[datetime] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    is_income: Optional[bool] = None
    reference: Optional[str] = None


class TransactionResponse(TransactionBase):
    """Модель для ответа с информацией о транзакции"""
    id: int
    statement_file_id: int
    category: Optional[TransactionCategoryResponse] = None

    class Config:
        orm_mode = True


class TransactionList(BaseModel):
    """Модель для списка транзакций"""
    transactions: List[TransactionResponse]
    total: int
    page: int
    page_size: int