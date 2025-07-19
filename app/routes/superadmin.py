from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from app.models import User, Budget, Expense, Transaction, EmployeeFund
from extensions import db
from sqlalchemy import func, case
from sqlalchemy.orm import aliased
from decimal import Decimal
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import csv
from io import StringIO
from sqlalchemy import or_ # Import or_ for filtering

superadmin_bp = Blueprint('superadmin', __name__)

@superadmin_bp.route('/overview')
@login_required
def get_superadmin_overview():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        total_admins = User.query.filter_by(role='admin').count()
        total_employees = User.query.filter_by(role='employee').count()
        total_superadmins = User.query.filter_by(role='superadmin').count()
        total_users = User.query.count()

        total_budget_allocated = db.session.query(func.sum(Budget.total_budget)).scalar() or Decimal('0.00')
        total_budget_spent = db.session.query(func.sum(Budget.total_spent)).scalar() or Decimal('0.00')
        
        # Calculate total expenses across all employees and admins
        total_expenses_overall = db.session.query(func.sum(Expense.amount))\
            .filter(Expense.status == 'approved').scalar() or Decimal('0.00')

        # Get top 5 employees by expense amount
        top_employees = db.session.query(
            User.name,
            func.sum(Expense.amount).label('total_spent')
        ).join(Expense, User.id == Expense.employee_id)\
        .filter(Expense.status == 'approved')\
        .group_by(User.name)\
        .order_by(func.sum(Expense.amount).desc())\
        .limit(5).all()

        top_employees_data = [{'name': name, 'total_spent': float(total_spent)} for name, total_spent in top_employees]

        # Get overall transaction types distribution
        transaction_type_distribution = db.session.query(
            Transaction.type,
            func.count(Transaction.id)
        ).group_by(Transaction.type).all()

        transaction_type_data = {t_type: count for t_type, count in transaction_type_distribution}


        return jsonify({
            'total_users': total_users,
            'total_superadmins': total_superadmins,
            'total_admins': total_admins,
            'total_employees': total_employees,
            'total_budget_allocated': float(total_budget_allocated),
            'total_budget_spent': float(total_budget_spent),
            'total_expenses_overall': float(total_expenses_overall),
            'top_employees_by_expense': top_employees_data,
            'transaction_type_distribution': transaction_type_data
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching superadmin overview: {e}")
        return jsonify({'error': 'Failed to fetch overview data'}), 500

@superadmin_bp.route('/users')
@login_required
def get_users():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    users = User.query.all()
    user_list = []
    for user in users:
        user_list.append({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'role': user.role,
            'is_active': user.is_active,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None
        })
    return jsonify({'users': user_list})

@superadmin_bp.route('/all-users')
@login_required
def get_all_users():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    users = User.query.all()
    user_list = []
    for user in users:
        user_list.append({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'role': user.role,
            'is_active': user.is_active,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None
        })
    return jsonify({'users': user_list})

@superadmin_bp.route('/admins')
@login_required
def get_admins():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    admins = User.query.filter_by(role='admin').all()
    admin_list = []
    for admin in admins:
        budget = Budget.query.filter_by(admin_id=admin.id).first()
        admin_list.append({
            'id': admin.id,
            'name': admin.name,
            'email': admin.email,
            'phone': admin.phone,
            'is_active': admin.is_active,
            'created_at': admin.created_at.strftime('%Y-%m-%d %H:%M:%S') if admin.created_at else None,
            'total_budget': float(budget.total_budget) if budget else 0.00,
            'total_spent': float(budget.total_spent) if budget else 0.00,
            'remaining': float(budget.remaining) if budget else 0.00
        })
    return jsonify({'admins': admin_list})

@superadmin_bp.route('/employees')
@login_required
def get_employees():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    employees = User.query.filter_by(role='employee').all()
    employee_list = []
    for employee in employees:
        employee_list.append({
            'id': employee.id,
            'name': employee.name,
            'email': employee.email,
            'phone': employee.phone,
            'is_active': employee.is_active,
            'created_at': employee.created_at.strftime('%Y-%m-%d %H:%M:%S') if employee.created_at else None
        })
    return jsonify({'employees': employee_list})

@superadmin_bp.route('/add-user', methods=['POST'])
@login_required
def add_user():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    role = data.get('role')

    if not all([name, email, password, role]):
        return jsonify({'error': 'Missing required fields'}), 400
    if role not in ['admin', 'employee', 'superadmin']:
        return jsonify({'error': 'Invalid role specified'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'User with this email already exists'}), 409
    
    try:
        new_user = User(
            name=name,
            email=email,
            phone=phone,
            password=generate_password_hash(password),
            role=role,
            created_by=current_user.id, # Set created_by for new users
            is_active=True
        )
        db.session.add(new_user)
        db.session.commit()

        # If an admin is added, create an empty budget for them
        if role == 'admin':
            new_budget = Budget(admin_id=new_user.id, total_budget=Decimal('0.00'), total_spent=Decimal('0.00'), remaining=Decimal('0.00'))
            db.session.add(new_budget)
            db.session.commit()
        
        return jsonify({'message': f'{role.capitalize()} added successfully', 'user': {'id': new_user.id, 'name': new_user.name, 'email': new_user.email, 'role': new_user.role}}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding user: {e}")
        return jsonify({'error': 'Failed to add user'}), 500

@superadmin_bp.route('/update-user/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    try:
        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            if User.query.filter(User.email == data['email'], User.id != user_id).first():
                return jsonify({'error': 'Email already in use by another user'}), 409
            user.email = data['email']
        if 'phone' in data:
            user.phone = data['phone']
        if 'role' in data:
            if data['role'] not in ['admin', 'employee', 'superadmin']:
                return jsonify({'error': 'Invalid role specified'}), 400
            user.role = data['role']
        if 'password' in data and data['password']:
            user.password = generate_password_hash(data['password'])
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])

        user.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'User updated successfully', 'user': {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role}}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user: {e}")
        return jsonify({'error': 'Failed to update user'}), 500

from datetime import datetime, timezone  # add this import at the top

@superadmin_bp.route('/allocate-budget', methods=['POST'])
@login_required
def allocate_budget():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    admin_id = data.get('admin_id')
    amount = data.get('amount')
    site_name = data.get('site_name')  # ✅ new field

    # ✅ ensure all necessary fields are present
    if not all([admin_id, amount, site_name]):
        return jsonify({'error': 'Missing required fields'}), 400

    admin = User.query.get(admin_id)
    if not admin or admin.role != 'admin':
        return jsonify({'error': 'Invalid admin ID'}), 404

    # Allocate budget logic
    budget = Budget.query.filter_by(admin_id=admin_id).first()
    if budget:
        budget.amount += float(amount)
        budget.updated_at = datetime.utcnow()
    else:
        budget = Budget(admin_id=admin_id, amount=float(amount))
        db.session.add(budget)

    # ✅ real-time timestamp + site_name
    transaction = Transaction(
        sender_id=current_user.id,
        receiver_id=admin_id,
        type='allocation',
        amount=float(amount),
        description=f"Budget allocation to {admin.name} (Admin)",
        site_name=site_name,
        timestamp=datetime.now(timezone.utc)  # ✅ real-time UTC timestamp
    )
    db.session.add(transaction)
    db.session.commit()

    return jsonify({
        'message': f'₹{amount} allocated to {admin.name} for site “{site_name}”'
    }), 200

@superadmin_bp.route('/transactions')
@login_required
def get_transactions():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Aliases for clarity in joins
        Sender = aliased(User)
        Receiver = aliased(User)

        transactions = db.session.query(
            Transaction,
            Sender.name.label('sender_name'),
            Sender.email.label('sender_email'),
            Receiver.name.label('receiver_name'),
            Receiver.email.label('receiver_email')
        ).outerjoin(Sender, Transaction.sender_id == Sender.id)\
        .outerjoin(Receiver, Transaction.receiver_id == Receiver.id)\
        .order_by(Transaction.timestamp.desc()).all()

        transaction_list = []
        for transaction, sender_name, sender_email, receiver_name, receiver_email in transactions:
            transaction_list.append({
                'id': transaction.id,
                'timestamp': transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'type': transaction.type,
                'amount': float(transaction.amount),
                'description': transaction.description,
                'sender': {'id': transaction.sender_id, 'name': sender_name, 'email': sender_email},
                'receiver': {'id': transaction.receiver_id, 'name': receiver_name, 'email': receiver_email},
                'expense_id': transaction.expense_id,
                'site_name': transaction.site_name
            })
        return jsonify({'transactions': transaction_list})
    except Exception as e:
        current_app.logger.error(f"Error fetching transactions: {e}")
        return jsonify({'error': 'Failed to fetch transactions'}), 500

@superadmin_bp.route('/export-transactions-csv')
@login_required
def export_transactions_csv():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        start_date = datetime.min
        end_date = datetime.max

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1) # Include end day

        Sender = aliased(User)
        Receiver = aliased(User)

        transactions = db.session.query(
            Transaction,
            Sender.name.label('sender_name'),
            Sender.email.label('sender_email'),
            Receiver.name.label('receiver_name'),
            Receiver.email.label('receiver_email')
        ).outerjoin(Sender, Transaction.sender_id == Sender.id)\
        .outerjoin(Receiver, Transaction.receiver_id == Receiver.id)\
        .filter(
            Transaction.timestamp >= start_date,
            Transaction.timestamp < end_date
        ).order_by(Transaction.timestamp.asc()).all()

        si = StringIO()
        cw = csv.writer(si)

        # CSV Header
        cw.writerow(['Transaction ID', 'Timestamp', 'Type', 'Amount', 'Description', 'Sender Name', 'Sender Email', 'Receiver Name', 'Receiver Email', 'Site Name', 'Expense ID'])

        for transaction, sender_name, sender_email, receiver_name, receiver_email in transactions:
            cw.writerow([
                transaction.id,
                transaction.timestamp.isoformat(),
                transaction.type,
                str(transaction.amount),
                transaction.description,
                sender_name,
                sender_email,
                receiver_name,
                receiver_email,
                transaction.site_name,
                transaction.expense_id
            ])

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=transactions_{start_date_str}_to_{end_date_str}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    except Exception as e:
        current_app.logger.error(f"Error exporting transactions CSV: {e}")
        return jsonify({'error': 'Failed to generate CSV report'}), 500

@superadmin_bp.route('/user/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Superadmin cannot deactivate themselves
        if user.id == current_user.id:
            return jsonify({'error': 'Superadmin cannot deactivate their own account via this endpoint'}), 400

        user.is_active = not user.is_active
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        action = 'activated' if user.is_active else 'deactivated'
        return jsonify({'message': f'User {user.name} ({user.role}) {action} successfully', 'is_active': user.is_active})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling user status: {str(e)}")
        return jsonify({'error': 'Failed to toggle user status'}), 500