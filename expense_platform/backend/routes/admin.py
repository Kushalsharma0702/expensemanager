from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, Budget, Expense, Transaction

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/expenses', methods=['GET'])
@login_required
def get_pending_expenses():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    expenses = Expense.query.filter_by(admin_id=current_user.id, status='pending').all()
    
    expense_list = []
    for expense in expenses:
        employee = User.query.get(expense.employee_id)
        expense_list.append({
            'id': expense.id,
            'employee_name': employee.name,
            'employee_email': employee.email,
            'amount': float(expense.amount),
            'reason': expense.reason,
            'created_at': expense.created_at.isoformat()
        })
    
    return jsonify({'expenses': expense_list}), 200

@admin_bp.route('/approve', methods=['POST'])
@login_required
def approve_expense():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    expense_id = data.get('expense_id')
    
    expense = Expense.query.get(expense_id)
    if not expense or expense.admin_id != current_user.id:
        return jsonify({'error': 'Expense not found'}), 404
    
    if expense.status != 'pending':
        return jsonify({'error': 'Expense already processed'}), 400
    
    # Update expense status
    expense.status = 'approved'
    
    # Update budget
    budget = Budget.query.filter_by(admin_id=current_user.id).first()
    if budget:
        budget.spent += expense.amount
        budget.remaining -= expense.amount
    
    # Log transaction
    transaction = Transaction(
        sender_id=current_user.id,
        receiver_id=expense.employee_id,
        amount=expense.amount,
        type='expense'
    )
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({'message': 'Expense approved successfully'}), 200

@admin_bp.route('/reject', methods=['POST'])
@login_required
def reject_expense():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    expense_id = data.get('expense_id')
    
    expense = Expense.query.get(expense_id)
    if not expense or expense.admin_id != current_user.id:
        return jsonify({'error': 'Expense not found'}), 404
    
    if expense.status != 'pending':
        return jsonify({'error': 'Expense already processed'}), 400
    
    expense.status = 'rejected'
    db.session.commit()
    
    return jsonify({'message': 'Expense rejected successfully'}), 200

@admin_bp.route('/budget', methods=['GET'])
@login_required
def get_budget():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    budget = Budget.query.filter_by(admin_id=current_user.id).first()
    if not budget:
        return jsonify({'error': 'No budget allocated'}), 404
    
    return jsonify({
        'allocated': float(budget.allocated),
        'spent': float(budget.spent),
        'remaining': float(budget.remaining)
    }), 200