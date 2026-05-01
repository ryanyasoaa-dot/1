from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models.user_model import UserModel
from services.auth_service import AuthService
from services.file_upload_service import FileUploadService
from security import rate_limit, generate_csrf_token

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()
file_service = FileUploadService()

@auth_bp.route('/register', methods=['GET', 'POST'])
@rate_limit(max_calls=10, window_seconds=300)
def register():
    if request.method == 'POST':
        return _handle_registration()
    return render_template('auth/register.html', csrf_token=generate_csrf_token())

@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(max_calls=10, window_seconds=60)
def login():
    if request.method == 'POST':
        return _handle_login()
    return render_template('auth/login.html', csrf_token=generate_csrf_token())

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def _handle_registration():
    try:
        result = auth_service.register_user(request.form, request.files)
        if result.get('success'):
            return jsonify({'success': True, 'message': 'Registration successful! Please wait for admin approval.'})
        return jsonify({'error': result.get('error', 'Registration failed')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _handle_login():
    try:
        data = request.get_json() or request.form
        result = auth_service.authenticate_user(
            data.get('email', '').strip().lower(),
            data.get('password', '')
        )
        if result.get('success'):
            session['user'] = result['user']
            role = result['user'].get('role', 'user')
            if role == 'admin':
                redirect_url = url_for('admin.dashboard')
            elif role == 'seller':
                redirect_url = url_for('seller.dashboard')
            elif role == 'buyer':
                redirect_url = url_for('index')
            elif role == 'rider':
                redirect_url = url_for('rider.dashboard')
            else:
                redirect_url = url_for('index')
            return jsonify({'success': True, 'redirect': redirect_url})
        return jsonify({'error': result.get('error', 'Invalid credentials')}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route aliases for backward compatibility
register_view = register
login_view = login