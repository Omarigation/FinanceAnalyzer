from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from Access.database import Base

class Role(Base):
    """SQLAlchemy модель роли для базы данных"""
    __tablename__ = "Roles"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(50), unique=True, nullable=False)
    Description = Column(String(255), nullable=True)

    # Отношения
    user_roles = relationship("UserRole", back_populates="role")


class UserRole(Base):
    """SQLAlchemy модель для связи пользователя и роли"""
    __tablename__ = "UserRoles"

    Id = Column(Integer, primary_key=True, index=True)
    UserId = Column(Integer, ForeignKey("Users.Id"), nullable=False)
    RoleId = Column(Integer, ForeignKey("Roles.Id"), nullable=False)
    AssignedDate = Column(DateTime, default=datetime.now)

    # Отношения
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="user_roles")


# Pydantic модели для валидации API запросов и ответов

class RoleBase(BaseModel):
    """Базовая модель роли"""
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Модель для создания роли"""
    pass


class RoleUpdate(BaseModel):
    """Модель для обновления роли"""
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(RoleBase):
    """Модель для ответа с информацией о роли"""
    id: int

    class Config:
        orm_mode = True


class UserRoleBase(BaseModel):
    """Базовая модель для назначения роли пользователю"""
    user_id: int
    role_id: int


class UserRoleCreate(UserRoleBase):
    """Модель для назначения роли пользователю"""
    pass


class UserRoleResponse(UserRoleBase):
    """Модель для ответа с информацией о назначенной роли"""
    id: int
    assigned_date: datetime
    role_name: str

    class Config:
        orm_mode = True