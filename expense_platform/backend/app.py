import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from extensions import db, login_manager
from models import User, Budget, Expense, Transaction
from routes.auth import auth_bp
from routes.superadmin import superadmin_bp
from routes.admin import admin_bp
from routes.employee import employee_bp
from dotenv import load_dotenv

load_dotenv()

# Fix: Use correct path to frontend directory
app = Flask(__name__, static_folder='../frontend', static_url_path='/')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Debug: Print the paths to verify
print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
print(f"Static folder: {app.static_folder}")
print(f"Static folder absolute path: {os.path.abspath(app.static_folder)}")

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
CORS(app, supports_credentials=True)

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(superadmin_bp, url_prefix='/superadmin')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(employee_bp, url_prefix='/employee')

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --------------------------
# Routes to serve frontend
# --------------------------

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'login.html')

@app.route('/dashboard/superadmin')
@login_required
def dashboard_superadmin():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    return send_from_directory(app.static_folder, 'dashboard_superadmin.html')

@app.route('/dashboard/admin')
@login_required
def dashboard_admin():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    return send_from_directory(app.static_folder, 'dashboard_admin.html')

@app.route('/dashboard/employee')
@login_required
def dashboard_employee():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403
    return send_from_directory(app.static_folder, 'dashboard_employee.html')

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

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# --------------------------
# Start App
# --------------------------
if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
