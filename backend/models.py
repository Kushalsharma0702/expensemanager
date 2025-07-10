from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from extensions import db
from sqlalchemy import Index

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    password = db.Column(db.Text, nullable=False)
    role = db.Column(db.Enum('superadmin', 'admin', 'employee', name='user_roles'), nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_users = db.relationship('User', backref=db.backref('creator', remote_side=[id]))
    budgets = db.relationship('Budget', backref='admin', lazy=True)
    employee_funds = db.relationship('EmployeeFund', foreign_keys='EmployeeFund.employee_id', backref='employee', lazy=True)
    admin_funds = db.relationship('EmployeeFund', foreign_keys='EmployeeFund.admin_id', backref='admin_user', lazy=True)
    
    # Flask-Login required methods
    def get_id(self):
        return str(self.id)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    @property
    def is_active_user(self):
        return self.is_active
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Budget(db.Model):
    __tablename__ = 'budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    allocated = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    spent = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    remaining = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EmployeeFund(db.Model):
    __tablename__ = 'employee_funds'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    allocated = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    spent = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    remaining = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    reason = db.Column(db.Text, nullable=False)  # <-- Add this line
    status = db.Column(db.Enum('pending', 'approved', 'rejected', name='expense_status'), 
                      default='pending', nullable=False, index=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewer_comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('User', foreign_keys=[employee_id], backref='submitted_expenses')
    admin_user = db.relationship('User', foreign_keys=[admin_id], backref='reviewed_expenses')

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=True, index=True)
    type = db.Column(db.Enum('allocation', 'expense', 'refund', name='transaction_type'), nullable=False, index=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_transactions')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_transactions')
    expense = db.relationship('Expense', backref='transactions')

# Add composite indexes for better query performance
Index('idx_employee_funds_composite', EmployeeFund.employee_id, EmployeeFund.admin_id)
Index('idx_expenses_composite', Expense.employee_id, Expense.status)
Index('idx_transactions_composite', Transaction.sender_id, Transaction.type, Transaction.created_at)