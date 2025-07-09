from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from models import User, Budget, Expense, Transaction
from extensions import db
from sqlalchemy import func
from decimal import Decimal

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
    amount = Decimal(str(data.get('amount')))
    
    if not admin_id or not amount:
        return jsonify({'error': 'Missing required fields'}), 400
    
    admin = User.query.filter_by(id=admin_id, role='admin').first()
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    # Check if budget already exists for this admin
    existing_budget = Budget.query.filter_by(admin_id=admin_id).first()
    
    if existing_budget:
        # Add to existing budget
        existing_budget.allocated += amount
        existing_budget.remaining += amount
    else:
        # Create new budget
        budget = Budget(admin_id=admin_id, allocated=amount)
        db.session.add(budget)
    
    # Create transaction record
    transaction = Transaction(
        sender_id=current_user.id,
        receiver_id=admin_id,
        amount=amount,
        type='allocation'
    )
    db.session.add(transaction)
    
    db.session.commit()
    
    return jsonify({'message': 'Budget allocated successfully'})

@superadmin_bp.route('/overview')
@login_required
def get_overview():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get budget overview
    budgets = db.session.query(
        Budget.id,
        Budget.allocated,
        Budget.spent,
        Budget.remaining,
        User.name.label('admin_name'),
        User.email.label('admin_email')
    ).join(User, Budget.admin_id == User.id).all()
    
    budget_data = []
    total_allocated = 0
    total_spent = 0
    
    for budget in budgets:
        usage_percentage = 0
        if budget.allocated > 0:
            usage_percentage = round((budget.spent / budget.allocated) * 100)
            
        budget_info = {
            'id': budget.id,
            'admin_name': budget.admin_name,
            'admin_email': budget.admin_email,
            'allocated': float(budget.allocated),
            'spent': float(budget.spent),
            'remaining': float(budget.remaining),
            'usage_percentage': usage_percentage
        }
        budget_data.append(budget_info)
        total_allocated += float(budget.allocated)
        total_spent += float(budget.spent)
    
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
        Transaction.timestamp,
        func.coalesce(User.name, 'Unknown').label('sender_name'),
        func.coalesce(User.email, 'Unknown').label('sender_email')
    ).outerjoin(User, Transaction.sender_id == User.id).order_by(Transaction.timestamp.desc()).limit(50).all()
    
    transaction_data = []
    
    # Process transactions
    for trans in transactions:
        # Get receiver name
        receiver = User.query.get(trans.id) if hasattr(trans, 'receiver_id') else None
        receiver_name = receiver.name if receiver else 'Unknown'
        
        transaction_data.append({
            'id': trans.id,
            'timestamp': trans.timestamp,
            'sender_name': trans.sender_name,
            'receiver_name': receiver_name,
            'amount': float(trans.amount),
            'type': trans.type,
            'reason': 'Budget Allocation' if trans.type == 'allocation' else 'Expense Payment'
        })
    
    return jsonify({'transactions': transaction_data})