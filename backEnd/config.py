import os
from dotenv import load_dotenv
from datetime import timedelta

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройки базы данных
DB_HOST = os.getenv("DB_HOST", "localhost\SQLEXPRESS")
DB_NAME = os.getenv("DB_NAME", "anime_portal")  # По умолчанию используем значение из задания
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC+Driver+17+for+SQL+Server")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "yourpassword")

# Формирование строки подключения к базе данных
DATABASE_URL = f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?driver={DB_DRIVER}"

# Настройки JWT
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

# Настройки загрузки файлов
UPLOAD_FOLDER = "uploads"
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 МБ

# Настройки для CORS
CORS_ORIGINS = [
    "http://localhost:3000",  # Локальный фронтенд
    "https://finance-analyzer.kz",  # Продакшн URL
]

# Доступные типы файлов для загрузки
ALLOWED_FILE_EXTENSIONS = ["pdf", "xls", "xlsx", "csv"]

# Лимиты для неавторизованных и авторизованных пользователей
GUEST_ANALYSIS_LIMIT = 1       # Количество анализов для неавторизованных пользователей
CLIENT_ANALYSIS_LIMIT = 5      # Количество анализов для авторизованных клиентов
ENTREPRENEUR_ANALYSIS_LIMIT = -1  # Неограниченное количество анализов для ИП/ТОО

# Налоговые ставки по умолчанию (в процентах)
DEFAULT_TAX_RATES = {
    "ip_simplified": 3.0,      # Упрощенный режим для ИП
    "ip_general": 10.0,        # Общий режим для ИП
    "too_simplified": 3.0,     # Упрощенный режим для ТОО
    "too_general": 20.0,       # Общий режим для ТОО
}

# Настройки для API уведомлений
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@finance-analyzer.kz")

# Определение окружения (разработка/продакшн)
ENV = os.getenv("ENV", "development")
DEBUG = ENV == "development"