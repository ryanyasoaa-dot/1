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
            '*, buyer:users!orders_buyer_id_fkey(first_name, last_name, email), rider:users!orders_rider_id_fkey(first_name, last_name), order_items(*, product:products(*), variant:product_variants(*))'
        ).eq('id', order_id).single().execute()
        return result.data if result.data else None
    
    def get_by_buyer(self, buyer_id):
        """Get all orders for a buyer"""
        result = self.supabase.table('orders').select(
            '*, rider:users!orders_rider_id_fkey(first_name, last_name), order_items(*, product:products(*), variant:product_variants(*))'
        ).eq('buyer_id', buyer_id).order('created_at', desc=True).execute()
        orders = result.data if result.data else []
        for order in orders:
            items = order.get('order_items') or []
            order['items_count'] = sum(int(i.get('quantity', 0) or 0) for i in items)
            order['total'] = order.get('total_amount', 0)
        return orders
    
    def get_by_seller(self, seller_id):
        """Get all orders for a seller (through their products)"""
        # Get all product IDs for this seller
        product_result = self.supabase.table('products').select('id').eq('seller_id', seller_id).execute()
        if not product_result.data:
            return []
        
        product_ids = [p['id'] for p in product_result.data]
        
        # Get orders containing these products
        result = self.supabase.table('order_items').select(
            '*, product:products(name, seller_id), variant:product_variants(value, variant_type), order:orders(*, buyer:users!orders_buyer_id_fkey(first_name, last_name), rider:users!orders_rider_id_fkey(first_name, last_name))'
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
        for order in orders:
            order['customer_name'] = f"{(order.get('buyer') or {}).get('first_name', '')} {(order.get('buyer') or {}).get('last_name', '')}".strip()
            order['items_count'] = sum(int(i.get('quantity', 0) or 0) for i in order.get('items', []))
            order['total'] = order.get('total_amount', 0)
        return orders
    
    def create(self, order_data, items_data):
        """Create a new order with items"""
        try:
            # Create order
            order_result = self.supabase.table('orders').insert(order_data).execute()
            order = order_result.data[0]
            
            # Create order items
            order_id = order['id']
            for item_data in items_data:
                item_data['order_id'] = order_id
                self.supabase.table('order_items').insert(item_data).execute()
            
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
        return self.update_status(order_id, new_status)

    def get_ready_for_pickup_orders(self):
        """Orders available for rider pickup"""
        result = self.supabase.table('orders').select(
            '*, buyer:users!orders_buyer_id_fkey(first_name, last_name), order_items(*, product:products(name, seller_id))'
        ).eq('status', 'ready_for_pickup').is_('rider_id', 'null').order('created_at', desc=True).execute()
        return result.data if result.data else []

    def get_assigned_orders_for_rider(self, rider_id):
        """Orders already accepted by this rider"""
        result = self.supabase.table('orders').select(
            '*, buyer:users!orders_buyer_id_fkey(first_name, last_name), order_items(*, product:products(name, seller_id))'
        ).eq('rider_id', rider_id).in_('status', ['in_transit', 'delivered']).order('created_at', desc=True).execute()
        return result.data if result.data else []

    def assign_rider(self, order_id, rider_id):
        """Assign rider and move status to in_transit (only from ready_for_pickup)"""
        result = self.supabase.table('orders').update({
            'rider_id': rider_id,
            'status': 'in_transit'
        }).eq('id', order_id).eq('status', 'ready_for_pickup').is_('rider_id', 'null').execute()
        return result.data[0] if result.data else None

    def update_status_for_rider(self, order_id, rider_id, new_status):
        """Rider can move in_transit -> delivered only"""
        if new_status != 'delivered':
            return None
        current = self.supabase.table('orders').select('status, rider_id').eq('id', order_id).eq('rider_id', rider_id).limit(1).execute()
        if not current.data:
            return None
        if current.data[0].get('status') != 'in_transit':
            return None
        result = self.supabase.table('orders').update({'status': 'delivered'}).eq('id', order_id).eq('rider_id', rider_id).execute()
        return result.data[0] if result.data else None
    
    def get_all(self):
        """Get all orders (admin view)"""
        result = self.supabase.table('orders').select('*, buyer:users(first_name, last_name, email)').order('created_at', desc=True).execute()
        return result.data if result.data else []

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
