from flask_login import UserMixin
from datetime import datetime
from extensions import db
from sqlalchemy import Index
from sqlalchemy.dialects.mysql import ENUM

# -------------------------
# 🚀 User Model (user table)
# -------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    password = db.Column(db.Text, nullable=False)
    role = db.Column(ENUM('superadmin', 'admin', 'employee'), nullable=False, index=True)

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_users = db.relationship('User', backref=db.backref('creator', remote_side=[id]))
    budgets = db.relationship('Budget', backref='admin', lazy=True)
    employee_funds = db.relationship('EmployeeFund', foreign_keys='EmployeeFund.employee_id', backref='employee', lazy=True)
    admin_funds = db.relationship('EmployeeFund', foreign_keys='EmployeeFund.admin_id', backref='admin_user', lazy=True)

    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.sender_id', back_populates='sender')
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.receiver_id', back_populates='receiver')

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

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

# -------------------------
# 💰 Budget Model
# -------------------------
class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False, index=True)
    total_budget = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    total_spent = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    remaining = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Budget for Admin {self.admin_id}: {self.remaining}>"

# -------------------------
# 🧾 EmployeeFund Model
# -------------------------
class EmployeeFund(db.Model):
    __tablename__ = 'employee_funds'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    amount_allocated = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    amount_spent = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    remaining_balance = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'admin_id', name='_employee_admin_uc'),
    )

    def __repr__(self):
        return f"<EmployeeFund Employee {self.employee_id} from Admin {self.admin_id}: {self.remaining_balance}>"

# -------------------------
# 📑 Expense Model
# -------------------------
class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    status = db.Column(ENUM('pending', 'approved', 'rejected'), default='pending', nullable=False, index=True)
    document_path = db.Column(db.String(500), nullable=True)
    site_name = db.Column(db.String(255), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Expense {self.id} by {self.employee_id} Status: {self.status}>"

# -------------------------
# 💳 Transaction Model
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
# 📊 Indexes (Performance)
# -------------------------
Index('idx_employee_funds_composite', EmployeeFund.employee_id, EmployeeFund.admin_id, unique=True)
Index('idx_expenses_employee_admin', Expense.employee_id, Expense.admin_id)
Index('idx_transactions_sender_receiver', Transaction.sender_id, Transaction.receiver_id)
Index('idx_transactions_type_timestamp', Transaction.type, Transaction.timestamp)
