import os
from flask import Flask
from extensions import db
from werkzeug.security import generate_password_hash
from app.models import User
from dotenv import load_dotenv
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

load_dotenv()

# ✅ Fix mysql:// to mysql+pymysql:// for SQLAlchemy
if "DATABASE_URL" in os.environ and os.environ["DATABASE_URL"].startswith("mysql://"):
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace("mysql://", "mysql+pymysql://")

# Convert DATABASE_URL to SQLALCHEMY_DATABASE_URI
if "SQLALCHEMY_DATABASE_URI" not in os.environ and "DATABASE_URL" in os.environ:
    os.environ["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]

# Create Flask app instance (same as in app.py)
app = Flask(__name__, static_folder="static", template_folder="templates")

# Configure the app (same as in app.py)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-super-secret-key-here-change-this-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)

def init_db():
    with app.app_context():
        print("📦 Dropping and creating all tables...")
        db.drop_all()
        db.create_all()

        default_password = 'password'

        try:
            # Create test users
            superadmin = User(
                name='Super supervisor',
                email='superadmin@test.com',
                phone='+1234567890',
                password=generate_password_hash(default_password),
                role='superadmin'
            )

            admin1 = User(
                name='supervisor One',
                email='supervisor1@test.com',
                phone='+1234567891',
                password=generate_password_hash(default_password),
                role='admin'
            )

            admin2 = User(
                name='supervisor Two',
                email='supervisor2@test.com',
                phone='+1234567892',
                password=generate_password_hash(default_password),
                role='admin'
            )

            employee1 = User(
                name='labour One',
                email='labour1@test.com',
                phone='+1234567893',
                password=generate_password_hash(default_password),
                role='employee'
            )

            employee2 = User(
                name='labour Two',
                email='labour2@test.com',
                phone='+1234567894',
                password=generate_password_hash(default_password),
                role='employee'
            )

            employee3 = User(
                name='labour Three',
                email='labour3@test.com',
                phone='+1234567895',
                password=generate_password_hash(default_password),
                role='employee'
            )

            db.session.add_all([superadmin, admin1, admin2, employee1, employee2, employee3])
            db.session.commit()

            print("✅ Database created and populated with test data!")
            print(f"\nAll users have the default password: {default_password}")
        except Exception as e:
            db.session.rollback()
            print("❌ Error during user insertion:", e)


        print("Database created and populated with test data!")
        print(f"\nAll users have the default password: {default_password}")
        print("\nTest accounts:")
        print(f"SuperAdmin: superadmin@test.com / {default_password}")
        print(f"Supervisor1: supervisor1@test.com / {default_password}")
        print(f"Supervisor2: supervisor2@test.com / {default_password}")
        print(f"Labour1: labour1@test.com / {default_password}")
        print(f"Labour2: labour2@test.com / {default_password}")
        print(f"Labour3: labour3@test.com / {default_password}")

if __name__ == "__main__":
    init_db()
