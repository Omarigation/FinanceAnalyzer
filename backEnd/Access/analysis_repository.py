from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

class AnalysisRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_transaction_analysis(self, 
                                 start_date: str = None, 
                                 end_date: str = None, 
                                 bank_id: int = None, 
                                 user_id: int = None) -> List[Dict[str, Any]]:
        """
        Perform comprehensive transaction analysis with optional filtering
        
        Args:
            start_date (str, optional): Start date for analysis
            end_date (str, optional): End date for analysis
            bank_id (int, optional): Specific bank to analyze
            user_id (int, optional): Specific user to analyze
        
        Returns:
            List of dictionaries containing analysis results
        """
        # Base query to build analysis
        query = self.session.query(
            func.sum(Transaction.amount).label('total_amount'),
            func.count(Transaction.id).label('transaction_count'),
            func.avg(Transaction.amount).label('average_amount'),
            Transaction.transaction_type,
            Transaction.category
        )

        # Apply filters
        conditions = []
        if start_date:
            conditions.append(Transaction.date >= start_date)
        if end_date:
            conditions.append(Transaction.date <= end_date)
        if bank_id:
            conditions.append(Transaction.bank_id == bank_id)
        if user_id:
            conditions.append(Transaction.user_id == user_id)

        if conditions:
            query = query.filter(and_(*conditions))

        # Group and order results
        analysis_results = query.group_by(
            Transaction.transaction_type, 
            Transaction.category
        ).all()

        # Convert to list of dictionaries
        return [
            {
                'total_amount': float(result.total_amount or 0),
                'transaction_count': result.transaction_count,
                'average_amount': float(result.average_amount or 0),
                'transaction_type': result.transaction_type,
                'category': result.category
            }
            for result in analysis_results
        ]

    def get_income_expense_breakdown(self, 
                                     start_date: str = None, 
                                     end_date: str = None, 
                                     user_id: int = None) -> Dict[str, Any]:
        """
        Get detailed income and expense breakdown
        
        Args:
            start_date (str, optional): Start date for analysis
            end_date (str, optional): End date for analysis
            user_id (int, optional): Specific user to analyze
        
        Returns:
            Dictionary with income and expense details
        """
        # Base conditions
        conditions = []
        if start_date:
            conditions.append(Transaction.date >= start_date)
        if end_date:
            conditions.append(Transaction.date <= end_date)
        if user_id:
            conditions.append(Transaction.user_id == user_id)

        # Income analysis
        income_query = self.session.query(
            func.sum(Transaction.amount).label('total_income'),
            func.count(Transaction.id).label('income_count')
        ).filter(
            Transaction.transaction_type == 'INCOME',
            *conditions
        )

        # Expense analysis
        expense_query = self.session.query(
            func.sum(Transaction.amount).label('total_expense'),
            func.count(Transaction.id).label('expense_count')
        ).filter(
            Transaction.transaction_type == 'EXPENSE',
            *conditions
        )

        # Execute queries
        income_result = income_query.first()
        expense_result = expense_query.first()

        return {
            'income': {
                'total_amount': float(income_result.total_income or 0),
                'transaction_count': income_result.income_count
            },
            'expense': {
                'total_amount': float(expense_result.total_expense or 0),
                'transaction_count': expense_result.expense_count
            },
            'net_balance': float((income_result.total_income or 0) - (expense_result.total_expense or 0))
        }

    def get_category_spending_analysis(self, 
                                       start_date: str = None, 
                                       end_date: str = None, 
                                       user_id: int = None) -> List[Dict[str, Any]]:
        """
        Analyze spending by category
        
        Args:
            start_date (str, optional): Start date for analysis
            end_date (str, optional): End date for analysis
            user_id (int, optional): Specific user to analyze
        
        Returns:
            List of category spending details
        """
        # Base conditions
        conditions = [Transaction.transaction_type == 'EXPENSE']
        if start_date:
            conditions.append(Transaction.date >= start_date)
        if end_date:
            conditions.append(Transaction.date <= end_date)
        if user_id:
            conditions.append(Transaction.user_id == user_id)

        # Category spending analysis
        category_analysis = self.session.query(
            Transaction.category,
            func.sum(Transaction.amount).label('total_spent'),
            func.count(Transaction.id).label('transaction_count')
        ).filter(
            and_(*conditions)
        ).group_by(Transaction.category).all()

        return [
            {
                'category': result.category,
                'total_spent': float(result.total_spent),
                'transaction_count': result.transaction_count
            }
            for result in category_analysis
        ]