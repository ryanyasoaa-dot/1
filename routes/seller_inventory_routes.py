"""
seller_inventory_routes.py — Seller inventory management routes
Handles inventory dashboard, suppliers, purchase orders, and stock alerts
"""

from flask import Blueprint, render_template, request, jsonify, session
from models.inventory_model import InventoryModel
from models.product_model import ProductModel
from routes.api.api_helpers import api_response, api_error

seller_inventory_bp = Blueprint('seller_inventory', __name__)

@seller_inventory_bp.route('/inventory')
def inventory_dashboard():
    """Render inventory management dashboard."""
    try:
        seller_id = session.get('user', {}).get('id')
        if not seller_id:
            return render_template('auth/login.html')
        
        # Get inventory data for the dashboard
        inventory_model = InventoryModel()
        product_model = ProductModel()
        
        # Get basic stats
        stats = inventory_model.get_inventory_stats(seller_id)
        
        # Get low stock alerts
        alerts = inventory_model.get_low_stock_alerts(seller_id)
        
        # Get suppliers
        suppliers = inventory_model.get_suppliers(seller_id)
        
        # Get products for inventory table
        products = product_model.get_by_seller(seller_id)
        
        return render_template('seller/inventory.html', 
                             stats=stats, 
                             alerts=alerts, 
                             suppliers=suppliers,
                             products=products)
    except Exception as e:
        print(f"Error loading inventory dashboard: {e}")
        return render_template('seller/inventory.html', 
                             stats={}, 
                             alerts=[], 
                             suppliers=[],
                             products=[])

@seller_inventory_bp.route('/inventory/data')
def get_inventory_data():
    """API endpoint to get inventory data for dashboard."""
    try:
        seller_id = session.get('user', {}).get('id')
        if not seller_id:
            return api_error("Not authenticated", status=401)
        
        inventory_model = InventoryModel()
        product_model = ProductModel()
        
        # Get all products and variants for inventory
        products = product_model.get_by_seller(seller_id)
        inventory_items = []
        
        for product in products or []:
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
                "reserved_stock": 0,
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
        
        return api_response(data={"inventory": inventory_items}, message="OK", status=200)
    except Exception as e:
        return api_error(f"Failed to fetch inventory data: {e}", status=500)

@seller_inventory_bp.route('/inventory/stats')
def get_inventory_stats():
    """Get inventory statistics."""
    try:
        seller_id = session.get('user', {}).get('id')
        if not seller_id:
            return api_error("Not authenticated", status=401)
        
        inventory_model = InventoryModel()
        stats = inventory_model.get_inventory_stats(seller_id)
        
        return api_response(data={"stats": stats}, message="OK", status=200)
    except Exception as e:
        return api_error(f"Failed to fetch stats: {e}", status=500)

@seller_inventory_bp.route('/inventory/alerts')
def get_low_stock_alerts():
    """Get low stock alerts."""
    try:
        seller_id = session.get('user', {}).get('id')
        if not seller_id:
            return api_error("Not authenticated", status=401)
        
        inventory_model = InventoryModel()
        alerts = inventory_model.get_low_stock_alerts(seller_id)
        
        return api_response(data={"alerts": alerts}, message="OK", status=200)
    except Exception as e:
        return api_error(f"Failed to fetch alerts: {e}", status=500)

@seller_inventory_bp.route('/inventory/alerts/<alert_id>/resolve', methods=['POST'])
def resolve_low_stock_alert(alert_id):
    """Resolve a low stock alert."""
    try:
        seller_id = session.get('user', {}).get('id')
        if not seller_id:
            return api_error("Not authenticated", status=401)
        
        inventory_model = InventoryModel()
        success = inventory_model.resolve_low_stock_alert(alert_id, seller_id)
        
        if success:
            return api_response(message="Alert resolved successfully", status=200)
        else:
            return api_error("Failed to resolve alert", status=400)
    except Exception as e:
        return api_error(f"Failed to resolve alert: {e}", status=500)


@seller_inventory_bp.route('/inventory/reports')
def get_inventory_reports():
    """Get inventory reports."""
    try:
        seller_id = session.get('user', {}).get('id')
        if not seller_id:
            return api_error("Not authenticated", status=401)
        
        report_type = request.args.get('type', 'summary')
        
        # Generate different types of reports
        if report_type == 'summary':
            inventory_model = InventoryModel()
            stats = inventory_model.get_inventory_stats(seller_id)
            
            report = {
                "period": "Last 30 days",
                "total_products": stats.get("total_products", 0),
                "total_stock": stats.get("total_stock", 0),
                "total_value": stats.get("total_value", 0.0),
                "low_stock_items": stats.get("low_stock_count", 0),
                "out_of_stock_items": stats.get("out_of_stock_count", 0),
                "categories_performance": stats.get("categories_breakdown", {}),
                "stock_turnover": 0.0,  # Would calculate from sales data
                "dead_stock_value": 0.0  # Would calculate from slow-moving items
            }
        elif report_type == 'sales':
            # Mock sales report data
            report = {
                "period": "Last 30 days",
                "total_sales": 0,
                "top_selling_products": [],
                "sales_by_category": {},
                "sales_trend": []
            }
        elif report_type == 'stock':
            # Mock stock report data
            inventory_model = InventoryModel()
            alerts = inventory_model.get_low_stock_alerts(seller_id)
            
            report = {
                "period": "Last 30 days",
                "stock_movements": [],
                "low_stock_alerts": alerts,
                "reorder_recommendations": [],
                "stock_value_trend": []
            }
        else:
            return api_error("Invalid report type", status=400)
        
        return api_response(data={"report": report}, message="OK", status=200)
    except Exception as e:
        return api_error(f"Failed to generate report: {e}", status=500)

@seller_inventory_bp.route('/inventory/snapshots', methods=['POST'])
def create_inventory_snapshot():
    """Create an inventory snapshot."""
    try:
        seller_id = session.get('user', {}).get('id')
        if not seller_id:
            return api_error("Not authenticated", status=401)
        
        inventory_model = InventoryModel()
        success = inventory_model.create_inventory_snapshot(seller_id)
        
        if success:
            return api_response(message="Snapshot created successfully", status=201)
        else:
            return api_error("Failed to create snapshot", status=400)
    except Exception as e:
        return api_error(f"Failed to create snapshot: {e}", status=500)


@seller_inventory_bp.route('/inventory/check-alerts', methods=['POST'])
def check_and_create_alerts():
    """Check stock levels and create alerts."""
    try:
        seller_id = session.get('user', {}).get('id')
        if not seller_id:
            return api_error("Not authenticated", status=401)
        
        inventory_model = InventoryModel()
        alerts_created = inventory_model.check_and_create_alerts(seller_id)
        
        return api_response(
            data={"alerts_created": alerts_created}, 
            message=f"Created {alerts_created} new alerts", 
            status=200
        )
    except Exception as e:
        return api_error(f"Failed to check alerts: {e}", status=500)
