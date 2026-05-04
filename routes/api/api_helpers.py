"""
Shared helpers for the Flutter-friendly JSON API.

Provides:
  * api_response()  -> uniform JSON envelope
  * api_error()     -> uniform JSON error envelope
  * get_json_body() -> safe JSON body parser (also tolerates form-data)
  * token_required / role_required decorators (token-or-session auth)
  * issue_token / decode_token helpers
  * register_api_error_handlers(app) -> JSON 400/401/403/404/405/500 handlers
"""

from __future__ import annotations

import os
import time
import hmac
import json
import base64
import hashlib
import functools
from typing import Any, Callable, Dict, Optional

from flask import jsonify, request, session, current_app


# ---------------------------------------------------------------------------
# Standard response envelope
# ---------------------------------------------------------------------------

def api_response(data: Any = None,
                 message: str = "",
                 status: int = 200,
                 success: bool = True):
    """Return the standard success envelope as a Flask response tuple."""
    body = {
        "success": bool(success),
        "data":    data if data is not None else {},
        "message": message or "",
        "error":   None,
    }
    return jsonify(body), status


def api_error(error: str = "An error occurred",
              status: int = 400,
              data: Any = None,
              message: str = ""):
    """Return the standard error envelope as a Flask response tuple."""
    body = {
        "success": False,
        "data":    data if data is not None else {},
        "message": message or "",
        "error":   error or "An error occurred",
    }
    return jsonify(body), status


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------

def get_json_body() -> Dict[str, Any]:
    """
    Safely fetch a dict from the incoming request.

    Priority:
      1. application/json body (Flutter default)
      2. multipart/form-data or x-www-form-urlencoded (compatibility)
      3. query string args (last resort)

    Always returns a dict (never None) so callers can use .get() freely.
    """
    data: Dict[str, Any] = {}
    try:
        body = request.get_json(silent=True)
        if isinstance(body, dict):
            data.update(body)
    except Exception:
        pass

    if not data and request.form:
        try:
            data.update(request.form.to_dict(flat=True))
        except Exception:
            pass

    if not data and request.args:
        try:
            data.update(request.args.to_dict(flat=True))
        except Exception:
            pass

    return data or {}


# ---------------------------------------------------------------------------
# Lightweight HMAC-signed token (no extra deps required)
# Format: base64url(payload_json).base64url(hmac_sha256)
# ---------------------------------------------------------------------------

def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _secret() -> bytes:
    secret = (current_app.secret_key
              or os.getenv("SECRET_KEY")
              or "dev-secret-change-me")
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    return secret


def issue_token(user: Dict[str, Any], ttl_seconds: int = 60 * 60 * 24 * 7) -> str:
    """Create an HMAC-signed token containing the minimal user identity."""
    payload = {
        "uid":   user.get("id"),
        "email": user.get("email"),
        "role":  user.get("role", "user"),
        "iat":   int(time.time()),
        "exp":   int(time.time()) + int(ttl_seconds),
    }
    payload_b = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(_secret(), payload_b, hashlib.sha256).digest()
    return f"{_b64u_encode(payload_b)}.{_b64u_encode(sig)}"


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate token signature + expiry and return the payload dict, or None."""
    if not token or "." not in token:
        return None
    try:
        payload_part, sig_part = token.split(".", 1)
        payload_b = _b64u_decode(payload_part)
        expected_sig = hmac.new(_secret(), payload_b, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, _b64u_decode(sig_part)):
            return None
        payload = json.loads(payload_b.decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _extract_bearer_token() -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    # Fallback: X-Auth-Token header
    xat = request.headers.get("X-Auth-Token")
    if xat:
        return xat.strip()
    return None


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Return the current authenticated user as a dict, or None.

    Resolution order:
      1. Bearer token in Authorization header (Flutter)
      2. Session cookie  (web reuse)
    """
    # 1) Token-based
    token = _extract_bearer_token()
    if token:
        payload = decode_token(token)
        if payload:
            return {
                "id":    payload.get("uid"),
                "email": payload.get("email"),
                "role":  payload.get("role", "user"),
            }

    # 2) Session-based fallback
    if session.get("user_id"):
        return {
            "id":    session.get("user_id"),
            "email": session.get("user_email"),
            "role":  session.get("user_role", "user"),
            "name":  session.get("user_name"),
        }

    return None


def token_required(fn: Callable) -> Callable:
    @functools.wraps(fn)
    def _wrap(*args, **kwargs):
        user = get_current_user()
        if not user or not user.get("id"):
            return api_error("Authentication required", status=401)
        request.current_user = user  # type: ignore[attr-defined]
        return fn(*args, **kwargs)
    return _wrap


def role_required(*roles: str) -> Callable:
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def _wrap(*args, **kwargs):
            user = get_current_user()
            if not user or not user.get("id"):
                return api_error("Authentication required", status=401)
            if roles and user.get("role") not in roles:
                return api_error("Insufficient permissions", status=403)
            request.current_user = user  # type: ignore[attr-defined]
            return fn(*args, **kwargs)
        return _wrap
    return deco


# ---------------------------------------------------------------------------
# Error handlers (registered globally; only respond JSON for /api/*)
# ---------------------------------------------------------------------------

def _is_api_request() -> bool:
    try:
        return (request.path or "").startswith("/api/")
    except Exception:
        return False


def register_api_error_handlers(app):
    """Install JSON error handlers that only kick in for /api/* paths."""

    @app.errorhandler(400)
    def _bad_request(e):
        if _is_api_request():
            return api_error(getattr(e, "description", "Bad request"), status=400)
        return e

    @app.errorhandler(401)
    def _unauthorized(e):
        if _is_api_request():
            return api_error(getattr(e, "description", "Unauthorized"), status=401)
        return e

    @app.errorhandler(403)
    def _forbidden(e):
        if _is_api_request():
            return api_error(getattr(e, "description", "Forbidden"), status=403)
        return e

    @app.errorhandler(404)
    def _not_found(e):
        if _is_api_request():
            return api_error("Resource not found", status=404)
        return e

    @app.errorhandler(405)
    def _method_not_allowed(e):
        if _is_api_request():
            return api_error("Method not allowed", status=405)
        return e

    @app.errorhandler(500)
    def _server_error(e):
        if _is_api_request():
            return api_error("Internal server error", status=500)
        return e

    @app.errorhandler(Exception)
    def _generic(e):
        # Re-raise HTTP exceptions so the dedicated handlers above run
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e
        if _is_api_request():
            try:
                current_app.logger.exception("Unhandled API error: %s", e)
            except Exception:
                pass
            return api_error("Internal server error", status=500)
        raise e


# ---------------------------------------------------------------------------
# Output normalisers — guarantee predictable Flutter-friendly fields
# ---------------------------------------------------------------------------

def _primary_image_url(product: Dict[str, Any]) -> Optional[str]:
    images = product.get("product_images") or product.get("images") or []
    if not images:
        return None
    primary = next((img for img in images if img.get("is_primary")), None)
    if not primary:
        primary = images[0]
    return primary.get("image_url") if isinstance(primary, dict) else None


def serialize_product(p: Dict[str, Any]) -> Dict[str, Any]:
    """Predictable shape: { id, name, price, stock, image, ... extras }."""
    if not p:
        return {}
    seller = p.get("seller") or {}
    seller_name = ""
    if isinstance(seller, dict):
        seller_name = (
            f"{seller.get('first_name', '')} {seller.get('last_name', '')}"
        ).strip()

    variants = p.get("product_variants") or []
    variants_out = []
    
    for v in variants:
        if not isinstance(v, dict):
            continue
            
        # Calculate variant final price after discount
        base_price = float(v.get("price") or 0)
        discount_type = v.get("discount_type", "none")
        discount_value = float(v.get("discount_value") or 0)
        
        final_price = base_price
        if discount_type == "percentage" and discount_value > 0:
            final_price = base_price * (1 - discount_value / 100)
        elif discount_type == "fixed_amount" and discount_value > 0:
            final_price = max(0, base_price - discount_value)
        
        variants_out.append({
            "id":            v.get("id"),
            "variant_type":  v.get("variant_type"),
            "value":         v.get("value"),
            "size":          v.get("size"),
            "color":         v.get("color"),
            "color_hex":     v.get("color_hex"),
            "stock":         int(v.get("stock") or 0),
            "price":         base_price,
            "final_price":   final_price,
            "discount_type": discount_type,
            "discount_value": discount_value,
            "sku":           v.get("sku"),
        })

    # Calculate product-level discount
    product_discount_type = p.get("discount_type", "none")
    product_discount_value = float(p.get("discount_value") or 0)
    
    # Compute lowest variant price (after all discounts)
    lowest_price = None
    if variants_out:
        variant_final_prices = [v["final_price"] for v in variants_out if v["final_price"] > 0]
        if variant_final_prices:
            lowest_price = min(variant_final_prices)
    
    # Apply product-level discount if no variant discounts
    if lowest_price is None:
        base_product_price = float(p.get("price") or 0)
        if product_discount_type == "percentage" and product_discount_value > 0:
            lowest_price = base_product_price * (1 - product_discount_value / 100)
        elif product_discount_type == "fixed_amount" and product_discount_value > 0:
            lowest_price = max(0, base_product_price - product_discount_value)
        else:
            lowest_price = base_product_price

    return {
        "id":          p.get("id"),
        "name":        p.get("name") or "",
        "price":       lowest_price,
        "stock":       int(p.get("total_stock") or 0),
        "image":       _primary_image_url(p),
        "category":    p.get("category") or "",
        "description": p.get("description") or "",
        "status":      p.get("status") or "",
        "seller_id":   p.get("seller_id"),
        "seller_name": seller_name,
        "variants":    variants_out,
        "discount_type": product_discount_type,
        "discount_value": product_discount_value,
        "has_discount": product_discount_type != "none" and product_discount_value > 0,
    }


def serialize_cart_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Predictable shape: { product_id, quantity, subtotal, ... extras }."""
    if not item:
        return {}
    product = item.get("product") or {}
    variant = item.get("variant") or {}

    price = item.get("price_snapshot")
    if price is None:
        price = product.get("price")
    try:
        price_val = float(price or 0)
    except (TypeError, ValueError):
        price_val = 0.0

    qty = int(item.get("quantity") or 0)
    subtotal = round(price_val * qty, 2)

    return {
        "id":           item.get("id"),
        "product_id":   item.get("product_id"),
        "product_name": product.get("name") or "",
        "image":        _primary_image_url(product) if isinstance(product, dict) else None,
        "variant_id":   item.get("variant_id"),
        "variant":      variant.get("value") if isinstance(variant, dict) else None,
        "price":        price_val,
        "quantity":     qty,
        "subtotal":     subtotal,
    }


def serialize_order(o: Dict[str, Any]) -> Dict[str, Any]:
    """Predictable shape: { order_id, status, total_price, ... extras }."""
    if not o:
        return {}
    items_raw = o.get("order_items") or o.get("items") or []
    items_out = []
    for it in items_raw:
        if not isinstance(it, dict):
            continue
        prod = it.get("product") or {}
        variant = it.get("variant") or {}
        
        # Calculate final price with discount
        unit_price = float(it.get("unit_price") or 0)
        final_price = unit_price
        
        if isinstance(variant, dict):
            discount_type = variant.get("discount_type", "none")
            discount_value = float(variant.get("discount_value") or 0)
            
            if discount_type == "percentage" and discount_value > 0:
                final_price = unit_price * (1 - discount_value / 100)
            elif discount_type == "fixed_amount" and discount_value > 0:
                final_price = max(0, unit_price - discount_value)
        
        items_out.append({
            "product_id":   it.get("product_id"),
            "product_name": prod.get("name") if isinstance(prod, dict) else "",
            "variant_id":   it.get("variant_id"),
            "variant": {
                "size": variant.get("size") if isinstance(variant, dict) else None,
                "color": variant.get("color") if isinstance(variant, dict) else None,
                "color_hex": variant.get("color_hex") if isinstance(variant, dict) else None,
                "discount_type": variant.get("discount_type") if isinstance(variant, dict) else "none",
                "discount_value": variant.get("discount_value") if isinstance(variant, dict) else 0,
            },
            "quantity":     int(it.get("quantity") or 0),
            "unit_price":   unit_price,
            "final_price":  final_price,
            "total_price":  float(it.get("total_price") or 0),
        })

    return {
        "order_id":         o.get("id"),
        "status":           o.get("status") or "pending",
        "total_price":      float(o.get("total_amount") or 0),
        "payment_method":   o.get("payment_method") or "cod",
        "shipping_address": o.get("shipping_address") or "",
        "items_count":      sum(int(i.get("quantity") or 0) for i in items_out),
        "items":            items_out,
        "created_at":       o.get("created_at"),
    }
