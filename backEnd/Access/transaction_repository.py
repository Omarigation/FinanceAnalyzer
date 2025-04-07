from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime
from Models import transaction as Transaction

class TransactionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_transaction(self, transaction_data: dict) -> Transaction:
        """
        Create a new transaction
        
        Args:
            transaction_data (dict): Dictionary containing transaction details
        
        Returns:
            Transaction: Created transaction object
        """
        # Validate transaction before creation
        self._validate_transaction(transaction_data)
        
        new_transaction = Transaction(**transaction_data)
        self.session.add(new_transaction)
        self.session.commit()
        return new_transaction

    def _validate_transaction(self, transaction_data: dict):
        """
        Validate transaction data before creation or update
        
        Args:
            transaction_data (dict): Transaction data to validate
        
        Raises:
            ValueError: If transaction data is invalid
        """
        # Check required fields
        required_fields = ['amount', 'transaction_type', 'date', 'bank_id', 'user_id']
        for field in required_fields:
            if field not in transaction_data or transaction_data[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate amount
        if transaction_data['amount'] <= 0:
            raise ValueError("Transaction amount must be positive")
        
        # Validate transaction type
        valid_types = ['INCOME', 'EXPENSE', 'TRANSFER']
        if transaction_data['transaction_type'] not in valid_types:
            raise ValueError(f"Invalid transaction type. Must be one of {valid_types}")

    def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Retrieve a transaction by its ID
        
        Args:
            transaction_id (int): Unique identifier for the transaction
        
        Returns:
            Optional[Transaction]: Transaction object if found, None otherwise
        """
        return self.session.query(Transaction).filter(Transaction.id == transaction_id).first()

    def get_user_transactions(self, 
                              user_id: int, 
                              start_date: Optional[datetime] = None, 
                              end_date: Optional[datetime] = None,
                              transaction_type: Optional[str] = None,
                              bank_id: Optional[int] = None) -> List[Transaction]:
        """
        Retrieve transactions for a specific user with optional filtering
        
        Args:
            user_id (int): User's unique identifier
            start_date (Optional[datetime]): Earliest transaction date
            end_date (Optional[datetime]): Latest transaction date
            transaction_type (Optional[str]): Filter by transaction type
            bank_id (Optional[int]): Filter by specific bank
        
        Returns:
            List[Transaction]: List of transactions matching the criteria
        """
        query = self.session.query(Transaction).filter(Transaction.user_id == user_id)
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        if bank_id:
            query = query.filter(Transaction.bank_id == bank_id)
        
        return query.order_by(desc(Transaction.date)).all()

    def update_transaction(self, transaction_id: int, update_data: dict) -> Optional[Transaction]:
        """
        Update an existing transaction's information
        
        Args:
            transaction_id (int): Unique identifier for the transaction
            update_data (dict): Dictionary of fields to update
        
        Returns:
            Optional[Transaction]: Updated transaction object if found, None otherwise
        """
        transaction = self.get_transaction_by_id(transaction_id)
        if not transaction:
            return None

        # Validate update data
        self._validate_transaction({**transaction.__dict__, **update_data})

        for key, value in update_data.items():
            setattr(transaction, key, value)

        self.session.commit()
        return transaction

    def delete_transaction(self, transaction_id: int) -> bool:
        """
        Delete a transaction entry
        
        Args:
            transaction_id (int): Unique identifier for the transaction
        
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        transaction = self.get_transaction_by_id(transaction_id)
        if not transaction:
            return False

        self.session.delete(transaction)
        self.session.commit()
        return True

    def get_transaction_summary(self, 
                                user_id: int, 
                                start_date: Optional[datetime] = None, 
                                end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate a summary of transactions for a specific user
        
        Args:
            user_id (int): User's unique identifier
            start_date (Optional[datetime]): Earliest transaction date
            end_date (Optional[datetime]): Latest transaction date
        
        Returns:
            Dict[str, Any]: Summary of transaction statistics
        """
        # Base query for transactions
        query = self.session.query(Transaction).filter(Transaction.user_id == user_id)
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        
        # Income summary
        income_summary = self.session.query(
            func.sum(Transaction.amount).label('total_income'),
            func.count(Transaction.id).label('income_count')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'INCOME',
            *([Transaction.date >= start_date] if start_date else []),
            *([Transaction.date <= end_date] if end_date else [])
        ).first()
        
        # Expense summary
        expense_summary = self.session.query(
            func.sum(Transaction.amount).label('total_expense'),
            func.count(Transaction.id).label('expense_count')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'EXPENSE',
            *([Transaction.date >= start_date] if start_date else []),
            *([Transaction.date <= end_date] if end_date else [])
        ).first()
        
        # Category-wise expense breakdown
        category_breakdown = self.session.query(
            Transaction.category,
            func.sum(Transaction.amount).label('total_amount'),
            func.count(Transaction.id).label('transaction_count')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'EXPENSE',
            *([Transaction.date >= start_date] if start_date else []),
            *([Transaction.date <= end_date] if end_date else [])
        ).group_by(Transaction.category).all()
        
        return {
            'total_transactions': query.count(),
            'income': {
                'total_amount': float(income_summary.total_income or 0),
                'transaction_count': income_summary.income_count
            },
            'expense': {
                'total_amount': float(expense_summary.total_expense or 0),
                'transaction_count': expense_summary.expense_count
            },
            'net_balance': float((income_summary.total_income or 0) - (expense_summary.total_expense or 0)),
            'category_breakdown': [
                {
                    'category': result.category,
                    'total_amount': float(result.total_amount),
                    'transaction_count': result.transaction_count
                }
                for result in category_breakdown
            ]
        }

    def search_transactions(self, 
                            user_id: Optional[int] = None, 
                            start_date: Optional[datetime] = None, 
                            end_date: Optional[datetime] = None,
                            transaction_type: Optional[str] = None,
                            bank_id: Optional[int] = None,
                            category: Optional[str] = None,
                            min_amount: Optional[float] = None,
                            max_amount: Optional[float] = None) -> List[Transaction]:
        """
        Search for transactions with multiple filter options
        
        Args:
            user_id (Optional[int]): Filter by user
            start_date (Optional[datetime]): Earliest transaction date
            end_date (Optional[datetime]): Latest transaction date
            transaction_type (Optional[str]): Filter by transaction type
            bank_id (Optional[int]): Filter by specific bank
            category (Optional[str]): Filter by transaction category
            min_amount (Optional[float]): Minimum transaction amount
            max_amount (Optional[float]): Maximum transaction amount
        
        Returns:
            List[Transaction]: List of transactions matching the search criteria
        """
        query = self.session.query(Transaction)
        
        if user_id:
            query = query.filter(Transaction.user_id == user_id)
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        if bank_id:
            query = query.filter(Transaction.bank_id == bank_id)
        
        if category:
            query = query.filter(Transaction.category == category)
        
        if min_amount is not None:
            query = query.filter(Transaction.amount >= min_amount)
        
        if max_amount is not None:
            query = query.filter(Transaction.amount <= max_amount)
        
        return query.order_by(desc(Transaction.date)).all()