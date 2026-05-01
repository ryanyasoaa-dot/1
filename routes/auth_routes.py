from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from models.user_model import UserModel
from services.auth_service import AuthService
from services.file_upload_service import FileUploadService

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()
file_service = FileUploadService()

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return _handle_registration()
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return _handle_login()
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def _handle_registration():
    try:
        result = auth_service.register_user(request.form, request.files)
        if result.get('success'):
            flash('Registration successful! Please wait for admin approval.', 'success')
            return redirect(url_for('auth.login'))
        return jsonify({'error': result.get('error', 'Registration failed')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _handle_login():
    try:
        result = auth_service.authenticate_user(
            request.form.get('email', '').strip().lower(),
            request.form.get('password', '')
        )
        if result.get('success'):
            session['user'] = result['user']
            # Redirect based on role
            role = result['user'].get('role', 'user')
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role == 'seller':
                return redirect(url_for('seller.dashboard'))
            elif role == 'buyer':
                return redirect(url_for('buyer.dashboard'))
            return redirect(url_for('index'))
        return jsonify({'error': result.get('error', 'Invalid credentials')}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route aliases for backward compatibility
register_view = register
login_view = login