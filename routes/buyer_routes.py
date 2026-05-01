from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models.order_model import OrderModel
from models.product_model import ProductModel
from services.auth_service import AuthService
from services.order_service import OrderService

buyer_bp = Blueprint('buyer', __name__)
order_model = OrderModel()
product_model = ProductModel()
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