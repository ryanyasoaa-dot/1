from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models.user_model import UserModel
from services.auth_service import AuthService
from services.file_upload_service import FileUploadService
from security import rate_limit, generate_csrf_token, validate_password, check_login_lockout, record_failed_login, clear_login_attempts, get_login_delay
import os
import time

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

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@rate_limit(max_calls=5, window_seconds=300)
def forgot_password():
    if request.method == 'GET':
        return render_template('auth/forgot_password.html', csrf_token=generate_csrf_token())

    data  = request.get_json() or request.form
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user_model = UserModel()
    user = user_model.get_by_email(email)
    # Always return success to prevent email enumeration
    if not user:
        return jsonify({'success': True, 'message': 'If that email exists, a reset link has been sent.'})

    import uuid, secrets
    from datetime import datetime, timezone, timedelta
    from supabase import create_client
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    token      = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    sb.table('password_reset_tokens').insert({
        'user_id':    user['id'],
        'token':      token,
        'expires_at': expires_at
    }).execute()

    reset_url = request.host_url.rstrip('/') + url_for('auth.reset_password', token=token)
    try:
        from services.email_service import send_password_reset
        sent = send_password_reset(
            to_email=email,
            name=f"{user.get('first_name','')} {user.get('last_name','')}".strip() or 'User',
            reset_url=reset_url
        )
        if not sent:
            print(f'Password reset email failed to send to {email}')
    except Exception as e:
        import traceback
        print(f'Password reset email error: {e}')
        traceback.print_exc()

    return jsonify({'success': True, 'message': 'If that email exists, a reset link has been sent.'})


@auth_bp.route('/send-otp', methods=['POST'])
@rate_limit(max_calls=5, window_seconds=60)
def send_otp():
    data = request.get_json() or request.form
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    import secrets
    from datetime import datetime, timezone, timedelta
    from supabase import create_client
    
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    
    otp = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    
    sb.table('email_otps').upsert({
        'email': email,
        'otp': otp,
        'expires_at': expires_at
    }).execute()
    
    from services.email_service import send_otp_email
    sent = send_otp_email(email, 'User', otp)
    
    if sent:
        return jsonify({'success': True, 'message': 'OTP sent to your email'})
    return jsonify({'error': 'Failed to send OTP'}), 500


@auth_bp.route('/verify-otp', methods=['POST'])
@rate_limit(max_calls=5, window_seconds=60)
def verify_otp():
    data = request.get_json() or request.form
    email = (data.get('email') or '').strip().lower()
    otp = (data.get('otp') or '').strip()
    
    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400
    
    from datetime import datetime, timezone
    from supabase import create_client
    
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    
    row = sb.table('email_otps').select('*').eq('email', email).eq('otp', otp).execute()
    
    if not row.data:
        return jsonify({'error': 'Invalid OTP'}), 400
    
    record = row.data[0]
    expires_at = datetime.fromisoformat(record['expires_at'].replace('Z', '+00:00'))
    
    if datetime.now(timezone.utc) > expires_at:
        return jsonify({'error': 'OTP has expired'}), 400
    
    sb.table('email_otps').delete().eq('email', email).execute()
    
    return jsonify({'success': True, 'message': 'Email verified successfully'})


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    from supabase import create_client
    from datetime import datetime, timezone
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    # Validate token
    row = sb.table('password_reset_tokens').select('*').eq('token', token).eq('used', False).limit(1).execute()
    if not row.data:
        return render_template('auth/reset_password.html', token=token, error='This reset link is invalid or has already been used.', csrf_token=generate_csrf_token())

    record = row.data[0]
    expires_at = datetime.fromisoformat(record['expires_at'].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        return render_template('auth/reset_password.html', token=token, error='This reset link has expired. Please request a new one.', csrf_token=generate_csrf_token())

    if request.method == 'GET':
        return render_template('auth/reset_password.html', token=token, error=None, csrf_token=generate_csrf_token())

    data         = request.get_json() or request.form
    new_password = (data.get('password') or '').strip()
    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    from security import hash_password
    user_model = UserModel()
    user_model.update(record['user_id'], {'password': hash_password(new_password)})
    sb.table('password_reset_tokens').update({'used': True}).eq('token', token).execute()

    return jsonify({'success': True, 'message': 'Password reset successfully. You can now log in.'})

def _handle_registration():
    try:
        if request.form.get('otp_verified') != 'true':
            return jsonify({'error': 'Email must be verified with OTP first'}), 400
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
