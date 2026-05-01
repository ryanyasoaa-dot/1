from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models.user_model import UserModel
from models.application_model import ApplicationModel
from models.order_model import OrderModel
from services.auth_service import AuthService

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        if session['user'].get('role') != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
user_model = UserModel()
app_model = ApplicationModel()
order_model = OrderModel()
auth_service = AuthService()

@admin_bp.route('/')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/sellers')
@admin_required
def sellers():
    sellers = user_model.get_by_role('seller')
    return render_template('admin/sellers.html', sellers=sellers)

@admin_bp.route('/riders')
@admin_required
def riders():
    riders = user_model.get_by_role('rider')
    return render_template('admin/riders.html', riders=riders)

@admin_bp.route('/products')
@admin_required
def products():
    products = auth_service.get_all_products()
    return render_template('admin/products.html', products=products)

@admin_bp.route('/orders')
@admin_required
def orders():
    orders = order_model.get_all()
    return render_template('admin/orders.html', orders=orders)

@admin_bp.route('/reports')
@admin_required
def reports():
    stats = auth_service.get_admin_stats()
    return render_template('admin/reports.html', stats=stats)

# API endpoints for admin
@admin_bp.route('/api/applications/<app_id>/status', methods=['POST'])
@admin_required
def update_application_status(app_id):
    data = request.get_json() or {}
    status = data.get('status')
    notes = data.get('notes', '')
    
    if status not in ('approved', 'rejected'):
        return jsonify({'error': 'Invalid status'}), 400
    
    try:
        app_model.update_status(app_id, status, session['user']['id'], notes)
        return jsonify({'success': True, 'message': 'Status updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/sellers/<user_id>/approve', methods=['POST'])
@admin_required
def approve_seller(user_id):
    try:
        user_model.update_role(user_id, 'seller')
        return jsonify({'success': True, 'message': 'Seller approved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/sellers/<user_id>/reject', methods=['POST'])
@admin_required
def reject_seller(user_id):
    try:
        user_model.update_role(user_id, 'user')
        return jsonify({'success': True, 'message': 'Seller rejected'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500