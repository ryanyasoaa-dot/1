from models.order_model import OrderModel
from models.product_model import ProductModel

class OrderService:
    """Handles order-related business logic"""
    
    def __init__(self):
        self.order_model = OrderModel()
        self.product_model = ProductModel()
    
    def create_order(self, buyer_id, items, address, payment_method='cod'):
        """Create a new order"""
        # Validate and calculate totals
        validated_items = []
        total_amount = 0
        
        for item in items:
            product_id = item.get('product_id')
            quantity = int(item.get('quantity', 1))
            variant_id = item.get('variant_id')
            
            if quantity <= 0:
                continue
            
            # Get product
            product = self.product_model.get_by_id(product_id)
            if not product or not product.get('is_active'):
                continue
            
            # Calculate item total
            item_price = float(product.get('price', 0))
            item_total = item_price * quantity
            total_amount += item_total
            
            validated_items.append({
                'product_id': product_id,
                'variant_id': variant_id,
                'quantity': quantity,
                'unit_price': item_price,
                'total_price': item_total
            })
        
        if len(validated_items) == 0:
            return {'success': False, 'error': 'No valid items in order.'}
        
        # Create order
        try:
            order_data = {
                'buyer_id': buyer_id,
                'total_amount': total_amount,
                'status': 'pending',
                'payment_method': payment_method,
                'shipping_address': address
            }
            
            order = self.order_model.create(order_data, validated_items)
            
            # Update product stocks (for variants)
            for item in validated_items:
                if item.get('variant_id'):
                    self.product_model.update_variant_stock(
                        item['variant_id'],
                        -item['quantity']
                    )
            
            return {
                'success': True,
                'message': 'Order created successfully!',
                'order': order
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_buyer_stats(self, buyer_id):
        """Get buyer order statistics"""
        orders = self.order_model.get_by_buyer(buyer_id)
        
        total_orders = len(orders)
        total_spent = sum(float(o.get('total_amount', 0)) for o in orders)
        
        status_counts = {'pending': 0, 'processing': 0, 'shipped': 0, 'delivered': 0, 'cancelled': 0}
        for order in orders:
            status = order.get('status', 'pending')
            if status in status_counts:
                status_counts[status] += 1
        
        return {
            'total_orders': total_orders,
            'total_spent': total_spent,
            'status_counts': status_counts
        }
    
    def get_cart(self, buyer_id):
        """Get buyer cart (for demo purposes)"""
        # In a real app, this would fetch from cart table/session
        return []
