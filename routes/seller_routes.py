from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models.product_model import ProductModel
from models.application_model import ApplicationModel
from services.auth_service import AuthService
from services.product_service import ProductService
from services.file_upload_service import FileUploadService

def seller_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        if session['user'].get('role') != 'seller':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

seller_bp = Blueprint('seller', __name__)
product_model = ProductModel()
app_model = ApplicationModel()
auth_service = AuthService()
product_service = ProductService()
file_service = FileUploadService()

@seller_bp.route('/')
@seller_required
def dashboard():
    seller_id = session['user']['id']
    stats = product_service.get_seller_stats(seller_id)
    return render_template('seller/dashboard.html', stats=stats)

@seller_bp.route('/products')
@seller_required
def products():
    seller_id = session['user']['id']
    products = product_model.get_by_seller(seller_id)
    category = auth_service.get_seller_category(seller_id)
    return render_template('seller/products.html', products=products, category=category)

@seller_bp.route('/products/add')
@seller_required
def product_add():
    seller_id = session['user']['id']
    category = auth_service.get_seller_category(seller_id)
    return render_template('seller/product-add.html', category=category)

@seller_bp.route('/api/seller/products', methods=['POST'])
@seller_required
def api_seller_product_create():
    seller_id = session['user']['id']
    try:
        result = product_service.create_product(seller_id, request.form, request.files)
        if result.get('success'):
            return jsonify(result), 201
        return jsonify({'error': result.get('error', 'Failed to create product')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@seller_bp.route('/api/seller/products/<product_id>', methods=['GET', 'PUT', 'DELETE'])
@seller_required
def api_seller_product_detail(product_id):
    seller_id = session['user']['id']
    
    if request.method == 'GET':
        product = product_model.get_by_id_and_seller(product_id, seller_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify(product)
    
    elif request.method == 'PUT':
        try:
            result = product_service.update_product(product_id, seller_id, request.form, request.files)
            if result.get('success'):
                return jsonify(result)
            return jsonify({'error': result.get('error')}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            product_model.delete(product_id, seller_id)
            return jsonify({'success': True, 'message': 'Product deleted'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@seller_bp.route('/orders')
@seller_required
def orders():
    seller_id = session['user']['id']
    from models.order_model import OrderModel
    order_model = OrderModel()
    orders = order_model.get_by_seller(seller_id)
    return render_template('seller/orders.html', orders=orders)

@seller_bp.route('/shipping')
@seller_required
def shipping():
    return render_template('seller/shipping.html')

@seller_bp.route('/earnings')
@seller_required
def earnings():
    seller_id = session['user']['id']
    stats = product_service.get_seller_stats(seller_id)
    return render_template('seller/earnings.html', stats=stats)

@seller_bp.route('/store')
@seller_required
def store():
    application = app_model.get_by_user_id(session['user']['id'])
    return render_template('seller/store.html', application=application)

@seller_bp.route('/reviews')
@seller_required
def reviews():
    return render_template('seller/reviews.html')

# Aliases for backward compatibility
product_add_view = product_add
products_view = products
dashboard_view = dashboard