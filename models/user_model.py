from supabase import create_client
import os

class UserModel:
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )

    def get_by_id(self, user_id):
        result = self.supabase.table('users').select('*').eq('id', user_id).limit(1).execute()
        return result.data[0] if result.data else None

    def get_by_email(self, email):
        result = self.supabase.table('users').select('*').eq('email', email).limit(1).execute()
        return result.data[0] if result.data else None

    def get_all(self):
        result = self.supabase.table('users').select('*').execute()
        return result.data if result.data else []

    def get_by_role(self, role):
        result = self.supabase.table('users').select('*').eq('role', role).execute()
        return result.data if result.data else []

    def create(self, user_data):
        result = self.supabase.table('users').insert(user_data).execute()
        return result.data[0] if result.data else None

    def update(self, user_id, update_data):
        result = self.supabase.table('users').update(update_data).eq('id', user_id).execute()
        return result.data[0] if result.data else None

    def update_role(self, user_id, new_role):
        return self.update(user_id, {'role': new_role})

    def get_addresses(self, user_id):
        result = self.supabase.table('addresses').select('*').eq('user_id', user_id).execute()
        return result.data if result.data else []

    def get_address_by_id(self, user_id, address_id):
        result = self.supabase.table('addresses').select('*').eq('user_id', user_id).eq('id', address_id).limit(1).execute()
        return result.data[0] if result.data else None

    def create_address(self, address_data):
        result = self.supabase.table('addresses').insert(address_data).execute()
        return result.data[0] if result.data else None

    def update_address(self, user_id, address_id, update_data):
        result = self.supabase.table('addresses').update(update_data).eq('user_id', user_id).eq('id', address_id).execute()
        return result.data[0] if result.data else None

    def delete_address(self, user_id, address_id):
        result = self.supabase.table('addresses').delete().eq('user_id', user_id).eq('id', address_id).execute()
        return result.data[0] if result.data else None
