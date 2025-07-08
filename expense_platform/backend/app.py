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

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost/expense_platform')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
CORS(app, supports_credentials=True)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(superadmin_bp, url_prefix='/superadmin')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(employee_bp, url_prefix='/employee')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Serve static files from frontend
@app.route('/')
def index():
    return send_from_directory('../frontend', 'login.html')

@app.route('/dashboard/superadmin')
@login_required
def dashboard_superadmin():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    return send_from_directory('../frontend', 'dashboard_superadmin.html')

@app.route('/dashboard/admin')
@login_required
def dashboard_admin():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    return send_from_directory('../frontend', 'dashboard_admin.html')

@app.route('/dashboard/employee')
@login_required
def dashboard_employee():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403
    return send_from_directory('../frontend', 'dashboard_employee.html')

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('../frontend/js', filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('../frontend/css', filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)