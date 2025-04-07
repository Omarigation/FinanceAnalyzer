from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, validator, Field
from typing import List, Optional
from datetime import datetime
import re

from Access.database import Base

class User(Base):
    """SQLAlchemy модель пользователя для базы данных"""
    __tablename__ = "Users"

    Id = Column(Integer, primary_key=True, index=True)
    FullName = Column(String(255), nullable=False)
    Login = Column(String(255), unique=True, nullable=False)
    Email = Column(String(255), unique=True, nullable=False)
    Password = Column(String(255), nullable=False)
    PhoneNumber = Column(String(20), nullable=True)
    RegistrationDate = Column(DateTime, default=datetime.now)
    LastLoginDate = Column(DateTime, nullable=True)
    IsActive = Column(Boolean, default=True)

    # Отношения
    roles = relationship("UserRole", back_populates="user")
    statements = relationship("StatementFile", back_populates="user")
    events = relationship("EventLogItem", back_populates="user")
    settings = relationship("UserSetting", back_populates="user", uselist=False)

# Pydantic модели для валидации API запросов и ответов

class UserBase(BaseModel):
    """Базовая модель пользователя"""
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    login: str = Field(..., min_length=3, max_length=50)
    phone_number: Optional[str] = None

    @validator('full_name')
    def full_name_must_contain_space(cls, v):
        if ' ' not in v:
            raise ValueError('ФИО должно содержать имя и фамилию, разделенные пробелом')
        return v

    @validator('login')
    def login_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Логин должен содержать только буквы и цифры')
        return v

    @validator('phone_number')
    def phone_number_valid(cls, v):
        if v is None:
            return v
        pattern = r'^\+?[0-9]{10,15}$'
        if not re.match(pattern, v):
            raise ValueError('Неверный формат номера телефона')
        return v

class UserCreate(UserBase):
    """Модель для создания пользователя"""
    password: str = Field(..., min_length=8)
    password_confirm: str

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v

    @validator('password_confirm')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Пароли не совпадают')
        return v

class UserLogin(BaseModel):
    """Модель для входа пользователя"""
    login: str
    password: str

class UserUpdate(BaseModel):
    """Модель для обновления пользователя"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None

    @validator('full_name')
    def full_name_must_contain_space(cls, v):
        if v is None:
            return v
        if ' ' not in v:
            raise ValueError('ФИО должно содержать имя и фамилию, разделенные пробелом')
        return v

    @validator('phone_number')
    def phone_number_valid(cls, v):
        if v is None:
            return v
        pattern = r'^\+?[0-9]{10,15}$'
        if not re.match(pattern, v):
            raise ValueError('Неверный формат номера телефона')
        return v

class PasswordChange(BaseModel):
    """Модель для изменения пароля"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @validator('new_password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Пароли не совпадают')
        return v

class RoleInfo(BaseModel):
    """Информация о роли"""
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    """Модель для ответа с информацией о пользователе"""
    id: int
    full_name: str
    email: EmailStr
    login: str
    phone_number: Optional[str] = None
    registration_date: datetime
    last_login_date: Optional[datetime] = None
    is_active: bool
    roles: List[RoleInfo] = []

    class Config:
        orm_mode = True

class UserWithToken(UserResponse):
    """Модель пользователя с токеном"""
    access_token: str
    token_type: str = "bearer"