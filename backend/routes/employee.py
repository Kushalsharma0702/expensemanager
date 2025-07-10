from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import User, Budget, Expense, Transaction
from extensions import db
from sqlalchemy import func, case

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/admins')
@login_required
def get_admins():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get admins who have budget allocated
    admins = db.session.query(
        User.id,
        User.name,
        User.email,
        Budget.remaining
    ).join(Budget, User.id == Budget.admin_id).filter(
        User.role == 'admin',
        Budget.remaining > 0
    ).all()
    
    admin_data = []
    for admin in admins:
        admin_data.append({
            'id': admin.id,
            'name': admin.name,
            'email': admin.email,
            'available_budget': float(admin.remaining)
        })
    
    return jsonify({'admins': admin_data})

@employee_bp.route('/submit', methods=['POST'])
@login_required
def submit_expense():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    admin_id = data.get('admin_id')
    amount = data.get('amount')
    reason = data.get('reason')
    
    if not all([admin_id, amount, reason]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Verify admin exists and has budget
    admin = User.query.filter_by(id=admin_id, role='admin').first()
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    budget = Budget.query.filter_by(admin_id=admin_id).first()
    if not budget or budget.remaining < amount:
        return jsonify({'error': 'Admin has insufficient budget'}), 400
    
    # Create expense request
    expense = Expense(
        employee_id=current_user.id,
        admin_id=admin_id,
        amount=amount,
        reason=reason
    )
    db.session.add(expense)
    db.session.commit()
    
    return jsonify({'message': 'Expense request submitted successfully'})

@employee_bp.route('/myrequests')
@login_required
def get_my_requests():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get employee's expense requests
    expenses = db.session.query(
        Expense.id,
        Expense.amount,
        Expense.reason,
        Expense.status,
        Expense.created_at,
        User.name.label('admin_name'),
        User.email.label('admin_email')
    ).join(User, Expense.admin_id == User.id).filter(
        Expense.employee_id == current_user.id
    ).order_by(Expense.created_at.desc()).all()
    
    expenses_data = []
    for expense in expenses:
        expenses_data.append({
            'id': expense.id,
            'amount': float(expense.amount),
            'reason': expense.reason,
            'status': expense.status,
            'created_at': expense.created_at.isoformat(),
            'admin_name': expense.admin_name,
            'admin_email': expense.admin_email
        })
    
    return jsonify({'expenses': expenses_data})

@employee_bp.route('/stats')
@login_required
def get_stats():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get employee statistics - Fixed SQLAlchemy syntax
    stats = db.session.query(
        func.count(Expense.id).label('total_requests'),
        func.count(case((Expense.status == 'approved', 1), else_=None)).label('approved_requests'),
        func.count(case((Expense.status == 'pending', 1), else_=None)).label('pending_requests'),
        func.count(case((Expense.status == 'rejected', 1), else_=None)).label('rejected_requests'),
        func.sum(case((Expense.status == 'approved', Expense.amount), else_=0)).label('total_approved_amount')
    ).filter(Expense.employee_id == current_user.id).first()
    
    return jsonify({
        'total_requests': stats.total_requests or 0,
        'approved_requests': stats.approved_requests or 0,
        'pending_requests': stats.pending_requests or 0,
        'rejected_requests': stats.rejected_requests or 0,
        'total_approved_amount': float(stats.total_approved_amount or 0)
    })