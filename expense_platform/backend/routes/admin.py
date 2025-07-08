from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import User, Budget, Expense, Transaction
from extensions import db
from sqlalchemy import func, case
from decimal import Decimal

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
def get_dashboard():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get admin's budget
    budget = Budget.query.filter_by(admin_id=current_user.id).first()
    if not budget:
        budget = Budget(admin_id=current_user.id, allocated=0)
        db.session.add(budget)
        db.session.commit()
    
    # Get pending expenses count
    pending_count = Expense.query.filter_by(admin_id=current_user.id, status='pending').count()
    
    return jsonify({
        'budget': {
            'total_budget': float(budget.allocated),
            'total_spent': float(budget.spent),
            'remaining': float(budget.remaining)
        },
        'pending_count': pending_count
    })

@admin_bp.route('/expenses')
@login_required
def get_expenses():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get pending expenses for this admin
    pending_expenses = db.session.query(
        Expense.id,
        Expense.amount,
        Expense.reason,
        Expense.created_at,
        User.name.label('employee_name'),
        User.email.label('employee_email')
    ).join(User, Expense.employee_id == User.id).filter(
        Expense.admin_id == current_user.id,
        Expense.status == 'pending'
    ).order_by(Expense.created_at.desc()).all()
    
    expenses_data = []
    for expense in pending_expenses:
        expenses_data.append({
            'id': expense.id,
            'employee_name': expense.employee_name,
            'employee_email': expense.employee_email,
            'amount': float(expense.amount),
            'reason': expense.reason,
            'created_at': expense.created_at.isoformat()
        })
    
    return jsonify({'expenses': expenses_data})

@admin_bp.route('/employee-stats')
@login_required
def get_employee_stats():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get employee statistics - Fixed the SQLAlchemy syntax
    stats = db.session.query(
        User.id,
        User.name,
        User.email,
        func.count(Expense.id).label('total_requests'),
        func.sum(Expense.amount).label('total_amount'),
        func.sum(case((Expense.status == 'approved', Expense.amount), else_=0)).label('approved_amount'),
        func.count(case((Expense.status == 'pending', 1), else_=None)).label('pending_count'),
        func.count(case((Expense.status == 'approved', 1), else_=None)).label('approved_count'),
        func.count(case((Expense.status == 'rejected', 1), else_=None)).label('rejected_count')
    ).outerjoin(Expense, User.id == Expense.employee_id).filter(
        User.role == 'employee'
    ).group_by(User.id, User.name, User.email).all()
    
    employee_data = []
    for stat in stats:
        employee_data.append({
            'id': stat.id,
            'name': stat.name,
            'email': stat.email,
            'total_requests': stat.total_requests or 0,
            'total_amount': float(stat.total_amount or 0),
            'approved_amount': float(stat.approved_amount or 0),
            'pending': stat.pending_count or 0,
            'approved': stat.approved_count or 0,
            'rejected': stat.rejected_count or 0
        })
    
    return jsonify({'employees': employee_data})

@admin_bp.route('/approve', methods=['POST'])
@login_required
def approve_expense():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    expense_id = data.get('expense_id')
    
    expense = Expense.query.filter_by(id=expense_id, admin_id=current_user.id).first()
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404
    
    if expense.status != 'pending':
        return jsonify({'error': 'Expense already processed'}), 400
    
    # Check if admin has sufficient budget
    budget = Budget.query.filter_by(admin_id=current_user.id).first()
    if not budget or budget.remaining < expense.amount:
        return jsonify({'error': 'Insufficient budget'}), 400
    
    # Update expense status
    expense.status = 'approved'
    
    # Update budget
    budget.spent += expense.amount
    budget.remaining -= expense.amount
    
    # Create transaction record
    transaction = Transaction(
        sender_id=current_user.id,
        receiver_id=expense.employee_id,
        amount=expense.amount,
        type='expense'
    )
    db.session.add(transaction)
    
    db.session.commit()
    
    return jsonify({'message': 'Expense approved successfully'})

@admin_bp.route('/reject', methods=['POST'])
@login_required
def reject_expense():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    expense_id = data.get('expense_id')
    
    expense = Expense.query.filter_by(id=expense_id, admin_id=current_user.id).first()
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404
    
    if expense.status != 'pending':
        return jsonify({'error': 'Expense already processed'}), 400
    
    expense.status = 'rejected'
    db.session.commit()
    
    return jsonify({'message': 'Expense rejected successfully'})