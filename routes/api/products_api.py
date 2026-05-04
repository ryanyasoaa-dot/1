"""
/api/products/* — public product catalogue for Flutter.

Endpoints:
  GET /api/products           -> list active products (optional ?category=)
  GET /api/products/<id>      -> single product detail
"""

from flask import Blueprint, request

from routes.api.api_helpers import api_response, api_error, serialize_product

products_api_bp = Blueprint('products_api', __name__, url_prefix='/products')


@products_api_bp.get('')
@products_api_bp.get('/')
def list_products():
    try:
        from models.product_model import ProductModel
        category = (request.args.get('category') or '').strip() or None
        products = ProductModel().get_all_active(category=category)
        items = [serialize_product(p) for p in (products or [])]
        return api_response(
            data={"products": items, "count": len(items)},
            message="OK",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to fetch products: {e}", status=500)


@products_api_bp.get('/<product_id>')
def get_product(product_id):
    try:
        from models.product_model import ProductModel
        product = ProductModel().get_by_id(product_id)
        if not product:
            return api_error("Product not found", status=404)
        
        serialized = serialize_product(product)
        
        # Add variant grouping by size for better Flutter integration
        variants_by_size = {}
        for variant in serialized.get("variants", []):
            size = variant.get("size", "One Size")
            if size not in variants_by_size:
                variants_by_size[size] = []
            variants_by_size[size].append(variant)
        
        return api_response(
            data={
                "product": serialized,
                "variants_by_size": variants_by_size,
                "available_sizes": sorted(variants_by_size.keys()),
                "price_range": {
                    "min": min([v["final_price"] for v in serialized.get("variants", []) if v["final_price"] > 0], default=0),
                    "max": max([v["final_price"] for v in serialized.get("variants", []) if v["final_price"] > 0], default=0)
                }
            },
            message="OK",
            status=200,
        )
    except Exception as e:
        return api_error(f"Failed to fetch product: {e}", status=500)
