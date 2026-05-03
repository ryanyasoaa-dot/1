from supabase import create_client
import os
from datetime import datetime, timezone

class ApplicationModel:
    """Handles all application-related database operations"""
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
    
    def get_by_user_id(self, user_id):
        """Get application by user ID"""
        result = self.supabase.table('applications').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(1).execute()
        return result.data[0] if result.data else None
    
    def get_all(self):
        result = self.supabase.table('applications').select('*').order('created_at', desc=True).execute()
        apps = result.data if result.data else []
        for a in apps:
            user_id = a.get('user_id')
            if user_id:
                u = self.supabase.table('users').select('first_name, last_name, email, phone').eq('id', user_id).limit(1).execute()
                u = u.data[0] if u.data else {}
                a['full_name'] = f"{u.get('first_name','')} {u.get('last_name','')}".strip()
                a['email']     = u.get('email', '')
                a['phone']     = u.get('phone', '')
        return apps

    def get_pending(self):
        result = self.supabase.table('applications').select('*').eq('status', 'pending').order('created_at', desc=True).execute()
        apps = result.data if result.data else []
        for a in apps:
            user_id = a.get('user_id')
            if user_id:
                u = self.supabase.table('users').select('first_name, last_name, email, phone').eq('id', user_id).limit(1).execute()
                u = u.data[0] if u.data else {}
                a['full_name'] = f"{u.get('first_name','')} {u.get('last_name','')}".strip()
                a['email']     = u.get('email', '')
                a['phone']     = u.get('phone', '')
        return apps
    
    def get_by_id(self, app_id):
        result = self.supabase.table('applications').select('*').eq('id', app_id).limit(1).execute()
        if not result.data:
            return None
        a = result.data[0]
        user_id = a.get('user_id', '')
        if user_id:
            u = self.supabase.table('users').select('*').eq('id', user_id).limit(1).execute()
            u = u.data[0] if u.data else {}
            a['full_name'] = f"{u.get('first_name','')} {u.get('last_name','')}".strip()
            a['email']     = u.get('email', '')
            a['phone']     = u.get('phone', '')
        # get address
        addr = self.supabase.table('addresses').select('*').eq('user_id', user_id).limit(1).execute()
        addr_data = addr.data[0] if addr.data else {}
        a['region']    = addr_data.get('region', '')
        a['city']      = addr_data.get('city', '')
        a['barangay']  = addr_data.get('barangay', '')
        a['street']    = addr_data.get('street', '')
        a['zip_code']  = addr_data.get('zip_code', '')
        a['latitude']  = addr_data.get('latitude', '')
        a['longitude'] = addr_data.get('longitude', '')
        # get documents
        docs = self.supabase.table('application_documents').select('*').eq('application_id', app_id).execute()
        a['documents'] = docs.data if docs.data else []
        return a
    
    def create(self, app_data):
        """Create a new application"""
        result = self.supabase.table('applications').insert(app_data).execute()
        return result.data[0] if result.data else None
    
    def update_status(self, app_id, status, reviewed_by=None, reject_reason=None):
        update_data = {
            'status': status,
            'reviewed_at': datetime.now(timezone.utc).isoformat()
        }
        if reject_reason:
            update_data['reject_reason'] = reject_reason
        result = self.supabase.table('applications').update(update_data).eq('id', app_id).execute()
        return result.data[0] if result.data else None
    
    def get_seller_category(self, user_id):
        """Get seller category from their application"""
        result = self.supabase.table('applications').select('store_category').eq('user_id', user_id).eq('status', 'approved').order('created_at', desc=True).limit(1).execute()
        if result.data and result.data[0] and result.data[0]['store_category']:
            return result.data[0]['store_category']
        
        # Fallback to checking user's applications
        all_results = self.supabase.table('applications').select('store_category').eq('user_id', user_id).order('created_at', desc=True).execute()
        if all_results.data:
            for app in all_results.data:
                if app.get('store_category'):
                    return app['store_category']
        
        return None
