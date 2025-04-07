from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config import SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from Access.database import get_db
from Models.user import User, UserResponse
from Models.event import EventLogCreate, EventTypeEnum, EventStatusEnum, log_event

# Контекст для шифрования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 схема с использованием токена JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка соответствия пароля хешу
    
    :param plain_password: Пароль в открытом виде
    :param hashed_password: Хеш пароля
    :return: True, если пароль соответствует хешу, иначе False
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Получение хеша пароля
    
    :param password: Пароль в открытом виде
    :return: Хеш пароля
    """
    return pwd_context.hash(password)


def authenticate_user(db: Session, login: str, password: str) -> Optional[User]:
    """
    Аутентификация пользователя
    
    :param db: Сессия базы данных
    :param login: Логин пользователя
    :param password: Пароль пользователя
    :return: Объект пользователя, если аутентификация успешна, иначе None
    """
    user = db.query(User).filter(User.Login == login).first()
    if not user:
        return None
    if not verify_password(password, user.Password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT токена
    
    :param data: Данные для включения в токен
    :param expires_delta: Срок действия токена
    :return: JWT токен
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Получение текущего пользователя по токену
    
    :param token: JWT токен
    :param db: Сессия базы данных
    :return: Объект пользователя
    :raises HTTPException: Если токен недействителен или пользователь не найден
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.Id == user_id).first()
    if user is None:
        raise credentials_exception
    
    # Обновляем время последнего входа
    user.LastLoginDate = datetime.now()
    db.commit()
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Получение текущего активного пользователя
    
    :param current_user: Текущий пользователь
    :return: Объект пользователя
    :raises HTTPException: Если пользователь неактивен
    """
    if not current_user.IsActive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен"
        )
    return current_user


def check_user_role(user: User, role_name: str) -> bool:
    """
    Проверка наличия у пользователя указанной роли
    
    :param user: Пользователь
    :param role_name: Название роли
    :return: True, если пользователь имеет указанную роль, иначе False
    """
    for user_role in user.roles:
        if user_role.role.Name == role_name:
            return True
    return False


async def get_admin_user(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)) -> User:
    """
    Получение текущего пользователя с ролью администратора
    
    :param current_user: Текущий пользователь
    :param db: Сессия базы данных
    :return: Объект пользователя
    :raises HTTPException: Если пользователь не имеет роли администратора
    """
    if not check_user_role(current_user, "Admin"):
        # Логируем неудачную попытку доступа к администраторскому функционалу
        event_data = EventLogCreate(
            user_id=current_user.Id,
            event_type=EventTypeEnum.ADMIN_ACTION,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка доступа к администраторскому функционалу пользователем без прав администратора"
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения данного действия"
        )
    return current_user


def get_user_role_names(user: User) -> list:
    """
    Получение списка названий ролей пользователя
    
    :param user: Пользователь
    :return: Список названий ролей
    """
    return [user_role.role.Name for user_role in user.roles]


def get_highest_role(user: User) -> str:
    """
    Получение наивысшей роли пользователя
    Порядок приоритета: Admin > Entrepreneur > Client > Guest
    
    :param user: Пользователь
    :return: Название наивысшей роли
    """
    role_priority = {
        "Admin": 4,
        "Entrepreneur": 3,
        "Client": 2,
        "Guest": 1
    }
    
    roles = get_user_role_names(user)
    if not roles:
        return "Guest"
    
    return max(roles, key=lambda x: role_priority.get(x, 0))