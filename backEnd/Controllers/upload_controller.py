from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Any, List, Optional
import os
import shutil
import uuid
from datetime import datetime

from Access.database import get_db
from Core.auth import get_current_active_user, get_highest_role
from Models.user import User
from Models.statement import StatementUpload, StatementFile, StatementFileResponse, StatementFileList
from Models.bank import Bank
from Models.event import EventLogCreate, EventTypeEnum, EventStatusEnum, log_event
from config import UPLOAD_FOLDER, ALLOWED_FILE_EXTENSIONS, GUEST_ANALYSIS_LIMIT, CLIENT_ANALYSIS_LIMIT, ENTREPRENEUR_ANALYSIS_LIMIT

router = APIRouter()

@router.post("/statement", response_model=StatementFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_statement_file(
    request: Request,
    file: UploadFile = File(...),
    bank_id: int = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Загрузка файла банковской выписки
    """
    # Проверяем формат файла
    ext = file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        # Логируем неудачную попытку загрузки
        event_data = EventLogCreate(
            user_id=current_user.Id,
            event_type=EventTypeEnum.UPLOAD_FILE,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка загрузки файла в неподдерживаемом формате: {ext}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат файла. Допустимые форматы: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
        )
    
    # Проверяем существование банка
    bank = db.query(Bank).filter(Bank.Id == bank_id).first()
    if not bank:
        # Логируем неудачную попытку загрузки
        event_data = EventLogCreate(
            user_id=current_user.Id,
            event_type=EventTypeEnum.UPLOAD_FILE,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка загрузки файла для несуществующего банка: {bank_id}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Банк не найден"
        )
    
    # Проверяем лимиты загрузок в зависимости от роли пользователя
    highest_role = get_highest_role(current_user)
    
    # Получаем количество уже загруженных файлов
    uploaded_count = db.query(StatementFile).filter(StatementFile.UserId == current_user.Id).count()
    
    # Проверяем лимиты
    if highest_role == "Client" and uploaded_count >= CLIENT_ANALYSIS_LIMIT:
        # Логируем превышение лимита
        event_data = EventLogCreate(
            user_id=current_user.Id,
            event_type=EventTypeEnum.UPLOAD_FILE,
            event_status=EventStatusEnum.FAILED,
            description=f"Превышение лимита загрузок для роли Client: {uploaded_count}/{CLIENT_ANALYSIS_LIMIT}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Превышен лимит загрузок ({CLIENT_ANALYSIS_LIMIT}). Обновите аккаунт до ИП/ТОО для снятия ограничений."
        )
    
    # Создаем директорию для загрузок пользователя, если она не существует
    user_upload_dir = os.path.join(UPLOAD_FOLDER, str(current_user.Id))
    os.makedirs(user_upload_dir, exist_ok=True)
    
    # Генерируем уникальное имя файла
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(user_upload_dir, unique_filename)
    
    # Сохраняем файл
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        # Логируем ошибку при сохранении файла
        event_data = EventLogCreate(
            user_id=current_user.Id,
            event_type=EventTypeEnum.UPLOAD_FILE,
            event_status=EventStatusEnum.FAILED,
            description=f"Ошибка при сохранении файла: {str(e)}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при сохранении файла"
        )
    
    # Получаем размер файла
    file_size = os.path.getsize(file_path)
    
    # Создаем запись в базе данных
    statement_file = StatementFile(
        UserId=current_user.Id,
        BankId=bank_id,
        FileName=file.filename,
        FileSize=file_size,
        FilePath=file_path,
        ProcessingStatus="Pending"
    )
    
    db.add(statement_file)
    db.commit()
    db.refresh(statement_file)
    
    # Логируем успешную загрузку
    event_data = EventLogCreate(
        user_id=current_user.Id,
        event_type=EventTypeEnum.UPLOAD_FILE,
        event_status=EventStatusEnum.SUCCESS,
        description=f"Успешная загрузка файла: {file.filename}, размер: {file_size} байт, банк: {bank.Name}",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    log_event(db, event_data)
    
    # Возвращаем информацию о загруженном файле
    return {
        "id": statement_file.Id,
        "user_id": statement_file.UserId,
        "bank": {
            "id": bank.Id,
            "name": bank.Name,
            "code": bank.Code
        },
        "file_name": statement_file.FileName,
        "file_size": statement_file.FileSize,
        "upload_date": statement_file.UploadDate,
        "processing_status": statement_file.ProcessingStatus,
        "processing_date": statement_file.ProcessingDate
    }


@router.get("/statements", response_model=StatementFileList)
async def get_user_statements(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение списка загруженных выписок пользователя
    """
    # Получаем общее количество записей
    total = db.query(StatementFile).filter(StatementFile.UserId == current_user.Id).count()
    
    # Получаем список выписок с пагинацией
    statements = db.query(StatementFile).filter(StatementFile.UserId == current_user.Id) \
        .order_by(StatementFile.UploadDate.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    # Формируем список с информацией о выписках
    statements_info = []
    for statement in statements:
        bank = db.query(Bank).filter(Bank.Id == statement.BankId).first()
        statements_info.append({
            "id": statement.Id,
            "user_id": statement.UserId,
            "bank": {
                "id": bank.Id,
                "name": bank.Name,
                "code": bank.Code
            },
            "file_name": statement.FileName,
            "file_size": statement.FileSize,
            "upload_date": statement.UploadDate,
            "processing_status": statement.ProcessingStatus,
            "processing_date": statement.ProcessingDate
        })
    
    # Возвращаем список выписок с информацией о пагинации
    return {
        "statements": statements_info,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/statements/{statement_id}", response_model=StatementFileResponse)
async def get_statement_details(
    statement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение подробной информации о загруженной выписке
    """
    # Получаем информацию о выписке
    statement = db.query(StatementFile).filter(
        StatementFile.Id == statement_id,
        StatementFile.UserId == current_user.Id
    ).first()
    
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Выписка не найдена или доступ запрещен"
        )
    
    # Получаем информацию о банке
    bank = db.query(Bank).filter(Bank.Id == statement.BankId).first()
    
    # Возвращаем подробную информацию о выписке
    return {
        "id": statement.Id,
        "user_id": statement.UserId,
        "bank": {
            "id": bank.Id,
            "name": bank.Name,
            "code": bank.Code
        },
        "file_name": statement.FileName,
        "file_size": statement.FileSize,
        "upload_date": statement.UploadDate,
        "processing_status": statement.ProcessingStatus,
        "processing_date": statement.ProcessingDate
    }


@router.delete("/statements/{statement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_statement(
    request: Request,
    statement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Удаление загруженной выписки
    """
    # Получаем информацию о выписке
    statement = db.query(StatementFile).filter(
        StatementFile.Id == statement_id,
        StatementFile.UserId == current_user.Id
    ).first()
    
    if not statement:
        # Логируем попытку удаления несуществующей выписки
        event_data = EventLogCreate(
            user_id=current_user.Id,
            event_type=EventTypeEnum.ADMIN_ACTION,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка удаления несуществующей или недоступной выписки: {statement_id}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Выписка не найдена или доступ запрещен"
        )
    
    # Удаляем файл с диска
    try:
        if os.path.exists(statement.FilePath):
            os.remove(statement.FilePath)
    except Exception as e:
        # Логируем ошибку при удалении файла
        event_data = EventLogCreate(
            user_id=current_user.Id,
            event_type=EventTypeEnum.ADMIN_ACTION,
            event_status=EventStatusEnum.FAILED,
            description=f"Ошибка при удалении файла выписки {statement_id}: {str(e)}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
    
    # Удаляем запись из базы данных
    db.delete(statement)
    db.commit()
    
    # Логируем успешное удаление
    event_data = EventLogCreate(
        user_id=current_user.Id,
        event_type=EventTypeEnum.ADMIN_ACTION,
        event_status=EventStatusEnum.SUCCESS,
        description=f"Успешное удаление выписки: {statement_id}",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    log_event(db, event_data)
    
    return None


@router.post("/guest-upload", response_model=StatementFileResponse, status_code=status.HTTP_201_CREATED)
async def guest_upload_statement(
    request: Request,
    file: UploadFile = File(...),
    bank_id: int = Form(...),
    db: Session = Depends(get_db)
) -> Any:
    """
    Загрузка файла выписки для гостя (без авторизации)
    """
    # Проверяем формат файла
    ext = file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        # Логируем неудачную попытку загрузки
        event_data = EventLogCreate(
            event_type=EventTypeEnum.UPLOAD_FILE,
            event_status=EventStatusEnum.FAILED,
            description=f"Гостевая загрузка: попытка загрузки файла в неподдерживаемом формате: {ext}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат файла. Допустимые форматы: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
        )
    
    # Проверяем существование банка
    bank = db.query(Bank).filter(Bank.Id == bank_id).first()
    if not bank:
        # Логируем неудачную попытку загрузки
        event_data = EventLogCreate(
            event_type=EventTypeEnum.UPLOAD_FILE,
            event_status=EventStatusEnum.FAILED,
            description=f"Гостевая загрузка: попытка загрузки файла для несуществующего банка: {bank_id}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Банк не найден"
        )
    
    # Создаем директорию для гостевых загрузок, если она не существует
    guest_upload_dir = os.path.join(UPLOAD_FOLDER, "guest")
    os.makedirs(guest_upload_dir, exist_ok=True)
    
    # Генерируем уникальное имя файла
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(guest_upload_dir, unique_filename)
    
    # Сохраняем файл
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        # Логируем ошибку при сохранении файла
        event_data = EventLogCreate(
            event_type=EventTypeEnum.UPLOAD_FILE,
            event_status=EventStatusEnum.FAILED,
            description=f"Гостевая загрузка: ошибка при сохранении файла: {str(e)}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при сохранении файла"
        )
    
    # Получаем размер файла
    file_size = os.path.getsize(file_path)
    
    # Создаем запись в базе данных (для гостя UserId = NULL)
    statement_file = StatementFile(
        UserId=None,  # Для гостя нет пользователя
        BankId=bank_id,
        FileName=file.filename,
        FileSize=file_size,
        FilePath=file_path,
        ProcessingStatus="Pending"
    )
    
    db.add(statement_file)
    db.commit()
    db.refresh(statement_file)
    
    # Логируем успешную загрузку
    event_data = EventLogCreate(
        event_type=EventTypeEnum.UPLOAD_FILE,
        event_status=EventStatusEnum.SUCCESS,
        description=f"Гостевая загрузка: успешная загрузка файла: {file.filename}, размер: {file_size} байт, банк: {bank.Name}",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    log_event(db, event_data)
    
    # Возвращаем информацию о загруженном файле
    return {
        "id": statement_file.Id,
        "user_id": None,
        "bank": {
            "id": bank.Id,
            "name": bank.Name,
            "code": bank.Code
        },
        "file_name": statement_file.FileName,
        "file_size": statement_file.FileSize,
        "upload_date": statement_file.UploadDate,
        "processing_status": statement_file.ProcessingStatus,
        "processing_date": statement_file.ProcessingDate
    }