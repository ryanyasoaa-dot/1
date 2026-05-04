"""
inventory_model.py — Inventory management database operations
Handles suppliers, purchase orders, low stock alerts, and inventory analytics
"""

from supabase import create_client, Client
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os

class InventoryModel:
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
    
    # ==================== LOW STOCK ALERTS ====================
    
    def get_low_stock_alerts(self, seller_id: str, unresolved_only: bool = True) -> List[Dict[str, Any]]:
        """Get low stock alerts for a seller."""
        try:
            query = self.supabase.table('low_stock_alerts').select('*').eq('seller_id', seller_id)
            if unresolved_only:
                query = query.eq('is_resolved', False)
            result = query.order('created_at', desc=True).execute()
            return result.data or []
        except Exception as e:
            print(f"Error fetching low stock alerts: {e}")
            return []
    
    def create_low_stock_alert(self, alert_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a low stock alert."""
        try:
            result = self.supabase.table('low_stock_alerts').insert(alert_data).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error creating low stock alert: {e}")
            return None
    
    def resolve_low_stock_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve a low stock alert."""
        try:
            result = self.supabase.table('low_stock_alerts').update({
                'is_resolved': True,
                'resolved_at': datetime.now().isoformat(),
                'resolved_by': resolved_by
            }).eq('id', alert_id).execute()
            return len(result.data or []) > 0
        except Exception as e:
            print(f"Error resolving low stock alert: {e}")
            return False
    
    def check_and_create_alerts(self, seller_id: str) -> int:
        """Check stock levels and create alerts for low stock items."""
        try:
            # This would typically call the database function
            # For now, implement the logic here
            
            # Get products with low stock
            products_result = self.supabase.table('products').select('*').eq('seller_id', seller_id).eq('status', 'active').execute()
            products = products_result.data or []
            
            alerts_created = 0
            
            for product in products:
                total_stock = product.get('total_stock', 0)
                threshold = product.get('low_stock_threshold', 10)
                
                if total_stock <= threshold and threshold > 0:
                    # Check if alert already exists and is unresolved
                    existing_alert = self.supabase.table('low_stock_alerts').select('*').eq('seller_id', seller_id).eq('product_id', product['id']).eq('variant_id', None).eq('is_resolved', False).execute()
                    
                    if not existing_alert.data:
                        # Create new alert
                        alert_data = {
                            'seller_id': seller_id,
                            'product_id': product['id'],
                            'variant_id': None,
                            'current_stock': total_stock,
                            'threshold': threshold
                        }
                        if self.create_low_stock_alert(alert_data):
                            alerts_created += 1
            
            # Check variants with low stock
            for product in products:
                variants_result = self.supabase.table('product_variants').select('*').eq('product_id', product['id']).execute()
                variants = variants_result.data or []
                
                for variant in variants:
                    stock = variant.get('stock', 0)
                    threshold = variant.get('low_stock_threshold', 10)
                    
                    if stock <= threshold and threshold > 0:
                        # Check if alert already exists
                        existing_alert = self.supabase.table('low_stock_alerts').select('*').eq('seller_id', seller_id).eq('product_id', product['id']).eq('variant_id', variant['id']).eq('is_resolved', False).execute()
                        
                        if not existing_alert.data:
                            # Create new alert
                            alert_data = {
                                'seller_id': seller_id,
                                'product_id': product['id'],
                                'variant_id': variant['id'],
                                'current_stock': stock,
                                'threshold': threshold
                            }
                            if self.create_low_stock_alert(alert_data):
                                alerts_created += 1
            
            return alerts_created
        except Exception as e:
            print(f"Error checking low stock alerts: {e}")
            return 0
    
    # ==================== INVENTORY ANALYTICS ====================
    
    def get_inventory_stats(self, seller_id: str) -> Dict[str, Any]:
        """Get comprehensive inventory statistics."""
        try:
            # Get all products and variants for the seller
            products_result = self.supabase.table('products').select('*').eq('seller_id', seller_id).eq('status', 'active').execute()
            products = products_result.data or []
            
            total_products = len(products)
            total_stock = 0
            total_value = 0.0
            low_stock_count = 0
            out_of_stock_count = 0
            categories_breakdown = {}
            
            for product in products:
                category = product.get('category', 'Uncategorized')
                stock = product.get('total_stock', 0)
                price = product.get('price', 0)
                
                total_stock += stock
                total_value += stock * price
                
                if category not in categories_breakdown:
                    categories_breakdown[category] = {'count': 0, 'stock': 0, 'value': 0.0}
                
                categories_breakdown[category]['count'] += 1
                categories_breakdown[category]['stock'] += stock
                categories_breakdown[category]['value'] += stock * price
                
                threshold = product.get('low_stock_threshold', 10)
                if stock == 0:
                    out_of_stock_count += 1
                elif stock <= threshold:
                    low_stock_count += 1
            
            # Get variant data
            for product in products:
                variants_result = self.supabase.table('product_variants').select('*').eq('product_id', product['id']).execute()
                variants = variants_result.data or []
                
                for variant in variants:
                    stock = variant.get('stock', 0)
                    price = variant.get('price', 0)
                    threshold = variant.get('low_stock_threshold', 10)
                    
                    total_stock += stock
                    total_value += stock * price
                    
                    if stock == 0:
                        out_of_stock_count += 1
                    elif stock <= threshold:
                        low_stock_count += 1
            
            return {
                'total_products': total_products,
                'total_stock': total_stock,
                'total_value': total_value,
                'low_stock_count': low_stock_count,
                'out_of_stock_count': out_of_stock_count,
                'categories_breakdown': categories_breakdown
            }
        except Exception as e:
            print(f"Error getting inventory stats: {e}")
            return {}
    
    def create_inventory_snapshot(self, seller_id: str) -> bool:
        """Create an inventory snapshot for analytics."""
        try:
            # Get all products and variants
            products_result = self.supabase.table('products').select('*').eq('seller_id', seller_id).eq('status', 'active').execute()
            products = products_result.data or []
            
            snapshot_date = datetime.now().isoformat()
            snapshots_created = 0
            
            for product in products:
                # Create product snapshot
                stock = product.get('total_stock', 0)
                price = product.get('price', 0)
                
                snapshot_data = {
                    'seller_id': seller_id,
                    'product_id': product['id'],
                    'variant_id': None,
                    'stock_level': stock,
                    'reserved_stock': 0,
                    'total_value': stock * price,
                    'snapshot_date': snapshot_date
                }
                
                result = self.supabase.table('inventory_snapshots').insert(snapshot_data).execute()
                if result.data:
                    snapshots_created += 1
                
                # Create variant snapshots
                variants_result = self.supabase.table('product_variants').select('*').eq('product_id', product['id']).execute()
                variants = variants_result.data or []
                
                for variant in variants:
                    stock = variant.get('stock', 0)
                    price = variant.get('price', 0)
                    reserved_stock = variant.get('reserved_stock', 0)
                    
                    variant_snapshot_data = {
                        'seller_id': seller_id,
                        'product_id': product['id'],
                        'variant_id': variant['id'],
                        'stock_level': stock,
                        'reserved_stock': reserved_stock,
                        'total_value': stock * price,
                        'snapshot_date': snapshot_date
                    }
                    
                    result = self.supabase.table('inventory_snapshots').insert(variant_snapshot_data).execute()
                    if result.data:
                        snapshots_created += 1
            
            return snapshots_created > 0
        except Exception as e:
            print(f"Error creating inventory snapshot: {e}")
            return False
    
    def get_inventory_snapshots(self, seller_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get inventory snapshots for the last N days."""
        try:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            result = self.supabase.table('inventory_snapshots').select('*').eq('seller_id', seller_id).gte('snapshot_date', start_date).order('snapshot_date', desc=True).execute()
            return result.data or []
        except Exception as e:
            print(f"Error fetching inventory snapshots: {e}")
            return []
    
    def get_inventory_settings(self, seller_id: str) -> Optional[Dict[str, Any]]:
        """Get inventory settings for a seller."""
        try:
            result = self.supabase.table('inventory_settings').select('*').eq('seller_id', seller_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error fetching inventory settings: {e}")
            return None
    
    def update_inventory_settings(self, seller_id: str, settings: Dict[str, Any]) -> bool:
        """Update inventory settings for a seller."""
        try:
            result = self.supabase.table('inventory_settings').update(settings).eq('seller_id', seller_id).execute()
            return len(result.data or []) > 0
        except Exception as e:
            print(f"Error updating inventory settings: {e}")
            return False
    
    def create_inventory_settings(self, seller_id: str, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create inventory settings for a seller."""
        try:
            settings['seller_id'] = seller_id
            result = self.supabase.table('inventory_settings').insert(settings).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error creating inventory settings: {e}")
            return None
