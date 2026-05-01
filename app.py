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
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(seller_bp, url_prefix='/seller')
    app.register_blueprint(buyer_bp, url_prefix='/buyer')
    app.register_blueprint(rider_bp, url_prefix='/rider')

    # Init CSRF AFTER blueprints are registered
    init_csrf(app)
    
    # Main routes (static pages)
    @app.route('/')
    def index():
        from models.product_model import ProductModel
        product_model = ProductModel()
        products = product_model.get_all_active()
        return __import__('flask').render_template('index.html', products=products)

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
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        from routes.auth_routes import login as login_func
        return login_func()
    
    @app.route('/logout')
    def logout():
        from routes.auth_routes import logout as logout_func
        return logout_func()
    
    return app

# For backward compatibility
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)