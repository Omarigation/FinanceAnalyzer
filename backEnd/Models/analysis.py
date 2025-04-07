from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, DECIMAL, Boolean
from sqlalchemy.orm import relationship
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

from Access.database import Base

class AnalysisResult(Base):
    """SQLAlchemy модель результатов анализа для базы данных"""
    __tablename__ = "AnalysisResults"

    Id = Column(Integer, primary_key=True, index=True)
    StatementFileId = Column(Integer, ForeignKey("StatementFiles.Id"), nullable=False)
    TotalIncome = Column(DECIMAL(18, 2), default=0)
    TotalExpense = Column(DECIMAL(18, 2), default=0)
    NetProfit = Column(DECIMAL(18, 2), default=0)
    RecommendedTaxAmount = Column(DECIMAL(18, 2), default=0)
    AnalysisDate = Column(DateTime, default=datetime.now)

    # Отношения
    statement_file = relationship("StatementFile", back_populates="analysis_result")


class UserSetting(Base):
    """SQLAlchemy модель настроек пользователя для базы данных"""
    __tablename__ = "UserSettings"

    Id = Column(Integer, primary_key=True, index=True)
    UserId = Column(Integer, ForeignKey("Users.Id"), nullable=False)
    TaxRate = Column(DECIMAL(5, 2), default=10.00)
    CurrencyCode = Column(String(10), default="KZT")
    EmailNotifications = Column(Boolean, default=True)
    TelegramNotifications = Column(Boolean, default=False)
    TelegramChatId = Column(String(100), nullable=True)

    # Отношения
    user = relationship("User", back_populates="settings")


# Pydantic модели для валидации API запросов и ответов

class AnalysisResultCreate(BaseModel):
    """Модель для создания результатов анализа"""
    statement_file_id: int
    total_income: float
    total_expense: float
    net_profit: float
    recommended_tax_amount: float


class AnalysisResultUpdate(BaseModel):
    """Модель для обновления результатов анализа"""
    total_income: Optional[float] = None
    total_expense: Optional[float] = None
    net_profit: Optional[float] = None
    recommended_tax_amount: Optional[float] = None


class StatementFileBasicInfo(BaseModel):
    """Базовая информация о файле выписки"""
    id: int
    file_name: str
    upload_date: datetime

    class Config:
        orm_mode = True


class AnalysisResultResponse(BaseModel):
    """Модель для ответа с информацией о результатах анализа"""
    id: int
    statement_file: StatementFileBasicInfo
    total_income: float
    total_expense: float
    net_profit: float
    recommended_tax_amount: float
    analysis_date: datetime

    class Config:
        orm_mode = True


class AnalysisSummary(BaseModel):
    """Модель для сводной информации об анализе"""
    total_income: float
    total_expense: float
    net_profit: float
    profit_margin: float  # Маржа прибыли в процентах
    recommended_tax_amount: float
    top_income_categories: List[Dict[str, Any]]
    top_expense_categories: List[Dict[str, Any]]
    monthly_summary: List[Dict[str, Any]]


class UserSettingCreate(BaseModel):
    """Модель для создания настроек пользователя"""
    user_id: int
    tax_rate: float = 10.0
    currency_code: str = "KZT"
    email_notifications: bool = True
    telegram_notifications: bool = False
    telegram_chat_id: Optional[str] = None

    @validator('tax_rate')
    def tax_rate_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Налоговая ставка не может быть отрицательной')
        if v > 100:
            raise ValueError('Налоговая ставка не может быть больше 100%')
        return v

    @validator('currency_code')
    def currency_code_must_be_valid(cls, v):
        valid_currencies = ['KZT', 'USD', 'EUR', 'RUB']
        if v not in valid_currencies:
            raise ValueError(f'Недопустимый код валюты. Допустимые значения: {", ".join(valid_currencies)}')
        return v


class UserSettingUpdate(BaseModel):
    """Модель для обновления настроек пользователя"""
    tax_rate: Optional[float] = None
    currency_code: Optional[str] = None
    email_notifications: Optional[bool] = None
    telegram_notifications: Optional[bool] = None
    telegram_chat_id: Optional[str] = None

    @validator('tax_rate')
    def tax_rate_must_be_positive(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError('Налоговая ставка не может быть отрицательной')
        if v > 100:
            raise ValueError('Налоговая ставка не может быть больше 100%')
        return v

    @validator('currency_code')
    def currency_code_must_be_valid(cls, v):
        if v is None:
            return v
        valid_currencies = ['KZT', 'USD', 'EUR', 'RUB']
        if v not in valid_currencies:
            raise ValueError(f'Недопустимый код валюты. Допустимые значения: {", ".join(valid_currencies)}')
        return v


class UserSettingResponse(BaseModel):
    """Модель для ответа с информацией о настройках пользователя"""
    id: int
    user_id: int
    tax_rate: float
    currency_code: str
    email_notifications: bool
    telegram_notifications: bool
    telegram_chat_id: Optional[str] = None

    class Config:
        orm_mode = True


class AnalysisRecommendation(BaseModel):
    """Модель для рекомендаций по результатам анализа"""
    type: str  # 'tax', 'expense', 'income', 'general'
    title: str
    description: str
    importance: int  # 1-5, где 5 - наиболее важная рекомендация


class AnalysisDetailedResponse(BaseModel):
    """Модель для детального ответа с информацией об анализе"""
    analysis_result: AnalysisResultResponse
    summary: AnalysisSummary
    transactions: List[Any]  # Список транзакций
    recommendations: List[AnalysisRecommendation]
    charts_data: Dict[str, Any]  # Данные для графиков