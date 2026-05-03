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

@seller_bp.route('/api/dashboard-summary', methods=['GET'])
@seller_required
def api_dashboard_summary():
    """Get comprehensive dashboard summary for seller"""
    seller_id = session['user']['id']
    from models.order_model import OrderModel
    from models.product_model import ProductModel
    
    order_model = OrderModel()
    product_model = ProductModel()
    
    # Get seller stats
    stats = order_model.get_seller_stats(seller_id)
    
    # Get product count
    products = product_model.get_by_seller(seller_id)
    total_products = len(products)
    active_products = len([p for p in products if p.get('status') == 'active'])
    
    # Get order status breakdown
    orders = order_model.get_by_seller(seller_id)
    status_counts = {
        'pending': 0,
        'processing': 0,
        'ready_for_pickup': 0,
        'in_transit': 0,
        'delivered': 0
    }
    
    for order in orders:
        status = order.get('status', 'pending')
        if status in status_counts:
            status_counts[status] += 1
    
    return jsonify({
        'total_sales': stats.get('total_revenue', 0),
        'total_orders': stats.get('total_orders', 0),
        'products_listed': total_products,
        'active_products': active_products,
        'pending_orders': status_counts['pending'],
        'completed_orders': status_counts['delivered'],
        'today_sales': stats.get('today_revenue', 0),
        'week_sales': stats.get('week_revenue', 0),
        'month_sales': stats.get('month_revenue', 0),
        'items_sold': stats.get('items_sold', 0),
        'status_breakdown': status_counts
    })

@seller_bp.route('/api/sales-analytics', methods=['GET'])
@seller_required
def api_sales_analytics():
    """Get sales analytics data for charts"""
    seller_id = session['user']['id']
    period = request.args.get('period', 'daily')  # daily, weekly, monthly
    
    from models.order_model import OrderModel
    from datetime import datetime, timedelta
    import calendar
    
    order_model = OrderModel()
    
    # Get all delivered orders for this seller
    orders = order_model.get_by_seller(seller_id)
    delivered_orders = [o for o in orders if o.get('status') == 'delivered']
    
    now = datetime.now()
    analytics_data = []
    
    if period == 'daily':
        # Last 7 days
        for i in range(6, -1, -1):
            date = now - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            day_orders = [o for o in delivered_orders if o.get('created_at', '').startswith(date_str)]
            total = sum(float(o.get('total_amount', 0)) for o in day_orders)
            analytics_data.append({
                'label': date.strftime('%m/%d'),
                'value': total,
                'orders': len(day_orders)
            })
    
    elif period == 'weekly':
        # Last 8 weeks
        for i in range(7, -1, -1):
            week_start = now - timedelta(weeks=i, days=now.weekday())
            week_end = week_start + timedelta(days=6)
            week_orders = []
            for o in delivered_orders:
                try:
                    order_date = datetime.fromisoformat(o.get('created_at', '').replace('Z', '+00:00'))
                    if week_start <= order_date <= week_end:
                        week_orders.append(o)
                except:
                    continue
            total = sum(float(o.get('total_amount', 0)) for o in week_orders)
            analytics_data.append({
                'label': f"Week {week_start.strftime('%m/%d')}",
                'value': total,
                'orders': len(week_orders)
            })
    
    elif period == 'monthly':
        # Last 6 months
        for i in range(5, -1, -1):
            month_date = now.replace(day=1) - timedelta(days=32*i)
            month_date = month_date.replace(day=1)
            month_str = month_date.strftime('%Y-%m')
            month_orders = [o for o in delivered_orders if o.get('created_at', '').startswith(month_str)]
            total = sum(float(o.get('total_amount', 0)) for o in month_orders)
            analytics_data.append({
                'label': month_date.strftime('%b %Y'),
                'value': total,
                'orders': len(month_orders)
            })
    
    return jsonify({
        'period': period,
        'data': analytics_data
    })

@seller_bp.route('/api/recent-orders', methods=['GET'])
@seller_required
def api_recent_orders():
    """Get recent orders for seller"""
    seller_id = session['user']['id']
    limit = int(request.args.get('limit', 10))
    
    from models.order_model import OrderModel
    order_model = OrderModel()
    
    orders = order_model.get_by_seller(seller_id)
    
    # Sort by created_at and limit
    recent_orders = sorted(orders, key=lambda x: x.get('created_at', ''), reverse=True)[:limit]
    
    # Format for frontend
    formatted_orders = []
    for order in recent_orders:
        formatted_orders.append({
            'id': order.get('id'),
            'order_id': order.get('id', '')[:8],
            'customer_name': order.get('customer_name', 'Unknown'),
            'buyer_id': order.get('buyer_id'),
            'items_count': order.get('items_count', 0),
            'total_amount': order.get('total_amount', 0),
            'status': order.get('status', 'pending'),
            'created_at': order.get('created_at', ''),
            'formatted_date': order.get('created_at', '')[:10] if order.get('created_at') else ''
        })
    
    return jsonify(formatted_orders)

@seller_bp.route('/api/top-products', methods=['GET'])
@seller_required
def api_top_products():
    """Get top selling products for seller"""
    seller_id = session['user']['id']
    limit = int(request.args.get('limit', 5))
    
    from models.order_model import OrderModel
    from models.product_model import ProductModel
    
    order_model = OrderModel()
    product_model = ProductModel()
    
    # Get all products for this seller
    products = product_model.get_by_seller(seller_id)
    
    # Get delivered orders to calculate sales
    orders = order_model.get_by_seller(seller_id)
    delivered_orders = [o for o in orders if o.get('status') == 'delivered']
    
    # Calculate product sales
    product_sales = {}
    for order in delivered_orders:
        for item in order.get('items', []):
            product_id = item.get('product_id')
            if product_id:
                if product_id not in product_sales:
                    product_sales[product_id] = {
                        'quantity': 0,
                        'revenue': 0
                    }
                product_sales[product_id]['quantity'] += int(item.get('quantity', 0))
                product_sales[product_id]['revenue'] += float(item.get('total_price', 0))
    
    # Match with product details and sort by revenue
    top_products = []
    for product in products:
        product_id = product.get('id')
        if product_id in product_sales:
            sales_data = product_sales[product_id]
            top_products.append({
                'id': product_id,
                'name': product.get('name', 'Unknown Product'),
                'quantity_sold': sales_data['quantity'],
                'total_revenue': sales_data['revenue'],
                'price': product.get('price', 0)
            })
    
    # Sort by revenue and limit
    top_products.sort(key=lambda x: x['total_revenue'], reverse=True)
    
    return jsonify(top_products[:limit])

@seller_bp.route('/api/low-stock', methods=['GET'])
@seller_required
def api_low_stock():
    """Get products with low stock"""
    seller_id = session['user']['id']
    threshold = int(request.args.get('threshold', 10))  # Default low stock threshold
    
    from models.product_model import ProductModel
    product_model = ProductModel()
    
    products = product_model.get_by_seller(seller_id)
    
    low_stock_products = []
    for product in products:
        if product.get('status') == 'active':  # Only check active products
            stock = int(product.get('total_stock', 0))
            if stock <= threshold:
                low_stock_products.append({
                    'id': product.get('id'),
                    'name': product.get('name', 'Unknown Product'),
                    'current_stock': stock,
                    'price': product.get('price', 0),
                    'status': 'critical' if stock == 0 else 'low' if stock <= 5 else 'warning'
                })
    
    # Sort by stock level (lowest first)
    low_stock_products.sort(key=lambda x: x['current_stock'])
    
    return jsonify(low_stock_products)

@seller_bp.route('/api/products', methods=['GET'])
@seller_required
def api_seller_products():
    seller_id = session['user']['id']
    products = product_model.get_by_seller(seller_id)
    return jsonify(products)

@seller_bp.route('/products/add')
@seller_required
def product_add():
    seller_id = session['user']['id']
    category = auth_service.get_seller_category(seller_id)
    return render_template('seller/product-add.html', category=category)

@seller_bp.route('/api/products', methods=['POST'])
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

@seller_bp.route('/api/products/<product_id>', methods=['GET', 'PUT', 'DELETE'])
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

@seller_bp.route('/orders/<order_id>')
@seller_required
def order_detail(order_id):
    seller_id = session['user']['id']
    from models.order_model import OrderModel
    order_model = OrderModel()
    
    # Get order details
    order = order_model.get_by_id(order_id)
    if not order:
        from flask import abort
        abort(404)
    
    # Verify seller owns at least one product in this order
    product_result = order_model.supabase.table('products').select('id').eq('seller_id', seller_id).execute()
    product_ids = [p.get('id') for p in (product_result.data or [])]
    if not product_ids:
        from flask import abort
        abort(403)
    owned_items = order_model.supabase.table('order_items').select('id').eq('order_id', order_id).in_('product_id', product_ids).limit(1).execute()
    if not owned_items.data:
        from flask import abort
        abort(403)
    
    return render_template('seller/order_detail.html', order=order)

@seller_bp.route('/api/orders/<order_id>', methods=['GET'])
@seller_required
def api_seller_order_detail(order_id):
    seller_id = session['user']['id']
    order_model = OrderModel()
    order = order_model.get_by_id(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    # Verify seller owns at least one product in this order
    product_result = order_model.supabase.table('products').select('id').eq('seller_id', seller_id).execute()
    product_ids = [p.get('id') for p in (product_result.data or [])]
    if not product_ids:
        return jsonify({'error': 'Not authorized'}), 403
    owned_items = order_model.supabase.table('order_items').select('id').eq('order_id', order_id).in_('product_id', product_ids).limit(1).execute()
    if not owned_items.data:
        return jsonify({'error': 'Not authorized'}), 403
    return jsonify(order)

@seller_bp.route('/api/orders', methods=['GET'])
@seller_required
def api_seller_orders():
    seller_id = session['user']['id']
    from models.order_model import OrderModel
    order_model = OrderModel()
    orders = order_model.get_by_seller(seller_id)
    # Add buyer_id to each order for the frontend
    for order in orders:
        order['buyer_id'] = order.get('buyer_id')
    return jsonify(orders)

@seller_bp.route('/api/orders/<order_id>/status', methods=['POST'])
@seller_required
def api_seller_update_order_status(order_id):
    seller_id = session['user']['id']
    data = request.get_json() or {}
    status = data.get('status')
    if status not in ('processing', 'ready_for_pickup'):
        return jsonify({'error': 'Invalid status'}), 400
    from models.order_model import OrderModel
    from models.notification_model import NotificationModel
    
    order_model = OrderModel()
    notification_model = NotificationModel()
    
    # Get current order status before updating
    current_order = order_model.get_by_id(order_id)
    if not current_order:
        return jsonify({'error': 'Order not found'}), 404
    
    current_status = current_order.get('status')
    updated = order_model.update_status_for_seller(order_id, seller_id, status)
    
    if not updated:
        return jsonify({'error': 'Order not found or invalid status transition'}), 404
    
    # Create notification when order moves from pending to processing (order approved)
    if current_status == 'pending' and status == 'processing':
        buyer_id = current_order.get('buyer_id')
        if buyer_id:
            try:
                notification_model.create_order_notification(
                    user_id=buyer_id,
                    order_id=order_id,
                    title="Order Approved",
                    message="Your order has been accepted by the seller and is now being processed.",
                    action_url=f"/buyer/orders#{order_id}"
                )
            except Exception as e:
                print(f"Error creating notification: {e}")
                # Don't fail the order update if notification fails
    
    return jsonify({'success': True, 'order': updated})

@seller_bp.route('/shipping')
@seller_required
def shipping():
    return render_template('seller/shipping.html')

@seller_bp.route('/earnings')
@seller_required
def earnings():
    return render_template('seller/earnings.html')

@seller_bp.route('/api/earnings', methods=['GET'])
@seller_required
def api_seller_earnings():
    seller_id = session['user']['id']
    from models.order_model import OrderModel
    stats = OrderModel().get_seller_stats(seller_id)
    return jsonify(stats)

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