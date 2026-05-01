from supabase import create_client
import os

class ProductModel:
    """Handles all product-related database operations"""
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
    
    def get_by_id(self, product_id):
        """Get product by ID with variants and images"""
        result = self.supabase.table('products').select(
            '*, seller:users!products_seller_id_fkey(id, first_name, last_name), product_variants (*), product_images (*)'
        ).eq('id', product_id).limit(1).execute()
        if not result.data:
            return None
        product = result.data[0]
        # Normalise image URLs so legacy local paths still resolve
        for img in product.get('product_images') or []:
            url = img.get('image_url', '')
            if url and not url.startswith('http') and not url.startswith('/'):
                img['image_url'] = '/' + url
        return product
    
    def get_by_id_and_seller(self, product_id, seller_id):
        """Get product by ID only if owned by seller"""
        result = self.supabase.table('products').select(
            '*, product_variants (*), product_images (*)'
        ).eq('id', product_id).eq('seller_id', seller_id).limit(1).execute()
        return result.data[0] if result.data else None
    
    def get_by_seller(self, seller_id):
        """Get all products for a seller"""
        query = self.supabase.table('products').select(
            '*, product_variants (*), product_images (*)'
        ).eq('seller_id', seller_id)
        result = query.order('created_at', desc=True).execute()
        return result.data if result.data else []
    
    def get_all_active(self, category=None):
        query = self.supabase.table('products').select(
            '*, seller:users!products_seller_id_fkey(first_name, last_name), product_images (*)'
        ).eq('status', 'active')
        if category:
            query = query.eq('category', category)
        result = query.order('created_at', desc=True).execute()
        products = result.data if result.data else []
        for p in products:
            for img in p.get('product_images') or []:
                url = img.get('image_url', '')
                if url and not url.startswith('http') and not url.startswith('/'):
                    img['image_url'] = '/' + url
        return products

    def get_all(self, status=None):
        """Get all products for admin, optional status filter"""
        query = self.supabase.table('products').select(
            '*, seller:users!products_seller_id_fkey(id, first_name, last_name, email, phone), product_variants (*), product_images (*)'
        )
        if status:
            query = query.eq('status', status)
        result = query.order('created_at', desc=True).execute()
        return result.data if result.data else []
    
    def create(self, product_data):
        """Create a new product"""
        result = self.supabase.table('products').insert(product_data).execute()
        return result.data[0] if result.data else None
    
    def update(self, product_id, seller_id, update_data):
        """Update product (only if owned by seller)"""
        result = self.supabase.table('products').update(update_data).eq('id', product_id).eq('seller_id', seller_id).execute()
        return result.data[0] if result.data else None

    def update_status(self, product_id, status, reviewed_by=None, reject_reason=None):
        payload = {'status': status}
        if status == 'rejected':
            payload['reject_reason'] = reject_reason
        else:
            payload['reject_reason'] = None
        result = self.supabase.table('products').update(payload).eq('id', product_id).execute()
        return result.data[0] if result.data else None
    
    def delete(self, product_id, seller_id):
        """Soft delete a product"""
        return self.update(product_id, seller_id, {'status': 'rejected'})
    
    # Variant methods
    def get_variants(self, product_id):
        """Get all variants for a product"""
        result = self.supabase.table('product_variants').select('*').eq('product_id', product_id).execute()
        return result.data if result.data else []
    
    def create_variant(self, variant_data):
        """Create a new variant"""
        result = self.supabase.table('product_variants').insert(variant_data).execute()
        return result.data[0] if result.data else None
    
    def update_variant_stock(self, variant_id, stock_delta):
        """Update variant stock (positive to add, negative to subtract)"""
        result = self.supabase.table('product_variants').select('stock').eq('id', variant_id).single().execute()
        if result.data:
            current_stock = result.data['stock']
            new_stock = max(0, current_stock + stock_delta)
            self.supabase.table('product_variants').update({'stock': new_stock}).eq('id', variant_id).execute()
            return new_stock
        return None
    
    # Image methods
    def get_images(self, product_id):
        """Get all images for a product"""
        result = self.supabase.table('product_images').select('*').eq('product_id', product_id).order('display_order').execute()
        return result.data if result.data else []
    
    def create_image(self, image_data):
        """Create a new product image"""
        result = self.supabase.table('product_images').insert(image_data).execute()
        return result.data[0] if result.data else None
    
    def set_primary_image(self, product_id, image_id):
        """Set the primary image for a product"""
        # Unset all primary images for this product
        self.supabase.table('product_images').update({'is_primary': False}).eq('product_id', product_id).execute()
        # Set the specified image as primary
        self.supabase.table('product_images').update({'is_primary': True}).eq('id', image_id).execute()
