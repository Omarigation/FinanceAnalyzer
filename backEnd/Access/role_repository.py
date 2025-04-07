from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from Models import role as Role

class RoleRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_role(self, role_data: dict) -> Role:
        """
        Create a new role
        
        Args:
            role_data (dict): Dictionary containing role details
        
        Returns:
            Role: Created role object
        """
        new_role = Role(**role_data)
        self.session.add(new_role)
        self.session.commit()
        return new_role

    def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """
        Retrieve a role by its ID
        
        Args:
            role_id (int): Unique identifier for the role
        
        Returns:
            Optional[Role]: Role object if found, None otherwise
        """
        return self.session.query(Role).filter(Role.id == role_id).first()

    def get_role_by_name(self, role_name: str) -> Optional[Role]:
        """
        Retrieve a role by its name
        
        Args:
            role_name (str): Name of the role
        
        Returns:
            Optional[Role]: Role object if found, None otherwise
        """
        return self.session.query(Role).filter(Role.name == role_name).first()

    def get_all_roles(self) -> List[Role]:
        """
        Retrieve all roles in the system
        
        Returns:
            List[Role]: List of all roles
        """
        return self.session.query(Role).all()

    def update_role(self, role_id: int, update_data: dict) -> Optional[Role]:
        """
        Update an existing role's information
        
        Args:
            role_id (int): Unique identifier for the role
            update_data (dict): Dictionary of fields to update
        
        Returns:
            Optional[Role]: Updated role object if found, None otherwise
        """
        role = self.get_role_by_id(role_id)
        if not role:
            return None

        for key, value in update_data.items():
            setattr(role, key, value)

        self.session.commit()
        return role

    def delete_role(self, role_id: int) -> bool:
        """
        Delete a role entry
        
        Args:
            role_id (int): Unique identifier for the role
        
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        role = self.get_role_by_id(role_id)
        if not role:
            return False

        # Check if role is in use before deletion
        user_count = self.session.query(User).filter(User.role_id == role_id).count()
        if user_count > 0:
            raise ValueError(f"Cannot delete role. {user_count} users are currently assigned to this role.")

        self.session.delete(role)
        self.session.commit()
        return True

    def get_role_permissions(self, role_id: int) -> Dict[str, Any]:
        """
        Retrieve permissions associated with a specific role
        
        Args:
            role_id (int): Unique identifier for the role
        
        Returns:
            Dict[str, Any]: Dictionary of role permissions
        """
        role = self.get_role_by_id(role_id)
        if not role:
            return {}

        return {
            'role_name': role.name,
            'permissions': {
                'can_create_transaction': role.can_create_transaction,
                'can_edit_transaction': role.can_edit_transaction,
                'can_delete_transaction': role.can_delete_transaction,
                'can_view_reports': role.can_view_reports,
                'can_manage_users': role.can_manage_users,
                'can_manage_banks': role.can_manage_banks
            }
        }

    def assign_role_to_user(self, user_id: int, role_id: int) -> bool:
        """
        Assign a role to a user
        
        Args:
            user_id (int): Unique identifier for the user
            role_id (int): Unique identifier for the role
        
        Returns:
            bool: True if role assignment was successful, False otherwise
        """
        user = self.session.query(User).filter(User.id == user_id).first()
        role = self.get_role_by_id(role_id)

        if not user or not role:
            return False

        user.role_id = role_id
        self.session.commit()
        return True

    def search_roles(self, 
                     name: Optional[str] = None, 
                     permission: Optional[str] = None) -> List[Role]:
        """
        Search for roles with optional filtering
        
        Args:
            name (Optional[str]): Partial match for role name
            permission (Optional[str]): Filter by a specific permission
        
        Returns:
            List[Role]: List of roles matching the search criteria
        """
        query = self.session.query(Role)
        
        if name:
            query = query.filter(Role.name.ilike(f'%{name}%'))
        
        # Add permission-based filtering if needed
        if permission:
            # This is a placeholder and would need to be implemented based on your specific permission model
            permission_filters = {
                'can_create_transaction': Role.can_create_transaction == True,
                'can_edit_transaction': Role.can_edit_transaction == True,
                # Add more permission filters as needed
            }
            
            if permission in permission_filters:
                query = query.filter(permission_filters[permission])
        
        return query.all()