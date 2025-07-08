from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, Expense

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/submit', methods=['POST'])
@login_required
def submit_expense():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    admin_id = data.get('admin_id')
    amount = float(data.get('amount'))
    reason = data.get('reason')
    
    if not admin_id or not amount or not reason:
        return jsonify({'error': 'Admin ID, amount, and reason required'}), 400
    
    admin = User.query.get(admin_id)
    if not admin or admin.role != 'admin':
        return jsonify({'error': 'Invalid admin'}), 400
    
    expense = Expense(
        employee_id=current_user.id,
        admin_id=admin_id,
        amount=amount,
        reason=reason
    )
    
    db.session.add(expense)
    db.session.commit()
    
    return jsonify({'message': 'Expense submitted successfully'}), 200

@employee_bp.route('/myrequests', methods=['GET'])
@login_required
def get_my_requests():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403
    
    expenses = Expense.query.filter_by(employee_id=current_user.id).all()
    
    expense_list = []
    for expense in expenses:
        admin = User.query.get(expense.admin_id)
        expense_list.append({
            'id': expense.id,
            'admin_name': admin.name,
            'amount': float(expense.amount),
            'reason': expense.reason,
            'status': expense.status,
            'created_at': expense.created_at.isoformat()
        })
    
    return jsonify({'expenses': expense_list}), 200

@employee_bp.route('/admins', methods=['GET'])
@login_required
def get_admins():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403
    
    admins = User.query.filter_by(role='admin').all()
    admin_list = [{'id': admin.id, 'name': admin.name, 'email': admin.email} for admin in admins]
    
    return jsonify({'admins': admin_list}), 200