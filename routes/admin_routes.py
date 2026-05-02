from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models.user_model import UserModel
from models.application_model import ApplicationModel
from models.order_model import OrderModel
from models.product_model import ProductModel
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
product_model = ProductModel()
auth_service = AuthService()

@admin_bp.route('/')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/applications')
@admin_required
def applications():
    apps = app_model.get_pending()
    return render_template('admin/applications.html', applications=apps)

@admin_bp.route('/users')
@admin_required
def users():
    all_users = user_model.get_all()
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/settings')
@admin_required
def settings():
    return render_template('admin/settings.html')

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
    products = product_model.get_all()
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

@admin_bp.route('/messages')
@admin_required
def messages():
    return redirect('/messages/admin')

# API endpoints for admin
@admin_bp.route('/api/applications', methods=['GET'])
@admin_required
def api_get_applications():
    apps = app_model.get_all()
    return jsonify(apps)

@admin_bp.route('/api/applications/<app_id>', methods=['GET'])
@admin_required
def api_get_application(app_id):
    app = app_model.get_by_id(app_id)
    if not app:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(app)

@admin_bp.route('/api/applications/<app_id>/status', methods=['POST'])
@admin_required
def update_application_status(app_id):
    data = request.get_json() or {}
    status = data.get('status')
    notes = data.get('notes', '')
    
    if status not in ('approved', 'rejected'):
        return jsonify({'error': 'Invalid status'}), 400

    try:
        application = app_model.get_by_id(app_id)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        app_model.update_status(app_id, status, reject_reason=notes if status == 'rejected' else None)
        if status == 'approved':
            user_model.update_role(application['user_id'], application['role'])
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

@admin_bp.route('/api/products', methods=['GET'])
@admin_required
def get_products():
    status = request.args.get('status', '').strip() or None
    products = product_model.get_all(status=status)
    return jsonify(products)

@admin_bp.route('/api/products/<product_id>', methods=['GET'])
@admin_required
def get_product(product_id):
    product = product_model.get_by_id(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    return jsonify(product)

@admin_bp.route('/api/products/<product_id>/status', methods=['POST'])
@admin_required
def update_product_status(product_id):
    data = request.get_json() or {}
    status = data.get('status')
    reason = (data.get('reason') or '').strip() or None
    if status not in ('active', 'rejected'):
        return jsonify({'error': 'Invalid status'}), 400
    if status == 'rejected' and not reason:
        return jsonify({'error': 'Rejection reason is required'}), 400
    try:
        updated = product_model.update_status(product_id, status, session['user']['id'], reason)
        if not updated:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify({'success': True, 'product': updated})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/orders', methods=['GET'])
@admin_required
def api_admin_orders():
    status = request.args.get('status', '').strip() or None
    orders = order_model.get_all()
    if status:
        orders = [o for o in orders if o.get('status') == status]
    return jsonify(orders)

@admin_bp.route('/api/orders/<order_id>/status', methods=['POST'])
@admin_required
def api_admin_order_status(order_id):
    data = request.get_json() or {}
    status = data.get('status')
    rider_id = data.get('rider_id')
    if not status:
        return jsonify({'error': 'Status is required'}), 400
    updated = order_model.update_status_for_admin(order_id, status, rider_id)
    if not updated:
        return jsonify({'error': 'Order not found or invalid status'}), 404
    return jsonify({'success': True, 'order': updated})

@admin_bp.route('/api/orders/<order_id>/cancel', methods=['POST'])
@admin_required
def api_admin_cancel_order(order_id):
    """Admin can cancel any order and restore stock"""
    try:
        cancelled_order = order_model.cancel_order(order_id, is_admin=True)
        if cancelled_order:
            return jsonify({
                'success': True, 
                'message': 'Order cancelled successfully by admin. Stock has been restored.', 
                'order': cancelled_order
            })
        else:
            return jsonify({
                'error': 'Order cannot be cancelled. It may not exist or already be completed/delivered.'
            }), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/stats', methods=['GET'])
@admin_required
def api_admin_stats():
    """Get comprehensive admin statistics"""
    try:
        all_orders = order_model.get_all()
        stats = {
            'total_orders':    len(all_orders),
            'delivered_orders': len([o for o in all_orders if o.get('status') == 'delivered']),
            'pending_orders':  len([o for o in all_orders if o.get('status') == 'pending']),
            'cancelled_orders': len([o for o in all_orders if o.get('status') == 'cancelled']),
            'total_revenue':   sum(float(o.get('total_amount', 0)) for o in all_orders if o.get('status') == 'delivered'),
            'pending_revenue': sum(float(o.get('total_amount', 0)) for o in all_orders if o.get('status') in ['pending', 'processing', 'ready_for_pickup', 'in_transit'])
        }
        all_users = user_model.get_all()
        stats.update({
            'total_users':   len(all_users),
            'total_sellers': len([u for u in all_users if u.get('role') == 'seller']),
            'total_buyers':  len([u for u in all_users if u.get('role') == 'buyer']),
            'total_riders':  len([u for u in all_users if u.get('role') == 'rider'])
        })
        all_products = product_model.get_all()
        stats.update({
            'total_products':   len(all_products),
            'active_products':  len([p for p in all_products if p.get('status') == 'active']),
            'pending_products': len([p for p in all_products if p.get('status') == 'pending'])
        })
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/dashboard', methods=['GET'])
@admin_required
def api_admin_dashboard():
    """Full dashboard summary: users, orders, revenue, commission."""
    from supabase import create_client
    import os
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    all_orders  = order_model.get_all()
    all_users   = user_model.get_all()
    delivered   = [o for o in all_orders if o.get('status') == 'delivered']
    total_rev   = sum(float(o.get('total_amount', 0)) for o in delivered)

    # Commission rate from settings
    settings = sb.table('admin_settings').select('key,value').execute()
    rates = {r['key']: r['value'] for r in (settings.data or [])}
    commission_rate = float(rates.get('commission_rate', 5)) / 100
    admin_commission = round(total_rev * commission_rate, 2)

    # Status breakdown
    status_counts = {}
    for o in all_orders:
        s = o.get('status', 'pending')
        status_counts[s] = status_counts.get(s, 0) + 1

    return jsonify({
        'total_users':      len(all_users),
        'total_sellers':    len([u for u in all_users if u.get('role') == 'seller']),
        'total_riders':     len([u for u in all_users if u.get('role') == 'rider']),
        'total_buyers':     len([u for u in all_users if u.get('role') == 'buyer']),
        'total_orders':     len(all_orders),
        'delivered_orders': len(delivered),
        'total_revenue':    total_rev,
        'admin_commission': admin_commission,
        'commission_rate':  float(rates.get('commission_rate', 5)),
        'status_breakdown': status_counts,
    })


@admin_bp.route('/api/earnings', methods=['GET'])
@admin_required
def api_admin_earnings():
    """Admin commission earnings breakdown."""
    from supabase import create_client
    from datetime import datetime, timezone, timedelta
    import os
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    settings = sb.table('admin_settings').select('key,value').execute()
    rates = {r['key']: r['value'] for r in (settings.data or [])}
    commission_rate = float(rates.get('commission_rate', 5)) / 100

    all_orders = order_model.get_all()
    delivered  = [o for o in all_orders if o.get('status') == 'delivered']

    now         = datetime.now(timezone.utc)
    today       = now.date()
    week_start  = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    total = today_c = week_c = month_c = 0.0
    for o in delivered:
        amt = float(o.get('total_amount', 0))
        c   = amt * commission_rate
        total += c
        try:
            d = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')).date()
            if d == today:       today_c += c
            if d >= week_start:  week_c  += c
            if d >= month_start: month_c += c
        except Exception:
            pass

    return jsonify({
        'commission_rate':   float(rates.get('commission_rate', 5)),
        'total_commission':  round(total, 2),
        'today_commission':  round(today_c, 2),
        'week_commission':   round(week_c, 2),
        'month_commission':  round(month_c, 2),
        'delivered_orders':  len(delivered),
    })


@admin_bp.route('/api/commission', methods=['GET', 'POST'])
@admin_required
def api_admin_commission():
    """GET current rates / POST to update them."""
    from supabase import create_client
    import os
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    if request.method == 'GET':
        rows = sb.table('admin_settings').select('key,value').execute()
        return jsonify({r['key']: r['value'] for r in (rows.data or [])})

    data = request.get_json() or {}
    for key in ('commission_rate', 'rider_rate'):
        if key in data:
            val = str(data[key]).strip()
            sb.table('admin_settings').upsert({'key': key, 'value': val, 'updated_at': 'now()'}).execute()
    return jsonify({'success': True})


@admin_bp.route('/api/sales-analytics', methods=['GET'])
@admin_required
def api_admin_sales_analytics():
    """Sales chart data (daily/weekly/monthly) from delivered orders."""
    from datetime import datetime, timedelta
    period = request.args.get('period', 'daily')
    all_orders = order_model.get_all()
    delivered  = [o for o in all_orders if o.get('status') == 'delivered']
    now = datetime.now()
    data = []

    if period == 'daily':
        for i in range(6, -1, -1):
            d = now - timedelta(days=i)
            ds = d.strftime('%Y-%m-%d')
            day_orders = [o for o in delivered if (o.get('created_at') or '').startswith(ds)]
            data.append({'label': d.strftime('%m/%d'), 'value': sum(float(o.get('total_amount', 0)) for o in day_orders), 'orders': len(day_orders)})
    elif period == 'weekly':
        for i in range(7, -1, -1):
            ws = now - timedelta(weeks=i, days=now.weekday())
            we = ws + timedelta(days=6)
            wk = []
            for o in delivered:
                try:
                    od = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00'))
                    if ws <= od.replace(tzinfo=None) <= we:
                        wk.append(o)
                except Exception:
                    pass
            data.append({'label': f"W{ws.strftime('%m/%d')}", 'value': sum(float(o.get('total_amount', 0)) for o in wk), 'orders': len(wk)})
    elif period == 'monthly':
        for i in range(5, -1, -1):
            md = (now.replace(day=1) - timedelta(days=32 * i)).replace(day=1)
            ms = md.strftime('%Y-%m')
            mo = [o for o in delivered if (o.get('created_at') or '').startswith(ms)]
            data.append({'label': md.strftime('%b %Y'), 'value': sum(float(o.get('total_amount', 0)) for o in mo), 'orders': len(mo)})

    return jsonify({'period': period, 'data': data})


@admin_bp.route('/api/recent-orders', methods=['GET'])
@admin_required
def api_admin_recent_orders():
    """Recent orders with buyer/seller/rider info."""
    limit  = int(request.args.get('limit', 10))
    orders = order_model.get_all()
    recent = sorted(orders, key=lambda x: x.get('created_at', ''), reverse=True)[:limit]
    result = []
    for o in recent:
        buyer = o.get('buyer') or {}
        rider = o.get('rider') or {}
        result.append({
            'id':           o.get('id'),
            'short_id':     (o.get('id') or '')[:8],
            'buyer_name':   f"{buyer.get('first_name','')} {buyer.get('last_name','')}".strip() or '—',
            'rider_name':   f"{rider.get('first_name','')} {rider.get('last_name','')}".strip() or 'Unassigned',
            'total_amount': o.get('total_amount', 0),
            'status':       o.get('status', 'pending'),
            'created_at':   o.get('created_at', ''),
        })
    return jsonify(result)