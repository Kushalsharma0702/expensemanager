from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, Budget, Transaction
from sqlalchemy import func

superadmin_bp = Blueprint('superadmin', __name__)

@superadmin_bp.route('/allocate', methods=['POST'])
@login_required
def allocate_budget():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    admin_id = data.get('admin_id')
    amount = float(data.get('amount'))
    
    if not admin_id or not amount:
        return jsonify({'error': 'Admin ID and amount required'}), 400
    
    admin = User.query.get(admin_id)
    if not admin or admin.role != 'admin':
        return jsonify({'error': 'Invalid admin'}), 400
    
    # Update or create budget
    budget = Budget.query.filter_by(admin_id=admin_id).first()
    if budget:
        budget.allocated = amount
        budget.remaining = amount - budget.spent
    else:
        budget = Budget(admin_id=admin_id, allocated=amount)
        db.session.add(budget)
    
    # Log transaction
    transaction = Transaction(
        sender_id=current_user.id,
        receiver_id=admin_id,
        amount=amount,
        type='allocation'
    )
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({'message': 'Budget allocated successfully'}), 200

@superadmin_bp.route('/overview', methods=['GET'])
@login_required
def get_overview():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get all budgets with admin names
    budgets = db.session.query(Budget, User.name).join(User, Budget.admin_id == User.id).all()
    
    overview = []
    for budget, admin_name in budgets:
        overview.append({
            'admin_id': budget.admin_id,
            'admin_name': admin_name,
            'allocated': float(budget.allocated),
            'spent': float(budget.spent),
            'remaining': float(budget.remaining)
        })
    
    return jsonify({'budgets': overview}), 200

@superadmin_bp.route('/admins', methods=['GET'])
@login_required
def get_admins():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    admins = User.query.filter_by(role='admin').all()
    admin_list = [{'id': admin.id, 'name': admin.name, 'email': admin.email} for admin in admins]
    
    return jsonify({'admins': admin_list}), 200