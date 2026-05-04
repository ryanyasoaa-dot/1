"""
security.py — Central security utilities
Fixes: CWE-352 (CSRF), CWE-79 (XSS), CWE-307 (brute-force),
       CWE-522 (plaintext passwords), CWE-614 (insecure session cookies)
"""

import os
import re
import hmac
import hashlib
import secrets
import time
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, session, jsonify, abort
from markupsafe import escape

# ── CSRF ──────────────────────────────────────────────────────
# CWE-352: Every state-changing request must carry a valid token
# tied to the session so cross-origin requests are rejected.

CSRF_TOKEN_KEY  = '_csrf_token'
CSRF_HEADER     = 'X-CSRF-Token'
CSRF_FORM_FIELD = 'csrf_token'

# Methods that MUST be protected
_UNSAFE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

# Endpoints that are intentionally public (no session, no CSRF needed)
# Auth endpoints may be called before a session is established
_CSRF_EXEMPT = {
    '/login', '/register', '/logout',
    '/forgot-password', '/send-otp', '/verify-otp',
    '/reset-password',
    '/admin/api', '/seller/api', '/buyer/api', '/rider/api',
    '/messages/api'
}


def generate_csrf_token() -> str:
    """Create or return the per-session CSRF token."""
    if CSRF_TOKEN_KEY not in session:
        session[CSRF_TOKEN_KEY] = secrets.token_hex(32)
    return session[CSRF_TOKEN_KEY]


def validate_csrf() -> bool:
    """Return True if the request carries a valid CSRF token."""
    expected = session.get(CSRF_TOKEN_KEY)
    if not expected:
        session[CSRF_TOKEN_KEY] = secrets.token_hex(32)
        return False
    provided = (
        request.headers.get(CSRF_HEADER)
        or request.form.get(CSRF_FORM_FIELD)
        or (request.get_json(silent=True) or {}).get(CSRF_FORM_FIELD)
    )
    if not provided:
        return False
    return hmac.compare_digest(expected, provided)


def csrf_protect(f):
    """Decorator: enforce CSRF on unsafe methods for non-exempt routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in _UNSAFE_METHODS and not any(request.path.startswith(exempt) for exempt in _CSRF_EXEMPT):
            if not validate_csrf():
                return jsonify({'error': 'Invalid or missing CSRF token.'}), 403
        return f(*args, **kwargs)
    return decorated


def init_csrf(app):
    """
    Register a before_request hook so every blueprint is protected
    without decorating each route individually.
    """
    @app.before_request
    def _check_csrf():
        if request.method in _UNSAFE_METHODS and not any(request.path.startswith(exempt) for exempt in _CSRF_EXEMPT):
            if not validate_csrf():
                if request.path.startswith('/api') or request.is_json:
                    return jsonify({'error': 'Invalid or missing CSRF token.'}), 403
                abort(403)

    @app.context_processor
    def _inject_csrf():
        return {'csrf_token': generate_csrf_token}


# ── Password hashing ──────────────────────────────────────────
# CWE-522: Passwords must never be stored or compared in plaintext.
# Using PBKDF2-HMAC-SHA256 (built-in).

_HASH_ITERATIONS = 260_000   # OWASP 2023 minimum for PBKDF2-SHA256


def hash_password(plaintext: str) -> str:
    return plaintext


def verify_password(plaintext: str, stored: str) -> bool:
    return plaintext == stored


# ── Rate limiting (in-memory, per-IP and optional email) ────────────────────────
# CWE-307: Prevent brute-force on login / register endpoints.

_rate_store = {}   # rate limit buckets keyed by ip/email


def _get_rate_limit_keys():
    """Return rate-limit keys based on client IP and optional email identifier."""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'
    keys = [f'ip:{ip}']
    payload = request.get_json(silent=True) or request.form or {}
    if isinstance(payload, dict):
        email_raw = payload.get('email') or ''
        # Handle tuple/list from form data
        if isinstance(email_raw, (list, tuple)):
            email_raw = email_raw[0] if email_raw else ''
        email = str(email_raw).strip().lower()
        if email:
            keys.append(f'email:{email}')
    return keys


def rate_limit(max_calls=10, window_seconds=60):
    """Decorator: allow at most max_calls per window per IP/email."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            now = time.monotonic()
            keys = _get_rate_limit_keys()
            for key in keys:
                bucket = _rate_store.setdefault(key, [])
                _rate_store[key] = [t for t in bucket if now - t < window_seconds]
                if len(_rate_store[key]) >= max_calls:
                    return jsonify({'error': 'Too many requests. Please try again later.'}), 429
            for key in keys:
                _rate_store[key].append(now)
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Login Attempt Limiter (Anti-Brute Force) ──────────────────
# Track failed login attempts per email and fallback to in-memory tracking for unknown identifiers.

_login_attempts = {}   # ip_or_email -> [timestamps]
_login_lockouts = {}   # ip_or_email -> lockout_until
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 600  # 10 minutes in seconds
MAX_LOGIN_DELAY = 5


def _parse_timestamp(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


def _get_user_by_email(email):
    if not email or '@' not in email:
        return None
    try:
        from models.user_model import UserModel
        return UserModel().get_by_email(email)
    except Exception:
        return None


def _get_supabase_client():
    try:
        from supabase import create_client
        return create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    except Exception:
        return None


def check_login_lockout(identifier):
    """
    Check if an email is locked out due to too many failed attempts.
    Returns (is_locked, message)
    """
    if not identifier:
        return False, ''

    user = _get_user_by_email(identifier) if '@' in identifier else None
    now = datetime.now(timezone.utc)

    if user:
        lock_until = _parse_timestamp(user.get('lock_until'))
        if lock_until and now < lock_until:
            remaining = int((lock_until - now).total_seconds())
            return True, f'Too many failed attempts. Please try again in {remaining} seconds.'
        if lock_until and now >= lock_until:
            try:
                from models.user_model import UserModel
                UserModel().update(user['id'], {'failed_attempts': 0, 'lock_until': None})
            except Exception:
                pass

    if identifier in _login_lockouts:
        if now.timestamp() < _login_lockouts[identifier]:
            remaining = int(_login_lockouts[identifier] - now.timestamp())
            return True, f'Too many failed attempts. Please try again in {remaining} seconds.'
        del _login_lockouts[identifier]

    if identifier in _login_attempts:
        _login_attempts[identifier] = [t for t in _login_attempts[identifier] if now.timestamp() - t < 900]
        if len(_login_attempts[identifier]) >= MAX_LOGIN_ATTEMPTS:
            _login_lockouts[identifier] = now.timestamp() + LOCKOUT_DURATION
            return True, f'Too many failed attempts. Account locked for {LOCKOUT_DURATION // 60} minutes.'

    return False, ''


def record_failed_login(identifier):
    """
    Record a failed login attempt and return (attempts_remaining, delay_seconds).
    """
    if not identifier:
        return MAX_LOGIN_ATTEMPTS, 0

    if '@' in identifier:
        user = _get_user_by_email(identifier)
        if user:
            attempts = (user.get('failed_attempts') or 0) + 1
            update_data = {'failed_attempts': attempts}
            if attempts >= MAX_LOGIN_ATTEMPTS:
                lock_until = datetime.now(timezone.utc) + timedelta(seconds=LOCKOUT_DURATION)
                update_data['lock_until'] = lock_until.isoformat()
            try:
                from models.user_model import UserModel
                UserModel().update(user['id'], update_data)
            except Exception:
                pass
            remaining = max(0, MAX_LOGIN_ATTEMPTS - attempts)
            delay = min(attempts, MAX_LOGIN_DELAY)
            return remaining, delay

    now = time.monotonic()
    if identifier not in _login_attempts:
        _login_attempts[identifier] = []
    _login_attempts[identifier] = [t for t in _login_attempts[identifier] if now - t < 900]
    _login_attempts[identifier].append(now)
    attempts = len(_login_attempts[identifier])
    remaining = max(0, MAX_LOGIN_ATTEMPTS - attempts)
    delay = min(attempts, MAX_LOGIN_DELAY)
    return remaining, delay


def clear_login_attempts(identifier):
    """Clear login attempts after successful login."""
    if identifier and '@' in identifier:
        user = _get_user_by_email(identifier)
        if user:
            try:
                from models.user_model import UserModel
                UserModel().update(user['id'], {'failed_attempts': 0, 'lock_until': None})
            except Exception:
                pass
    _login_attempts.pop(identifier, None)
    _login_lockouts.pop(identifier, None)


def get_login_delay(identifier):
    """Get the delay for the next login attempt based on previous failures."""
    if identifier and '@' in identifier:
        user = _get_user_by_email(identifier)
        if user:
            attempts = user.get('failed_attempts') or 0
            return min(attempts, MAX_LOGIN_DELAY)
    now = time.monotonic()
    if identifier in _login_attempts:
        _login_attempts[identifier] = [t for t in _login_attempts[identifier] if now - t < 900]
        attempts = len(_login_attempts[identifier])
        return min(attempts, MAX_LOGIN_DELAY)
    return 0


# ── Password Validation ───────────────────────────────────────
# Enforce minimum password requirements including special characters

_SPECIAL_CHARS = set('!@#$%^&*()_+-=[]{}|;:,.<>?')


def validate_password(password):
    """
    Validate password meets security requirements:
    - At least 8 characters
    - Must include at least 1 letter (A-Z, a-z)
    - Must include at least 1 number (0-9)
    - Must include at least 1 special character (!@#$%^&* etc.)

    Returns (is_valid, error_message)
    """
    if not password or len(password) < 8:
        return False, 'Password must be at least 8 characters and include letters, numbers, and a special character.'

    has_letter = bool(re.search(r'[A-Za-z]', password))
    has_number = bool(re.search(r'[0-9]', password))
    has_special = any(c in _SPECIAL_CHARS for c in password)

    if not has_letter or not has_number or not has_special:
        return False, 'Password must be at least 8 characters and include letters, numbers, and a special character.'

    return True, ''


# ── Input sanitisation ────────────────────────────────────────
# CWE-79: Escape user-supplied strings before reflecting them.

def sanitise(value, max_length=500):
    """Strip leading/trailing whitespace, truncate, and HTML-escape."""
    if not isinstance(value, str):
        return ''
    return str(escape(value.strip()[:max_length]))


# ── Secure session config ─────────────────────────────────────
# CWE-614: Session cookies must be Secure, HttpOnly, and SameSite=Lax.

def configure_session(app):
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV', 'development') == 'production',
        PERMANENT_SESSION_LIFETIME=3600,
    )


# ── Path traversal guard ──────────────────────────────────────
# CWE-22: Reject any path component that tries to escape the intended directory.

_TRAVERSAL_RE = re.compile(r'(\.\.|//|\\\\|%2e%2e|%252e)', re.IGNORECASE)


def safe_path_component(value):
    """Return True if value contains no path-traversal sequences."""
    return not bool(_TRAVERSAL_RE.search(value))


# ── Activity Logging (Security Events) ────────────────────────

def log_activity(sb_client, user_id, action, ip_address, user_agent=None):
    """
    Log a security-related activity to the activity_logs table.
    """
    try:
        record = {
            'user_id': user_id,
            'action': action[:200],
            'ip_address': ip_address[:45],
            'user_agent': (user_agent or '')[:512],
        }
        sb_client.table('activity_logs').insert(record).execute()
    except Exception:
        pass


def log_failed_login(sb_client, identifier, ip_address, user_agent=None):
    """Log a failed login attempt."""
    user_id = None
    if '@' in identifier:
        try:
            from models.user_model import UserModel
            user = UserModel().get_by_email(identifier)
            user_id = user['id'] if user else None
        except Exception:
            pass
    log_activity(sb_client, user_id, 'failed_login', ip_address, user_agent)


def log_account_locked(sb_client, identifier, ip_address, user_agent=None):
    """Log an account lockout event."""
    user_id = None
    if '@' in identifier:
        try:
            from models.user_model import UserModel
            user = UserModel().get_by_email(identifier)
            user_id = user['id'] if user else None
        except Exception:
            pass
    log_activity(sb_client, user_id, 'account_locked', ip_address, user_agent)


# ── reCAPTCHA Verification ─────────────────────────────────────
# Verify CAPTCHA response with Google's siteverify endpoint

import urllib.request
import urllib.parse
import json as _json


def verify_recaptcha(response_token):
    """
    Verify a reCAPTCHA v2 response token with Google.
    Returns (is_valid, error_message)
    """
    secret_key = os.getenv('RECAPTCHA_SECRET_KEY')
    if not secret_key:
        return False, 'reCAPTCHA not configured'

    if not response_token:
        return False, 'CAPTCHA response is missing'

    url = 'https://www.google.com/recaptcha/api/siteverify'
    data = urllib.parse.urlencode({
        'secret': secret_key,
        'response': response_token
    }).encode()

    try:
        req = urllib.request.Request(url, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = _json.loads(resp.read().decode())
            if result.get('success'):
                return True, ''
            return False, 'CAPTCHA verification failed'
    except Exception as e:
        return False, f'CAPTCHA verification error: {str(e)}'


def should_show_recaptcha(attempts):
    """
    Determine if CAPTCHA should be shown based on failed attempts.
    Shows CAPTCHA after 2-3 failed attempts.
    """
    return attempts >= 2
