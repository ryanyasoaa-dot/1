from models.product_model import ProductModel
from models.application_model import ApplicationModel
from services.file_upload_service import FileUploadService
import os

class ProductService:
    """Handles product-related business logic"""
    
    def __init__(self):
        self.product_model = ProductModel()
        self.app_model = ApplicationModel()
        self.file_service = FileUploadService()
    
    def create_product(self, seller_id, form_data, files):
        """Create a new product with variants and images"""
        # Validate required fields
        name = form_data.get('name', '').strip()
        category = form_data.get('category', '').strip()
        price = form_data.get('price', '').strip()
        description = form_data.get('description', '').strip() or None
        
        if not name:
            return {'success': False, 'error': 'Product name is required.'}
        if not category:
            return {'success': False, 'error': 'Category is required.'}
        
        valid_categories = ['Dresses & Skirts', 'Tops & Blouses', 'Activewear & Yoga Pants',
                            'Lingerie & Sleepwear', 'Jackets & Coats', 'Shoes & Accessories']
        if category not in valid_categories:
            return {'success': False, 'error': 'Invalid category.'}
        
        try:
            price_val = float(price)
            if price_val <= 0:
                return {'success': False, 'error': 'Price must be greater than 0.'}
        except (ValueError, TypeError):
            return {'success': False, 'error': 'Invalid price.'}
        
        # Parse variants
        variants = self._parse_variants(form_data)
        if len(variants) == 0:
            return {'success': False, 'error': 'At least one variant is required.'}
        
        # Validate no duplicate variants
        seen = set()
        for v in variants:
            key = (v['variant_type'], v['value'])
            if key in seen:
                return {'success': False, 'error': f'Duplicate variant: {v["value"]}'}
            seen.add(key)
        
        # Process images
        image_files = files.getlist('images[]')
        if len(image_files) == 0 or (len(image_files) == 1 and image_files[0].filename == ''):
            return {'success': False, 'error': 'At least one product image is required.'}
        
        saved_image_paths = []
        for f in image_files:
            if f and f.filename:
                ext = f.filename.rsplit('.', 1)[-1].lower()
                if ext in {'png', 'jpg', 'jpeg', 'webp', 'gif'}:
                    path = self.file_service.save_file(f, f'products/{seller_id}')
                    if path:
                        saved_image_paths.append(path)
        
        if len(saved_image_paths) == 0:
            return {'success': False, 'error': 'No valid images uploaded.'}
        
        # Create product
        try:
            product_data = {
                'seller_id': seller_id,
                'name': name,
                'description': description,
                'category': category,
                'price': price_val,
                'total_stock': sum(v['stock'] for v in variants),
                'is_active': True
            }
            
            product = self.product_model.create(product_data)
            if not product:
                return {'success': False, 'error': 'Failed to create product.'}
            
            product_id = product['id']
            
            # Create variants
            for v in variants:
                self.product_model.create_variant({
                    'product_id': product_id,
                    'variant_type': v['variant_type'],
                    'value': v['value'],
                    'stock': v['stock'],
                    'sku': f"{product_id[:8]}-{v['variant_type'][0].upper()}-{v['value']}"
                })
            
            # Create images
            for idx, path in enumerate(saved_image_paths):
                self.product_model.create_image({
                    'product_id': product_id,
                    'image_url': path,
                    'is_primary': (idx == 0),
                    'variant_id': None,
                    'display_order': idx
                })
            
            return {
                'success': True,
                'message': 'Product created successfully!',
                'product_id': product_id
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_product(self, product_id, seller_id, form_data, files):
        """Update an existing product"""
        # Verify ownership
        product = self.product_model.get_by_id_and_seller(product_id, seller_id)
        if not product:
            return {'success': False, 'error': 'Product not found or access denied.'}
        
        # Update basic info if provided
        update_data = {}
        if 'name' in form_data:
            name = form_data.get('name', '').strip()
            if name:
                update_data['name'] = name
        
        if 'description' in form_data:
            description = form_data.get('description', '').strip() or None
            update_data['description'] = description
        
        if 'price' in form_data:
            try:
                price_val = float(form_data.get('price', '').strip())
                if price_val > 0:
                    update_data['price'] = price_val
            except (ValueError, TypeError):
                pass
        
        if 'is_active' in form_data:
            update_data['is_active'] = form_data.get('is_active') == 'true'
        
        if update_data:
            self.product_model.update(product_id, seller_id, update_data)
        
        # Handle new images if uploaded
        image_files = files.getlist('images[]')
        if len(image_files) > 0 and not (len(image_files) == 1 and image_files[0].filename == ''):
            for f in image_files:
                if f and f.filename:
                    ext = f.filename.rsplit('.', 1)[-1].lower()
                    if ext in {'png', 'jpg', 'jpeg', 'webp', 'gif'}:
                        path = self.file_service.save_file(f, f'products/{seller_id}')
                        if path:
                            images = self.product_model.get_images(product_id)
                            is_primary = len(images) == 0
                            display_order = len(images)
                            self.product_model.create_image({
                                'product_id': product_id,
                                'image_url': path,
                                'is_primary': is_primary,
                                'variant_id': None,
                                'display_order': display_order
                            })
        
        return {'success': True, 'message': 'Product updated successfully!'}
    
    def get_seller_stats(self, seller_id):
        """Get seller statistics"""
        products = self.product_model.get_by_seller(seller_id)
        total_products = len(products)
        active_products = sum(1 for p in products if p.get('is_active'))
        total_stock = sum(p.get('total_stock', 0) for p in products)
        
        return {
            'total_products': total_products,
            'active_products': active_products,
            'total_stock': total_stock
        }
    
    def _parse_variants(self, form_data):
        """Parse variant data from form"""
        variants = []
        i = 0
        while True:
            v_type = form_data.get(f'variants[{i}][type]')
            v_value = form_data.get(f'variants[{i}][value]', '').strip()
            v_stock = form_data.get(f'variants[{i}][stock]', '0').strip()
            
            if not v_type or not v_value:
                break
            
            try:
                v_stock_int = int(v_stock)
                if v_stock_int < 0:
                    v_stock_int = 0
            except ValueError:
                v_stock_int = 0
            
            variants.append({
                'variant_type': v_type,
                'value': v_value,
                'stock': v_stock_int
            })
            i += 1
        
        return variants
