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
_CSRF_EXEMPT = {'/login', '/register', '/logout'}


def generate_csrf_token() -> str:
    """Create or return the per-session CSRF token."""
    if CSRF_TOKEN_KEY not in session:
        session[CSRF_TOKEN_KEY] = secrets.token_hex(32)
    return session[CSRF_TOKEN_KEY]


def validate_csrf() -> bool:
    """Return True if the request carries a valid CSRF token."""
    expected = session.get(CSRF_TOKEN_KEY)
    if not expected:
        return False
    # Accept token from header (AJAX) or form field
    provided = (
        request.headers.get(CSRF_HEADER)
        or request.form.get(CSRF_FORM_FIELD)
        or (request.get_json(silent=True) or {}).get(CSRF_FORM_FIELD)
    )
    if not provided:
        return False
    # Constant-time comparison prevents timing attacks
    return hmac.compare_digest(expected, provided)


def csrf_protect(f):
    """Decorator: enforce CSRF on unsafe methods for non-exempt routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in _UNSAFE_METHODS and request.path not in _CSRF_EXEMPT:
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
        if request.method in _UNSAFE_METHODS and request.path not in _CSRF_EXEMPT:
            if not validate_csrf():
                # Return JSON for API paths, abort 403 for page paths
                if request.path.startswith('/api') or request.is_json:
                    return jsonify({'error': 'Invalid or missing CSRF token.'}), 403
                abort(403)

    @app.context_processor
    def _inject_csrf():
        """Make csrf_token() available in every Jinja template."""
        return {'csrf_token': generate_csrf_token}


# ── Password hashing ──────────────────────────────────────────
# CWE-522: Passwords must never be stored or compared in plaintext.
# Using PBKDF2-HMAC-SHA256 (built-in, no extra deps).

_HASH_ITERATIONS = 260_000   # OWASP 2023 minimum for PBKDF2-SHA256


def hash_password(plaintext: str) -> str:
    salt = secrets.token_hex(16)
    dk   = hashlib.pbkdf2_hmac('sha256', plaintext.encode(), salt.encode(), _HASH_ITERATIONS)
    return f'pbkdf2:{salt}:{dk.hex()}'


def verify_password(plaintext: str, stored: str) -> bool:
    """Return True if plaintext matches the stored hash.
    Also accepts legacy plaintext passwords so existing accounts keep working
    until they next log in (at which point the hash is upgraded).
    """
    if not stored:
        return False
    if stored.startswith('pbkdf2:'):
        try:
            _, salt, dk_hex = stored.split(':', 2)
            dk = hashlib.pbkdf2_hmac('sha256', plaintext.encode(), salt.encode(), _HASH_ITERATIONS)
            return hmac.compare_digest(dk.hex(), dk_hex)
        except ValueError:
            return False
    # Legacy plaintext fallback (remove after all users have re-logged in)
    return hmac.compare_digest(plaintext, stored)


# ── Rate limiting (in-memory, per-IP) ────────────────────────
# CWE-307: Prevent brute-force on login / register endpoints.

_rate_store: dict[str, list[float]] = {}   # ip -> [timestamp, ...]

def rate_limit(max_calls: int = 10, window_seconds: int = 60):
    """Decorator: allow at most max_calls per window per IP."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            ip  = request.remote_addr or 'unknown'
            now = time.monotonic()
            bucket = _rate_store.setdefault(ip, [])
            # Evict old entries
            _rate_store[ip] = [t for t in bucket if now - t < window_seconds]
            if len(_rate_store[ip]) >= max_calls:
                return jsonify({'error': 'Too many requests. Please try again later.'}), 429
            _rate_store[ip].append(now)
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Input sanitisation ────────────────────────────────────────
# CWE-79: Escape user-supplied strings before reflecting them.

def sanitise(value: str, max_length: int = 500) -> str:
    """Strip leading/trailing whitespace, truncate, and HTML-escape."""
    if not isinstance(value, str):
        return ''
    return str(escape(value.strip()[:max_length]))


# ── Secure session config ─────────────────────────────────────
# CWE-614: Session cookies must be Secure, HttpOnly, and SameSite=Lax.

def configure_session(app):
    app.config.update(
        SESSION_COOKIE_HTTPONLY = True,
        SESSION_COOKIE_SAMESITE = 'Lax',
        # Set Secure=True in production (requires HTTPS)
        SESSION_COOKIE_SECURE   = os.getenv('FLASK_ENV', 'development') == 'production',
        PERMANENT_SESSION_LIFETIME = 3600,   # 1 hour
    )


# ── Path traversal guard ──────────────────────────────────────
# CWE-22: Reject any path component that tries to escape the intended directory.

_TRAVERSAL_RE = re.compile(r'(\.\.|//|\\\\|%2e%2e|%252e)', re.IGNORECASE)

def safe_path_component(value: str) -> bool:
    """Return True if value contains no path-traversal sequences."""
    return not bool(_TRAVERSAL_RE.search(value))
