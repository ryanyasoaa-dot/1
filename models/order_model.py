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
        result = self.supabase.table('orders').select('*, buyer:users!inner(first_name, last_name, email), order_items(*, product:products(*))').eq('id', order_id).single().execute()
        return result.data if result.data else None
    
    def get_by_buyer(self, buyer_id):
        """Get all orders for a buyer"""
        result = self.supabase.table('orders').select('*, order_items(*, product:products(*))').eq('buyer_id', buyer_id).order('created_at', desc=True).execute()
        return result.data if result.data else []
    
    def get_by_seller(self, seller_id):
        """Get all orders for a seller (through their products)"""
        # Get all product IDs for this seller
        product_result = self.supabase.table('products').select('id').eq('seller_id', seller_id).execute()
        if not product_result.data:
            return []
        
        product_ids = [p['id'] for p in product_result.data]
        
        # Get orders containing these products
        result = self.supabase.table('order_items').select('*, order:orders(*, buyer:users(first_name, last_name))').in_('product_id', product_ids).execute()
        
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
        
        return list(orders_map.values())
    
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
    
    def get_all(self):
        """Get all orders (admin view)"""
        result = self.supabase.table('orders').select('*, buyer:users(first_name, last_name, email)').order('created_at', desc=True).execute()
        return result.data if result.data else []
