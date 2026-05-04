from supabase import create_client
import os

class OrderModel:
    """Handles all order-related database operations"""
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
    
    def get_by_id(self, order_id):
        """Get order by ID with related data"""
        result = self.supabase.table('orders').select(
            '*, order_items(*, product:products(*), variant:product_variants(*))'
        ).eq('id', order_id).single().execute()
        order = result.data if result.data else None
        if order:
            # Fetch buyer and rider separately to avoid FK relationship issues
            if order.get('buyer_id'):
                buyer = self.supabase.table('users').select('first_name, last_name, email').eq('id', order['buyer_id']).single().execute()
                order['buyer'] = buyer.data if buyer.data else None
            if order.get('rider_id'):
                rider = self.supabase.table('users').select('first_name, last_name').eq('id', order['rider_id']).single().execute()
                order['rider'] = rider.data if rider.data else None
        return order
    
    def get_by_buyer(self, buyer_id):
        """Get all orders for a buyer"""
        result = self.supabase.table('orders').select(
            '*, order_items(*, product:products(*), variant:product_variants(*))'
        ).eq('buyer_id', buyer_id).order('created_at', desc=True).execute()
        orders = result.data if result.data else []
        for order in orders:
            items = order.get('order_items') or []
            order['items_count'] = sum(int(i.get('quantity', 0) or 0) for i in items)
            order['total'] = order.get('total_amount', 0)
            # Fetch rider separately to avoid FK relationship issues
            if order.get('rider_id'):
                rider = self.supabase.table('users').select('first_name, last_name').eq('id', order['rider_id']).single().execute()
                order['rider'] = rider.data if rider.data else None
        return orders
    
    def get_by_seller(self, seller_id):
        """Get all orders for a seller (through their products)"""
        # Get all product IDs for this seller
        product_result = self.supabase.table('products').select('id').eq('seller_id', seller_id).execute()
        if not product_result.data:
            return []
        
        product_ids = [p['id'] for p in product_result.data]
        
        # Get orders containing these products (without embedded relationships to avoid FK issues)
        result = self.supabase.table('order_items').select(
            '*, product:products(name, seller_id), variant:product_variants(value, variant_type), order:orders(*)'
        ).in_('product_id', product_ids).execute()
        
        # Group by order
        orders_map = {}
        if result.data:
            for item in result.data:
                order_id = item['order']['id']
                if order_id not in orders_map:
                    orders_map[order_id] = {
                        **item['order'],
                        'items': []
                    }
                orders_map[order_id]['items'].append(item)
        orders = list(orders_map.values())
        
        # Fetch buyer info for each order
        for order in orders:
            buyer_id = order.get('buyer_id')
            if buyer_id:
                buyer = self.supabase.table('users').select('first_name, last_name, email').eq('id', buyer_id).single().execute()
                if buyer.data:
                    order['buyer'] = buyer.data
                    order['customer_name'] = f"{buyer.data.get('first_name', '')} {buyer.data.get('last_name', '')}".strip()
                    order['customer_email'] = buyer.data.get('email', '')
            order['items_count'] = sum(int(i.get('quantity', 0) or 0) for i in order.get('items', []))
            order['total'] = order.get('total_amount', 0)
        return orders
    
    def create(self, order_data, items_data):
        """Create a new order with items and reserve stock"""
        try:
            # Validate stock availability before creating order
            for item_data in items_data:
                product_id = item_data['product_id']
                variant_id = item_data.get('variant_id')
                quantity = int(item_data['quantity'])
                
                if not self._check_stock_availability(product_id, variant_id, quantity):
                    raise Exception(f"Insufficient stock for product {product_id}")
            
            # Create order
            order_result = self.supabase.table('orders').insert(order_data).execute()
            order = order_result.data[0]
            
            # Create order items and reserve stock
            order_id = order['id']
            for item_data in items_data:
                item_data['order_id'] = order_id
                self.supabase.table('order_items').insert(item_data).execute()
                # Reserve stock (reduce available but don't deduct from total yet)
                self._reserve_stock(item_data['product_id'], item_data.get('variant_id'), int(item_data['quantity']))
            
            return order
        except Exception as e:
            raise e
    
    def update_status(self, order_id, new_status):
        """Update order status"""
        result = self.supabase.table('orders').update({'status': new_status}).eq('id', order_id).execute()
        return result.data[0] if result.data else None

    def update_status_for_seller(self, order_id, seller_id, new_status):
        """Update order status if seller owns at least one item in the order"""
        if new_status not in ('processing', 'ready_for_pickup'):
            return None
        product_result = self.supabase.table('products').select('id').eq('seller_id', seller_id).execute()
        product_ids = [p.get('id') for p in (product_result.data or [])]
        if not product_ids:
            return None
        owned_items = self.supabase.table('order_items').select('id').eq('order_id', order_id).in_('product_id', product_ids).limit(1).execute()
        if not owned_items.data:
            return None
        current = self.supabase.table('orders').select('status').eq('id', order_id).limit(1).execute()
        if not current.data:
            return None
        current_status = current.data[0].get('status')
        valid_next = {
            'pending': 'processing',
            'processing': 'ready_for_pickup'
        }
        if valid_next.get(current_status) != new_status:
            return None
        
        # When seller approves order (changes to 'processing'), deduct stock
        if current_status == 'pending' and new_status == 'processing':
            # Get order items to deduct stock
            items_result = self.supabase.table('order_items').select('product_id, variant_id, quantity').eq('order_id', order_id).execute()
            for item in items_result.data or []:
                self._deduct_stock(item['product_id'], item.get('variant_id'), int(item['quantity']))
        
        return self.update_status(order_id, new_status)

    def update_status_for_admin(self, order_id, new_status, rider_id=None):
        """Admin can override any valid order status and optionally assign a rider."""
        allowed = ('pending', 'processing', 'ready_for_pickup', 'in_transit', 'delivered')
        if new_status not in allowed:
            return None
        payload = {'status': new_status}
        if rider_id:
            payload['rider_id'] = rider_id
        result = self.supabase.table('orders').update(payload).eq('id', order_id).execute()
        return result.data[0] if result.data else None

    def get_ready_for_pickup_orders(self):
        """Orders available for rider pickup"""
        result = self.supabase.table('orders').select(
            '*, order_items(*, product:products(name, seller_id))'
        ).eq('status', 'ready_for_pickup').is_('rider_id', 'null').order('created_at', desc=True).execute()
        orders = result.data if result.data else []
        # Fetch buyer separately for each order
        for order in orders:
            if order.get('buyer_id'):
                buyer = self.supabase.table('users').select('first_name, last_name').eq('id', order['buyer_id']).single().execute()
                order['buyer'] = buyer.data if buyer.data else None
        return orders

    def get_assigned_orders_for_rider(self, rider_id):
        """Orders already accepted by this rider"""
        result = self.supabase.table('orders').select(
            '*, order_items(*, product:products(name, seller_id))'
        ).eq('rider_id', rider_id).in_('status', ['in_transit', 'delivered']).order('created_at', desc=True).execute()
        orders = result.data if result.data else []
        # Fetch buyer separately for each order
        for order in orders:
            if order.get('buyer_id'):
                buyer = self.supabase.table('users').select('first_name, last_name').eq('id', order['buyer_id']).single().execute()
                order['buyer'] = buyer.data if buyer.data else None
        return orders

    def assign_rider(self, order_id, rider_id):
        """Assign rider and move status to in_transit (only from ready_for_pickup)"""
        result = self.supabase.table('orders').update({
            'rider_id': rider_id,
            'status': 'in_transit'
        }).eq('id', order_id).eq('status', 'ready_for_pickup').is_('rider_id', 'null').execute()
        return result.data[0] if result.data else None

    def update_status_for_rider(self, order_id, rider_id, new_status):
        """Rider can move in_transit -> delivered only.
        On delivery: finalize stock deduction and count sales."""
        if new_status != 'delivered':
            return None
        current = self.supabase.table('orders').select('status, rider_id').eq('id', order_id).eq('rider_id', rider_id).limit(1).execute()
        if not current.data:
            return None
        if current.data[0].get('status') != 'in_transit':
            return None
        result = self.supabase.table('orders').update({'status': 'delivered'}).eq('id', order_id).eq('rider_id', rider_id).execute()
        if not result.data:
            return None
        # Finalize stock deduction and count sales only on delivery
        self._finalize_delivery(order_id)
        return result.data[0]

    def _check_stock_availability(self, product_id, variant_id, quantity):
        """Check if requested quantity is available (considering reserved stock)"""
        if variant_id:
            # Check variant stock minus reserved stock
            variant = self.supabase.table('product_variants').select('stock, reserved_stock').eq('id', variant_id).limit(1).execute()
            if variant.data:
                stock = int(variant.data[0].get('stock', 0))
                reserved = int(variant.data[0].get('reserved_stock', 0))
                available = stock - reserved
            else:
                return False
        else:
            # Check product total stock minus reserved stock
            product = self.supabase.table('products').select('total_stock, reserved_stock').eq('id', product_id).limit(1).execute()
            if not product.data:
                return False
            total = int(product.data[0].get('total_stock', 0))
            reserved = int(product.data[0].get('reserved_stock', 0))
            available = total - reserved
        
        return available >= quantity
    
    def _reserve_stock(self, product_id, variant_id, quantity):
        """Reserve stock when order is created (don't deduct, just mark as reserved)"""
        if variant_id:
            # Reserve variant stock (increase reserved_stock, don't decrease stock)
            variant = self.supabase.table('product_variants').select('stock, reserved_stock').eq('id', variant_id).limit(1).execute()
            if variant.data:
                current_stock = int(variant.data[0].get('stock', 0))
                current_reserved = int(variant.data[0].get('reserved_stock', 0))
                
                # Check if enough stock is available (stock - reserved_stock)
                available_stock = current_stock - current_reserved
                if available_stock < quantity:
                    raise Exception(f"Insufficient stock. Available: {available_stock}, Requested: {quantity}")
                
                # Increase reserved stock
                new_reserved = current_reserved + quantity
                self.supabase.table('product_variants').update({'reserved_stock': new_reserved}).eq('id', variant_id).execute()
        
        # Always reserve from total_stock on the product
        product = self.supabase.table('products').select('total_stock, reserved_stock').eq('id', product_id).limit(1).execute()
        if product.data:
            current_total = int(product.data[0].get('total_stock', 0))
            current_reserved = int(product.data[0].get('reserved_stock', 0))
            
            # Check if enough total stock is available
            available_total = current_total - current_reserved
            if available_total < quantity:
                raise Exception(f"Insufficient total stock. Available: {available_total}, Requested: {quantity}")
            
            # Increase reserved stock
            new_reserved = current_reserved + quantity
            self.supabase.table('products').update({'reserved_stock': new_reserved}).eq('id', product_id).execute()
    
    def _deduct_stock(self, product_id, variant_id, quantity):
        """Actually deduct stock when seller approves the order"""
        if variant_id:
            # Deduct from variant stock and reserved_stock
            variant = self.supabase.table('product_variants').select('stock, reserved_stock').eq('id', variant_id).limit(1).execute()
            if variant.data:
                current_stock = int(variant.data[0].get('stock', 0))
                current_reserved = int(variant.data[0].get('reserved_stock', 0))
                
                # Decrease both stock and reserved_stock
                new_stock = max(0, current_stock - quantity)
                new_reserved = max(0, current_reserved - quantity)
                self.supabase.table('product_variants').update({
                    'stock': new_stock,
                    'reserved_stock': new_reserved
                }).eq('id', variant_id).execute()
        
        # Deduct from product total_stock and reserved_stock
        product = self.supabase.table('products').select('total_stock, reserved_stock').eq('id', product_id).limit(1).execute()
        if product.data:
            current_total = int(product.data[0].get('total_stock', 0))
            current_reserved = int(product.data[0].get('reserved_stock', 0))
            
            # Decrease both total_stock and reserved_stock
            new_total = max(0, current_total - quantity)
            new_reserved = max(0, current_reserved - quantity)
            self.supabase.table('products').update({
                'total_stock': new_total,
                'reserved_stock': new_reserved
            }).eq('id', product_id).execute()
    
    def _finalize_delivery(self, order_id):
        """On delivery: record rider earnings and admin commission."""
        try:
            order = self.supabase.table('orders').select('rider_id, total_amount').eq('id', order_id).limit(1).execute()
            if not order.data:
                return
            rider_id    = order.data[0].get('rider_id')
            total       = float(order.data[0].get('total_amount') or 0)

            # Fetch configurable rates
            settings = self.supabase.table('admin_settings').select('key, value').in_('key', ['rider_rate']).execute()
            rates = {r['key']: r['value'] for r in (settings.data or [])}
            rider_rate = float(rates.get('rider_rate', 50))

            # Record rider earnings (fixed rate per delivery)
            if rider_id:
                self.supabase.table('rider_earnings').upsert({
                    'rider_id': rider_id,
                    'order_id': order_id,
                    'amount':   rider_rate
                }, on_conflict='rider_id,order_id').execute()
        except Exception as e:
            print(f"_finalize_delivery error: {e}")
    
    def cancel_order(self, order_id, user_id=None, is_admin=False):
        """Cancel an order and restore reserved stock"""
        # Get order details
        order = self.supabase.table('orders').select('status, buyer_id').eq('id', order_id).limit(1).execute()
        if not order.data:
            return None
        
        order_data = order.data[0]
        
        # Check permissions
        if not is_admin and order_data.get('buyer_id') != user_id:
            return None
        
        # Only allow cancellation of pending/processing orders
        if order_data.get('status') not in ['pending', 'processing']:
            return None
        
        # Release reserved stock for cancelled order
        items = self.supabase.table('order_items').select('product_id, variant_id, quantity').eq('order_id', order_id).execute()
        for item in (items.data or []):
            qty = int(item.get('quantity', 0))
            variant_id = item.get('variant_id')
            product_id = item.get('product_id')
            
            if variant_id:
                # Release variant reserved stock
                variant = self.supabase.table('product_variants').select('reserved_stock').eq('id', variant_id).limit(1).execute()
                if variant.data:
                    current_reserved = int(variant.data[0].get('reserved_stock', 0))
                    new_reserved = max(0, current_reserved - qty)
                    self.supabase.table('product_variants').update({'reserved_stock': new_reserved}).eq('id', variant_id).execute()
            
            # Release product total reserved stock
            product = self.supabase.table('products').select('reserved_stock').eq('id', product_id).limit(1).execute()
            if product.data:
                current_reserved = int(product.data[0].get('reserved_stock', 0))
                new_reserved = max(0, current_reserved - qty)
                self.supabase.table('products').update({'reserved_stock': new_reserved}).eq('id', product_id).execute()
        
        # Update order status to cancelled (we need to add this status to schema)
        result = self.supabase.table('orders').update({'status': 'cancelled'}).eq('id', order_id).execute()
        return result.data[0] if result.data else None

    def get_seller_stats(self, seller_id):
        """Return delivered-only sales stats for a seller."""
        product_result = self.supabase.table('products').select('id').eq('seller_id', seller_id).execute()
        product_ids = [p['id'] for p in (product_result.data or [])]
        if not product_ids:
            return {'total_orders': 0, 'items_sold': 0, 'total_revenue': 0.0,
                    'today_revenue': 0.0, 'week_revenue': 0.0, 'month_revenue': 0.0}

        # Get delivered order items for this seller's products
        items_result = self.supabase.table('order_items').select(
            'quantity, total_price, order:orders(status, created_at)'
        ).in_('product_id', product_ids).execute()

        from datetime import datetime, timezone, timedelta
        now   = datetime.now(timezone.utc)
        today = now.date()
        week_start  = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        total_orders_set = set()
        items_sold = 0
        total_revenue = 0.0
        today_revenue = 0.0
        week_revenue  = 0.0
        month_revenue = 0.0

        for item in (items_result.data or []):
            order = item.get('order') or {}
            if order.get('status') != 'delivered':
                continue
            qty   = int(item.get('quantity') or 0)
            price = float(item.get('total_price') or 0)
            items_sold    += qty
            total_revenue += price

            created_raw = order.get('created_at', '')
            try:
                created = datetime.fromisoformat(created_raw.replace('Z', '+00:00')).date()
            except Exception:
                continue

            if created == today:
                today_revenue += price
            if created >= week_start:
                week_revenue  += price
            if created >= month_start:
                month_revenue += price

        # Count distinct delivered orders containing seller products
        orders_result = self.supabase.table('order_items').select('order_id, order:orders(status)').in_('product_id', product_ids).execute()
        for item in (orders_result.data or []):
            if (item.get('order') or {}).get('status') == 'delivered':
                total_orders_set.add(item.get('order_id'))

        return {
            'total_orders':  len(total_orders_set),
            'items_sold':    items_sold,
            'total_revenue': total_revenue,
            'today_revenue': today_revenue,
            'week_revenue':  week_revenue,
            'month_revenue': month_revenue,
        }
    
    def get_all(self):
        """Get all orders (admin view)"""
        result = self.supabase.table('orders').select('*').order('created_at', desc=True).execute()
        orders = result.data if result.data else []
        # Fetch buyer and rider separately to avoid FK relationship issues
        for order in orders:
            if order.get('buyer_id'):
                buyer = self.supabase.table('users').select('first_name, last_name, email').eq('id', order['buyer_id']).single().execute()
                order['buyer'] = buyer.data if buyer.data else None
            if order.get('rider_id'):
                rider = self.supabase.table('users').select('first_name, last_name').eq('id', order['rider_id']).single().execute()
                order['rider'] = rider.data if rider.data else None
        return orders

    # Cart operations
    def get_cart_items(self, user_id):
        result = self.supabase.table('cart_items').select(
            '*, product:products(*, product_images(*)), variant:product_variants(*)'
        ).eq('user_id', user_id).order('created_at', desc=True).execute()
        return result.data if result.data else []

    def find_cart_item(self, user_id, product_id, variant_id=None):
        query = self.supabase.table('cart_items').select('*').eq('user_id', user_id).eq('product_id', product_id)
        if variant_id:
            query = query.eq('variant_id', variant_id)
        else:
            query = query.is_('variant_id', 'null')
        result = query.limit(1).execute()
        return result.data[0] if result.data else None

    def add_or_increment_cart_item(self, user_id, product_id, variant_id, quantity, price_snapshot):
        existing = self.find_cart_item(user_id, product_id, variant_id)
        if existing:
            new_qty = int(existing.get('quantity', 0) or 0) + int(quantity)
            result = self.supabase.table('cart_items').update({'quantity': new_qty}).eq('id', existing['id']).execute()
            return result.data[0] if result.data else None
        result = self.supabase.table('cart_items').insert({
            'user_id': user_id,
            'product_id': product_id,
            'variant_id': variant_id,
            'quantity': quantity,
            'price_snapshot': price_snapshot
        }).execute()
        return result.data[0] if result.data else None

    def update_cart_item_qty(self, user_id, item_id, quantity):
        result = self.supabase.table('cart_items').update({'quantity': quantity}).eq('id', item_id).eq('user_id', user_id).execute()
        return result.data[0] if result.data else None

    def remove_cart_item(self, user_id, item_id):
        self.supabase.table('cart_items').delete().eq('id', item_id).eq('user_id', user_id).execute()
        return True

    def clear_cart(self, user_id):
        self.supabase.table('cart_items').delete().eq('user_id', user_id).execute()
        return True
