"""
/api/auth/* — Flutter-friendly authentication.

Endpoints:
  POST /api/auth/login         -> issue token + return user
  POST /api/auth/register      -> create buyer account (JSON, no file uploads)
  POST /api/auth/logout        -> stateless OK (client just drops token)
  GET  /api/auth/me            -> current authenticated user
"""

from flask import Blueprint, session

from routes.api.api_helpers import (
    api_response, api_error, get_json_body,
    token_required, get_current_user, issue_token,
)

auth_api_bp = Blueprint('auth_api', __name__, url_prefix='/auth')


@auth_api_bp.post('/login')
def api_login():
    data = get_json_body()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return api_error("Email and password are required", status=400)

    from services.auth_service import AuthService
    try:
        result = AuthService().authenticate_user(email, password)
    except Exception as e:
        return api_error(f"Login failed: {e}", status=500)

    if not result.get('success'):
        return api_error(result.get('error') or "Invalid credentials", status=401)

    user = result.get('user') or {}

    # Mirror to session so the same backend can serve the web UI seamlessly
    try:
        session.clear()
        session['user_id']    = user.get('id')
        session['user_email'] = user.get('email')
        session['user_role']  = user.get('role', 'user')
        session['user_name']  = user.get('name', '')
    except Exception:
        pass

    token = issue_token(user)

    return api_response(
        data={"token": token, "user": user},
        message="Login successful",
        status=200,
    )


@auth_api_bp.post('/register')
def api_register():
    """
    Flutter-friendly registration (buyer only, JSON-only, no document uploads).

    For seller/rider applications that require document files, the existing
    web flow at /register should still be used.
    """
    data = get_json_body()
    required = ['first_name', 'last_name', 'email', 'password', 'phone', 'gender']
    missing = [k for k in required if not (data.get(k) or '').strip() if isinstance(data.get(k), str)]
    # Also catch missing keys entirely
    missing += [k for k in required if k not in data]
    missing = sorted(set(missing))
    if missing:
        return api_error(
            f"Missing required fields: {', '.join(missing)}",
            status=400,
            data={"missing": missing},
        )

    # Force role=buyer over the API; seller/rider need the document flow.
    payload = dict(data)
    payload['role'] = 'buyer'

    from services.auth_service import AuthService
    try:
        result = AuthService().register_user(payload, files={})
    except Exception as e:
        return api_error(f"Registration failed: {e}", status=500)

    if not result.get('success'):
        return api_error(result.get('error') or "Registration failed", status=400)

    return api_response(
        data={},
        message=result.get('message') or "Registration successful",
        status=201,
    )


@auth_api_bp.post('/logout')
def api_logout():
    # Stateless: client drops the token. Also clear server session if present.
    try:
        session.clear()
    except Exception:
        pass
    return api_response(message="Logged out", status=200)


@auth_api_bp.get('/me')
@token_required
def api_me():
    user = get_current_user() or {}
    # Best-effort enrichment (profile picture, full name, etc.)
    try:
        from models.user_model import UserModel
        full = UserModel().get_by_id(user.get('id'))
        if full:
            user = {
                "id":              full.get('id'),
                "email":           full.get('email'),
                "first_name":      full.get('first_name'),
                "last_name":       full.get('last_name'),
                "phone":           full.get('phone'),
                "role":            full.get('role', 'user'),
                "profile_picture": full.get('profile_picture'),
                "name": (
                    f"{full.get('first_name', '')} {full.get('last_name', '')}"
                ).strip(),
            }
    except Exception:
        pass
    return api_response(data={"user": user}, message="OK", status=200)
