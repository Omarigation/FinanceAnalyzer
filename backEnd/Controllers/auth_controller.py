from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Any

from Access.database import get_db
from Core.auth import authenticate_user, create_access_token, get_password_hash, get_current_active_user
from Models.user import User, UserCreate, UserLogin, UserResponse, UserWithToken, PasswordChange
from Models.role import Role, UserRole
from Models.event import EventLogCreate, EventTypeEnum, EventStatusEnum, log_event
from config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

@router.post("/register", response_model=UserWithToken, status_code=status.HTTP_201_CREATED)
async def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Регистрация нового пользователя
    """
    # Проверяем, существует ли пользователь с таким логином
    db_user_by_login = db.query(User).filter(User.Login == user_data.login).first()
    if db_user_by_login:
        # Логируем неудачную попытку регистрации
        event_data = EventLogCreate(
            event_type=EventTypeEnum.REGISTER,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка регистрации с существующим логином: {user_data.login}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким логином уже существует"
        )
    
    # Проверяем, существует ли пользователь с таким email
    db_user_by_email = db.query(User).filter(User.Email == user_data.email).first()
    if db_user_by_email:
        # Логируем неудачную попытку регистрации
        event_data = EventLogCreate(
            event_type=EventTypeEnum.REGISTER,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка регистрации с существующим email: {user_data.email}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    # Создаем нового пользователя
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        FullName=user_data.full_name,
        Login=user_data.login,
        Email=user_data.email,
        Password=hashed_password,
        PhoneNumber=user_data.phone_number
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Назначаем роль "Client" новому пользователю
    client_role = db.query(Role).filter(Role.Name == "Client").first()
    if client_role:
        user_role = UserRole(
            UserId=new_user.Id,
            RoleId=client_role.Id
        )
        db.add(user_role)
        db.commit()
    
    # Логируем успешную регистрацию
    event_data = EventLogCreate(
        user_id=new_user.Id,
        event_type=EventTypeEnum.REGISTER,
        event_status=EventStatusEnum.SUCCESS,
        description=f"Успешная регистрация пользователя: {user_data.login}",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    log_event(db, event_data)
    
    # Создаем токен доступа
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(new_user.Id)},
        expires_delta=access_token_expires
    )
    
    # Собираем информацию о ролях
    roles = []
    for user_role in db.query(UserRole).filter(UserRole.UserId == new_user.Id).all():
        role = db.query(Role).filter(Role.Id == user_role.RoleId).first()
        roles.append({
            "id": role.Id,
            "name": role.Name,
            "description": role.Description
        })
    
    # Создаем ответ
    return {
        "id": new_user.Id,
        "full_name": new_user.FullName,
        "email": new_user.Email,
        "login": new_user.Login,
        "phone_number": new_user.PhoneNumber,
        "registration_date": new_user.RegistrationDate,
        "last_login_date": new_user.LastLoginDate,
        "is_active": new_user.IsActive,
        "roles": roles,
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/login", response_model=UserWithToken)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Any:
    """
    Вход пользователя в систему (получение токена)
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Логируем неудачную попытку входа
        event_data = EventLogCreate(
            event_type=EventTypeEnum.LOGIN,
            event_status=EventStatusEnum.FAILED,
            description=f"Неудачная попытка входа с логином: {form_data.username}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.IsActive:
        # Логируем попытку входа неактивного пользователя
        event_data = EventLogCreate(
            user_id=user.Id,
            event_type=EventTypeEnum.LOGIN,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка входа неактивного пользователя: {form_data.username}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен"
        )
    
    # Обновляем дату последнего входа
    user.LastLoginDate = timedelta
    db.commit()
    
    # Логируем успешный вход
    event_data = EventLogCreate(
        user_id=user.Id,
        event_type=EventTypeEnum.LOGIN,
        event_status=EventStatusEnum.SUCCESS,
        description=f"Успешный вход пользователя: {form_data.username}",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    log_event(db, event_data)
    
    # Создаем токен доступа
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.Id)},
        expires_delta=access_token_expires
    )
    
    # Собираем информацию о ролях
    roles = []
    for user_role in db.query(UserRole).filter(UserRole.UserId == user.Id).all():
        role = db.query(Role).filter(Role.Id == user_role.RoleId).first()
        roles.append({
            "id": role.Id,
            "name": role.Name,
            "description": role.Description
        })
    
    # Создаем ответ
    return {
        "id": user.Id,
        "full_name": user.FullName,
        "email": user.Email,
        "login": user.Login,
        "phone_number": user.PhoneNumber,
        "registration_date": user.RegistrationDate,
        "last_login_date": user.LastLoginDate,
        "is_active": user.IsActive,
        "roles": roles,
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/login/custom", response_model=UserWithToken)
async def login_custom(request: Request, login_data: UserLogin, db: Session = Depends(get_db)) -> Any:
    """
    Альтернативный вход пользователя в систему (с использованием JSON)
    """
    user = authenticate_user(db, login_data.login, login_data.password)
    if not user:
        # Логируем неудачную попытку входа
        event_data = EventLogCreate(
            event_type=EventTypeEnum.LOGIN,
            event_status=EventStatusEnum.FAILED,
            description=f"Неудачная попытка входа с логином: {login_data.login}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.IsActive:
        # Логируем попытку входа неактивного пользователя
        event_data = EventLogCreate(
            user_id=user.Id,
            event_type=EventTypeEnum.LOGIN,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка входа неактивного пользователя: {login_data.login}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен"
        )
    
    # Обновляем дату последнего входа
    user.LastLoginDate = timedelta
    db.commit()
    
    # Логируем успешный вход
    event_data = EventLogCreate(
        user_id=user.Id,
        event_type=EventTypeEnum.LOGIN,
        event_status=EventStatusEnum.SUCCESS,
        description=f"Успешный вход пользователя: {login_data.login}",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    log_event(db, event_data)
    
    # Создаем токен доступа
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.Id)},
        expires_delta=access_token_expires
    )
    
    # Собираем информацию о ролях
    roles = []
    for user_role in db.query(UserRole).filter(UserRole.UserId == user.Id).all():
        role = db.query(Role).filter(Role.Id == user_role.RoleId).first()
        roles.append({
            "id": role.Id,
            "name": role.Name,
            "description": role.Description
        })
    
    # Создаем ответ
    return {
        "id": user.Id,
        "full_name": user.FullName,
        "email": user.Email,
        "login": user.Login,
        "phone_number": user.PhoneNumber,
        "registration_date": user.RegistrationDate,
        "last_login_date": user.LastLoginDate,
        "is_active": user.IsActive,
        "roles": roles,
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)) -> Any:
    """
    Получение информации о текущем авторизованном пользователе
    """
    # Собираем информацию о ролях
    roles = []
    for user_role in db.query(UserRole).filter(UserRole.UserId == current_user.Id).all():
        role = db.query(Role).filter(Role.Id == user_role.RoleId).first()
        roles.append({
            "id": role.Id,
            "name": role.Name,
            "description": role.Description
        })
    
    # Создаем ответ
    return {
        "id": current_user.Id,
        "full_name": current_user.FullName,
        "email": current_user.Email,
        "login": current_user.Login,
        "phone_number": current_user.PhoneNumber,
        "registration_date": current_user.RegistrationDate,
        "last_login_date": current_user.LastLoginDate,
        "is_active": current_user.IsActive,
        "roles": roles
    }


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Изменение пароля текущего пользователя
    """
    # Проверяем текущий пароль
    if not authenticate_user(db, current_user.Login, password_data.current_password):
        # Логируем неудачную попытку изменения пароля
        event_data = EventLogCreate(
            user_id=current_user.Id,
            event_type=EventTypeEnum.CHANGE_PASSWORD,
            event_status=EventStatusEnum.FAILED,
            description="Неверный текущий пароль при попытке изменения пароля",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )
    
    # Меняем пароль
    current_user.Password = get_password_hash(password_data.new_password)
    db.commit()
    
    # Логируем успешное изменение пароля
    event_data = EventLogCreate(
        user_id=current_user.Id,
        event_type=EventTypeEnum.CHANGE_PASSWORD,
        event_status=EventStatusEnum.SUCCESS,
        description="Успешное изменение пароля",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    log_event(db, event_data)
    
    return {"message": "Пароль успешно изменен"}