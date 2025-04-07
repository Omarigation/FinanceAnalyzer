from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from Core.dependencies import get_db
from Core.security import (
    create_access_token, 
    get_current_user, 
    verify_password, 
    get_password_hash
)
from Models.user import User
from Schemas.user import (
    UserCreate, 
    UserResponse, 
    UserUpdate, 
    UserSearchParams
)

class UserController:
    def __init__(self):
        self.router = APIRouter(prefix="/users", tags=["Users"])
        self.setup_routes()

    def setup_routes(self):
        """
        Set up all user-related API routes
        """
        # User registration
        self.router.add_api_route("/register", self.register, methods=["POST"])
        
        # User login
        self.router.add_api_route("/login", self.login, methods=["POST"])
        
        # Get current user profile
        self.router.add_api_route("/me", self.get_current_user_profile, methods=["GET"])
        
        # Update user profile
        self.router.add_api_route("/me", self.update_profile, methods=["PUT"])
        
        # Search users
        self.router.add_api_route("/search", self.search_users, methods=["GET"])

    def register(self, user: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
        """
        Register a new user
        
        Args:
            user (UserCreate): User registration details
            db (Session): Database session
        
        Returns:
            UserResponse: Created user details
        
        Raises:
            HTTPException: If user registration fails
        """
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Email already registered"
            )
        
        # Create new user
        try:
            # Hash the password
            hashed_password = get_password_hash(user.password)
            
            # Create user model
            db_user = User(
                email=user.email,
                hashed_password=hashed_password,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Add and commit
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            return UserResponse.from_orm(db_user)
        
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Registration failed: {str(e)}"
            )

    def login(self, 
              form_data: OAuth2PasswordRequestForm = Depends(), 
              db: Session = Depends(get_db)) -> Dict[str, str]:
        """
        User login
        
        Args:
            form_data (OAuth2PasswordRequestForm): Login credentials
            db (Session): Database session
        
        Returns:
            Dict[str, str]: Access token
        
        Raises:
            HTTPException: If login fails
        """
        # Find user
        user = db.query(User).filter(User.email == form_data.username).first()
        
        # Validate user and password
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email})
        
        return {
            "access_token": access_token, 
            "token_type": "bearer"
        }

    def get_current_user_profile(self, 
                                  current_user: User = Depends(get_current_user)) -> UserResponse:
        """
        Get current user's profile
        
        Args:
            current_user (User): Authenticated user
        
        Returns:
            UserResponse: User profile details
        """
        return UserResponse.from_orm(current_user)

    def update_profile(self, 
                       user_update: UserUpdate, 
                       current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)) -> UserResponse:
        """
        Update user profile
        
        Args:
            user_update (UserUpdate): Profile update details
            current_user (User): Authenticated user
            db (Session): Database session
        
        Returns:
            UserResponse: Updated user details
        
        Raises:
            HTTPException: If update fails
        """
        try:
            # Update fields that are not None
            if user_update.first_name is not None:
                current_user.first_name = user_update.first_name
            
            if user_update.last_name is not None:
                current_user.last_name = user_update.last_name
            
            # Handle password update separately
            if user_update.password is not None:
                current_user.hashed_password = get_password_hash(user_update.password)
            
            # Commit changes
            db.commit()
            db.refresh(current_user)
            
            return UserResponse.from_orm(current_user)
        
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Update failed: {str(e)}"
            )

    def search_users(self, 
                     params: UserSearchParams = Depends(),
                     db: Session = Depends(get_db)) -> List[UserResponse]:
        """
        Search users with optional filters
        
        Args:
            params (UserSearchParams): Search parameters
            db (Session): Database session
        
        Returns:
            List[UserResponse]: List of users matching search criteria
        """
        # Build query
        query = db.query(User)
        
        # Apply filters
        if params.email:
            query = query.filter(User.email.ilike(f"%{params.email}%"))
        
        if params.first_name:
            query = query.filter(User.first_name.ilike(f"%{params.first_name}%"))
        
        if params.last_name:
            query = query.filter(User.last_name.ilike(f"%{params.last_name}%"))
        
        # Execute query and convert to response models
        users = query.all()
        return [UserResponse.from_orm(user) for user in users]

# Create router instance
user_router = UserController().router