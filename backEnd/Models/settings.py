import os
from typing import List, Dict, Any
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    """
    Application configuration settings
    """
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./finance_analyzer.db"
    
    # Security Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # File Upload Settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv'
    ]
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/finance_analyzer.log"
    
    # Analysis Settings
    TRANSACTION_CATEGORIES: List[str] = [
        'SALARY', 'FREELANCE', 'INVESTMENTS', 
        'GROCERIES', 'RENT', 'UTILITIES', 
        'ENTERTAINMENT', 'TRANSPORTATION', 'HEALTHCARE'
    ]
    
    # External API Keys (if needed)
    CURRENCY_EXCHANGE_API_KEY: str = os.getenv("CURRENCY_EXCHANGE_API_KEY", "")
    
    # Validation for file types
    @validator('ALLOWED_FILE_TYPES')
    def validate_file_types(cls, v):
        """
        Validate allowed file types
        """
        if not v:
            raise ValueError("At least one file type must be allowed")
        return v
    
    # Method to get configuration as dictionary
    def dict_config(self) -> Dict[str, Any]:
        """
        Convert settings to a dictionary
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        return {
            k: v for k, v in self.__dict__.items() 
            if not k.startswith('_') and not callable(v)
        }

# Create a singleton instance of settings
settings = Settings()