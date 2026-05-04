from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models.order_model import OrderModel
from models.product_model import ProductModel
from models.user_model import UserModel
from models.notification_model import NotificationModel
from models.review_model import ReviewModel
from services.auth_service import AuthService
from services.order_service import OrderService
from routes.api.api_helpers import api_response, api_error, serialize_product, serialize_cart_item, serialize_order

buyer_bp = Blueprint('buyer', __name__)
order_model = OrderModel()
product_model = ProductModel()
user_model = UserModel()
notification_model = NotificationModel()
review_model = ReviewModel()
auth_service = AuthService()
order_service = OrderService()

def buyer_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        if session['user'].get('role') not in ('buyer', 'seller', 'admin', 'rider'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@buyer_bp.route('/')
@buyer_required
def dashboard():
    buyer_id = session['user']['id']
    stats = order_service.get_buyer_stats(buyer_id)
    return render_template('buyer/dashboard.html', stats=stats)

# Route functions

@buyer_bp.route('/market')
def market():
    return render_template('buyer/market.html')

@buyer_bp.route('/product')
@buyer_required
def product():
    return render_template('buyer/product.html')

@buyer_bp.route('/api/products', methods=['GET'])
def api_buyer_products():
    try:
        category  = request.args.get('category', '').strip()
        search    = request.args.get('search', '').strip().lower()
        min_price = request.args.get('min_price', '').strip()
        max_price = request.args.get('max_price', '').strip()
        sort      = request.args.get('sort', '').strip()

        products = product_model.get_all_active(category=category or None)

        if search:
            products = [p for p in products if search in (p.get('name', '') + ' ' + (p.get('description') or '')).lower()]
        if min_price:
            try:
                products = [p for p in products if float(p.get('price', 0) or 0) >= float(min_price)]
            except ValueError:
                pass
        if max_price:
            try:
                products = [p for p in products if float(p.get('price', 0) or 0) <= float(max_price)]
            except ValueError:
                pass
        if sort == 'price_asc':
            products.sort(key=lambda p: float(p.get('price', 0) or 0))
        elif sort == 'price_desc':
            products.sort(key=lambda p: float(p.get('price', 0) or 0), reverse=True)

        items = [serialize_product(p) for p in products]
        return api_response(
            data={"products": items, "count": len(items)},
            message="OK",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to fetch products: {e}", status=500)

@buyer_bp.route('/api/products/<product_id>', methods=['GET'])
def api_buyer_product_detail(product_id):
    try:
        product = product_model.get_by_id(product_id)
        if not product or product.get('status') != 'active':
            return api_error("Product not found", status=404)
        return api_response(
            data={"product": serialize_product(product)},
            message="OK",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to fetch product: {e}", status=500)

@buyer_bp.route('/cart')
@buyer_required
def cart():
    buyer_id = session['user']['id']
    cart_items = order_service.get_cart(buyer_id)
    return render_template('buyer/cart.html', cart_items=cart_items)

@buyer_bp.route('/checkout')
@buyer_required
def checkout():
    buyer_id = session['user']['id']
    address = auth_service.get_default_address(buyer_id)
    return render_template('buyer/checkout.html', address=address)

@buyer_bp.route('/orders')
@buyer_required
def orders():
    return render_template('buyer/orders.html')

@buyer_bp.route('/address_book')
@buyer_required
def address_book():
    return render_template('buyer/address_book.html')

@buyer_bp.route('/order_summary')
@buyer_required
def order_summary():
    return render_template('buyer/order_summary.html')

@buyer_bp.route('/notifications')
@buyer_required
def notifications():
    return render_template('buyer/notifications.html')

@buyer_bp.route('/wishlist')
@buyer_required
def wishlist():
    return redirect(url_for('buyer.orders') + '#wishlist')

@buyer_bp.route('/api/notifications/unread-count', methods=['GET'])
@buyer_required
def api_notifications_unread_count():
    """Get the count of unread notifications for the current user."""
    try:
        user_id = session['user']['id']
        count = notification_model.get_unread_count(user_id)
        return api_response(
            data={"count": count},
            message="OK",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to get unread count: {e}", status=500)

@buyer_bp.route('/api/notifications', methods=['GET'])
@buyer_required
def api_notifications():
    """Get notifications for the current user."""
    try:
        user_id = session['user']['id']
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))
        notifications = notification_model.get_all(user_id, limit=limit, unread_only=unread_only)
        return api_response(
            data={"notifications": notifications, "count": len(notifications or [])},
            message="OK",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to fetch notifications: {e}", status=500)

@buyer_bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
@buyer_required
def api_mark_notification_as_read(notification_id):
    """Mark a specific notification as read."""
    try:
        user_id = session['user']['id']
        success = notification_model.mark_as_read(notification_id, user_id)
        if success:
            return api_response(
                data={},
                message="Notification marked as read",
                status=200,
            )
        return api_error("Notification not found", status=404)
    except Exception as e:
        return api_error(f"Failed to mark notification as read: {e}", status=500)

@buyer_bp.route('/api/notifications/read-all', methods=['POST'])
@buyer_required
def api_mark_all_as_read():
    """Mark all notifications as read for the current user."""
    try:
        user_id = session['user']['id']
        count = notification_model.mark_all_as_read(user_id)
        return api_response(
            data={"marked_count": count},
            message=f"Marked {count} notifications as read",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to mark all notifications as read: {e}", status=500)

@buyer_bp.route('/api/cart', methods=['GET', 'POST'])
@buyer_required
def api_cart():
    user_id = session['user']['id']
    if request.method == 'GET':
        try:
            items = order_model.get_cart_items(user_id)
            serialized_items = [serialize_cart_item(item) for item in items]
            total = round(sum(item.get('subtotal', 0.0) for item in serialized_items), 2)
            return api_response(
                data={
                    "items": serialized_items,
                    "item_count": sum(item.get('quantity', 0) for item in serialized_items),
                    "total": total,
                },
                message="OK",
                status=200,
            )
        except Exception as e:
            return api_error(f"Failed to fetch cart: {e}", status=500)

    # POST — add to cart with comprehensive stock validation
    try:
        data       = request.get_json() or {}
        product_id = data.get('product_id')
        variant_id = data.get('variant_id')
        quantity   = int(data.get('quantity', 1) or 1)

        if quantity <= 0:
            return api_error("Quantity must be at least 1", status=400)

        product = product_model.get_by_id(product_id)
        if not product or product.get('status') != 'active':
            return api_error("Product not available", status=400)

        # Determine available stock (variant-level if variant selected, else product total)
        if variant_id:
            variant = next((v for v in (product.get('product_variants') or []) if v['id'] == variant_id), None)
            if not variant:
                return api_error("Selected variant not found", status=400)
            available = int(variant.get('stock') or 0)
            variant_name = f"{variant.get('variant_type', '')}: {variant.get('value', '')}"
        else:
            available = int(product.get('total_stock') or 0)
            variant_name = ""

        if available <= 0:
            return api_error(f'This product{(" (" + variant_name + ")" if variant_name else "")} is out of stock', status=400)

        # Check how many the buyer already has in cart
        existing = order_model.find_cart_item(user_id, product_id, variant_id)
        already_in_cart = int((existing or {}).get('quantity') or 0)
        requested_total = already_in_cart + quantity

        if requested_total > available:
            allowed = available - already_in_cart
            if allowed <= 0:
                return api_error(f'Maximum stock reached. You already have {already_in_cart} in your cart (available: {available})', status=400)
            return api_error(f'Only {allowed} more unit(s) available (total stock: {available})', status=400)

        price_snapshot = float(product.get('price', 0) or 0)
        item = order_model.add_or_increment_cart_item(user_id, product_id, variant_id, quantity, price_snapshot)
        if item:
            # Return updated cart
            cart_items = order_model.get_cart_items(user_id)
            serialized_items = [serialize_cart_item(cart_item) for cart_item in cart_items]
            total = round(sum(cart_item.get('subtotal', 0.0) for cart_item in serialized_items), 2)
            return api_response(
                data={
                    "items": serialized_items,
                    "item_count": sum(cart_item.get('quantity', 0) for cart_item in serialized_items),
                    "total": total,
                },
                message=f'Added {quantity} item(s) to cart',
                status=201,
            )
        return api_error("Failed to add item to cart", status=500)
    except Exception as e:
        return api_error(f"Failed to add to cart: {e}", status=500)

@buyer_bp.route('/api/cart/<item_id>', methods=['PUT', 'DELETE'])
@buyer_required
def api_cart_item(item_id):
    user_id = session['user']['id']
    if request.method == 'PUT':
        try:
            data     = request.get_json() or {}
            quantity = int(data.get('quantity', 1) or 1)
            if quantity <= 0:
                order_model.remove_cart_item(user_id, item_id)
                # Return updated cart
                cart_items = order_model.get_cart_items(user_id)
                serialized_items = [serialize_cart_item(cart_item) for cart_item in cart_items]
                total = round(sum(cart_item.get('subtotal', 0.0) for cart_item in serialized_items), 2)
                return api_response(
                    data={
                        "items": serialized_items,
                        "item_count": sum(cart_item.get('quantity', 0) for cart_item in serialized_items),
                        "total": total,
                    },
                    message="Item removed from cart",
                    status=200,
                )

            # Validate new quantity against available stock
            cart_items = order_model.get_cart_items(user_id)
            target = next((i for i in cart_items if i['id'] == item_id), None)
            if target:
                product = target.get('product') or {}
                variant_id = target.get('variant_id')
                if variant_id:
                    variant   = next((v for v in (product.get('product_variants') or []) if v['id'] == variant_id), None)
                    available = int((variant or {}).get('stock') or 0)
                else:
                    available = int(product.get('total_stock') or 0)
                if quantity > available:
                    return api_error(f'Only {available} unit(s) available in stock', status=400)

            updated = order_model.update_cart_item_qty(user_id, item_id, quantity)
            if updated:
                # Return updated cart
                cart_items = order_model.get_cart_items(user_id)
                serialized_items = [serialize_cart_item(cart_item) for cart_item in cart_items]
                total = round(sum(cart_item.get('subtotal', 0.0) for cart_item in serialized_items), 2)
                return api_response(
                    data={
                        "items": serialized_items,
                        "item_count": sum(cart_item.get('quantity', 0) for cart_item in serialized_items),
                        "total": total,
                    },
                    message="Cart updated",
                    status=200,
                )
            return api_error("Cart item not found", status=404)
        except Exception as e:
            return api_error(f"Failed to update cart item: {e}", status=500)
    
    # DELETE method
    try:
        order_model.remove_cart_item(user_id, item_id)
        # Return updated cart
        cart_items = order_model.get_cart_items(user_id)
        serialized_items = [serialize_cart_item(cart_item) for cart_item in cart_items]
        total = round(sum(cart_item.get('subtotal', 0.0) for cart_item in serialized_items), 2)
        return api_response(
            data={
                "items": serialized_items,
                "item_count": sum(cart_item.get('quantity', 0) for cart_item in serialized_items),
                "total": total,
            },
            message="Item removed from cart",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to remove cart item: {e}", status=500)

@buyer_bp.route('/api/checkout', methods=['POST'])
@buyer_required
def api_checkout():
    try:
        user_id = session['user']['id']
        data = request.get_json() or {}
        address_id = data.get('address_id')
        payment_method = data.get('payment_method', 'cod')
        if payment_method not in ('cod', 'card', 'bank_transfer', 'gcash'):
            payment_method = 'cod'

        address = user_model.get_address_by_id(user_id, address_id)
        if not address:
            return api_error('Invalid delivery address', status=400)

        cart_items = order_model.get_cart_items(user_id)
        if not cart_items:
            return api_error('Your cart is empty', status=400)

        # Validate stock availability for all items before proceeding
        for ci in cart_items:
            product = ci.get('product') or {}
            if product.get('status') != 'active':
                return api_error(f'Product "{product.get("name", "Unknown")}" is no longer available', status=400)
            
            qty = int(ci.get('quantity', 0) or 0)
            variant_id = ci.get('variant_id')
            product_id = ci.get('product_id')
            
            # Check current stock availability
            if not order_model._check_stock_availability(product_id, variant_id, qty):
                product_name = product.get('name', 'Unknown product')
                return api_error(f'Insufficient stock for "{product_name}". Please update your cart and try again.', status=400)

        order_items = []
        total_amount = 0.0
        for ci in cart_items:
            product = ci.get('product') or {}
            qty = int(ci.get('quantity', 0) or 0)
            unit_price = float(ci.get('price_snapshot', 0) or 0)
            line_total = unit_price * qty
            total_amount += line_total
            order_items.append({
                'product_id': ci.get('product_id'),
                'variant_id': ci.get('variant_id'),
                'quantity': qty,
                'unit_price': unit_price,
                'total_price': line_total
            })

        order = order_model.create({
            'buyer_id': user_id,
            'total_amount': total_amount,
            'shipping_address': address,
            'status': 'pending',
            'payment_method': 'bank_transfer' if payment_method == 'gcash' else payment_method
        }, order_items)

        order_model.clear_cart(user_id)

        # Send order confirmation email (non-blocking)
        try:
            from services.email_service import send_order_confirmation
            buyer = user_model.get_by_id(user_id)
            if buyer and buyer.get('email'):
                full_order = order_model.get_by_id(order.get('id'))
                items_data = (full_order or {}).get('order_items') or order_items
                send_order_confirmation(
                    to_email=buyer['email'],
                    buyer_name=f"{buyer.get('first_name','')} {buyer.get('last_name','')}".strip(),
                    order=full_order or order,
                    items=items_data
                )
        except Exception as mail_err:
            print(f'Order email error: {mail_err}')

        return api_response(
            data={"order": serialize_order(order_model.get_by_id(order.get('id')))} ,
            message='Order placed successfully! Stock has been reserved.',
            status=201,
        )
    except Exception as e:
        return api_error(f'Failed to create order: {str(e)}', status=500)

@buyer_bp.route('/api/orders', methods=['GET', 'POST'])
@buyer_required
def api_orders():
    user_id = session['user']['id']
    if request.method == 'GET':
        try:
            orders = order_model.get_by_buyer(user_id)
            items = [serialize_order(o) for o in (orders or [])]
            return api_response(
                data={"orders": items, "count": len(items)},
                message="OK",
                status=200,
            )
        except Exception as e:
            return api_error(f"Failed to fetch orders: {e}", status=500)
    # Backward-compatible alias: POST /api/orders -> checkout
    return api_checkout()

@buyer_bp.route('/api/orders/<order_id>', methods=['GET'])
@buyer_required
def api_order_detail(order_id):
    try:
        user_id = session['user']['id']
        order = order_model.get_by_id(order_id)
        if not order or order.get('buyer_id') != user_id:
            return api_error("Order not found", status=404)
        return api_response(
            data={"order": serialize_order(order)},
            message="OK",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to fetch order: {e}", status=500)

@buyer_bp.route('/api/orders/<order_id>/cancel', methods=['POST'])
@buyer_required
def api_cancel_order(order_id):
    """Cancel an order and restore stock"""
    try:
        user_id = session['user']['id']
        cancelled_order = order_model.cancel_order(order_id, user_id)
        if cancelled_order:
            return api_response(
                data={"order": serialize_order(cancelled_order)},
                message="Order cancelled successfully. Stock has been restored.",
                status=200,
            )
        else:
            return api_error("Order cannot be cancelled. It may not exist, not belong to you, or already be in progress.", status=400)
    except Exception as e:
        return api_error(f"Failed to cancel order: {str(e)}", status=500)

@buyer_bp.route('/api/addresses', methods=['GET'])
@buyer_required
def api_addresses():
    try:
        user_id = session['user']['id']
        addresses = user_model.get_addresses(user_id)
        return api_response(
            data={"addresses": addresses or [], "count": len(addresses or [])},
            message="OK",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to fetch addresses: {e}", status=500)

@buyer_bp.route('/api/addresses', methods=['POST'])
@buyer_required
def api_create_address():
    try:
        user_id = session['user']['id']
        data = request.get_json() or {}
        
        # Validate required fields
        required_fields = ['label', 'region', 'city', 'barangay', 'street', 'zip_code']
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return api_error(f"Missing required fields: {', '.join(missing)}", status=400)
        
        # Prepare address data
        address_data = {
            'user_id': user_id,
            'label': data['label'],
            'region': data['region'],
            'city': data['city'],
            'barangay': data['barangay'],
            'street': data['street'],
            'zip_code': data['zip_code'],
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude')
        }
        
        # Check if this is the first address (make it default)
        addresses = user_model.get_addresses(user_id)
        if len(addresses) == 0:
            address_data['is_default'] = True
        
        address = user_model.create_address(address_data)
        if address:
            return api_response(
                data={"address": address},
                message="Address created successfully",
                status=201,
            )
        else:
            return api_error("Failed to create address", status=500)
    except Exception as e:
        return api_error(f"Failed to create address: {e}", status=500)

@buyer_bp.route('/api/addresses/<address_id>', methods=['PUT'])
@buyer_required
def api_update_address(address_id):
    try:
        user_id = session['user']['id']
        data = request.get_json() or {}
        
        # Verify address belongs to user
        address = user_model.get_address_by_id(user_id, address_id)
        if not address:
            return api_error("Address not found", status=404)
        
        # Update address fields
        update_data = {}
        if 'label' in data:
            update_data['label'] = data['label']
        if 'region' in data:
            update_data['region'] = data['region']
        if 'city' in data:
            update_data['city'] = data['city']
        if 'barangay' in data:
            update_data['barangay'] = data['barangay']
        if 'street' in data:
            update_data['street'] = data['street']
        if 'zip_code' in data:
            update_data['zip_code'] = data['zip_code']
        if 'latitude' in data:
            update_data['latitude'] = data['latitude']
        if 'longitude' in data:
            update_data['longitude'] = data['longitude']
        
        if not update_data:
            return api_error("No fields to update", status=400)
        
        updated_address = user_model.update_address(user_id, address_id, update_data)
        if updated_address:
            return api_response(
                data={"address": updated_address},
                message="Address updated successfully",
                status=200,
            )
        else:
            return api_error("Failed to update address", status=500)
    except Exception as e:
        return api_error(f"Failed to update address: {e}", status=500)

@buyer_bp.route('/api/addresses/<address_id>', methods=['DELETE'])
@buyer_required
def api_delete_address(address_id):
    try:
        user_id = session['user']['id']
        
        # Verify address belongs to user
        address = user_model.get_address_by_id(user_id, address_id)
        if not address:
            return api_error("Address not found", status=404)
        
        # Don't allow deletion of default address without setting another as default
        if address.get('is_default'):
            addresses = user_model.get_addresses(user_id)
            if len(addresses) <= 1:
                return api_error("Cannot delete the only address. Please add another address first.", status=400)
        
        success = user_model.delete_address(user_id, address_id)
        if success:
            # If deleted address was default, set another as default
            if address.get('is_default'):
                addresses = user_model.get_addresses(user_id)
                if addresses:
                    user_model.update_address(user_id, addresses[0]['id'], {'is_default': True})
            return api_response(
                data={},
                message="Address deleted successfully",
                status=200,
            )
        else:
            return api_error("Failed to delete address", status=500)
    except Exception as e:
        return api_error(f"Failed to delete address: {e}", status=500)

@buyer_bp.route('/api/addresses/<address_id>/default', methods=['POST'])
@buyer_required
def api_set_default_address(address_id):
    try:
        user_id = session['user']['id']
        
        # Verify address belongs to user
        address = user_model.get_address_by_id(user_id, address_id)
        if not address:
            return api_error("Address not found", status=404)
        
        # Remove default flag from all addresses
        addresses = user_model.get_addresses(user_id)
        for addr in addresses:
            if addr['id'] != address_id:
                user_model.update_address(user_id, addr['id'], {'is_default': False})
        
        # Set this address as default
        updated_address = user_model.update_address(user_id, address_id, {'is_default': True})
        if updated_address:
            return api_response(
                data={"address": updated_address},
                message="Default address set successfully",
                status=200,
            )
        else:
            return api_error("Failed to set default address", status=500)
    except Exception as e:
        return api_error(f"Failed to set default address: {e}", status=500)

@buyer_bp.route('/api/profile', methods=['PUT'])
@buyer_required
def api_update_profile():
    try:
        user_id = session['user']['id']
        data = request.get_json() or {}
        from security import sanitise

        update_data = {}
        if 'full_name' in data:
            full_name   = sanitise(data['full_name'], 100)
            name_parts  = full_name.strip().split(' ', 1)
            update_data['first_name'] = name_parts[0]
            update_data['last_name']  = name_parts[1] if len(name_parts) > 1 else ''
        if 'phone' in data:
            update_data['phone'] = sanitise(data['phone'], 20)

        if not update_data:
            return api_error("No fields to update", status=400)

        updated_user = user_model.update(user_id, update_data)
        if updated_user:
            session['user'].update({
                'first_name': updated_user.get('first_name'),
                'last_name':  updated_user.get('last_name'),
                'phone':      updated_user.get('phone')
            })
            session['user']['name'] = f"{updated_user.get('first_name', '')} {updated_user.get('last_name', '')}".strip()
            return api_response(
                data={"user": updated_user},
                message="Profile updated successfully",
                status=200,
            )
        return api_error("Failed to update profile", status=500)
    except Exception as e:
        return api_error(f"Failed to update profile: {e}", status=500)

@buyer_bp.route('/api/password', methods=['PUT'])
@buyer_required
def api_change_password():
    try:
        user_id = session['user']['id']
        data = request.get_json() or {}
        from security import validate_password, verify_password, hash_password

        current_password = data.get('current_password', '')
        new_password     = data.get('new_password', '')

        if not current_password or not new_password:
            return api_error('Current password and new password are required', status=400)

        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            return api_error(error_msg, status=400)

        user = user_model.get_by_id(user_id)
        if not user:
            return api_error('User not found', status=404)

        if not verify_password(current_password, user['password']):
            return api_error('Current password is incorrect', status=400)

        updated_user = user_model.update(user_id, {'password': hash_password(new_password)})
        if updated_user:
            return api_response(
                data={},
                message='Password changed successfully',
                status=200,
            )
        return api_error('Failed to change password', status=500)
    except Exception as e:
        return api_error(f'Failed to change password: {e}', status=500)


@buyer_bp.route('/profile')
@buyer_required
def profile():
    return redirect(url_for('buyer.settings'))

@buyer_bp.route('/settings')
@buyer_required
def settings():
    return render_template('buyer/settings.html')

# ============================================
# REVIEW API ENDPOINTS (Flutter-ready)
# ============================================

@buyer_bp.route('/api/reviews', methods=['GET'])
@buyer_required
def api_reviews():
    """
    Get reviews - supports multiple query patterns:
    - GET /api/reviews?product_id=xxx - Get reviews for a product
    - GET /api/reviews?user_id=xxx - Get reviews by a user
    """
    try:
        product_id = request.args.get('product_id')
        user_id = request.args.get('user_id')
        
        if product_id:
            # Get product reviews with stats
            reviews = review_model.get_product_reviews(product_id)
            stats = review_model.get_review_stats(product_id)
            
            # Check if current user has reviewed this product
            current_user_id = session['user']['id']
            has_reviewed = review_model.has_reviewed_product(current_user_id, product_id)
            
            return api_response(
                data={
                    "reviews": reviews,
                    "stats": stats,
                    "has_reviewed": has_reviewed,
                    "count": len(reviews or [])
                },
                message="OK",
                status=200,
            )
        
        if user_id:
            # Get user's reviews (own reviews)
            current_user_id = session['user']['id']
            if user_id != current_user_id:
                return api_error("Unauthorized", status=403)
            
            reviews = review_model.get_user_reviews(user_id)
            return api_response(
                data={"reviews": reviews, "count": len(reviews or [])},
                message="OK",
                status=200,
            )
        
        return api_error("Missing required parameter: product_id or user_id", status=400)
    except Exception as e:
        return api_error(f"Failed to fetch reviews: {e}", status=500)

@buyer_bp.route('/api/reviews', methods=['POST'])
@buyer_required
def api_create_review():
    """Create a new review. Validates order status and eligibility."""
    try:
        user_id = session['user']['id']
        data = request.get_json() or {}
        
        product_id = data.get('product_id')
        order_id = data.get('order_id')
        rating = data.get('rating')
        comment = data.get('comment', '')
        image_url = data.get('image_url')
        
        # Validate required fields
        if not product_id or not order_id or rating is None:
            return api_error('Missing required fields: product_id, order_id, rating', status=400)
        
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return api_error('Rating must be an integer between 1 and 5', status=400)
        
        # Check if user can review this product
        eligibility = review_model.can_review(user_id, product_id, order_id)
        if not eligibility['can_review']:
            return api_error(eligibility['reason'], status=400)
        
        # Create the review
        review = review_model.create_review(user_id, product_id, order_id, rating, comment, image_url)
        
        if review:
            return api_response(
                data={"review": review},
                message='Review submitted successfully!',
                status=201,
            )
        
        return api_error('Failed to create review. You may have already reviewed this product.', status=400)
    except Exception as e:
        return api_error(f"Failed to create review: {e}", status=500)

@buyer_bp.route('/api/reviews/<review_id>', methods=['GET'])
@buyer_required
def api_get_review(review_id):
    """Get a specific review."""
    try:
        review = review_model.get_review_by_id(review_id)
        if not review:
            return api_error("Review not found", status=404)
        
        return api_response(
            data={"review": review},
            message="OK",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to fetch review: {e}", status=500)

@buyer_bp.route('/api/reviews/<review_id>', methods=['PUT'])
@buyer_required
def api_update_review(review_id):
    """Update own review."""
    try:
        user_id = session['user']['id']
        data = request.get_json() or {}
        
        rating = data.get('rating')
        comment = data.get('comment')
        image_url = data.get('image_url')
        
        # Validate rating if provided
        if rating is not None and (not isinstance(rating, int) or rating < 1 or rating > 5):
            return api_error('Rating must be an integer between 1 and 5', status=400)
        
        success = review_model.update_review(review_id, user_id, rating, comment, image_url)
        
        if success:
            return api_response(
                data={},
                message='Review updated successfully',
                status=200,
            )
        
        return api_error('Review not found or you do not have permission to update it', status=404)
    except Exception as e:
        return api_error(f"Failed to update review: {e}", status=500)

@buyer_bp.route('/api/reviews/<review_id>', methods=['DELETE'])
@buyer_required
def api_delete_review(review_id):
    """Delete own review."""
    try:
        user_id = session['user']['id']
        success = review_model.delete_review(review_id, user_id)
        
        if success:
            return api_response(
                data={},
                message='Review deleted successfully',
                status=200,
            )
        
        return api_error('Review not found or you do not have permission to delete it', status=404)
    except Exception as e:
        return api_error(f"Failed to delete review: {e}", status=500)

@buyer_bp.route('/api/orders/<order_id>/products/<product_id>/can_review', methods=['GET'])
@buyer_required
def api_can_review(order_id, product_id):
    """Check if user can review a specific product from an order."""
    try:
        user_id = session['user']['id']
        eligibility = review_model.can_review(user_id, product_id, order_id)
        return api_response(
            data=eligibility,
            message="OK",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to check review eligibility: {e}", status=500)

# Aliases for backward compatibility  
market_view = market
cart_view = cart
profile_view = profile
