from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models.order_model import OrderModel
from models.product_model import ProductModel
from models.user_model import UserModel
from models.notification_model import NotificationModel
from models.review_model import ReviewModel
from services.auth_service import AuthService
from services.order_service import OrderService

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

        for p in products:
            images  = p.get('product_images') or []
            primary = next((img for img in images if img.get('is_primary')), images[0] if images else None)
            p['image'] = primary.get('image_url') if primary else None
            p['stock'] = p.get('total_stock', 0)

        return jsonify(products)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@buyer_bp.route('/api/products/<product_id>', methods=['GET'])
def api_buyer_product_detail(product_id):
    try:
        product = product_model.get_by_id(product_id)
        if not product or product.get('status') != 'active':
            return jsonify({'error': 'Product not found'}), 404
        return jsonify(product)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    user_id = session['user']['id']
    count = notification_model.get_unread_count(user_id)
    return jsonify({'count': count})

@buyer_bp.route('/api/notifications', methods=['GET'])
@buyer_required
def api_notifications():
    """Get notifications for the current user."""
    user_id = session['user']['id']
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 50))
    notifications = notification_model.get_all(user_id, limit=limit, unread_only=unread_only)
    return jsonify(notifications)

@buyer_bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
@buyer_required
def api_mark_notification_as_read(notification_id):
    """Mark a specific notification as read."""
    user_id = session['user']['id']
    success = notification_model.mark_as_read(notification_id, user_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Notification not found'}), 404

@buyer_bp.route('/api/notifications/read-all', methods=['POST'])
@buyer_required
def api_mark_all_as_read():
    """Mark all notifications as read for the current user."""
    user_id = session['user']['id']
    count = notification_model.mark_all_as_read(user_id)
    return jsonify({'success': True, 'marked_count': count})

@buyer_bp.route('/api/cart', methods=['GET', 'POST'])
@buyer_required
def api_cart():
    user_id = session['user']['id']
    if request.method == 'GET':
        items = order_model.get_cart_items(user_id)
        for item in items:
            qty   = int(item.get('quantity', 0) or 0)
            price = float(item.get('price_snapshot', 0) or 0)
            item['subtotal'] = qty * price
            product = item.get('product') or {}
            item['name'] = product.get('name')
            item['image'] = next(
                (img.get('image_url') for img in (product.get('product_images') or []) if img.get('is_primary')),
                None
            )
            # Expose available stock so frontend can enforce the limit
            item['available_stock'] = int(product.get('total_stock') or 0)
        return jsonify(items)

    # POST — add to cart with comprehensive stock validation
    data       = request.get_json() or {}
    product_id = data.get('product_id')
    variant_id = data.get('variant_id')
    quantity   = int(data.get('quantity', 1) or 1)

    if quantity <= 0:
        return jsonify({'error': 'Quantity must be at least 1'}), 400

    product = product_model.get_by_id(product_id)
    if not product or product.get('status') != 'active':
        return jsonify({'error': 'Product not available'}), 400

    # Determine available stock (variant-level if variant selected, else product total)
    if variant_id:
        variant = next((v for v in (product.get('product_variants') or []) if v['id'] == variant_id), None)
        if not variant:
            return jsonify({'error': 'Selected variant not found'}), 400
        available = int(variant.get('stock') or 0)
        variant_name = f"{variant.get('variant_type', '')}: {variant.get('value', '')}"
    else:
        available = int(product.get('total_stock') or 0)
        variant_name = ""

    if available <= 0:
        return jsonify({'error': f'This product{" (" + variant_name + ")" if variant_name else ""} is out of stock'}), 400

    # Check how many the buyer already has in cart
    existing = order_model.find_cart_item(user_id, product_id, variant_id)
    already_in_cart = int((existing or {}).get('quantity') or 0)
    requested_total = already_in_cart + quantity

    if requested_total > available:
        allowed = available - already_in_cart
        if allowed <= 0:
            return jsonify({'error': f'Maximum stock reached. You already have {already_in_cart} in your cart (available: {available})'}), 400
        return jsonify({'error': f'Only {allowed} more unit(s) available (total stock: {available})'}), 400

    price_snapshot = float(product.get('price', 0) or 0)
    item = order_model.add_or_increment_cart_item(user_id, product_id, variant_id, quantity, price_snapshot)
    return jsonify({'success': True, 'item': item, 'message': f'Added {quantity} item(s) to cart'})

@buyer_bp.route('/api/cart/<item_id>', methods=['PUT', 'DELETE'])
@buyer_required
def api_cart_item(item_id):
    user_id = session['user']['id']
    if request.method == 'PUT':
        data     = request.get_json() or {}
        quantity = int(data.get('quantity', 1) or 1)
        if quantity <= 0:
            order_model.remove_cart_item(user_id, item_id)
            return jsonify({'success': True})

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
                return jsonify({'error': f'Only {available} unit(s) available in stock', 'max': available}), 400

        updated = order_model.update_cart_item_qty(user_id, item_id, quantity)
        return jsonify({'success': True, 'item': updated})
    order_model.remove_cart_item(user_id, item_id)
    return jsonify({'success': True})

@buyer_bp.route('/api/checkout', methods=['POST'])
@buyer_required
def api_checkout():
    user_id = session['user']['id']
    data = request.get_json() or {}
    address_id = data.get('address_id')
    payment_method = data.get('payment_method', 'cod')
    if payment_method not in ('cod', 'card', 'bank_transfer', 'gcash'):
        payment_method = 'cod'

    address = user_model.get_address_by_id(user_id, address_id)
    if not address:
        return jsonify({'error': 'Invalid delivery address'}), 400

    cart_items = order_model.get_cart_items(user_id)
    if not cart_items:
        return jsonify({'error': 'Your cart is empty'}), 400

    # Validate stock availability for all items before proceeding
    for ci in cart_items:
        product = ci.get('product') or {}
        if product.get('status') != 'active':
            return jsonify({'error': f'Product "{product.get("name", "Unknown")}" is no longer available'}), 400
        
        qty = int(ci.get('quantity', 0) or 0)
        variant_id = ci.get('variant_id')
        product_id = ci.get('product_id')
        
        # Check current stock availability
        if not order_model._check_stock_availability(product_id, variant_id, qty):
            product_name = product.get('name', 'Unknown product')
            return jsonify({'error': f'Insufficient stock for "{product_name}". Please update your cart and try again.'}), 400

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

    try:
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

        return jsonify({'success': True, 'order_id': order.get('id'), 'message': 'Order placed successfully! Stock has been reserved.'})
    except Exception as e:
        return jsonify({'error': f'Failed to create order: {str(e)}'}), 500

@buyer_bp.route('/api/orders', methods=['GET', 'POST'])
@buyer_required
def api_orders():
    user_id = session['user']['id']
    if request.method == 'GET':
        orders = order_model.get_by_buyer(user_id)
        return jsonify(orders)
    # Backward-compatible alias: POST /api/orders -> checkout
    return api_checkout()

@buyer_bp.route('/api/orders/<order_id>', methods=['GET'])
@buyer_required
def api_order_detail(order_id):
    user_id = session['user']['id']
    order = order_model.get_by_id(order_id)
    if not order or order.get('buyer_id') != user_id:
        return jsonify({'error': 'Order not found'}), 404
    order['total'] = order.get('total_amount', 0)
    return jsonify(order)

@buyer_bp.route('/api/orders/<order_id>/cancel', methods=['POST'])
@buyer_required
def api_cancel_order(order_id):
    """Cancel an order and restore stock"""
    user_id = session['user']['id']
    try:
        cancelled_order = order_model.cancel_order(order_id, user_id)
        if cancelled_order:
            return jsonify({'success': True, 'message': 'Order cancelled successfully. Stock has been restored.', 'order': cancelled_order})
        else:
            return jsonify({'error': 'Order cannot be cancelled. It may not exist, not belong to you, or already be in progress.'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@buyer_bp.route('/api/addresses', methods=['GET'])
@buyer_required
def api_addresses():
    user_id = session['user']['id']
    return jsonify(user_model.get_addresses(user_id))

@buyer_bp.route('/api/addresses', methods=['POST'])
@buyer_required
def api_create_address():
    user_id = session['user']['id']
    data = request.get_json() or {}
    
    # Validate required fields
    required_fields = ['label', 'region', 'city', 'barangay', 'street', 'zip_code']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400
    
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
        return jsonify({'success': True, 'address': address})
    else:
        return jsonify({'error': 'Failed to create address'}), 500

@buyer_bp.route('/api/addresses/<address_id>', methods=['PUT'])
@buyer_required
def api_update_address(address_id):
    user_id = session['user']['id']
    data = request.get_json() or {}
    
    # Verify address belongs to user
    address = user_model.get_address_by_id(user_id, address_id)
    if not address:
        return jsonify({'error': 'Address not found'}), 404
    
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
        return jsonify({'error': 'No fields to update'}), 400
    
    updated_address = user_model.update_address(user_id, address_id, update_data)
    if updated_address:
        return jsonify({'success': True, 'address': updated_address})
    else:
        return jsonify({'error': 'Failed to update address'}), 500

@buyer_bp.route('/api/addresses/<address_id>', methods=['DELETE'])
@buyer_required
def api_delete_address(address_id):
    user_id = session['user']['id']
    
    # Verify address belongs to user
    address = user_model.get_address_by_id(user_id, address_id)
    if not address:
        return jsonify({'error': 'Address not found'}), 404
    
    # Don't allow deletion of default address without setting another as default
    if address.get('is_default'):
        addresses = user_model.get_addresses(user_id)
        if len(addresses) <= 1:
            return jsonify({'error': 'Cannot delete the only address. Please add another address first.'}), 400
    
    success = user_model.delete_address(user_id, address_id)
    if success:
        # If deleted address was default, set another as default
        if address.get('is_default'):
            addresses = user_model.get_addresses(user_id)
            if addresses:
                user_model.update_address(user_id, addresses[0]['id'], {'is_default': True})
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to delete address'}), 500

@buyer_bp.route('/api/addresses/<address_id>/default', methods=['POST'])
@buyer_required
def api_set_default_address(address_id):
    user_id = session['user']['id']
    
    # Verify address belongs to user
    address = user_model.get_address_by_id(user_id, address_id)
    if not address:
        return jsonify({'error': 'Address not found'}), 404
    
    # Remove default flag from all addresses
    addresses = user_model.get_addresses(user_id)
    for addr in addresses:
        if addr['id'] != address_id:
            user_model.update_address(user_id, addr['id'], {'is_default': False})
    
    # Set this address as default
    updated_address = user_model.update_address(user_id, address_id, {'is_default': True})
    if updated_address:
        return jsonify({'success': True, 'address': updated_address})
    else:
        return jsonify({'error': 'Failed to set default address'}), 500

@buyer_bp.route('/api/profile', methods=['PUT'])
@buyer_required
def api_update_profile():
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
        return jsonify({'error': 'No fields to update'}), 400

    updated_user = user_model.update(user_id, update_data)
    if updated_user:
        session['user'].update({
            'first_name': updated_user.get('first_name'),
            'last_name':  updated_user.get('last_name'),
            'phone':      updated_user.get('phone')
        })
        session['user']['name'] = f"{updated_user.get('first_name', '')} {updated_user.get('last_name', '')}".strip()
        return jsonify({'success': True, 'user': updated_user})
    return jsonify({'error': 'Failed to update profile'}), 500

@buyer_bp.route('/api/password', methods=['PUT'])
@buyer_required
def api_change_password():
    user_id = session['user']['id']
    data = request.get_json() or {}
    from security import validate_password, verify_password, hash_password

    current_password = data.get('current_password', '')
    new_password     = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'error': 'Current password and new password are required'}), 400


    is_valid, error_msg = validate_password(new_password)
    if not is_valid:
        return jsonify({'error': error_msg}), 400

    user = user_model.get_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if not verify_password(current_password, user['password']):
        return jsonify({'error': 'Current password is incorrect'}), 400

    updated_user = user_model.update(user_id, {'password': hash_password(new_password)})
    if updated_user:
        return jsonify({'success': True, 'message': 'Password changed successfully'})
    return jsonify({'error': 'Failed to change password'}), 500


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
    product_id = request.args.get('product_id')
    user_id = request.args.get('user_id')
    
    if product_id:
        # Get product reviews with stats
        reviews = review_model.get_product_reviews(product_id)
        stats = review_model.get_review_stats(product_id)
        
        # Check if current user has reviewed this product
        current_user_id = session['user']['id']
        has_reviewed = review_model.has_reviewed_product(current_user_id, product_id)
        
        return jsonify({
            'reviews': reviews,
            'stats': stats,
            'has_reviewed': has_reviewed
        })
    
    if user_id:
        # Get user's reviews (own reviews)
        current_user_id = session['user']['id']
        if user_id != current_user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        reviews = review_model.get_user_reviews(user_id)
        return jsonify({'reviews': reviews})
    
    return jsonify({'error': 'Missing required parameter: product_id or user_id'}), 400

@buyer_bp.route('/api/reviews', methods=['POST'])
@buyer_required
def api_create_review():
    """Create a new review. Validates order status and eligibility."""
    user_id = session['user']['id']
    data = request.get_json() or {}
    
    product_id = data.get('product_id')
    order_id = data.get('order_id')
    rating = data.get('rating')
    comment = data.get('comment', '')
    image_url = data.get('image_url')
    
    # Validate required fields
    if not product_id or not order_id or rating is None:
        return jsonify({'error': 'Missing required fields: product_id, order_id, rating'}), 400
    
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'error': 'Rating must be an integer between 1 and 5'}), 400
    
    # Check if user can review this product
    eligibility = review_model.can_review(user_id, product_id, order_id)
    if not eligibility['can_review']:
        return jsonify({'error': eligibility['reason']}), 400
    
    # Create the review
    review = review_model.create_review(user_id, product_id, order_id, rating, comment, image_url)
    
    if review:
        return jsonify({
            'success': True,
            'message': 'Review submitted successfully!',
            'review': review
        }), 201
    
    return jsonify({'error': 'Failed to create review. You may have already reviewed this product.'}), 400

@buyer_bp.route('/api/reviews/<review_id>', methods=['GET'])
@buyer_required
def api_get_review(review_id):
    """Get a specific review."""
    review = review_model.get_review_by_id(review_id)
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    return jsonify({'review': review})

@buyer_bp.route('/api/reviews/<review_id>', methods=['PUT'])
@buyer_required
def api_update_review(review_id):
    """Update own review."""
    user_id = session['user']['id']
    data = request.get_json() or {}
    
    rating = data.get('rating')
    comment = data.get('comment')
    image_url = data.get('image_url')
    
    # Validate rating if provided
    if rating is not None and (not isinstance(rating, int) or rating < 1 or rating > 5):
        return jsonify({'error': 'Rating must be an integer between 1 and 5'}), 400
    
    success = review_model.update_review(review_id, user_id, rating, comment, image_url)
    
    if success:
        return jsonify({'success': True, 'message': 'Review updated successfully'})
    
    return jsonify({'error': 'Review not found or you do not have permission to update it'}), 404

@buyer_bp.route('/api/reviews/<review_id>', methods=['DELETE'])
@buyer_required
def api_delete_review(review_id):
    """Delete own review."""
    user_id = session['user']['id']
    success = review_model.delete_review(review_id, user_id)
    
    if success:
        return jsonify({'success': True, 'message': 'Review deleted successfully'})
    
    return jsonify({'error': 'Review not found or you do not have permission to delete it'}), 404

@buyer_bp.route('/api/orders/<order_id>/products/<product_id>/can_review', methods=['GET'])
@buyer_required
def api_can_review(order_id, product_id):
    """Check if user can review a specific product from an order."""
    user_id = session['user']['id']
    eligibility = review_model.can_review(user_id, product_id, order_id)
    return jsonify(eligibility)

# Aliases for backward compatibility  
market_view = market
cart_view = cart
profile_view = profile
