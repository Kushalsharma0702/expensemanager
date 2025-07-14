import os
from flask import Flask, render_template, send_from_directory, jsonify, make_response
from flask_cors import CORS
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from extensions import db, login_manager
from models import User, Budget, Expense, Transaction
from routes.auth import auth_bp
from routes.superadmin import superadmin_bp
from routes.admin import admin_bp
from routes.employee import employee_bp
from routes.ai_insights import ai_insights_bp  # ADD THIS LINE
from dotenv import load_dotenv

load_dotenv()
# Before (relative path)
# app = Flask(__name__, static_folder='../frontend', static_url_path='/')

# ✅ After (absolute path works on all platforms)
# frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../frontend')
# app = Flask(__name__, static_folder=frontend_path, static_url_path='/')

app = Flask(__name__, static_folder="static", template_folder="templates")
# Convert DATABASE_URL to SQLALCHEMY_DATABASE_URI
if "SQLALCHEMY_DATABASE_URI" not in os.environ and "DATABASE_URL" in os.environ:
    os.environ["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]

# Secure & database configs
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-super-secret-key-here-change-this-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')  # ✅ fixed here
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session cookies
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24h

print("✅ Database URL:", app.config['SQLALCHEMY_DATABASE_URI'])

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.session_protection = 'strong'  # Enable strong session protection

# Enable CORS for frontend
CORS(app, 
     origins=['http://127.0.0.1:5000', 'http://localhost:5000'],
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Flask-Login unauthorized handler: redirect to /login for browser, JSON for API
@login_manager.unauthorized_handler
def unauthorized_callback():
    from flask import request, redirect, url_for
    if request.accept_mimetypes.accept_json:
        return make_response(jsonify({'error': 'Unauthorized'}), 401)
    return redirect('/login')

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(superadmin_bp, url_prefix='/superadmin')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(employee_bp, url_prefix='/employee')
app.register_blueprint(ai_insights_bp, url_prefix='/ai')  # ADD THIS LINE


# Serve login page for / and /login (GET)
@app.route('/')
@app.route('/login', methods=['GET'])
def serve_login():
    return render_template('login.html')

@app.route('/dashboard/<role>')
@login_required
def serve_dashboard(role):
    # Only allow access if user is authenticated and role matches
    if not current_user.is_authenticated:
        return send_from_directory(app.static_folder, 'login.html')
    if current_user.role != role:
        # Optionally, redirect to their correct dashboard
        return jsonify({'error': 'Forbidden'}), 403

    dashboard_files = {
        'superadmin': 'dashboard_superadmin.html',
        'admin': 'dashboard_admin.html',
        'employee': 'dashboard_employee.html'
    }

    if role in dashboard_files:
        return render_template(dashboard_files[role])
    else:
        return jsonify({'error': 'Invalid role'}), 404

# Serve JS files
@app.route('/js/<path:filename>')
def serve_js(filename):
    js_path = os.path.join(app.static_folder, 'js')
    return send_from_directory(js_path, filename)

# Serve CSS files if needed
@app.route('/css/<path:filename>')
def serve_css(filename):
    css_path = os.path.join(app.static_folder, 'css')
    return send_from_directory(css_path, filename)

# Add session status endpoint
@app.route('/session-status')
@login_required
def session_status():
    return jsonify({
        'authenticated': True,
        'user': {
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.email,
            'role': current_user.role
        }
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden - Access denied'}), 403

if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully!")
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
    
    # 🔥 Use Railway's port (8080) instead of 127.0.0.1
    app.run(host="0.0.0.0", debug=True, port=int(os.environ.get("PORT", 8080)))
