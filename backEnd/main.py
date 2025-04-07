from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import os
from typing import List, Optional

# Импорт модулей из проекта
from Access.database import get_db
from Models.user import UserCreate, UserLogin, UserResponse
from Models.statement import StatementUpload
from Models.analysis import AnalysisResponse
from Core.auth import create_access_token, get_current_user
from Controllers.auth_controller import router as auth_router
from Controllers.user_controller import router as user_router
from Controllers.upload_controller import router as upload_router
from Controllers.analysis_controller import router as analysis_router
from Controllers.bank_controller import router as bank_router
from Controllers.admin_controller import router as admin_router
from Controllers.report_controller import router as report_router

# Создание приложения FastAPI
app = FastAPI(
    title="FinanceAnalyzer API",
    description="API для автоматического анализа банковских выписок для ИП и ТОО",
    version="1.0.0"
)

# Настройка CORS
origins = [
    "http://localhost:3000",  # Разрешить фронтенд на разработке
    "https://finance-analyzer.kz",  # Продакшн URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/api/users", tags=["Users"])
app.include_router(upload_router, prefix="/api/uploads", tags=["File Uploads"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(bank_router, prefix="/api/banks", tags=["Banks"])
app.include_router(admin_router, prefix="/api/admin", tags=["Administration"])
app.include_router(report_router, prefix="/api/reports", tags=["Reports"])

# Создаем директорию для загруженных файлов, если она не существует
os.makedirs("uploads", exist_ok=True)

# Монтирование статических файлов
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def root():
    """Проверка здоровья API"""
    return {"status": "API is running", "version": "1.0.0"}

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Обработчик HTTP исключений"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

if __name__ == "__main__":
    # Запуск сервера
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)