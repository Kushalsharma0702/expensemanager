from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import User, Budget, Expense, Transaction, EmployeeFund
from extensions import db
from sqlalchemy import func, case
from datetime import datetime
from werkzeug.security import generate_password_hash
from decimal import Decimal

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
def get_dashboard():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        budget = Budget.query.filter_by(admin_id=current_user.id).first()
        if not budget:
            return jsonify({
                'budget': {
                    'total_budget': 0,
                    'total_spent': 0,
                    'remaining': 0
                },
                'pending_count': 0,
                'employees_count': 0
            })

        # Calculate total funds allocated to employees
        total_allocated_to_employees = db.session.query(
            func.sum(EmployeeFund.allocated)
        ).filter(EmployeeFund.admin_id == current_user.id).scalar() or Decimal('0')

        # Calculate total spent by employees
        total_spent_by_employees = db.session.query(
            func.sum(EmployeeFund.spent)
        ).filter(EmployeeFund.admin_id == current_user.id).scalar() or Decimal('0')

        pending_count = Expense.query.filter_by(admin_id=current_user.id, status='pending').count()
        employees_count = User.query.filter_by(role='employee', created_by=current_user.id).count()

        return jsonify({
            'budget': {
                'total_budget': float(budget.allocated),
                'total_spent': float(total_allocated_to_employees),  # Amount allocated to employees
                'remaining': float(budget.remaining),  # Amount not yet allocated
                'employee_spent': float(total_spent_by_employees)  # Amount actually spent by employees
            },
            'pending_count': pending_count,
            'employees_count': employees_count
        })
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/stats')
@login_required
def get_stats():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        budget = Budget.query.filter_by(admin_id=current_user.id).first()
        if not budget:
            return jsonify({
                'total_budget': 0,
                'total_allocated': 0,
                'total_spent': 0,
                'total_remaining': 0,
                'pending_count': 0
            })

        # Calculate total funds allocated to employees
        total_allocated = db.session.query(
            func.sum(EmployeeFund.allocated)
        ).filter(EmployeeFund.admin_id == current_user.id).scalar() or Decimal('0')

        # Calculate total spent by employees
        total_spent = db.session.query(
            func.sum(EmployeeFund.spent)
        ).filter(EmployeeFund.admin_id == current_user.id).scalar() or Decimal('0')

        pending_count = Expense.query.filter_by(admin_id=current_user.id, status='pending').count()

        return jsonify({
            'total_budget': float(budget.allocated),
            'total_allocated': float(total_allocated),
            'total_spent': float(total_spent),
            'total_remaining': float(budget.remaining),
            'pending_count': pending_count
        })

    except Exception as e:
        current_app.logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/employees')
@login_required
def get_employees():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Get employees created by this admin with their fund info
        employees_data = db.session.query(
            User.id,
            User.name,
            User.email,
            User.phone,
            func.coalesce(EmployeeFund.allocated, 0).label('allocated_amount'),
            func.coalesce(EmployeeFund.spent, 0).label('spent_amount')
        ).outerjoin(
            EmployeeFund, 
            (EmployeeFund.employee_id == User.id) & (EmployeeFund.admin_id == current_user.id)
        ).filter(
            User.role == 'employee',
            User.created_by == current_user.id
        ).all()

        employees = []
        for emp in employees_data:
            employees.append({
                'id': emp.id,
                'name': emp.name,
                'email': emp.email,
                'phone': emp.phone,
                'allocated_amount': float(emp.allocated_amount),
                'spent_amount': float(emp.spent_amount)
            })

        return jsonify({'employees': employees})

    except Exception as e:
        current_app.logger.error(f"Error getting employees: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/edit-employee/<int:employee_id>', methods=['PUT'])
@login_required
def edit_employee(employee_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Check if employee exists and belongs to this admin
        employee = User.query.filter_by(
            id=employee_id,
            role='employee',
            created_by=current_user.id
        ).first()

        if not employee:
            return jsonify({'error': 'Employee not found'}), 404

        data = request.get_json()
        
        # Validate required fields
        if not data.get('name') or not data.get('email') or not data.get('phone'):
            return jsonify({'error': 'Name, email, and phone are required'}), 400

        # Check if email is already taken by another user
        existing_user = User.query.filter(
            User.email == data['email'],
            User.id != employee_id
        ).first()
        
        if existing_user:
            return jsonify({'error': 'Email already exists'}), 400

        # Update employee data
        employee.name = data['name'].strip()
        employee.email = data['email'].strip()
        employee.phone = data['phone'].strip()
        
        # Update password if provided
        if data.get('password'):
            employee.password_hash = generate_password_hash(data['password'])

        db.session.commit()

        return jsonify({'message': 'Employee updated successfully'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating employee: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/delete-employee/<int:employee_id>', methods=['DELETE'])
@login_required
def delete_employee(employee_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Check if employee exists and belongs to this admin
        employee = User.query.filter_by(
            id=employee_id,
            role='employee',
            created_by=current_user.id
        ).first()

        if not employee:
            return jsonify({'error': 'Employee not found'}), 404

        # Delete associated data
        # Delete employee fund allocations
        EmployeeFund.query.filter_by(employee_id=employee_id, admin_id=current_user.id).delete()
        
        # Delete expenses
        Expense.query.filter_by(employee_id=employee_id, admin_id=current_user.id).delete()
        
        # Delete transactions
        Transaction.query.filter_by(employee_id=employee_id, admin_id=current_user.id).delete()

        # Delete the employee
        db.session.delete(employee)
        db.session.commit()

        return jsonify({'message': 'Employee deleted successfully'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting employee: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/expenses')
@login_required
def get_expenses():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        expenses = db.session.query(
            Expense, User
        ).join(User, Expense.employee_id == User.id).filter(
            Expense.admin_id == current_user.id,
            Expense.status == 'pending'
        ).order_by(Expense.created_at.desc()).all()

        expenses_data = [{
            'id': exp.id,
            'employee_name': user.name,
            'employee_email': user.email,
            'amount': float(exp.amount),
            'reason': exp.reason,
            'created_at': exp.created_at.isoformat()
        } for exp, user in expenses]

        return jsonify({'expenses': expenses_data})
    except Exception as e:
        current_app.logger.error(f"Get expenses error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/pending-expenses')
@login_required
def get_pending_expenses():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        pending_expenses = db.session.query(
            Expense.id,
            Expense.amount,
            Expense.reason,
            Expense.date_created,
            User.name.label('employee_name')
        ).join(User, Expense.employee_id == User.id).filter(
            Expense.admin_id == current_user.id,
            Expense.status == 'pending'
        ).order_by(Expense.date_created.desc()).all()

        expenses = []
        for expense in pending_expenses:
            expenses.append({
                'id': expense.id,
                'amount': float(expense.amount),
                'reason': expense.reason,
                'date': expense.date_created.isoformat(),
                'employee_name': expense.employee_name
            })

        return jsonify({'expenses': expenses})

    except Exception as e:
        current_app.logger.error(f"Error getting pending expenses: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/approve-expense/<int:expense_id>', methods=['POST'])
@login_required
def approve_expense(expense_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        expense = Expense.query.filter_by(
            id=expense_id,
            admin_id=current_user.id,
            status='pending'
        ).first()

        if not expense:
            return jsonify({'error': 'Expense not found'}), 404

        # Check if employee has sufficient allocated funds
        employee_fund = EmployeeFund.query.filter_by(
            employee_id=expense.employee_id,
            admin_id=current_user.id
        ).first()

        if not employee_fund:
            return jsonify({'error': 'Employee has no allocated funds'}), 400

        remaining_funds = employee_fund.allocated - employee_fund.spent
        if remaining_funds < expense.amount:
            return jsonify({'error': 'Insufficient allocated funds'}), 400

        # Approve the expense
        expense.status = 'approved'
        expense.date_approved = datetime.utcnow()

        # Update employee fund spent amount
        employee_fund.spent += expense.amount

        # Create transaction record
        transaction = Transaction(
            employee_id=expense.employee_id,
            admin_id=current_user.id,
            amount=expense.amount,
            type='expense',
            description=expense.reason,
            status='approved'
        )
        db.session.add(transaction)

        db.session.commit()
        return jsonify({'message': 'Expense approved successfully'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving expense: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/reject-expense/<int:expense_id>', methods=['POST'])
@login_required
def reject_expense(expense_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        expense = Expense.query.filter_by(
            id=expense_id,
            admin_id=current_user.id,
            status='pending'
        ).first()

        if not expense:
            return jsonify({'error': 'Expense not found'}), 404

        # Reject the expense
        expense.status = 'rejected'
        expense.date_approved = datetime.utcnow()

        # Create transaction record
        transaction = Transaction(
            employee_id=expense.employee_id,
            admin_id=current_user.id,
            amount=expense.amount,
            type='expense',
            description=expense.reason,
            status='rejected'
        )
        db.session.add(transaction)

        db.session.commit()
        return jsonify({'message': 'Expense rejected successfully'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rejecting expense: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/allocate-fund', methods=['POST'])
@login_required
def allocate_fund():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    employee_id = data.get('employee_id')
    amount = data.get('amount', 0)
    
    if not employee_id or amount <= 0:
        return jsonify({'error': 'Missing or invalid fields'}), 400

    try:
        # CRITICAL FIX: Convert to Decimal immediately
        amount_decimal = Decimal(str(amount))
        
        # Check admin budget
        admin_budget = Budget.query.filter_by(admin_id=current_user.id).first()
        if not admin_budget or admin_budget.remaining < amount_decimal:
            return jsonify({'error': 'Insufficient admin funds'}), 400

        # Check employee exists
        employee = User.query.filter_by(id=employee_id, role='employee', created_by=current_user.id).first()
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404

        # Deduct from admin budget (Decimal + Decimal = Decimal)
        admin_budget.spent += amount_decimal
        admin_budget.remaining -= amount_decimal

        # Add to employee fund
        fund = EmployeeFund.query.filter_by(employee_id=employee_id, admin_id=current_user.id).first()
        if fund:
            fund.allocated += amount_decimal
            fund.remaining += amount_decimal
        else:
            fund = EmployeeFund(
                employee_id=employee_id, 
                admin_id=current_user.id, 
                allocated=amount_decimal, 
                remaining=amount_decimal,
                spent=Decimal('0')
            )
            db.session.add(fund)

        # Create transaction
        transaction = Transaction(
            sender_id=current_user.id,
            receiver_id=employee_id,
            amount=amount_decimal,
            type='allocation',
            description=f'Fund allocated to {employee.name}'
        )
        db.session.add(transaction)
        db.session.commit()
        return jsonify({'message': 'Fund allocated successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Allocate fund error: {str(e)}")
        return jsonify({'error': 'Failed to allocate fund'}), 500

@admin_bp.route('/add-employee', methods=['POST'])
@login_required
def add_employee():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')  # Add phone field
    password = data.get('password', 'password')
    
    if not all([name, email, phone]):  # Make phone required
        return jsonify({'error': 'Name, email, and phone are required'}), 400
    
    try:
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        user = User(
            name=name,
            email=email,
            phone=phone,  # Add phone field
            password=generate_password_hash(password),
            role='employee',
            created_by=current_user.id
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'Employee added successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add employee error: {str(e)}")
        return jsonify({'error': 'Failed to add employee'}), 500

@admin_bp.route('/add-expense', methods=['POST'])
@login_required
def add_expense():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    employee_id = data.get('employee_id')
    amount = data.get('amount')
    reason = data.get('reason')
    
    if not all([employee_id, amount, reason]):
        return jsonify({'error': 'All fields are required'}), 400
    
    try:
        # Convert to Decimal
        amount_decimal = Decimal(str(amount))
        
        # Check employee exists and belongs to this admin
        employee = User.query.filter_by(id=employee_id, role='employee', created_by=current_user.id).first()
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Check employee fund
        fund = EmployeeFund.query.filter_by(employee_id=employee_id, admin_id=current_user.id).first()
        if not fund or fund.remaining < amount_decimal:
            return jsonify({'error': 'Insufficient employee funds'}), 400
        
        # Create expense as approved (admin adding directly)
        expense = Expense(
            employee_id=employee_id,
            admin_id=current_user.id,
            amount=amount_decimal,
            reason=reason,
            status='approved',
            reviewed_at=datetime.utcnow()
        )
        
        # FIXED: Only deduct from employee fund, NOT from admin budget
        fund.spent += amount_decimal
        fund.remaining -= amount_decimal
        
        db.session.add(expense)
        
        # Create transaction
        transaction = Transaction(
            sender_id=current_user.id,
            receiver_id=employee_id,
            amount=amount_decimal,
            type='expense',
            description=f'Admin added expense: {reason}'
        )
        db.session.add(transaction)
        db.session.commit()
        return jsonify({'message': 'Expense added successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add expense error: {str(e)}")
        return jsonify({'error': 'Failed to add expense'}), 500

@admin_bp.route('/employee-stats')
@login_required
def get_employee_stats():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        employees = User.query.filter_by(role='employee', created_by=current_user.id).all()
        stats = []
        
        for emp in employees:
            # Get expense statistics for this employee
            expense_stats = db.session.query(
                func.count(Expense.id).label('total_requests'),
                func.sum(Expense.amount).label('total_amount'),
                func.count(case((Expense.status == 'approved', 1), else_=None)).label('approved'),
                func.count(case((Expense.status == 'pending', 1), else_=None)).label('pending'),
                func.count(case((Expense.status == 'rejected', 1), else_=None)).label('rejected'),
                func.sum(case((Expense.status == 'approved', Expense.amount), else_=0)).label('approved_amount')
            ).filter(
                Expense.employee_id == emp.id,
                Expense.admin_id == current_user.id
            ).first()
            
            stats.append({
                'id': emp.id,
                'name': emp.name,
                'email': emp.email,
                'phone': emp.phone,
                'total_requests': expense_stats.total_requests or 0,
                'total_amount': float(expense_stats.total_amount or 0),
                'approved': expense_stats.approved or 0,
                'pending': expense_stats.pending or 0,
                'rejected': expense_stats.rejected or 0,
                'approved_amount': float(expense_stats.approved_amount or 0)
            })
        
        return jsonify({'employees': stats})
    except Exception as e:
        current_app.logger.error(f"Get employee stats error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/reports')
@login_required
def get_reports():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        budget = Budget.query.filter_by(admin_id=current_user.id).first()
        if not budget:
            return jsonify({'error': 'No budget allocated'}), 404

        # Get employee funds with proper allocation vs spending
        employee_funds = db.session.query(
            User.name,
            EmployeeFund.allocated,
            EmployeeFund.spent,
            EmployeeFund.remaining
        ).join(
            EmployeeFund, User.id == EmployeeFund.employee_id
        ).filter(
            EmployeeFund.admin_id == current_user.id
        ).all()

        # Calculate totals
        total_allocated_to_employees = sum([float(ef.allocated) for ef in employee_funds])
        total_spent_by_employees = sum([float(ef.spent) for ef in employee_funds])

        # Get expenses summary
        expenses_summary = db.session.query(
            Expense.status,
            func.count(Expense.id).label('count')
        ).filter(
            Expense.admin_id == current_user.id
        ).group_by(Expense.status).all()

        return jsonify({
            'report_data': {
                'budget_summary': {
                    'total_budget': float(budget.allocated),
                    'allocated_to_employees': total_allocated_to_employees,
                    'spent_by_employees': total_spent_by_employees,
                    'remaining_with_admin': float(budget.remaining),
                    'utilization_percentage': round((total_spent_by_employees / total_allocated_to_employees) * 100, 2) if total_allocated_to_employees > 0 else 0
                },
                'employee_summary': {
                    'total_employees': len(employee_funds),
                    'total_funds_allocated': total_allocated_to_employees,
                    'total_funds_spent': total_spent_by_employees,
                    'total_funds_remaining': sum([float(ef.remaining) for ef in employee_funds])
                },
                'expenses_summary': {
                    'pending': next((e.count for e in expenses_summary if e.status == 'pending'), 0),
                    'approved': next((e.count for e in expenses_summary if e.status == 'approved'), 0),
                    'rejected': next((e.count for e in expenses_summary if e.status == 'rejected'), 0)
                },
                'employee_funds': [
                    {
                        'name': ef.name,
                        'allocated': float(ef.allocated),
                        'spent': float(ef.spent),
                        'remaining': float(ef.remaining),
                        'utilization_percentage': round((float(ef.spent) / float(ef.allocated)) * 100, 2) if ef.allocated > 0 else 0
                    } for ef in employee_funds
                ]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Get reports error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# NEW ENDPOINT: Get employee transactions for admin
@admin_bp.route('/employee-transactions')
@login_required
def get_employee_transactions():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        transactions = db.session.query(
            Transaction.amount,
            Transaction.type,
            Transaction.description,
            Transaction.created_at,
            User.name.label('employee_name')
        ).join(
            User, Transaction.receiver_id == User.id
        ).filter(
            Transaction.sender_id == current_user.id,
            Transaction.type.in_(['allocation', 'expense'])
        ).order_by(Transaction.created_at.desc()).limit(50).all()

        transaction_data = [{
            'date': t.created_at.isoformat(),
            'employee_name': t.employee_name,
            'amount': float(t.amount),
            'type': t.type.title(),
            'description': t.description
        } for t in transactions]

        return jsonify({'transactions': transaction_data})
    except Exception as e:
        current_app.logger.error(f"Get employee transactions error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Add missing PDF endpoint
@admin_bp.route('/employee-transactions-pdf')
@login_required
def get_employee_transactions_pdf():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from flask import make_response
        
        # Get transactions data
        transactions = db.session.query(
            Transaction.amount,
            Transaction.type,
            Transaction.description,
            Transaction.created_at,
            User.name.label('employee_name')
        ).join(
            User, Transaction.receiver_id == User.id
        ).filter(
            Transaction.sender_id == current_user.id,
            Transaction.type.in_(['allocation', 'expense'])
        ).order_by(Transaction.created_at.desc()).all()

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Sample style sheet
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(f"Employee Transactions Report - {current_user.name}", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Create table data
        data = [['Date', 'Employee', 'Amount (₹)', 'Type', 'Description']]
        
        for t in transactions:
            data.append([
                t.created_at.strftime('%Y-%m-%d'),
                t.employee_name,
                f"₹{float(t.amount):.2f}",
                t.type.title(),
                t.description[:50] + '...' if len(t.description) > 50 else t.description
            ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        # FileResponse
        buffer.seek(0)
        
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=employee_transactions_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        buffer.close()
        return response
        
    except ImportError:
        # If reportlab is not installed, return a simple text response
        return jsonify({'error': 'PDF generation not available. Please install reportlab: pip install reportlab'}), 500
    except Exception as e:
        current_app.logger.error(f"Generate PDF error: {str(e)}")
        return jsonify({'error': 'Failed to generate PDF'}), 500
