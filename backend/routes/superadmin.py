from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from models import User, Budget, Expense, Transaction, EmployeeFund
from extensions import db
from sqlalchemy import func, case
from decimal import Decimal  # ADD THIS IMPORT
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

superadmin_bp = Blueprint('superadmin', __name__)

@superadmin_bp.route('/admins')
@login_required
def get_admins():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    admins = User.query.filter_by(role='admin').all()
    return jsonify({
        'admins': [{'id': admin.id, 'name': admin.name, 'email': admin.email} for admin in admins]
    })

@superadmin_bp.route('/allocate', methods=['POST'])
@login_required
def allocate_budget():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    admin_id = data.get('admin_id')
    amount = data.get('amount')
    
    if not admin_id or not amount:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # CRITICAL FIX: Convert to Decimal
        amount_decimal = Decimal(str(amount))
        
        admin = User.query.filter_by(id=admin_id, role='admin').first()
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
        
        # Check if budget already exists for this admin
        existing_budget = Budget.query.filter_by(admin_id=admin_id).first()
        
        if existing_budget:
            # Add to existing budget
            existing_budget.allocated += amount_decimal
            existing_budget.remaining += amount_decimal
        else:
            # Create new budget - FIXED: Set remaining = allocated
            budget = Budget(
                admin_id=admin_id, 
                allocated=amount_decimal,
                spent=Decimal('0'),
                remaining=amount_decimal
            )
            db.session.add(budget)
        
        # Create transaction record
        transaction = Transaction(
            sender_id=current_user.id,
            receiver_id=admin_id,
            amount=amount_decimal,
            type='allocation',
            description=f'Budget allocation to {admin.name}'
        )
        db.session.add(transaction)
        
        db.session.commit()
        
        return jsonify({'message': 'Budget allocated successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Allocate budget error: {str(e)}")
        return jsonify({'error': 'Failed to allocate budget'}), 500

@superadmin_bp.route('/overview')
@login_required
def get_overview():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403

    # LEFT OUTER JOIN to include all admins, even those without budgets
    admins = db.session.query(
        User.id,
        User.name,
        User.email,
        User.phone,
        Budget.allocated,
        Budget.spent,
        Budget.remaining
    ).outerjoin(Budget, User.id == Budget.admin_id).filter(
        User.role == 'admin'
    ).all()

    budget_data = []
    total_allocated = 0
    total_spent = 0

    for admin in admins:
        allocated = float(admin.allocated or 0)
        spent = float(admin.spent or 0)
        remaining = float(admin.remaining or 0)
        usage_percentage = round((spent / allocated) * 100) if allocated > 0 else 0

        budget_info = {
            'admin_id': admin.id,
            'admin_name': admin.name,
            'admin_email': admin.email,
            'admin_phone': admin.phone,
            'allocated': allocated,
            'spent': spent,
            'remaining': remaining,
            'usage_percentage': usage_percentage
        }
        budget_data.append(budget_info)
        total_allocated += allocated
        total_spent += spent

    # Get pending requests count
    pending_count = Expense.query.filter_by(status='pending').count()

    # Get active admins count (admins with allocated budget)
    active_admins = Budget.query.filter(Budget.allocated > 0).count()

    return jsonify({
        'budgets': budget_data,
        'stats': {
            'total_allocated': total_allocated,
            'total_spent': total_spent,
            'pending_expenses': pending_count,
            'active_admins': active_admins
        }
    })

@superadmin_bp.route('/transactions')
@login_required
def get_all_transactions():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get all transactions with user details
    transactions = db.session.query(
        Transaction.id,
        Transaction.amount,
        Transaction.type,
        Transaction.description,
        Transaction.timestamp,
        User.name.label('sender_name'),
        User.email.label('sender_email')
    ).join(User, Transaction.sender_id == User.id).order_by(Transaction.timestamp.desc()).limit(100).all()
    
    transaction_data = []
    
    # Process transactions
    for trans in transactions:
        # Get receiver details
        receiver_query = db.session.query(Transaction, User).join(
            User, Transaction.receiver_id == User.id
        ).filter(Transaction.id == trans.id).first()
        
        receiver_name = receiver_query[1].name if receiver_query else 'Unknown'
        
        transaction_data.append({
            'id': trans.id,
            'timestamp': trans.timestamp,
            'sender_name': trans.sender_name,
            'receiver_name': receiver_name,
            'amount': float(trans.amount),
            'type': trans.type,
            'reason': trans.description or ('Budget Allocation' if trans.type == 'allocation' else 'Expense Payment')
        })
    
    return jsonify({'transactions': transaction_data})

@superadmin_bp.route('/reports')
@login_required
def get_reports():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get date range (default to last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Get all transactions
    transactions = db.session.query(
        Transaction.id,
        Transaction.amount,
        Transaction.type,
        Transaction.description,
        Transaction.timestamp,
        User.name.label('sender_name'),
        User.email.label('sender_email')
    ).join(User, Transaction.sender_id == User.id).filter(
        Transaction.timestamp >= start_date
    ).order_by(Transaction.timestamp.desc()).all()
    
    # Get total allocations today
    today_allocations = db.session.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.type == 'allocation',
        func.date(Transaction.timestamp) == datetime.now().date()
    ).scalar() or 0
    
    # Get total expenses today
    today_expenses = db.session.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.type.in_(['expense', 'employee_fund']),
        func.date(Transaction.timestamp) == datetime.now().date()
    ).scalar() or 0
    
    # Get monthly summary
    monthly_summary = db.session.query(
        func.extract('month', Transaction.timestamp).label('month'),
        func.extract('year', Transaction.timestamp).label('year'),
        func.sum(case((Transaction.type == 'allocation', Transaction.amount), else_=0)).label('total_allocations'),
        func.sum(case((Transaction.type.in_(['expense', 'employee_fund']), Transaction.amount), else_=0)).label('total_expenses')
    ).filter(
        Transaction.timestamp >= start_date
    ).group_by(
        func.extract('month', Transaction.timestamp),
        func.extract('year', Transaction.timestamp)
    ).all()
    
    return jsonify({
        'today_summary': {
            'allocations': float(today_allocations),
            'expenses': float(today_expenses)
        },
        'transactions': [{
            'id': t.id,
            'sender_name': t.sender_name,
            'sender_email': t.sender_email,
            'amount': float(t.amount),
            'type': t.type,
            'description': t.description,
            'date': t.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        } for t in transactions],
        'monthly_summary': [{
            'month': int(m.month),
            'year': int(m.year),
            'total_allocations': float(m.total_allocations),
            'total_expenses': float(m.total_expenses)
        } for m in monthly_summary]
    })

@superadmin_bp.route('/add-employee', methods=['POST'])
@login_required
def add_employee():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    created_by = data.get('created_by')  # Admin ID
    if not all([name, email, password, phone, created_by]):
        return jsonify({'error': 'Name, email, phone, and password are required'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    user = User(
        name=name,
        email=email,
        phone=phone,
        password=generate_password_hash(password),
        role='employee',
        created_by=created_by
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Employee added successfully'})

@superadmin_bp.route('/edit-employee', methods=['PUT'])
@login_required
def edit_employee():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    employee_id = data.get('employee_id')
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    
    if not employee_id:
        return jsonify({'error': 'Employee ID is required'}), 400
    
    try:
        # Check if employee exists
        employee = User.query.filter_by(id=employee_id, role='employee').first()
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Check if email is already taken by another user
        if email and email != employee.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return jsonify({'error': 'Email already exists'}), 400
        
        # Update fields if provided
        if name:
            employee.name = name
        if email:
            employee.email = email
        if phone:
            employee.phone = phone
        if password:
            employee.password = generate_password_hash(password)
        
        employee.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Employee updated successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Edit employee error: {str(e)}")
        return jsonify({'error': 'Failed to update employee'}), 500

@superadmin_bp.route('/edit-admin', methods=['PUT'])
@login_required
def edit_admin():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    
    if not admin_id:
        return jsonify({'error': 'Admin ID is required'}), 400
    
    try:
        # Check if admin exists
        admin = User.query.filter_by(id=admin_id, role='admin').first()
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
        
        # Check if email is already taken by another user
        if email and email != admin.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return jsonify({'error': 'Email already exists'}), 400
        
        # Update fields if provided
        if name:
            admin.name = name
        if email:
            admin.email = email
        if phone:
            admin.phone = phone
        if password:
            admin.password = generate_password_hash(password)
        
        admin.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Admin updated successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Edit admin error: {str(e)}")
        return jsonify({'error': 'Failed to update admin'}), 500

@superadmin_bp.route('/add-client', methods=['POST'])
@login_required
def add_client():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password', 'password')
    if not all([name, email, phone, password]):
        return jsonify({'error': 'Name, email, phone, and password are required'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    user = User(
        name=name,
        email=email,
        phone=phone,
        password=generate_password_hash(password),
        role='admin',
        created_by=current_user.id
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Client (Admin) added successfully'})