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
        
        # Enhanced address handling with coordinates
        address = row.get('shipping_address') or {}
        row['address'] = ", ".join(
            [str(x) for x in [address.get('street'), address.get('barangay'), address.get('city'), address.get('region')] if x]
        )
        
        # Add delivery coordinates
        row['delivery_latitude'] = address.get('latitude')
        row['delivery_longitude'] = address.get('longitude')
        row['delivery_full_address'] = {
            'street': address.get('street', ''),
            'barangay': address.get('barangay', ''),
            'city': address.get('city', ''),
            'region': address.get('region', ''),
            'latitude': address.get('latitude'),
            'longitude': address.get('longitude')
        }
        
        # Get seller information and address
        items = row.get('order_items') or []
        if items:
            product = items[0].get('product') or {}
            seller_id = product.get('seller_id')
            row['store_name'] = product.get('name', 'Store')
            
            # Fetch seller address with coordinates
            if seller_id:
                from models.user_model import UserModel
                user_model = UserModel()
                seller_addresses = user_model.get_addresses(seller_id)
                
                # Get default address or first available
                seller_address = None
                for addr in seller_addresses:
                    if addr.get('is_default'):
                        seller_address = addr
                        break
                if not seller_address and seller_addresses:
                    seller_address = seller_addresses[0]
                
                if seller_address:
                    row['pickup_latitude'] = seller_address.get('latitude')
                    row['pickup_longitude'] = seller_address.get('longitude')
                    row['pickup_full_address'] = {
                        'street': seller_address.get('street', ''),
                        'barangay': seller_address.get('barangay', ''),
                        'city': seller_address.get('city', ''),
                        'region': seller_address.get('region', ''),
                        'latitude': seller_address.get('latitude'),
                        'longitude': seller_address.get('longitude')
                    }
                    row['pickup_address'] = ", ".join([
                        str(x) for x in [
                            seller_address.get('street'),
                            seller_address.get('barangay'),
                            seller_address.get('city'),
                            seller_address.get('region')
                        ] if x
                    ])
        else:
            row['store_name'] = 'Store'
    
    return jsonify(rows)


@rider_bp.route('/api/deliveries/<order_id>/accept', methods=['POST'])
@rider_required
def api_accept_delivery(order_id):
    rider_id = session['user']['id']
    updated = order_model.assign_rider(order_id, rider_id)
    if not updated:
        return jsonify({'error': 'Order is no longer available for pickup'}), 400
    return jsonify({'success': True, 'order': updated})


@rider_bp.route('/api/deliveries/<order_id>/locations', methods=['GET'])
@rider_required
def api_delivery_locations(order_id):
    """Get detailed location information for a specific delivery"""
    order = order_model.get_by_id(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    # Get delivery address (buyer)
    delivery_address = order.get('shipping_address', {})
    
    # Get pickup address (seller)
    pickup_address = None
    order_items = order.get('order_items', [])
    
    if order_items:
        product = order_items[0].get('product', {})
        seller_id = product.get('seller_id')
        
        if seller_id:
            from models.user_model import UserModel
            user_model = UserModel()
            seller_addresses = user_model.get_addresses(seller_id)
            
            # Get default address or first available
            for addr in seller_addresses:
                if addr.get('is_default'):
                    pickup_address = addr
                    break
            if not pickup_address and seller_addresses:
                pickup_address = seller_addresses[0]
    
    response_data = {
        'order_id': order_id,
        'pickup_location': {
            'latitude': pickup_address.get('latitude') if pickup_address else None,
            'longitude': pickup_address.get('longitude') if pickup_address else None,
            'address': {
                'street': pickup_address.get('street', '') if pickup_address else '',
                'barangay': pickup_address.get('barangay', '') if pickup_address else '',
                'city': pickup_address.get('city', '') if pickup_address else '',
                'region': pickup_address.get('region', '') if pickup_address else ''
            },
            'formatted_address': ", ".join([
                str(x) for x in [
                    pickup_address.get('street'),
                    pickup_address.get('barangay'),
                    pickup_address.get('city'),
                    pickup_address.get('region')
                ] if x
            ]) if pickup_address else 'Address not available'
        },
        'delivery_location': {
            'latitude': delivery_address.get('latitude'),
            'longitude': delivery_address.get('longitude'),
            'address': {
                'street': delivery_address.get('street', ''),
                'barangay': delivery_address.get('barangay', ''),
                'city': delivery_address.get('city', ''),
                'region': delivery_address.get('region', '')
            },
            'formatted_address': ", ".join([
                str(x) for x in [
                    delivery_address.get('street'),
                    delivery_address.get('barangay'),
                    delivery_address.get('city'),
                    delivery_address.get('region')
                ] if x
            ])
        }
    }
    
    return jsonify(response_data)


@rider_bp.route('/api/dashboard', methods=['GET'])
@rider_required
def api_rider_dashboard():
    """Rider dashboard summary: deliveries + earnings."""
    from supabase import create_client
    from datetime import datetime, timezone, timedelta
    import os
    rider_id = session['user']['id']
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    # All orders assigned to this rider
    all_assigned = order_model.get_assigned_orders_for_rider(rider_id)
    completed    = [o for o in all_assigned if o.get('status') == 'delivered']
    active       = [o for o in all_assigned if o.get('status') == 'in_transit']

    # Earnings
    earnings_rows = sb.table('rider_earnings').select('amount, created_at').eq('rider_id', rider_id).execute()
    now         = datetime.now(timezone.utc)
    today       = now.date()
    week_start  = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    total_earn = today_earn = week_earn = month_earn = 0.0
    for row in (earnings_rows.data or []):
        amt = float(row.get('amount', 0))
        total_earn += amt
        try:
            d = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')).date()
            if d == today:       today_earn += amt
            if d >= week_start:  week_earn  += amt
            if d >= month_start: month_earn += amt
        except Exception:
            pass

    # Rider rate from settings
    settings = sb.table('admin_settings').select('key,value').eq('key', 'rider_rate').execute()
    rider_rate = float((settings.data or [{}])[0].get('value', 50))

    return jsonify({
        'total_deliveries':     len(all_assigned),
        'completed_deliveries': len(completed),
        'active_deliveries':    len(active),
        'total_earnings':       round(total_earn, 2),
        'today_earnings':       round(today_earn, 2),
        'week_earnings':        round(week_earn, 2),
        'month_earnings':       round(month_earn, 2),
        'rate_per_delivery':    rider_rate,
    })


@rider_bp.route('/api/earnings', methods=['GET'])
@rider_required
def api_rider_earnings():
    """Rider earnings history with analytics."""
    from supabase import create_client
    from datetime import datetime, timezone, timedelta
    import os
    rider_id = session['user']['id']
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    rows = sb.table('rider_earnings').select(
        'amount, created_at, order:orders(id, total_amount, status, created_at)'
    ).eq('rider_id', rider_id).order('created_at', desc=True).execute()

    now         = datetime.now(timezone.utc)
    today       = now.date()
    week_start  = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    total = today_e = week_e = month_e = 0.0
    history = []
    for row in (rows.data or []):
        amt   = float(row.get('amount', 0))
        total += amt
        order = row.get('order') or {}
        try:
            d = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')).date()
            if d == today:       today_e += amt
            if d >= week_start:  week_e  += amt
            if d >= month_start: month_e += amt
        except Exception:
            d = None
        history.append({
            'order_id':    (order.get('id') or '')[:8],
            'amount':      amt,
            'order_total': float(order.get('total_amount', 0)),
            'created_at':  row.get('created_at', ''),
        })

    # Daily chart — last 7 days
    chart = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_total = sum(
            float(r.get('amount', 0)) for r in (rows.data or [])
            if _parse_date(r.get('created_at', '')) == day
        )
        chart.append({'label': day.strftime('%m/%d'), 'value': day_total})

    return jsonify({
        'total':        round(total, 2),
        'today':        round(today_e, 2),
        'week':         round(week_e, 2),
        'month':        round(month_e, 2),
        'deliveries':   len(history),
        'history':      history,
        'chart':        chart,
    })


def _parse_date(iso):
    from datetime import datetime, timezone
    try:
        return datetime.fromisoformat(iso.replace('Z', '+00:00')).date()
    except Exception:
        return None


@rider_required
def api_update_delivery_status(order_id):
    rider_id = session['user']['id']
    data = request.get_json() or {}
    status = data.get('status')
    updated = order_model.update_status_for_rider(order_id, rider_id, status)
    if not updated:
        return jsonify({'error': 'Unable to update delivery status'}), 400
    return jsonify({'success': True, 'order': updated})
