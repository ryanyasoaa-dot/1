"""
Flutter-compatible JSON API package.

All routes registered under blueprints in this package live under the /api/*
URL prefix and:
  * accept JSON input (application/json)
  * return a single, standard JSON envelope:
        { "success": bool, "data": {}, "message": "", "error": null }
  * never render HTML / templates
  * are CSRF-exempt and CORS-enabled

Web routes (HTML) are NOT touched by this package.
"""

from flask import Blueprint

# A single parent blueprint that mounts all API sub-blueprints under /api
api_bp = Blueprint('api', __name__, url_prefix='/api')


def register_api(app):
    """Register the unified /api blueprint with all sub-blueprints attached."""
    # Import sub-blueprints lazily to avoid circular imports
    from routes.api.api_helpers import register_api_error_handlers
    from routes.api.auth_api import auth_api_bp
    from routes.api.products_api import products_api_bp
    from routes.api.cart_api import cart_api_bp
    from routes.api.orders_api import orders_api_bp

    api_bp.register_blueprint(auth_api_bp)
    api_bp.register_blueprint(products_api_bp)
    api_bp.register_blueprint(cart_api_bp)
    api_bp.register_blueprint(orders_api_bp)

    app.register_blueprint(api_bp)

    # JSON error handlers scoped to the API blueprint
    register_api_error_handlers(app)

    # Exempt all /api/* routes from CSRF (Flutter cannot send CSRF cookies)
    try:
        from security import csrf as _csrf  # type: ignore
        if _csrf is not None:
            _csrf.exempt(api_bp)
    except Exception:
        # If CSRF isn't using flask-wtf style, fall back to per-route exemption
        pass
