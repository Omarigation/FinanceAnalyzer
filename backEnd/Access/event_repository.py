from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta
from Models import event as Event

class EventRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_event(self, event_data: dict) -> 'Event':
        """
        Create a new event
        
        Args:
            event_data (dict): Dictionary containing event details
        
        Returns:
            Event: Created event object
        """
        # Validate event data
        self._validate_event_data(event_data)
        
        new_event = Event(**event_data)
        self.session.add(new_event)
        self.session.commit()
        return new_event

    def _validate_event_data(self, event_data: dict):
        """
        Validate event data before creation or update
        
        Args:
            event_data (dict): Event data to validate
        
        Raises:
            ValueError: If event data is invalid
        """
        # Check required fields
        required_fields = ['title', 'date', 'user_id']
        for field in required_fields:
            if field not in event_data or not event_data[field]:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate date
        if not isinstance(event_data['date'], datetime):
            try:
                event_data['date'] = datetime.fromisoformat(event_data['date'])
            except (TypeError, ValueError):
                raise ValueError("Invalid date format. Use ISO format or datetime object.")
        
        # Validate event type if provided
        if 'event_type' in event_data:
            valid_types = ['PERSONAL', 'FINANCIAL', 'REMINDER', 'MILESTONE']
            if event_data['event_type'] not in valid_types:
                raise ValueError(f"Invalid event type. Must be one of {valid_types}")

    def get_event_by_id(self, event_id: int) -> Optional['Event']:
        """
        Retrieve an event by its ID
        
        Args:
            event_id (int): Unique identifier for the event
        
        Returns:
            Optional[Event]: Event object if found, None otherwise
        """
        return self.session.query(Event).filter(Event.id == event_id).first()

    def get_user_events(self, 
                        user_id: int, 
                        start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None,
                        event_type: Optional[str] = None) -> List['Event']:
        """
        Retrieve events for a specific user with optional filtering
        
        Args:
            user_id (int): User's unique identifier
            start_date (Optional[datetime]): Earliest event date
            end_date (Optional[datetime]): Latest event date
            event_type (Optional[str]): Type of event to filter
        
        Returns:
            List[Event]: List of events matching the criteria
        """
        query = self.session.query(Event).filter(Event.user_id == user_id)
        
        # Apply date range filters
        if start_date:
            query = query.filter(Event.date >= start_date)
        
        if end_date:
            query = query.filter(Event.date <= end_date)
        
        # Apply event type filter
        if event_type:
            query = query.filter(Event.event_type == event_type)
        
        # Sort by date in ascending order
        query = query.order_by(Event.date)
        
        return query.all()

    def update_event(self, event_id: int, update_data: dict) -> Optional['Event']:
        """
        Update an existing event's information
        
        Args:
            event_id (int): Unique identifier for the event
            update_data (dict): Dictionary of fields to update
        
        Returns:
            Optional[Event]: Updated event object if found, None otherwise
        """
        event = self.get_event_by_id(event_id)
        if not event:
            return None

        # Validate update data
        self._validate_event_data({**event.__dict__, **update_data})

        for key, value in update_data.items():
            setattr(event, key, value)

        self.session.commit()
        return event

    def delete_event(self, event_id: int) -> bool:
        """
        Delete an event entry
        
        Args:
            event_id (int): Unique identifier for the event
        
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        event = self.get_event_by_id(event_id)
        if not event:
            return False

        self.session.delete(event)
        self.session.commit()
        return True

    def get_upcoming_events(self, 
                            user_id: int, 
                            days_ahead: int = 30) -> List['Event']:
        """
        Retrieve upcoming events for a user within a specified time frame
        
        Args:
            user_id (int): User's unique identifier
            days_ahead (int, optional): Number of days to look ahead. Defaults to 30.
        
        Returns:
            List[Event]: List of upcoming events
        """
        today = datetime.now()
        future_date = today + timedelta(days=days_ahead)
        
        return self.session.query(Event).filter(
            and_(
                Event.user_id == user_id,
                Event.date >= today,
                Event.date <= future_date
            )
        ).order_by(Event.date).all()

    def get_event_statistics(self, 
                             user_id: int, 
                             start_date: Optional[datetime] = None, 
                             end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate statistics for user's events
        
        Args:
            user_id (int): User's unique identifier
            start_date (Optional[datetime]): Start date for event statistics
            end_date (Optional[datetime]): End date for event statistics
        
        Returns:
            Dict[str, Any]: Event statistics
        """
        # Base query for events
        query = self.session.query(Event).filter(Event.user_id == user_id)
        
        # Apply date filters
        if start_date:
            query = query.filter(Event.date >= start_date)
        if end_date:
            query = query.filter(Event.date <= end_date)
        
        # Total event count
        total_events = query.count()
        
        # Event type distribution
        type_distribution = self.session.query(
            Event.event_type, 
            func.count(Event.id).label('count')
        ).filter(
            Event.user_id == user_id,
            *([Event.date >= start_date] if start_date else []),
            *([Event.date <= end_date] if end_date else [])
        ).group_by(Event.event_type).all()
        
        # Convert type distribution to dictionary
        type_dist_dict = dict(type_distribution)
        
        # Upcoming events
        upcoming_events = self.get_upcoming_events(user_id)
        
        return {
            'total_events': total_events,
            'event_type_distribution': type_dist_dict,
            'upcoming_events_count': len(upcoming_events),
            'upcoming_events': [
                {
                    'id': event.id,
                    'title': event.title,
                    'date': event.date,
                    'event_type': event.event_type
                }
                for event in upcoming_events[:5]  # Limit to top 5
            ]
        }

    def search_events(self, 
                      user_id: Optional[int] = None, 
                      event_type: Optional[str] = None,
                      keyword: Optional[str] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> List['Event']:
        """
        Search for events with multiple filter options
        
        Args:
            user_id (Optional[int]): Filter by user
            event_type (Optional[str]): Filter by event type
            keyword (Optional[str]): Search in event title or description
            start_date (Optional[datetime]): Earliest event date
            end_date (Optional[datetime]): Latest event date
        
        Returns:
            List[Event]: List of events matching the search criteria
        """
        query = self.session.query(Event)
        
        # Apply user filter
        if user_id:
            query = query.filter(Event.user_id == user_id)
        
        # Apply event type filter
        if event_type:
            query = query.filter(Event.event_type == event_type)
        
        # Apply keyword search
        if keyword:
            query = query.filter(
                or_(
                    Event.title.ilike(f'%{keyword}%'),
                    Event.description.ilike(f'%{keyword}%')
                )
            )
        
        # Apply date range filters
        if start_date:
            query = query.filter(Event.date >= start_date)
        
        if end_date:
            query = query.filter(Event.date <= end_date)
        
        # Sort by date
        query = query.order_by(Event.date)
        
        return query.all()