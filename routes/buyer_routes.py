from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models.order_model import OrderModel
from models.product_model import ProductModel
from models.user_model import UserModel
from services.auth_service import AuthService
from services.order_service import OrderService

buyer_bp = Blueprint('buyer', __name__)
order_model = OrderModel()
product_model = ProductModel()
user_model = UserModel()
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
@buyer_required
def market():
    products = product_model.get_all_active()
    return render_template('buyer/market.html', products=products)

@buyer_bp.route('/product')
@buyer_required
def product():
    return render_template('buyer/product.html')

@buyer_bp.route('/api/products', methods=['GET'])
@buyer_required
def api_buyer_products():
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip().lower()
    min_price = request.args.get('min_price', '').strip()
    max_price = request.args.get('max_price', '').strip()

    products = product_model.get_all_active(category=category or None)

    if search:
        products = [p for p in products if search in (p.get('name', '') + ' ' + (p.get('description') or '')).lower()]
    if min_price:
        try:
            min_val = float(min_price)
            products = [p for p in products if float(p.get('price', 0) or 0) >= min_val]
        except ValueError:
            pass
    if max_price:
        try:
            max_val = float(max_price)
            products = [p for p in products if float(p.get('price', 0) or 0) <= max_val]
        except ValueError:
            pass

    for p in products:
        images = p.get('product_images') or []
        primary = next((img for img in images if img.get('is_primary')), images[0] if images else None)
        p['image'] = primary.get('image_url') if primary else None
        p['stock'] = p.get('total_stock', 0)

    return jsonify(products)

@buyer_bp.route('/api/products/<product_id>', methods=['GET'])
@buyer_required
def api_buyer_product_detail(product_id):
    product = product_model.get_by_id(product_id)
    if not product or product.get('status') != 'active':
        return jsonify({'error': 'Product not found'}), 404
    return jsonify(product)

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
    buyer_id = session['user']['id']
    orders = order_model.get_by_buyer(buyer_id)
    return render_template('buyer/orders.html', orders=orders)

@buyer_bp.route('/api/cart', methods=['GET', 'POST'])
@buyer_required
def api_cart():
    user_id = session['user']['id']
    if request.method == 'GET':
        items = order_model.get_cart_items(user_id)
        for item in items:
            qty = int(item.get('quantity', 0) or 0)
            price = float(item.get('price_snapshot', 0) or 0)
            item['subtotal'] = qty * price
            product = item.get('product') or {}
            item['name'] = product.get('name')
            item['image'] = next(
                (img.get('image_url') for img in (product.get('product_images') or []) if img.get('is_primary')),
                None
            )
        return jsonify(items)

    data = request.get_json() or {}
    product_id = data.get('product_id')
    variant_id = data.get('variant_id')
    quantity = int(data.get('quantity', 1) or 1)
    if quantity <= 0:
        return jsonify({'error': 'Quantity must be at least 1'}), 400
    product = product_model.get_by_id(product_id)
    if not product or product.get('status') != 'active':
        return jsonify({'error': 'Product not available'}), 400
    price_snapshot = float(product.get('price', 0) or 0)
    item = order_model.add_or_increment_cart_item(user_id, product_id, variant_id, quantity, price_snapshot)
    return jsonify({'success': True, 'item': item})

@buyer_bp.route('/api/cart/<item_id>', methods=['PUT', 'DELETE'])
@buyer_required
def api_cart_item(item_id):
    user_id = session['user']['id']
    if request.method == 'PUT':
        data = request.get_json() or {}
        quantity = int(data.get('quantity', 1) or 1)
        if quantity <= 0:
            order_model.remove_cart_item(user_id, item_id)
            return jsonify({'success': True})
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

    order_items = []
    total_amount = 0.0
    for ci in cart_items:
        product = ci.get('product') or {}
        if product.get('status') != 'active':
            continue
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
    if not order_items:
        return jsonify({'error': 'No valid cart items to checkout'}), 400

    order = order_model.create({
        'buyer_id': user_id,
        'total_amount': total_amount,
        'shipping_address': address,
        'status': 'pending',
        'payment_method': 'bank_transfer' if payment_method == 'gcash' else payment_method
    }, order_items)

    order_model.clear_cart(user_id)
    return jsonify({'success': True, 'order_id': order.get('id')})

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

@buyer_bp.route('/api/addresses', methods=['GET'])
@buyer_required
def api_addresses():
    user_id = session['user']['id']
    return jsonify(user_model.get_addresses(user_id))

@buyer_bp.route('/profile')
@buyer_required
def profile():
    profile_data = auth_service.get_user_profile(session['user']['id'])
    addresses = auth_service.get_addresses(session['user']['id'])
    return render_template('buyer/profile.html', profile=profile_data, addresses=addresses)

# Aliases for backward compatibility  
market_view = market
cart_view = cart
profile_view = profile