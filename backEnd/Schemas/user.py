from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional

class UserBase(BaseModel):
    """
    Base user model for shared fields
    """
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserCreate(UserBase):
    """
    Model for user registration
    """
    password: str = Field(..., min_length=8, description="User password")

class UserUpdate(BaseModel):
    """
    Model for user profile update
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = Field(
        None, 
        min_length=8, 
        description="New password (optional)"
    )

class UserResponse(UserBase):
    """
    Model for returning user information
    """
    id: int
    
    # Allow reading from ORM models
    model_config = ConfigDict(from_attributes=True)

class UserSearchParams(BaseModel):
    """
    Model for searching users
    """
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None