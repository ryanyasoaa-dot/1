from supabase import create_client
import os
import uuid
from models.user_model import UserModel
from models.application_model import ApplicationModel
from services.file_upload_service import FileUploadService
from security import validate_password, sanitise, hash_password

class AuthService:

    def __init__(self):
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        self.user_model = UserModel()
        self.app_model = ApplicationModel()
        self.file_service = FileUploadService()

    def authenticate_user(self, email, password):
        from security import check_login_lockout, record_failed_login, clear_login_attempts
        from security import log_failed_login, log_account_locked, log_activity
        
        # Ensure email and password are strings (handle tuple/list from form data)
        if isinstance(email, (list, tuple)):
            email = email[0] if email else ''
        if isinstance(password, (list, tuple)):
            password = password[0] if password else ''
        email = str(email).strip().lower() if email else ''
        password = str(password) if password else ''
        
        user = self.user_model.get_by_email(email)
        
        # Handle case where user might be a tuple instead of dict
        if user and isinstance(user, (list, tuple)):
            # Convert tuple to dict using column names from Supabase
            user = dict(user) if hasattr(user, '_asdict') else user
        if user and not isinstance(user, dict):
            user = None
        
        ip = self._get_client_ip()
        ua = self._get_user_agent()
        
        locked, msg = check_login_lockout(email)
        if locked:
            log_account_locked(self.supabase, email, ip, ua)
            return {'success': False, 'error': msg}
        
        if not user:
            remaining, _ = record_failed_login(email)
            log_failed_login(self.supabase, email, ip, ua)
            if remaining == 0:
                log_account_locked(self.supabase, email, ip, ua)
                return {'success': False, 'error': 'Too many failed attempts. Account locked for 10 minutes.'}
            return {'success': False, 'error': 'Invalid email or password (attempts remaining: %d)' % remaining}

        from security import verify_password, hash_password
        if not verify_password(password, user.get('password', '')):
            remaining, delay = record_failed_login(email)
            log_failed_login(self.supabase, email, ip, ua)
            if remaining == 0:
                log_account_locked(self.supabase, email, ip, ua)
                return {'success': False, 'error': 'Too many failed attempts. Account locked for 10 minutes.'}
            msg = 'Invalid email or password'
            msg += ' (attempts remaining: %d)' % remaining
            return {'success': False, 'error': msg}

        application = self.app_model.get_by_user_id(user.get('id', ''))
        if application and application['status'] == 'pending':
            return {'success': False, 'error': 'Your account is pending admin approval.'}
        if application and application['status'] == 'rejected':
            return {'success': False, 'error': 'Your application was rejected. Please contact support.'}

        clear_login_attempts(email)
        try:
            log_activity(self.supabase, user.get('id', ''), 'successful_login', ip, ua)
        except Exception:
            pass

        return {
            'success': True,
            'user': {
                'id':              user.get('id', ''),
                'email':           user.get('email', ''),
                'first_name':      user.get('first_name', ''),
                'last_name':       user.get('last_name', ''),
                'phone':           user.get('phone', ''),
                'role':            user.get('role', 'user'),
                'name':            ('%s %s' % (user.get('first_name',''), user.get('last_name',''))).strip(),
                'profile_picture': user.get('profile_picture')
            }
        }

    def register_user(self, form_data, files):
        first_name  = str(form_data.get('first_name', '')).strip()
        middle_name = str(form_data.get('middle_name', '')).strip() or None
        last_name   = str(form_data.get('last_name', '')).strip()
        email       = str(form_data.get('email', '')).strip().lower()
        password    = str(form_data.get('password', ''))
        phone       = str(form_data.get('phone', '')).strip()
        role        = str(form_data.get('role', 'buyer'))
        gender      = str(form_data.get('gender', ''))

        if not all([first_name, last_name, email, password, phone, gender]):
            return {'success': False, 'error': 'All required fields must be filled.'}
        
        if gender not in ['male', 'female']:
            return {'success': False, 'error': 'Please select a valid gender.'}
        
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            return {'success': False, 'error': error_msg}
        
        if self.user_model.get_by_email(email):
            return {'success': False, 'error': 'This email is already registered.'}

        user = self.user_model.create({
            'id':          str(uuid.uuid4()),
            'first_name':  sanitise(first_name, 100),
            'middle_name': sanitise(middle_name, 100) if middle_name else None,
            'last_name':   sanitise(last_name, 100),
            'email':       email,
            'password':    hash_password(password),
            'phone':       sanitise(phone, 20),
            'role':        role,
            'gender':      gender
        })
        if not user:
            return {'success': False, 'error': 'Failed to create user account.'}

        # Save address if provided
        region    = str(form_data.get('region', '')).strip()
        city      = str(form_data.get('city', '')).strip()
        barangay  = str(form_data.get('barangay', '')).strip()
        street    = str(form_data.get('street', '')).strip()
        zip_code  = str(form_data.get('zip_code', '')).strip()
        latitude  = str(form_data.get('latitude', '')).strip() or None
        longitude = str(form_data.get('longitude', '')).strip() or None
        if any([region, city, barangay, street]):
            self.user_model.create_address({
                'user_id':    user['id'],
                'region':     region,
                'city':       city,
                'barangay':   barangay,
                'street':     street,
                'zip_code':   zip_code,
                'latitude':   latitude,
                'longitude':  longitude,
                'is_default': True
            })

        # Build application
        app_data = {'user_id': user['id'], 'role': role, 'status': 'pending'}
        if role == 'seller':
            app_data['store_name']        = str(form_data.get('store_name', '')).strip()
            app_data['store_category']    = str(form_data.get('store_category', '')).strip()
            app_data['store_description'] = str(form_data.get('store_description', '')).strip() or None
            if not app_data['store_name']:
                return {'success': False, 'error': 'Store name is required for sellers.'}
            if not app_data['store_category']:
                return {'success': False, 'error': 'Store category is required for sellers.'}
        elif role == 'rider':
            app_data['vehicle_type']   = str(form_data.get('vehicle_type', '')).strip() or None
            app_data['license_number'] = str(form_data.get('license_number', '')).strip()
            if not app_data['license_number']:
                return {'success': False, 'error': 'License number is required for riders.'}

        application = self.app_model.create(app_data)

        # Document uploads
        for doc_type, file in self._get_doc_map(role, files).items():
            if file:
                path = self.file_service.save_file(file, f'documents/{user["id"]}')
                if path:
                    self.supabase.table('application_documents').insert({
                        'application_id': application['id'],
                        'doc_type':       doc_type,
                        'file_path':      path
                    }).execute()

        return {'success': True, 'message': 'Registration successful! Please wait for admin approval.'}

    def get_user_profile(self, user_id):
        return self.user_model.get_by_id(user_id)

    def get_seller_category(self, user_id):
        return self.app_model.get_seller_category(user_id)

    def get_all_products(self):
        from models.product_model import ProductModel
        return ProductModel().get_all()

    def get_default_address(self, user_id):
        addresses = self.user_model.get_addresses(user_id)
        for addr in addresses:
            if addr.get('is_default'):
                return addr
        return addresses[0] if addresses else None

    def get_addresses(self, user_id):
        return self.user_model.get_addresses(user_id)

    def get_admin_stats(self):
        users    = self.supabase.table('users').select('role').execute()
        apps     = self.supabase.table('applications').select('status').execute()
        products = self.supabase.table('products').select('id').eq('status', 'active').execute()
        orders   = self.supabase.table('orders').select('id').execute()

        role_counts   = {'user': 0, 'seller': 0, 'rider': 0, 'admin': 0}
        status_counts = {'pending': 0, 'approved': 0, 'rejected': 0}

        for u in (users.data or []):
            r = u.get('role', 'user')
            if r in role_counts:
                role_counts[r] += 1

        for a in (apps.data or []):
            s = a.get('status', 'pending')
            if s in status_counts:
                status_counts[s] += 1

        return {
            'users':        role_counts,
            'applications': status_counts,
            'products':     len(products.data) if products.data else 0,
            'orders':       len(orders.data) if orders.data else 0
        }

    def _get_doc_map(self, role, files):
        if role == 'buyer':
            return {'valid_id': files.get('valid_id')}
        elif role == 'seller':
            return {
                'valid_id':        files.get('valid_id'),
                'business_permit': files.get('business_permit'),
                'dti_or_sec':      files.get('dti_or_sec')
            }
        elif role == 'rider':
            return {
                'driver_license': files.get('driver_license'),
                'valid_id':       files.get('valid_id')
            }
        return {}

    def _get_client_ip(self):
        from flask import request
        return request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'

    def _get_user_agent(self):
        from flask import request
        return request.headers.get('User-Agent', '') or ''
