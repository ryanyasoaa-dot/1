"""
/api/cart/* — buyer cart management for Flutter.

All endpoints require an authenticated buyer (Bearer token).

Endpoints:
  GET    /api/cart              -> list cart items + totals
  POST   /api/cart               -> add item   {product_id, variant_id?, quantity}
  PATCH  /api/cart/<item_id>    -> update qty {quantity}
  DELETE /api/cart/<item_id>    -> remove item
  DELETE /api/cart              -> clear cart
"""

from flask import Blueprint, request

from routes.api.api_helpers import (
    api_response, api_error, get_json_body,
    token_required, serialize_cart_item,
)

cart_api_bp = Blueprint('cart_api', __name__, url_prefix='/cart')


def _cart_payload(user_id: str):
    from models.order_model import OrderModel
    items_raw = OrderModel().get_cart_items(user_id) or []
    items = [serialize_cart_item(i) for i in items_raw]
    total = round(sum(i.get('subtotal', 0.0) for i in items), 2)
    return {
        "items":      items,
        "item_count": sum(i.get('quantity', 0) for i in items),
        "total":      total,
    }


@cart_api_bp.get('')
@cart_api_bp.get('/')
@token_required
def list_cart():
    user = request.current_user  # type: ignore[attr-defined]
    try:
        return api_response(data=_cart_payload(user['id']), message="OK", status=200)
    except Exception as e:
        return api_error(f"Failed to load cart: {e}", status=500)


@cart_api_bp.post('')
@cart_api_bp.post('/')
@token_required
def add_to_cart():
    user = request.current_user  # type: ignore[attr-defined]
    data = get_json_body()

    product_id = (data.get('product_id') or '').strip() if isinstance(data.get('product_id'), str) else data.get('product_id')
    variant_id = data.get('variant_id') or None
    try:
        quantity = int(data.get('quantity') or 1)
    except (TypeError, ValueError):
        return api_error("quantity must be an integer", status=400)

    if not product_id:
        return api_error("product_id is required", status=400)
    if quantity <= 0:
        return api_error("quantity must be greater than 0", status=400)

    try:
        from models.product_model import ProductModel
        from models.order_model import OrderModel

        product = ProductModel().get_by_id(product_id)
        if not product or product.get('status') != 'active':
            return api_error("Product not available", status=404)

        price_snapshot = float(product.get('price') or 0)
        item = OrderModel().add_or_increment_cart_item(
            user_id=user['id'],
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            price_snapshot=price_snapshot,
        )
        if not item:
            return api_error("Failed to add item to cart", status=500)

        return api_response(
            data={"cart": _cart_payload(user['id'])},
            message="Item added to cart",
            status=201,
        )
    except Exception as e:
        return api_error(f"Failed to add to cart: {e}", status=500)


@cart_api_bp.patch('/<item_id>')
@cart_api_bp.put('/<item_id>')
@token_required
def update_cart_item(item_id):
    user = request.current_user  # type: ignore[attr-defined]
    data = get_json_body()

    try:
        quantity = int(data.get('quantity'))
    except (TypeError, ValueError):
        return api_error("quantity must be an integer", status=400)

    if quantity <= 0:
        return api_error("quantity must be greater than 0", status=400)

    try:
        from models.order_model import OrderModel
        updated = OrderModel().update_cart_item_qty(user['id'], item_id, quantity)
        if not updated:
            return api_error("Cart item not found", status=404)
        return api_response(
            data={"cart": _cart_payload(user['id'])},
            message="Cart updated",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to update cart: {e}", status=500)


@cart_api_bp.delete('/<item_id>')
@token_required
def delete_cart_item(item_id):
    user = request.current_user  # type: ignore[attr-defined]
    try:
        from models.order_model import OrderModel
        OrderModel().remove_cart_item(user['id'], item_id)
        return api_response(
            data={"cart": _cart_payload(user['id'])},
            message="Item removed",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to remove item: {e}", status=500)


@cart_api_bp.delete('')
@cart_api_bp.delete('/')
@token_required
def clear_cart():
    user = request.current_user  # type: ignore[attr-defined]
    try:
        from models.order_model import OrderModel
        OrderModel().clear_cart(user['id'])
        return api_response(data=_cart_payload(user['id']), message="Cart cleared", status=200)
    except Exception as e:
        return api_error(f"Failed to clear cart: {e}", status=500)
