from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from Models import bank as Bank

class BankRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_bank(self, bank_data: dict) -> Bank:
        """
        Create a new bank entry
        
        Args:
            bank_data (dict): Dictionary containing bank details
        
        Returns:
            Bank: Created bank object
        """
        new_bank = Bank(**bank_data)
        self.session.add(new_bank)
        self.session.commit()
        return new_bank

    def get_bank_by_id(self, bank_id: int) -> Optional[Bank]:
        """
        Retrieve a bank by its ID
        
        Args:
            bank_id (int): Unique identifier for the bank
        
        Returns:
            Optional[Bank]: Bank object if found, None otherwise
        """
        return self.session.query(Bank).filter(Bank.id == bank_id).first()

    def get_banks_by_user(self, user_id: int) -> List[Bank]:
        """
        Retrieve all banks associated with a specific user
        
        Args:
            user_id (int): User's unique identifier
        
        Returns:
            List[Bank]: List of banks associated with the user
        """
        return self.session.query(Bank).filter(Bank.user_id == user_id).all()

    def update_bank(self, bank_id: int, update_data: dict) -> Optional[Bank]:
        """
        Update an existing bank's information
        
        Args:
            bank_id (int): Unique identifier for the bank
            update_data (dict): Dictionary of fields to update
        
        Returns:
            Optional[Bank]: Updated bank object if found, None otherwise
        """
        bank = self.get_bank_by_id(bank_id)
        if not bank:
            return None

        for key, value in update_data.items():
            setattr(bank, key, value)

        self.session.commit()
        return bank

    def delete_bank(self, bank_id: int) -> bool:
        """
        Delete a bank entry
        
        Args:
            bank_id (int): Unique identifier for the bank
        
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        bank = self.get_bank_by_id(bank_id)
        if not bank:
            return False

        self.session.delete(bank)
        self.session.commit()
        return True

    def get_bank_balance(self, bank_id: int) -> float:
        """
        Calculate total balance for a specific bank
        
        Args:
            bank_id (int): Unique identifier for the bank
        
        Returns:
            float: Total balance of the bank
        """
        # This assumes a relationship between Bank and Transaction models
        balance_query = self.session.query(
            func.sum(Transaction.amount).label('total_balance')
        ).filter(
            and_(
                Transaction.bank_id == bank_id,
                Transaction.transaction_type == 'INCOME'
            )
        )

        expense_query = self.session.query(
            func.sum(Transaction.amount).label('total_expenses')
        ).filter(
            and_(
                Transaction.bank_id == bank_id,
                Transaction.transaction_type == 'EXPENSE'
            )
        )

        balance_result = balance_query.first()
        expense_result = expense_query.first()

        total_income = balance_result.total_balance or 0
        total_expenses = expense_result.total_expenses or 0

        return float(total_income - total_expenses)

    def search_banks(self, 
                     user_id: Optional[int] = None, 
                     bank_name: Optional[str] = None) -> List[Bank]:
        """
        Search for banks with optional filtering
        
        Args:
            user_id (Optional[int]): Filter by user
            bank_name (Optional[str]): Partial match for bank name
        
        Returns:
            List[Bank]: List of banks matching the search criteria
        """
        query = self.session.query(Bank)
        
        if user_id:
            query = query.filter(Bank.user_id == user_id)
        
        if bank_name:
            query = query.filter(Bank.name.ilike(f'%{bank_name}%'))
        
        return query.all()