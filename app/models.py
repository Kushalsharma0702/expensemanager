from flask_login import UserMixin
from datetime import datetime
from extensions import db
from sqlalchemy import Index
from sqlalchemy.dialects.mysql import ENUM
from decimal import Decimal

# -------------------------
# 💡 User Model (user table)
# -------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    password = db.Column(db.Text, nullable=False)
    role = db.Column(ENUM('superadmin', 'admin', 'employee'), nullable=False, index=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)  

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- Relationships (Corrected) ---
    # Relationship for users created by this user
    created_users = db.relationship(
        'User',
        backref=db.backref('creator', foreign_keys='User.created_by'),
        foreign_keys='User.created_by',
        remote_side=[id]
    )

    # Relationship for employees supervised by this user (if this user is an admin)
    supervised_employees = db.relationship(
        'User',
        backref=db.backref('supervisor', foreign_keys='User.supervisor_id'),
        foreign_keys='User.supervisor_id',
        remote_side=[id]
    )

    # Relationship for expenses submitted by this user (employee)
    expenses = db.relationship(
        'Expense', 
        foreign_keys='Expense.employee_id',  # Explicitly specifies the foreign key to use
        backref='employee', 
        lazy=True, 
        cascade='all, delete-orphan'
    )

    # Other relationships
    budgets = db.relationship('Budget', backref='admin', lazy=True, cascade='all, delete-orphan')
    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.sender_id', back_populates='sender', lazy=True)
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.receiver_id', back_populates='receiver', lazy=True)
    employee_fund = db.relationship(
        'EmployeeFund',
        foreign_keys='EmployeeFund.employee_id',
        backref=db.backref('employee_user', lazy=True),
        uselist=False,
        lazy=True,
        cascade='all, delete-orphan'
    )
    managed_funds = db.relationship(
        'EmployeeFund',
        foreign_keys='EmployeeFund.admin_id',
        backref=db.backref('admin_user', lazy=True),
        lazy=True,
        cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f'<User {self.email}>'

# -------------------------
# 📊 Budget Model
# -------------------------
class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    total_budget = db.Column(db.Numeric(15, 2), default=Decimal('0.00'), nullable=False)
    total_spent = db.Column(db.Numeric(15, 2), default=Decimal('0.00'), nullable=False)
    remaining = db.Column(db.Numeric(15, 2), default=Decimal('0.00'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Budget for Admin {self.admin_id}>'

# -------------------------
# 💰 Expense Model
# -------------------------
class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(ENUM('pending', 'approved', 'rejected'), default='pending', nullable=False)
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    receipt_url = db.Column(db.String(255), nullable=True)
    document_path = db.Column(db.String(255), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    status = db.Column(ENUM('pending', 'approved', 'rejected'), default='pending', nullable=False)
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    admin = db.relationship('User', foreign_keys=[admin_id], backref=db.backref('reviewed_expenses', lazy=True))
    # Note: `employee` relationship is defined in the User model with backref

# -------------------------
# 💹 Transaction Model
# -------------------------
class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=True, index=True)
    type = db.Column(ENUM('allocation', 'expense', 'refund'), nullable=False, index=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    site_name = db.Column(db.String(100), nullable=True)

    sender = db.relationship('User', foreign_keys=[sender_id], back_populates='sent_transactions')
    receiver = db.relationship('User', foreign_keys=[receiver_id], back_populates='received_transactions')
    expense = db.relationship('Expense', backref='transactions')

# -------------------------
# 🏦 Employee Fund Model
# -------------------------
class EmployeeFund(db.Model):
    __tablename__ = 'employee_funds'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount_allocated = db.Column(db.Numeric(15, 2), default=Decimal('0.00'), nullable=False)
    amount_spent = db.Column(db.Numeric(15, 2), default=Decimal('0.00'), nullable=False)
    remaining_balance = db.Column(db.Numeric(15, 2), default=Decimal('0.00'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# -------------------------
# 🔍 Indexes (Performance)
# -------------------------
Index('idx_employee_funds_composite', EmployeeFund.employee_id, EmployeeFund.admin_id, unique=True)
Index('idx_expenses_employee', Expense.employee_id)
Index('idx_expenses_admin', Expense.admin_id)