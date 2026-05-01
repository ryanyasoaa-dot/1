from supabase import create_client
import os

class UserModel:
    """Handles all user-related database operations"""
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
    
    def get_by_id(self, user_id):
        """Get user by ID"""
        result = self.supabase.table('users').select('*').eq('id', user_id).single().execute()
        return result.data if result.data else None
    
    def get_by_email(self, email):
        """Get user by email"""
        result = self.supabase.table('users').select('*').eq('email', email).single().execute()
        return result.data if result.data else None
    
    def get_by_role(self, role):
        """Get all users by role"""
        result = self.supabase.table('users').select('*').eq('role', role).execute()
        return result.data if result.data else []
    
    def create(self, user_data):
        """Create a new user"""
        result = self.supabase.table('users').insert(user_data).execute()
        return result.data[0] if result.data else None
    
    def update(self, user_id, update_data):
        """Update user data"""
        result = self.supabase.table('users').update(update_data).eq('id', user_id).execute()
        return result.data[0] if result.data else None
    
    def update_role(self, user_id, new_role):
        """Update user role"""
        return self.update(user_id, {'role': new_role})
    
    def get_addresses(self, user_id):
        """Get all addresses for a user"""
        result = self.supabase.table('addresses').select('*').eq('user_id', user_id).execute()
        return result.data if result.data else []
    
    def create_address(self, address_data):
        """Create a new address"""
        result = self.supabase.table('addresses').insert(address_data).execute()
        return result.data[0] if result.data else None
