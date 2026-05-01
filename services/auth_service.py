from supabase import create_client
import os
from models.user_model import UserModel
from models.application_model import ApplicationModel
from services.file_upload_service import FileUploadService

class AuthService:
    """Handles authentication and user-related business logic"""
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        self.user_model = UserModel()
        self.app_model = ApplicationModel()
        self.file_service = FileUploadService()
    
    def authenticate_user(self, email, password):
        """Authenticate user with email and password"""
        user = self.user_model.get_by_email(email)
        if not user:
            return {'success': False, 'error': 'Invalid email or password'}
        
        # Check password (currently plaintext, should be hashed in production)
        if user['password'] != password:
            return {'success': False, 'error': 'Invalid email or password'}
        
        # Get application status
        application = self.app_model.get_by_user_id(user['id'])
        if application and application['status'] == 'pending':
            return {'success': False, 'error': 'Your account is pending admin approval.'}
        if application and application['status'] == 'rejected':
            return {'success': False, 'error': 'Your application was rejected. Please contact support.'}
        
        return {
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'phone': user['phone'],
                'role': user['role']
            }
        }
    
    def register_user(self, form_data, files):
        """Register a new user with role-based application"""
        first_name = form_data.get('first_name', '').strip()
        middle_name = form_data.get('middle_name', '').strip() or None
        last_name = form_data.get('last_name', '').strip()
        email = form_data.get('email', '').strip().lower()
        password = form_data.get('password', '')
        phone = form_data.get('phone', '').strip()
        role = form_data.get('role', 'buyer')
        
        # Validations
        if not all([first_name, last_name, email, password, phone]):
            return {'success': False, 'error': 'All required fields must be filled.'}
        if len(password) < 8:
            return {'success': False, 'error': 'Password must be at least 8 characters.'}
        if self.user_model.get_by_email(email):
            return {'success': False, 'error': 'This email is already registered.'}
        
        # Create user (role defaults to 'user', application will set proper role)
        user_data = {
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'password': password,  # In production, hash this!
            'role': 'user'
        }
        
        user = self.user_model.create(user_data)
        if not user:
            return {'success': False, 'error': 'Failed to create user account.'}
        
        # Create application
        app_data = {
            'user_id': user['id'],
            'role': role,
            'status': 'pending'
        }
        
        # Role-specific data
        if role == 'buyer':
            pass  # No extra data needed
        elif role == 'seller':
            app_data['store_name'] = form_data.get('store_name', '').strip()
            app_data['store_category'] = form_data.get('store_category', '').strip()
            app_data['store_description'] = form_data.get('store_description', '').strip() or None
            if not app_data['store_name']:
                return {'success': False, 'error': 'Store name is required for sellers.'}
            if not app_data['store_category']:
                return {'success': False, 'error': 'Store category is required for sellers.'}
        elif role == 'rider':
            app_data['vehicle_type'] = form_data.get('vehicle_type', '').strip() or None
            app_data['license_number'] = form_data.get('license_number', '').strip()
            if not app_data['license_number']:
                return {'success': False, 'error': 'License number is required for riders.'}
        
        application = self.app_model.create(app_data)
        
        # Handle document uploads
        doc_map = self._get_doc_map(role, files)
        for doc_type, file in doc_map.items():
            if file:
                path = self.file_service.save_file(file, f'documents/{user["id"]}')
                if path:
                    self.supabase.table('application_documents').insert({
                        'application_id': application['id'],
                        'doc_type': doc_type,
                        'file_path': path
                    }).execute()
        
        return {'success': True, 'message': 'Application submitted successfully!'}
    
    def get_user_profile(self, user_id):
        """Get complete user profile"""
        return self.user_model.get_by_id(user_id)
    
    def get_seller_category(self, user_id):
        """Get the category of a seller"""
        return self.app_model.get_seller_category(user_id)
    
    def get_all_products(self):
        """Get all products (admin view)"""
        from models.product_model import ProductModel
        product_model = ProductModel()
        return product_model.get_all()
    
    def get_default_address(self, user_id):
        """Get default address for user"""
        addresses = self.user_model.get_addresses(user_id)
        for addr in addresses:
            if addr.get('is_default'):
                return addr
        return addresses[0] if addresses else None
    
    def get_addresses(self, user_id):
        """Get all addresses for user"""
        return self.user_model.get_addresses(user_id)
    
    def get_admin_stats(self):
        """Get statistics for admin dashboard"""
        # Count users by role
        users = self.supabase.table('users').select('role').execute()
        role_counts = {'user': 0, 'seller': 0, 'rider': 0, 'admin': 0}
        if users.data:
            for u in users.data:
                role = u.get('role', 'user')
                if role in role_counts:
                    role_counts[role] += 1
        
        # Count applications by status
        apps = self.supabase.table('applications').select('status').execute()
        status_counts = {'pending': 0, 'approved': 0, 'rejected': 0}
        if apps.data:
            for a in apps.data:
                status = a.get('status', 'pending')
                if status in status_counts:
                    status_counts[status] += 1
        
        # Count products
        products = self.supabase.table('products').select('id').eq('status', 'active').execute()
        product_count = len(products.data) if products.data else 0
        
        # Count orders
        orders = self.supabase.table('orders').select('id').execute()
        order_count = len(orders.data) if orders.data else 0
        
        return {
            'users': role_counts,
            'applications': status_counts,
            'products': product_count,
            'orders': order_count
        }
    
    def _get_doc_map(self, role, files):
        """Map files to document types based on role"""
        if role == 'buyer':
            return {'valid_id': files.get('valid_id')}
        elif role == 'seller':
            return {
                'valid_id': files.get('valid_id'),
                'business_permit': files.get('business_permit'),
                'dti_or_sec': files.get('dti_or_sec')
            }
        elif role == 'rider':
            return {
                'driver_license': files.get('driver_license'),
                'valid_id': files.get('valid_id')
            }
        return {}
