import os
from app import app
from models import User, Budget, Expense, Transaction
from extensions import db
from werkzeug.security import generate_password_hash

with app.app_context():
    # Drop all tables and recreate
    db.drop_all()
    db.create_all()
    
    # Create test users
    superadmin = User(
        name='Super Admin',
        email='superadmin@test.com',
        password=generate_password_hash('password'),
        role='superadmin'
    )
    
    admin1 = User(
        name='Admin One',
        email='admin1@test.com',
        password=generate_password_hash('password'),
        role='admin'
    )
    
    admin2 = User(
        name='Admin Two',
        email='admin2@test.com',
        password=generate_password_hash('password'),
        role='admin'
    )
    
    employee1 = User(
        name='Employee One',
        email='employee1@test.com',
        password=generate_password_hash('password'),
        role='employee'
    )
    
    employee2 = User(
        name='Employee Two',
        email='employee2@test.com',
        password=generate_password_hash('password'),
        role='employee'
    )
    
    employee3 = User(
        name='Employee Three',
        email='employee3@test.com',
        password=generate_password_hash('password'),
        role='employee'
    )
    
    # Add users to session
    db.session.add_all([superadmin, admin1, admin2, employee1, employee2, employee3])
    db.session.commit()
    
    print("Database created and populated with test data!")
    print("\nTest accounts:")
    print("SuperAdmin: superadmin@test.com / password")
    print("Admin1: admin1@test.com / password")
    print("Admin2: admin2@test.com / password")
    print("Employee1: employee1@test.com / password")
    print("Employee2: employee2@test.com / password")
    print("Employee3: employee3@test.com / password")