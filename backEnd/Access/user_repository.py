from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime
import bcrypt
import re
from Models import user as User

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def _hash_password(self, password: str) -> bytes:
        """
        Hash a password using bcrypt
        
        Args:
            password (str): Plain text password
        
        Returns:
            bytes: Hashed password
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    def _verify_password(self, stored_password: bytes, provided_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            stored_password (bytes): Stored hashed password
            provided_password (str): Password to verify
        
        Returns:
            bool: True if password is correct, False otherwise
        """
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password)

    def _validate_email(self, email: str) -> bool:
        """
        Validate email format
        
        Args:
            email (str): Email to validate
        
        Returns:
            bool: True if email is valid, False otherwise
        """
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_regex, email) is not None

    def _validate_password_strength(self, password: str) -> bool:
        """
        Validate password strength
        
        Args:
            password (str): Password to validate
        
        Returns:
            bool: True if password meets strength requirements
        """
        # At least 8 characters, one uppercase, one lowercase, one number
        return (
            len(password) >= 8 and 
            any(c.isupper() for c in password) and 
            any(c.islower() for c in password) and 
            any(c.isdigit() for c in password)
        )

    def create_user(self, user_data: dict) -> 'User':
        """
        Create a new user
        
        Args:
            user_data (dict): Dictionary containing user details
        
        Returns:
            User: Created user object
        
        Raises:
            ValueError: If user data is invalid
        """
        # Validate user data
        self._validate_user_creation(user_data)
        
        # Hash password
        if 'password' in user_data:
            user_data['password'] = self._hash_password(user_data['password'])
        
        # Set default role if not provided
        if 'role_id' not in user_data:
            default_role = self.session.query(Role).filter(Role.name == 'USER').first()
            if default_role:
                user_data['role_id'] = default_role.id
        
        # Create user
        new_user = User(**user_data)
        self.session.add(new_user)
        self.session.commit()
        return new_user

    def _validate_user_creation(self, user_data: dict):
        """
        Comprehensive validation for user creation
        
        Args:
            user_data (dict): User data to validate
        
        Raises:
            ValueError: If user data is invalid
        """
        # Check required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if field not in user_data or not user_data[field]:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate email
        email = user_data['email']
        if not self._validate_email(email):
            raise ValueError("Invalid email format")
        
        # Check if email already exists
        existing_user = self.get_user_by_email(email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Validate password strength
        password = user_data['password']
        if not self._validate_password_strength(password):
            raise ValueError("Password does not meet strength requirements")

    def get_user_by_id(self, user_id: int) -> Optional['User']:
        """
        Retrieve a user by their ID
        
        Args:
            user_id (int): User's unique identifier
        
        Returns:
            Optional[User]: User object if found, None otherwise
        """
        return self.session.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional['User']:
        """
        Retrieve a user by their email
        
        Args:
            email (str): User's email address
        
        Returns:
            Optional[User]: User object if found, None otherwise
        """
        return self.session.query(User).filter(User.email == email).first()

    def update_user(self, user_id: int, update_data: dict) -> Optional['User']:
        """
        Update an existing user's information
        
        Args:
            user_id (int): User's unique identifier
            update_data (dict): Dictionary of fields to update
        
        Returns:
            Optional[User]: Updated user object if found, None otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        # Validate and process specific fields
        if 'email' in update_data:
            # Validate new email
            if not self._validate_email(update_data['email']):
                raise ValueError("Invalid email format")
            
            # Check if new email is already in use
            existing_user = self.get_user_by_email(update_data['email'])
            if existing_user and existing_user.id != user_id:
                raise ValueError("Email is already in use by another user")

        # Update password with hashing if provided
        if 'password' in update_data:
            if not self._validate_password_strength(update_data['password']):
                raise ValueError("Password does not meet strength requirements")
            update_data['password'] = self._hash_password(update_data['password'])

        # Update user fields
        for key, value in update_data.items():
            setattr(user, key, value)

        self.session.commit()
        return user

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user entry
        
        Args:
            user_id (int): User's unique identifier
        
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        # Optional: Add checks before deletion (e.g., no active transactions)
        active_transactions = self.session.query(Transaction).filter(Transaction.user_id == user_id).count()
        if active_transactions > 0:
            raise ValueError("Cannot delete user with active transactions")

        self.session.delete(user)
        self.session.commit()
        return True

    def authenticate_user(self, email: str, password: str) -> Optional['User']:
        """
        Authenticate a user
        
        Args:
            email (str): User's email
            password (str): User's password
        
        Returns:
            Optional[User]: Authenticated user if credentials are correct, None otherwise
        """
        user = self.get_user_by_email(email)
        if not user:
            return None

        # Verify password
        if not self._verify_password(user.password, password):
            return None

        return user

    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """
        Retrieve comprehensive user profile
        
        Args:
            user_id (int): User's unique identifier
        
        Returns:
            Dict[str, Any]: User profile information
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return {}

        # Fetch related information
        total_banks = self.session.query(Bank).filter(Bank.user_id == user_id).count()
        total_transactions = self.session.query(Transaction).filter(Transaction.user_id == user_id).count()
        
        return {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role.name if user.role else None,
            'total_banks': total_banks,
            'total_transactions': total_transactions,
            'last_login': user.last_login,
            'date_joined': user.date_joined
        }

    def search_users(self, 
                     email: Optional[str] = None, 
                     first_name: Optional[str] = None, 
                     last_name: Optional[str] = None,
                     role_id: Optional[int] = None) -> List['User']:
        """
        Search for users with multiple filter options
        
        Args:
            email (Optional[str]): Partial email match
            first_name (Optional[str]): Partial first name match
            last_name (Optional[str]): Partial last name match
            role_id (Optional[int]): Filter by role
        
        Returns:
            List[User]: List of users matching the search criteria
        """
        query = self.session.query(User)
        
        if email:
            query = query.filter(User.email.ilike(f'%{email}%'))
        
        if first_name:
            query = query.filter(User.first_name.ilike(f'%{first_name}%'))
        
        if last_name:
            query = query.filter(User.last_name.ilike(f'%{last_name}%'))
        
        if role_id:
            query = query.filter(User.role_id == role_id)
        
        return query.all()