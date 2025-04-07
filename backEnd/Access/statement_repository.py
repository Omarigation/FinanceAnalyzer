from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime
from Models import statement as Statement

class StatementRepository:
    def __init__(self, session: Session):
        self.session = session

    def _validate_statement_data(self, statement_data: dict):
        """
        Validate statement data before creation or update
        
        Args:
            statement_data (dict): Statement data to validate
        
        Raises:
            ValueError: If statement data is invalid
        """
        # Check required fields
        required_fields = ['bank_id', 'statement_date', 'opening_balance', 'closing_balance']
        for field in required_fields:
            if field not in statement_data or statement_data[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate dates
        if not isinstance(statement_data['statement_date'], datetime):
            try:
                statement_data['statement_date'] = datetime.fromisoformat(statement_data['statement_date'])
            except (TypeError, ValueError):
                raise ValueError("Invalid statement date format. Use ISO format or datetime object.")
        
        # Validate balances
        if statement_data['opening_balance'] is None or statement_data['closing_balance'] is None:
            raise ValueError("Opening and closing balances must be provided")

    def create_statement(self, statement_data: dict) -> 'Statement':
        """
        Create a new bank statement
        
        Args:
            statement_data (dict): Dictionary containing statement details
        
        Returns:
            Statement: Created statement object
        """
        # Validate statement data
        self._validate_statement_data(statement_data)
        
        new_statement = Statement(**statement_data)
        self.session.add(new_statement)
        self.session.commit()
        return new_statement

    def get_statement_by_id(self, statement_id: int) -> Optional['Statement']:
        """
        Retrieve a statement by its ID
        
        Args:
            statement_id (int): Unique identifier for the statement
        
        Returns:
            Optional[Statement]: Statement object if found, None otherwise
        """
        return self.session.query(Statement).filter(Statement.id == statement_id).first()

    def get_bank_statements(self, 
                            bank_id: int, 
                            start_date: Optional[datetime] = None, 
                            end_date: Optional[datetime] = None) -> List['Statement']:
        """
        Retrieve statements for a specific bank with optional date filtering
        
        Args:
            bank_id (int): Bank's unique identifier
            start_date (Optional[datetime]): Earliest statement date
            end_date (Optional[datetime]): Latest statement date
        
        Returns:
            List[Statement]: List of statements matching the criteria
        """
        query = self.session.query(Statement).filter(Statement.bank_id == bank_id)
        
        if start_date:
            query = query.filter(Statement.statement_date >= start_date)
        
        if end_date:
            query = query.filter(Statement.statement_date <= end_date)
        
        return query.order_by(desc(Statement.statement_date)).all()

    def update_statement(self, statement_id: int, update_data: dict) -> Optional['Statement']:
        """
        Update an existing statement's information
        
        Args:
            statement_id (int): Unique identifier for the statement
            update_data (dict): Dictionary of fields to update
        
        Returns:
            Optional[Statement]: Updated statement object if found, None otherwise
        """
        statement = self.get_statement_by_id(statement_id)
        if not statement:
            return None

        # Validate update data
        self._validate_statement_data({**statement.__dict__, **update_data})

        for key, value in update_data.items():
            setattr(statement, key, value)

        self.session.commit()
        return statement

    def delete_statement(self, statement_id: int) -> bool:
        """
        Delete a statement entry
        
        Args:
            statement_id (int): Unique identifier for the statement
        
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        statement = self.get_statement_by_id(statement_id)
        if not statement:
            return False

        self.session.delete(statement)
        self.session.commit()
        return True

    def generate_bank_statement_summary(self, 
                                        bank_id: int, 
                                        year: Optional[int] = None, 
                                        month: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of bank statements
        
        Args:
            bank_id (int): Bank's unique identifier
            year (Optional[int]): Specific year to filter
            month (Optional[int]): Specific month to filter
        
        Returns:
            Dict[str, Any]: Detailed statement summary
        """
        # Base query for statements
        query = self.session.query(Statement).filter(Statement.bank_id == bank_id)
        
        # Apply year filter
        if year:
            query = query.filter(func.extract('year', Statement.statement_date) == year)
        
        # Apply month filter
        if month:
            query = query.filter(func.extract('month', Statement.statement_date) == month)
        
        # Calculate summary statistics
        summary_stats = self.session.query(
            func.count(Statement.id).label('total_statements'),
            func.min(Statement.opening_balance).label('min_opening_balance'),
            func.max(Statement.closing_balance).label('max_closing_balance'),
            func.avg(Statement.closing_balance - Statement.opening_balance).label('avg_balance_change')
        ).filter(Statement.bank_id == bank_id).first()
        
        # Get statements for detailed analysis
        statements = query.order_by(Statement.statement_date).all()
        
        # Prepare detailed statement information
        detailed_statements = [
            {
                'id': stmt.id,
                'statement_date': stmt.statement_date,
                'opening_balance': float(stmt.opening_balance),
                'closing_balance': float(stmt.closing_balance),
                'balance_change': float(stmt.closing_balance - stmt.opening_balance)
            }
            for stmt in statements
        ]
        
        return {
            'bank_id': bank_id,
            'total_statements': summary_stats.total_statements,
            'min_opening_balance': float(summary_stats.min_opening_balance or 0),
            'max_closing_balance': float(summary_stats.max_closing_balance or 0),
            'avg_balance_change': float(summary_stats.avg_balance_change or 0),
            'statements': detailed_statements
        }
        

    def import_statements_from_file(self, 
                                    bank_id: int, 
                                    file_path: str, 
                                    statement_type: str = 'BANK_UPLOAD') -> List['Statement']:
        """
        Import statements from a file (CSV, Excel, etc.)
        
        Args:
            bank_id (int): Bank's unique identifier
            file_path (str): Path to the statement file
            statement_type (str): Type of statement import
        
        Returns:
            List[Statement]: List of imported statement objects
        """
        from Core.parser.excel_parser import ExcelParser
        from Core.parser.halyk_parser import HalykParser
        
        # Determine parser based on file type or source
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            parser = ExcelParser(file_path)
        elif 'halyk' in file_path.lower():
            parser = HalykParser(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")
        
        # Parse the file
        parsed_statements = parser.parse()
        
        # Create statement objects
        imported_statements = []
        for statement_data in parsed_statements:
            # Add bank_id and statement_type to the parsed data
            statement_data['bank_id'] = bank_id
            statement_data['statement_type'] = statement_type
            
            # Create and save statement
            try:
                new_statement = self.create_statement(statement_data)
                imported_statements.append(new_statement)
            except ValueError as e:
                # Log the error or handle invalid statements
                print(f"Skipping invalid statement: {e}")
        
        return imported_statements
    
    def get_statement_balance_trend(self, 
                                    bank_id: int, 
                                    start_date: Optional[datetime] = None, 
                                    end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get balance trend for a bank over time
        
        Args:
            bank_id (int): Bank's unique identifier
            start_date (Optional[datetime]): Start date for trend analysis
            end_date (Optional[datetime]): End date for trend analysis
        
        Returns:
            List[Dict[str, Any]]: Balance trend data
        """
        query = self.session.query(Statement).filter(Statement.bank_id == bank_id)
        
        if start_date:
            query = query.filter(Statement.statement_date >= start_date)
        
        if end_date:
            query = query.filter(Statement.statement_date <= end_date)
        
        statements = query.order_by(Statement.statement_date).all()
        
        return [
            {
                'date': stmt.statement_date,
                'opening_balance': float(stmt.opening_balance),
                'closing_balance': float(stmt.closing_balance)
            }
            for stmt in statements
        ]
    
    def calculate_statement_metrics(self, 
                                    bank_id: int, 
                                    year: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics for bank statements
        
        Args:
            bank_id (int): Bank's unique identifier
            year (Optional[int]): Specific year to analyze
        
        Returns:
            Dict[str, Any]: Detailed statement metrics
        """
        query = self.session.query(Statement).filter(Statement.bank_id == bank_id)
        
        if year:
            query = query.filter(func.extract('year', Statement.statement_date) == year)
        
        # Calculate detailed metrics
        metrics_query = self.session.query(
            func.count(Statement.id).label('total_statements'),
            func.sum(Statement.closing_balance - Statement.opening_balance).label('total_balance_change'),
            func.avg(Statement.closing_balance - Statement.opening_balance).label('avg_monthly_change'),
            func.min(Statement.closing_balance).label('min_balance'),
            func.max(Statement.closing_balance).label('max_balance')
        ).filter(Statement.bank_id == bank_id)
        
        if year:
            metrics_query = metrics_query.filter(func.extract('year', Statement.statement_date) == year)
        
        metrics = metrics_query.first()
        
        return {
            'bank_id': bank_id,
            'total_statements': metrics.total_statements,
            'total_balance_change': float(metrics.total_balance_change or 0),
            'avg_monthly_change': float(metrics.avg_monthly_change or 0),
            'min_balance': float(metrics.min_balance or 0),
            'max_balance': float(metrics.max_balance or 0)
        }
    
    def search_statements(self, 
                          bank_id: Optional[int] = None, 
                          start_date: Optional[datetime] = None, 
                          end_date: Optional[datetime] = None,
                          min_balance: Optional[float] = None,
                          max_balance: Optional[float] = None) -> List['Statement']:
        """
        Search for statements with multiple filter options
        
        Args:
            bank_id (Optional[int]): Filter by bank
            start_date (Optional[datetime]): Earliest statement date
            end_date (Optional[datetime]): Latest statement date
            min_balance (Optional[float]): Minimum closing balance
            max_balance (Optional[float]): Maximum closing balance
        
        Returns:
            List[Statement]: List of statements matching the search criteria
        """
        query = self.session.query(Statement)
        
        if bank_id:
            query = query.filter(Statement.bank_id == bank_id)
        
        if start_date:
            query = query.filter(Statement.statement_date >= start_date)
        
        if end_date:
            query = query.filter(Statement.statement_date <= end_date)
        
        if min_balance is not None:
            query = query.filter(Statement.closing_balance >= min_balance)
        
        if max_balance is not None:
            query = query.filter(Statement.closing_balance <= max_balance)
        
        return query.order_by(desc(Statement.statement_date)).all() 