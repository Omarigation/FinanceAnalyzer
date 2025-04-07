import re
from typing import Any, Dict, Optional
from decimal import Decimal, InvalidOperation

class Validators:
    """
    Utility class for various validation methods
    """
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format
        
        Args:
            email (str): Email to validate
        
        Returns:
            bool: True if email is valid, False otherwise
        """
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_regex, email) is not None

    @staticmethod
    def validate_password(password: str) -> bool:
        """
        Validate password strength
        
        Args:
            password (str): Password to validate
        
        Returns:
            bool: True if password meets requirements, False otherwise
        """
        # At least 8 characters, one uppercase, one lowercase, one number
        return (
            len(password) >= 8 and
            any(c.isupper() for c in password) and
            any(c.islower() for c in password) and
            any(c.isdigit() for c in password)
        )

    @staticmethod
    def validate_decimal(value: Any) -> Optional[Decimal]:
        """
        Validate and convert value to Decimal
        
        Args:
            value (Any): Value to validate
        
        Returns:
            Optional[Decimal]: Validated Decimal value or None
        """
        try:
            return Decimal(str(value))
        except (TypeError, InvalidOperation):
            return None

    @staticmethod
    def validate_positive_number(value: Any) -> bool:
        """
        Check if value is a positive number
        
        Args:
            value (Any): Value to validate
        
        Returns:
            bool: True if value is a positive number, False otherwise
        """
        try:
            decimal_value = Decimal(str(value))
            return decimal_value > 0
        except (TypeError, InvalidOperation):
            return False

    @staticmethod
    def validate_transaction_data(transaction: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate transaction data
        
        Args:
            transaction (Dict[str, Any]): Transaction data to validate
        
        Returns:
            Dict[str, str]: Dictionary of validation errors
        """
        errors = {}

        # Validate amount
        if 'amount' not in transaction or not Validators.validate_positive_number(transaction['amount']):
            errors['amount'] = 'Invalid or negative amount'

        # Validate date
        if 'date' not in transaction or not transaction['date']:
            errors['date'] = 'Date is required'

        # Validate transaction type
        valid_types = ['INCOME', 'EXPENSE', 'TRANSFER']
        if 'transaction_type' not in transaction or transaction['transaction_type'] not in valid_types:
            errors['transaction_type'] = 'Invalid transaction type'

        # Validate category (optional but should be a string if provided)
        if 'category' in transaction and not isinstance(transaction['category'], str):
            errors['category'] = 'Category must be a string'

        return errors

    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """
        Sanitize input string to prevent XSS and injection
        
        Args:
            input_str (str): Input string to sanitize
        
        Returns:
            str: Sanitized string
        """
        # Remove or escape potentially dangerous characters
        return re.sub(r'[<>&\'"()]', '', input_str).strip()

    @staticmethod
    def validate_file_upload(file_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate file upload data
        
        Args:
            file_data (Dict[str, Any]): File upload information
        
        Returns:
            Dict[str, str]: Dictionary of validation errors
        """
        errors = {}

        # Validate file exists
        if not file_data or 'file' not in file_data:
            errors['file'] = 'No file uploaded'
            return errors

        # Validate file size (e.g., max 10MB)
        max_file_size = 10 * 1024 * 1024  # 10MB
        if file_data.get('size', 0) > max_file_size:
            errors['file'] = 'File size exceeds maximum limit (10MB)'

        # Validate file type
        allowed_types = [
            'application/vnd.ms-excel',  # .xls
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
            'text/csv'  # .csv
        ]
        if file_data.get('type') not in allowed_types:
            errors['file'] = 'Unsupported file type'

        return errors