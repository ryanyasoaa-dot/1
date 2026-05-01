from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY')
    
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
    
    # Main routes (static pages)
    @app.route('/')
    def index():
        return __import__('flask').render_template('index.html')
    
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