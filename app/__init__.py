import os
from flask import Flask, render_template, send_from_directory, jsonify, make_response
from flask_cors import CORS
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from extensions import db, login_manager
from app.models import User, Budget, Expense, Transaction
from app.routes.auth import auth_bp
from app.routes.superadmin import superadmin_bp
from app.routes.admin import admin_bp
from app.routes.employee import employee_bp
from app.routes.ai_insights import ai_insights_bp
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")

# Convert DATABASE_URL to SQLALCHEMY_DATABASE_URI
# Convert DATABASE_URL to SQLALCHEMY_DATABASE_URI
db_uri = os.getenv("DATABASE_URL")
if db_uri and db_uri.startswith("mysql://"):
    db_uri = db_uri.replace("mysql://", "mysql+pymysql://")

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-super-secret-key-here-change-this-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Define UPLOAD_FOLDER explicitly outside static, e.g., at the project root level
# This creates an 'uploads' directory parallel to your 'app.py' and 'static'
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    print(f"Created UPLOAD_FOLDER: {UPLOAD_FOLDER}")

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login' # Specify the login view for Flask-Login

# Set the session protection to 'strong' (or 'basic')
login_manager.session_protection = "strong"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(superadmin_bp, url_prefix='/superadmin')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(employee_bp, url_prefix='/employee')
app.register_blueprint(ai_insights_bp, url_prefix='/ai')

# Enable CORS for all routes by default
CORS(app,
     origins=["http://v21.in", "https://v21.in"], # Add localhost for development
     supports_credentials=True
     # You might not need to explicitly list allow_headers and methods if supports_credentials is True and default allows are sufficient
)

# Routes to serve your HTML dashboards
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/dashboard/<role>')
@login_required
def dashboard(role):
    if current_user.role == role:
        if role == 'superadmin':
            return render_template('dashboard_superadmin.html')
        elif role == 'admin':
            return render_template('dashboard_admin.html')
        elif role == 'employee':
            return render_template('dashboard_employee.html')
    else:
        # Redirect to their actual dashboard if role doesn't match
        return jsonify({'error': 'Invalid role for dashboard'}), 404

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
        # db.create_all() # Use create_db.py for initial setup and migrate_db.py for migrations
        print("💡 Consider running 'python create_db.py' once to set up the database and initial users.")
        print("💡 Use 'python migrate_db.py' for schema updates.")
import logging
logging.basicConfig(filename='logs/error.log', level=logging.WARNING)

app.run(host="0.0.0.0", debug=False, port=int(os.environ.get("PORT", 8080)))