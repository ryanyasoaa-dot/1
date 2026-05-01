from supabase import create_client
import os

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
    
    def get_pending(self):
        """Get all pending applications"""
        result = self.supabase.table('applications').select('*, user:users(first_name, last_name, email, phone)').eq('status', 'pending').order('created_at', desc=True).execute()
        return result.data if result.data else []
    
    def get_by_id(self, app_id):
        """Get application by ID"""
        result = self.supabase.table('applications').select('*, user:users(*)').eq('id', app_id).single().execute()
        return result.data if result.data else None
    
    def create(self, app_data):
        """Create a new application"""
        result = self.supabase.table('applications').insert(app_data).execute()
        return result.data[0] if result.data else None
    
    def update_status(self, app_id, status, reviewed_by, reject_reason=None):
        """Update application status (approved/rejected)"""
        update_data = {
            'status': status,
            'reviewed_by': reviewed_by,
            'reviewed_at': 'now()'
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
        all_results = self.supabase.table('applications').select('store_category').eq('user_id', user_id).order('created_at', desc()).execute()
        if all_results.data:
            for app in all_results.data:
                if app.get('store_category'):
                    return app['store_category']
        
        return None
