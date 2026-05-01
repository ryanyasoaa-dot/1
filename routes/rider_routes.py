from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models.order_model import OrderModel


def rider_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        if session['user'].get('role') != 'rider':
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated


rider_bp = Blueprint('rider', __name__)
order_model = OrderModel()


@rider_bp.route('/')
@rider_required
def dashboard():
    return render_template('rider/dashboard.html')


@rider_bp.route('/deliveries')
@rider_required
def deliveries():
    return render_template('rider/deliveries.html')


@rider_bp.route('/earnings')
@rider_required
def earnings():
    return render_template('rider/earnings.html')


@rider_bp.route('/profile')
@rider_required
def profile():
    return render_template('rider/profile.html')


@rider_bp.route('/api/deliveries', methods=['GET'])
@rider_required
def api_deliveries():
    rider_id = session['user']['id']
    available = order_model.get_ready_for_pickup_orders()
    assigned = order_model.get_assigned_orders_for_rider(rider_id)
    rows = available + assigned

    for row in rows:
        buyer = row.get('buyer') or {}
        row['customer_name'] = f"{buyer.get('first_name', '')} {buyer.get('last_name', '')}".strip()
        address = row.get('shipping_address') or {}
        row['address'] = ", ".join(
            [str(x) for x in [address.get('street'), address.get('barangay'), address.get('city'), address.get('region')] if x]
        )
        items = row.get('order_items') or []
        row['store_name'] = (items[0].get('product') or {}).get('name') if items else 'Store'
    return jsonify(rows)


@rider_bp.route('/api/deliveries/<order_id>/accept', methods=['POST'])
@rider_required
def api_accept_delivery(order_id):
    rider_id = session['user']['id']
    updated = order_model.assign_rider(order_id, rider_id)
    if not updated:
        return jsonify({'error': 'Order is no longer available for pickup'}), 400
    return jsonify({'success': True, 'order': updated})


@rider_bp.route('/api/deliveries/<order_id>/status', methods=['POST'])
@rider_required
def api_update_delivery_status(order_id):
    rider_id = session['user']['id']
    data = request.get_json() or {}
    status = data.get('status')
    updated = order_model.update_status_for_rider(order_id, rider_id, status)
    if not updated:
        return jsonify({'error': 'Unable to update delivery status'}), 400
    return jsonify({'success': True, 'order': updated})
