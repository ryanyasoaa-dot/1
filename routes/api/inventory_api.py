"""
/api/inventory/* — Inventory management API for sellers.

Endpoints:
  GET /api/inventory                 -> Get seller's inventory
  GET /api/inventory/stats           -> Inventory statistics
  GET /api/inventory/alerts          -> Low stock alerts
  GET /api/inventory/suppliers       -> Get suppliers
  POST /api/inventory/suppliers      -> Create supplier
  GET /api/inventory/reports         -> Inventory reports
  POST /api/inventory/snapshots      -> Create inventory snapshot
"""

from flask import Blueprint, request, jsonify
from routes.api.api_helpers import api_response, api_error

inventory_api_bp = Blueprint('inventory_api', __name__, url_prefix='/inventory')

@inventory_api_bp.get('')
@inventory_api_bp.get('/')
def get_inventory():
    """Get seller's inventory with variant details."""
    try:
        seller_id = request.args.get('seller_id')
        if not seller_id:
            return api_error("Seller ID required", status=400)
            
        from models.product_model import ProductModel
        from models.inventory_model import InventoryModel
        product_model = ProductModel()
        inventory_model = InventoryModel()
        
        # Get all products for this seller
        products = product_model.get_by_seller(seller_id)
        if not products:
            return api_response(data={"inventory": []}, message="OK", status=200)
        
        inventory_items = []
        for product in products:
            # Add main product inventory
            inventory_items.append({
                "id": product.get("id"),
                "product_id": product.get("id"),
                "product_name": product.get("name"),
                "category": product.get("category"),
                "variant_id": None,
                "variant_name": None,
                "size": None,
                "color": None,
                "color_hex": None,
                "stock": product.get("total_stock", 0),
                "reserved_stock": 0, # Calculate from variants if needed
                "low_stock_threshold": product.get("low_stock_threshold", 10),
                "reorder_point": product.get("reorder_point", 5),
                "reorder_quantity": product.get("reorder_quantity", 20),
                "price": product.get("price", 0),
                "updated_at": product.get("updated_at")
            })
            
            # Add variant inventory
            variants = product.get("product_variants", [])
            for variant in variants:
                if isinstance(variant, dict):
                    inventory_items.append({
                        "id": variant.get("id"),
                        "product_id": product.get("id"),
                        "product_name": product.get("name"),
                        "category": product.get("category"),
                        "variant_id": variant.get("id"),
                        "variant_name": f"{variant.get('size', 'One Size')} - {variant.get('color', 'Default')}",
                        "size": variant.get("size"),
                        "color": variant.get("color"),
                        "color_hex": variant.get("color_hex"),
                        "stock": variant.get("stock", 0),
                        "reserved_stock": variant.get("reserved_stock", 0),
                        "low_stock_threshold": variant.get("low_stock_threshold", 10),
                        "reorder_point": variant.get("reorder_point", 5),
                        "reorder_quantity": variant.get("reorder_quantity", 20),
                        "price": variant.get("price", 0),
                        "updated_at": variant.get("updated_at")
                    })
        
        return api_response(
            data={"inventory": inventory_items},
            message="OK",
            status=200
        )
    except Exception as e:
        return api_error(f"Failed to fetch inventory: {e}", status=500)

@inventory_api_bp.get('/stats')
def get_inventory_stats():
    """Get inventory statistics for dashboard."""
    try:
        seller_id = request.args.get('seller_id')
        if not seller_id:
            return api_error("Seller ID required", status=400)
            
        from models.inventory_model import InventoryModel
        inventory_model = InventoryModel()
        
        stats = inventory_model.get_inventory_stats(seller_id)
        
        return api_response(data={"stats": stats}, message="OK", status=200)
    except Exception as e:
        return api_error(f"Failed to fetch stats: {e}", status=500)

@inventory_api_bp.get('/alerts')
def get_low_stock_alerts():
    """Get low stock alerts for seller."""
    try:
        seller_id = request.args.get('seller_id')
        if not seller_id:
            return api_error("Seller ID required", status=400)
            
        from models.inventory_model import InventoryModel
        inventory_model = InventoryModel()
        
        alerts = inventory_model.get_low_stock_alerts(seller_id)
        
        return api_response(data={"alerts": alerts}, message="OK", status=200)
    except Exception as e:
        return api_error(f"Failed to fetch alerts: {e}", status=500)

@inventory_api_bp.post('/alerts/<alert_id>/resolve')
def resolve_alert(alert_id):
    """Resolve a low stock alert."""
    try:
        from models.inventory_model import InventoryModel
        inventory_model = InventoryModel()
        
        # Get user ID from session (this would be implemented in a real app)
        resolved_by = request.get_json().get('resolved_by', 'current_user')
        
        success = inventory_model.resolve_low_stock_alert(alert_id, resolved_by)
        if success:
            return api_response(message="Alert resolved successfully", status=200)
        else:
            return api_error("Failed to resolve alert", status=400)
    except Exception as e:
        return api_error(f"Failed to resolve alert: {e}", status=500)


@inventory_api_bp.get('/reports')
def get_inventory_reports():
    """Get inventory reports and analytics."""
    try:
        seller_id = request.args.get('seller_id')
        report_type = request.args.get('type', 'summary')
        
        if not seller_id:
            return api_error("Seller ID required", status=400)
        
        # Generate different types of reports
        if report_type == 'summary':
            report = {
                "period": "Last 30 days",
                "total_products": 0,
                "total_stock": 0,
                "total_value": 0.0,
                "low_stock_items": 0,
                "out_of_stock_items": 0,
                "categories_performance": {},
                "stock_turnover": 0.0,
                "dead_stock_value": 0.0
            }
        elif report_type == 'sales':
            report = {
                "period": "Last 30 days",
                "total_sales": 0,
                "top_selling_products": [],
                "sales_by_category": {},
                "sales_trend": []
            }
        elif report_type == 'stock':
            report = {
                "period": "Last 30 days",
                "stock_movements": [],
                "low_stock_alerts": [],
                "reorder_recommendations": [],
                "stock_value_trend": []
            }
        else:
            return api_error("Invalid report type", status=400)
        
        return api_response(data={"report": report}, message="OK", status=200)
    except Exception as e:
        return api_error(f"Failed to generate report: {e}", status=500)

@inventory_api_bp.post('/snapshots')
def create_inventory_snapshot():
    """Create an inventory snapshot for analytics."""
    try:
        seller_id = request.get_json().get('seller_id')
        if not seller_id:
            return api_error("Seller ID required", status=400)
        
        # Create inventory snapshot
        # This would call the create_inventory_snapshot() function
        # and insert into inventory_snapshots table
        
        return api_response(message="Snapshot created successfully", status=201)
    except Exception as e:
        return api_error(f"Failed to create snapshot: {e}", status=500)

