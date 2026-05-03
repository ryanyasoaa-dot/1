from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY')

    # ── Security configuration ────────────────────────────────
    from security import configure_session, init_csrf
    configure_session(app)
    
    # Supabase client (lazy-loaded in services)
    app.config['SUPABASE_URL'] = os.getenv('SUPABASE_URL')
    app.config['SUPABASE_SERVICE_ROLE_KEY'] = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    # Register blueprints
    from routes.auth_routes import auth_bp
    from routes.admin_routes import admin_bp
    from routes.seller_routes import seller_bp
    from routes.buyer_routes import buyer_bp
    from routes.rider_routes import rider_bp
    from routes.messages_routes import messages_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(seller_bp, url_prefix='/seller')
    app.register_blueprint(buyer_bp, url_prefix='/buyer')
    app.register_blueprint(rider_bp, url_prefix='/rider')
    app.register_blueprint(messages_bp)

    # Init CSRF AFTER blueprints are registered
    init_csrf(app)

    # Ensure csrf_token is always available in templates even if init_csrf fails
    @app.context_processor
    def inject_csrf():
        from security import generate_csrf_token
        return {'csrf_token': generate_csrf_token}
    
    # Main routes (static pages)
    @app.route('/')
    def index():
        from models.product_model import ProductModel
        product_model = ProductModel()
        products = product_model.get_all_active()
        return __import__('flask').render_template('buyer/index.html', products=products)

    @app.route('/api/products')
    def api_public_products():
        from flask import jsonify, request
        from models.product_model import ProductModel
        product_model = ProductModel()
        category = request.args.get('category', '').strip() or None
        products  = product_model.get_all_active(category=category)
        for p in products:
            images  = p.get('product_images') or []
            primary = next((img for img in images if img.get('is_primary')), images[0] if images else None)
            p['image'] = primary.get('image_url') if primary else None
        return jsonify(products)
    
    # Note: /login and /logout are handled by auth_bp blueprint
    # No need to duplicate them here
    
    return app

# For backward compatibility
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)