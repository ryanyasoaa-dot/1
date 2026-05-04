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
        seller_application = self.app_model.get_by_user_id(seller_id)
        if not seller_application or seller_application.get('role') != 'seller' or seller_application.get('status') != 'approved':
            return {'success': False, 'error': 'Only approved sellers can add products.'}

        # Validate required fields
        name = form_data.get('name', '').strip()
        category = form_data.get('category', '').strip()
        description = form_data.get('description', '').strip() or None
        
        if not name:
            return {'success': False, 'error': 'Product name is required.'}
        if not category:
            return {'success': False, 'error': 'Category is required.'}
        
        valid_categories = ['Dresses & Skirts', 'Tops & Blouses', 'Activewear & Yoga Pants',
                            'Lingerie & Sleepwear', 'Jackets & Coats', 'Shoes & Accessories']
        if category not in valid_categories:
            return {'success': False, 'error': 'Invalid category.'}
        
        # Parse variants
        variants = self._parse_variants(form_data)
        if len(variants) == 0:
            return {'success': False, 'error': 'At least one variant is required.'}
        
        # Validate no duplicate variants and ensure all variants have prices
        seen = set()
        for v in variants:
            key = (v['variant_type'], v['value'])
            if key in seen:
                return {'success': False, 'error': f'Duplicate variant: {v["value"]}'}
            seen.add(key)
            
            # Validate variant price
            if v.get('price') is None or v.get('price') <= 0:
                return {'success': False, 'error': f'Variant {v["value"]} must have a valid price greater than 0.'}
        
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
                'total_stock': sum(v['stock'] for v in variants),
                'status': 'pending'
            }
            
            product = self.product_model.create(product_data)
            if not product:
                return {'success': False, 'error': 'Failed to create product.'}
            
            product_id = product['id']
            
            # Create variants and their images
            for v in variants:
                # SKU encodes the hex color so the frontend resolveColor() can read it
                hex_val = v.get('hex', '').strip()
                sku = f"{product_id[:8]}-{v['variant_type'][0].upper()}-{v['value']}"
                if hex_val:
                    sku += f"-{hex_val}"
                created_variant = self.product_model.create_variant({
                    'product_id':   product_id,
                    'variant_type': v['variant_type'],
                    'value':        v['value'],
                    'stock':        v['stock'],
                    'price':        v['price'],
                    'sku':          sku
                })
                if not created_variant:
                    # Variant creation failed — log and skip image save
                    print(f"[WARN] Failed to create variant {v['value']} for product {product_id}")
                    continue
                # Save per-variant image
                variant_img = files.get(f"variant_image_{v['index']}")
                if variant_img and variant_img.filename:
                    ext = variant_img.filename.rsplit('.', 1)[-1].lower()
                    if ext in {'png', 'jpg', 'jpeg', 'webp', 'gif'}:
                        path = self.file_service.save_file(variant_img, f'products/{seller_id}')
                        if path:
                            self.product_model.create_image({
                                'product_id':    product_id,
                                'image_url':     path,
                                'is_primary':    False,
                                'variant_id':    created_variant['id'],
                                'display_order': v['index']
                            })

            # Create general images
            for idx, path in enumerate(saved_image_paths):
                self.product_model.create_image({
                    'product_id':    product_id,
                    'image_url':     path,
                    'is_primary':    (idx == 0),
                    'variant_id':    None,
                    'display_order': idx
                })
            
            return {
                'success': True,
                'message': 'Product submitted for admin approval.',
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
        
                
        if 'status' in form_data:
            status = form_data.get('status')
            if status in ('pending', 'active', 'rejected'):
                update_data['status'] = status
        
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
        active_products = sum(1 for p in products if p.get('status') == 'active')
        pending_products = sum(1 for p in products if p.get('status') == 'pending')
        rejected_products = sum(1 for p in products if p.get('status') == 'rejected')
        total_stock = sum(p.get('total_stock', 0) for p in products)
        
        return {
            'total_products': total_products,
            'active_products': active_products,
            'pending_products': pending_products,
            'rejected_products': rejected_products,
            'total_stock': total_stock
        }
    
    def _parse_variants(self, form_data):
        """Parse variant data from form"""
        variants = []
        i = 0
        while True:
            v_type  = form_data.get(f'variants[{i}][type]')
            v_value = form_data.get(f'variants[{i}][value]', '').strip()
            v_hex   = form_data.get(f'variants[{i}][hex]', '').strip()
            v_price = form_data.get(f'variants[{i}][price]', '').strip()
            v_stock = form_data.get(f'variants[{i}][stock]', '0').strip()

            if not v_type or not v_value:
                break

            try:
                v_stock_int = max(0, int(v_stock))
            except ValueError:
                v_stock_int = 0

            try:
                v_price_val = float(v_price) if v_price else 0.0
                if v_price_val <= 0:
                    v_price_val = 0.0  # Will be validated later
            except ValueError:
                v_price_val = 0.0

            variants.append({
                'variant_type': v_type,
                'value':        v_value,
                'hex':          v_hex,
                'price':        v_price_val,
                'stock':        v_stock_int,
                'index':        i
            })
            i += 1
        return variants
