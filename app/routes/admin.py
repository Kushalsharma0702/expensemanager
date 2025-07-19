# admin.py
import os
import mimetypes
from flask import Blueprint, request, jsonify, current_app, make_response, send_from_directory
from flask_login import login_required, current_user
from app.models import User, Budget, Expense, Transaction, EmployeeFund
from extensions import db
from sqlalchemy import func, case, and_, or_
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from decimal import Decimal
import csv
from io import StringIO

admin_bp = Blueprint('admin', __name__)

# Allowed extensions for document uploads (adjust as needed)
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/dashboard')
@login_required
def get_dashboard():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        budget = Budget.query.filter_by(admin_id=current_user.id).first()
        if not budget:
            # If no budget is set, return default zero values and an empty pending expenses list
            return jsonify({
                'budget': {
                    'total_budget': 0,
                    'total_spent': 0, # This refers to admin's own spent budget
                    'remaining': 0
                },
                'pending_count': 0,
                'employees_count': 0,
                'total_allocated_to_employees': 0,
                'total_spent_by_employees': 0,
                'recent_pending_expenses': []
            })

        pending_expenses_count = Expense.query.filter_by(admin_id=current_user.id, status='pending').count()
        employees_count = User.query.filter_by(created_by=current_user.id, role='employee').count()

        # Total amount allocated to employees by this admin
        total_allocated_to_employees = db.session.query(func.sum(EmployeeFund.amount_allocated))\
            .filter_by(admin_id=current_user.id).scalar() or Decimal('0.00')
        
        # Total amount spent by employees under this admin's management
        total_spent_by_employees = db.session.query(func.sum(Expense.amount))\
            .filter(Expense.admin_id == current_user.id, Expense.status == 'approved').scalar() or Decimal('0.00')

        # Fetch recent pending expenses with employee details
        recent_pending_expenses = db.session.query(Expense, User.name, User.email)\
            .join(User, Expense.employee_id == User.id)\
            .filter(Expense.admin_id == current_user.id, Expense.status == 'pending')\
            .order_by(Expense.created_at.desc())\
            .limit(5)\
            .all()

        pending_expenses_list = []
        for expense, employee_name, employee_email in recent_pending_expenses:
            pending_expenses_list.append({
                'id': expense.id,
                'employee_name': employee_name,
                'employee_email': employee_email,
                'title': expense.title,
                'amount': float(expense.amount),
                'created_at': expense.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'site_name': expense.site_name
            })


        return jsonify({
            'budget': {
                'total_budget': float(budget.total_budget),
                'total_spent': float(budget.total_spent),
                'remaining': float(budget.remaining)
            },
            'pending_count': pending_expenses_count,
            'employees_count': employees_count,
            'total_allocated_to_employees': float(total_allocated_to_employees),
            'total_spent_by_employees': float(total_spent_by_employees),
            'recent_pending_expenses': pending_expenses_list
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching admin dashboard data: {e}")
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500

@admin_bp.route('/employees')
@login_required
def get_employees_managed_by_admin():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    employees = User.query.filter_by(created_by=current_user.id, role='employee').all()
    employee_list = []
    for employee in employees:
        fund = EmployeeFund.query.filter_by(employee_id=employee.id, admin_id=current_user.id).first()
        employee_list.append({
            'id': employee.id,
            'name': employee.name,
            'email': employee.email,
            'phone': employee.phone,
            'is_active': employee.is_active,
            'created_at': employee.created_at.strftime('%Y-%m-%d %H:%M:%S') if employee.created_at else None,
            'allocated_funds': float(fund.amount_allocated) if fund else 0.00,
            'spent_funds': float(fund.amount_spent) if fund else 0.00,
            'remaining_funds': float(fund.remaining_balance) if fund else 0.00
        })
    return jsonify({'employees': employee_list})

@admin_bp.route('/add-employee', methods=['POST'])
@login_required
def add_employee():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Employee with this email already exists'}), 409
    
    try:
        new_employee = User(
            name=name,
            email=email,
            phone=phone,
            password=generate_password_hash(password),
            role='employee',
            created_by=current_user.id, # Set created_by for new employees
            is_active=True
        )
        db.session.add(new_employee)
        db.session.commit()

        # Create an empty employee fund entry for the new employee
        new_fund = EmployeeFund(employee_id=new_employee.id, admin_id=current_user.id, amount_allocated=Decimal('0.00'), amount_spent=Decimal('0.00'), remaining_balance=Decimal('0.00'))
        db.session.add(new_fund)
        db.session.commit()
        
        return jsonify({'message': 'Employee added successfully', 'employee': {'id': new_employee.id, 'name': new_employee.name, 'email': new_employee.email}}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding employee: {e}")
        return jsonify({'error': 'Failed to add employee'}), 500

@admin_bp.route('/allocate-fund', methods=['POST'])
@login_required
def allocate_fund_to_employee():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    employee_id = data.get('employee_id')
    amount = data.get('amount')
    description = data.get('description', 'Fund allocation')
    site_name = data.get('site_name') # New field

    if not all([employee_id, amount, site_name]):
        return jsonify({'error': 'Missing required fields (employee_id, amount, site_name)'}), 400
    
    try:
        amount = Decimal(str(amount))
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400

        # Check if admin has sufficient budget
        admin_budget = Budget.query.filter_by(admin_id=current_user.id).first()
        if not admin_budget or admin_budget.remaining < amount:
            return jsonify({'error': 'Insufficient budget'}), 400

        employee = User.query.filter_by(id=employee_id, role='employee', created_by=current_user.id).first()
        if not employee:
            return jsonify({'error': 'Employee not found or not managed by you'}), 404
        
        fund = EmployeeFund.query.filter_by(employee_id=employee_id, admin_id=current_user.id).first()
        if not fund:
            fund = EmployeeFund(employee_id=employee_id, admin_id=current_user.id, amount_allocated=Decimal('0.00'), amount_spent=Decimal('0.00'), remaining_balance=Decimal('0.00'))
            db.session.add(fund)
            db.session.flush() # Ensure the new fund object is available for update

        fund.amount_allocated += amount
        fund.remaining_balance += amount
        fund.updated_at = datetime.utcnow()

        admin_budget.total_spent += amount # Admin's budget spent for allocation
        admin_budget.remaining -= amount
        admin_budget.updated_at = datetime.utcnow()

        # Record transaction for fund allocation
        transaction = Transaction(
            sender_id=current_user.id, # Admin is the sender
            receiver_id=employee_id,
            type='allocation',
            amount=amount,
            description=description,
            site_name=site_name
        )
        db.session.add(transaction)
        
        db.session.commit()
        
        return jsonify({'message': f'Fund of {amount} allocated to {employee.name} successfully', 'employee_id': employee.id}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error allocating fund: {e}")
        return jsonify({'error': 'Failed to allocate fund'}), 500

@admin_bp.route('/add-expense', methods=['POST'])
@login_required
def add_expense():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # This endpoint is typically for employees submitting, not admins adding directly.
    # Reconfirm if an admin can 'add' an expense on behalf of an employee or if this route
    # is repurposed for admins to approve (which is handled by other routes).
    # Assuming this route might be for an admin to log their *own* expense if they are also an employee.
    # If it's for employees, this route should be in employee.py.
    # Based on the prompt "Admins to handle expenses, including approving, rejecting, and tracking employee spending",
    # this route seems misplaced here if it's for 'adding' a new expense record.
    # I'll keep it for now but note that its functionality might overlap or be better placed.
    return jsonify({'message': 'This endpoint is typically for employee submission, not admin adding expenses directly.'}), 400

@admin_bp.route('/expenses/<int:expense_id>/details')
@login_required
def get_expense_details(expense_id):
    if current_user.role not in ['admin', 'superadmin']:
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        expense = Expense.query.get(expense_id)
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404

        # Admins can only view expenses they manage
        if current_user.role == 'admin' and expense.admin_id != current_user.id:
            return jsonify({'error': 'Forbidden - You can only view expenses managed by you'}), 403
        
        employee = User.query.get(expense.employee_id)
        admin = User.query.get(expense.admin_id)

        return jsonify({
            'id': expense.id,
            'employee_name': employee.name if employee else 'N/A',
            'employee_email': employee.email if employee else 'N/A',
            'admin_name': admin.name if admin else 'N/A',
            'title': expense.title,
            'description': expense.description,
            'amount': float(expense.amount),
            'status': expense.status,
            'document_path': expense.document_path,
            'site_name': expense.site_name,
            'created_at': expense.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': expense.updated_at.strftime('%Y-%m-%d %H:%M:%S') if expense.updated_at else None,
            'approved_at': expense.approved_at.strftime('%Y-%m-%d %H:%M:%S') if expense.approved_at else None
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching expense details: {e}")
        return jsonify({'error': 'Failed to fetch expense details'}), 500

@admin_bp.route('/expenses/<int:expense_id>/approve', methods=['POST'])
@login_required
def approve_expense(expense_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        expense = Expense.query.get(expense_id)
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
        
        if expense.admin_id != current_user.id:
            return jsonify({'error': 'Forbidden - You can only approve your own managed expenses'}), 403

        if expense.status != 'pending':
            return jsonify({'error': 'Expense is not in pending status'}), 400
        
        employee_fund = EmployeeFund.query.filter_by(employee_id=expense.employee_id, admin_id=current_user.id).first()
        if not employee_fund:
            return jsonify({'error': 'Employee fund not found for this admin'}), 404
        
        if employee_fund.remaining_balance < expense.amount:
            return jsonify({'error': 'Insufficient employee fund balance to approve this expense'}), 400
        
        # Update expense status
        expense.status = 'approved'
        expense.approved_at = datetime.utcnow()
        expense.updated_at = datetime.utcnow() # Update review timestamp

        # Update employee's allocated fund
        employee_fund.amount_spent += expense.amount
        employee_fund.remaining_balance -= expense.amount
        employee_fund.updated_at = datetime.utcnow()

        # Record transaction for expense approval
        transaction = Transaction(
            sender_id=expense.employee_id, # Employee is the sender
            receiver_id=expense.admin_id, # Admin is the receiver (for tracking)
            expense_id=expense.id,
            type='expense',
            amount=expense.amount,
            description=expense.title,
            site_name=expense.site_name
        )
        db.session.add(transaction)

        db.session.commit()
        
        return jsonify({'message': 'Expense approved successfully', 'expense_id': expense.id})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving expense: {e}")
        return jsonify({'error': 'Failed to approve expense'}), 500

@admin_bp.route('/expenses/<int:expense_id>/reject', methods=['POST'])
@login_required
def reject_expense(expense_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        expense = Expense.query.get(expense_id)
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
        if expense.admin_id != current_user.id:
            return jsonify({'error': 'Forbidden - You can only reject your own managed expenses'}), 403

        if expense.status != 'pending':
            return jsonify({'error': 'Expense is not in pending status'}), 400

        expense.status = 'rejected'
        expense.updated_at = datetime.utcnow() # Update review timestamp
        db.session.commit()

        # --- DELETE ASSOCIATED DOCUMENT ---
        if expense.document_path:
            try:
                upload_folder = current_app.config.get('UPLOAD_FOLDER')
                # Use os.path.basename to get just the filename from document_path
                # in case document_path stores a full path or a path from a different system
                file_path = os.path.join(upload_folder, os.path.basename(expense.document_path))
                if os.path.exists(file_path):
                    os.remove(file_path)
                    current_app.logger.info(f"Deleted document: {file_path}")
                else:
                    current_app.logger.warning(f"Document not found for deletion: {file_path}")
            except Exception as e:
                current_app.logger.error(f"Error deleting document {expense.document_path}: {e}")
        # --- END DELETE ---

        return jsonify({'message': 'Expense rejected successfully', 'expense_id': expense.id})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rejecting expense: {e}")
        return jsonify({'error': 'Failed to reject expense'}), 500

@admin_bp.route('/documents/<filename>')
@login_required
def serve_document(filename):
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not upload_folder:
        return jsonify({'error': 'Upload folder not configured'}), 500

    safe_filename = secure_filename(filename)
    file_path = os.path.join(upload_folder, safe_filename)

    if not os.path.exists(file_path):
        return jsonify({'error': 'Document not found'}), 404

    # --- ROBUST AUTHORIZATION CHECK ---
    # Check if the document belongs to an expense managed by the current admin
    expense = Expense.query.filter_by(document_path=os.path.join(upload_folder, safe_filename)).first()

    if not expense: # If no expense record found for this document_path
        current_app.logger.warning(f"Attempt to access unlinked document: {safe_filename}")
        return jsonify({'error': 'Document access denied (not linked to an expense)'}), 403

    # Allow access if current_user is superadmin, or is the admin managing this expense,
    # or is the employee who submitted this expense.
    if current_user.role == 'superadmin' or \
       expense.admin_id == current_user.id or \
       expense.employee_id == current_user.id:
        mimetype = mimetypes.guess_type(file_path)[0]
        if not mimetype:
            mimetype = 'application/octet-stream' # Default if type cannot be guessed
        return send_from_directory(upload_folder, safe_filename, mimetype=mimetype)
    else:
        return jsonify({'error': 'Unauthorized to view this document'}), 403

@admin_bp.route('/employee-transactions')
@login_required
def get_employee_transactions():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Get all transactions where the sender or receiver is an employee managed by this admin
        # This will include allocations from admin to employee and expenses by employee to admin
        transactions = db.session.query(
            Transaction,
            User.name.label('sender_name'),
            User.name.label('receiver_name'),
            Expense.document_path.label('document_path') # Get document path for expense type transactions
        ).outerjoin(User, Transaction.sender_id == User.id)\
        .outerjoin(Expense, Transaction.expense_id == Expense.id)\
        .filter(
            or_(
                # Transactions where this admin is the sender (allocations to their employees)
                and_(Transaction.sender_id == current_user.id, Transaction.type == 'allocation'),
                # Transactions where an employee managed by this admin is the sender (expenses)
                and_(Transaction.type == 'expense', Expense.admin_id == current_user.id, Expense.employee_id == Transaction.sender_id)
            )
        )\
        .order_by(Transaction.timestamp.desc()).all()

        transaction_list = []
        for transaction, sender_name, receiver_name, document_path in transactions:
            # Dynamically get receiver name for allocations
            if transaction.type == 'allocation' and transaction.receiver_id:
                receiver_user = User.query.get(transaction.receiver_id)
                receiver_name = receiver_user.name if receiver_user else 'N/A'
            elif transaction.type == 'expense' and transaction.receiver_id:
                receiver_user = User.query.get(transaction.receiver_id)
                receiver_name = receiver_user.name if receiver_user else 'N/A'
            elif transaction.type == 'expense' and transaction.expense_id:
                 # For expenses, the receiver is typically the admin, or implied as the company
                 # sender_name would be the employee
                 pass


            transaction_list.append({
                'id': transaction.id,
                'timestamp': transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'type': transaction.type,
                'amount': float(transaction.amount),
                'description': transaction.description,
                'sender_name': sender_name,
                'receiver_name': receiver_name, # This will be the admin for employee expenses
                'expense_id': transaction.expense_id,
                'document_link': f"/admin/documents/{os.path.basename(document_path)}" if document_path and transaction.type == 'expense' else None,
                'site_name': transaction.site_name
            })
        return jsonify({'transactions': transaction_list})
    except Exception as e:
        current_app.logger.error(f"Error fetching employee transactions: {e}")
        return jsonify({'error': 'Failed to fetch employee transactions'}), 500


@admin_bp.route('/export-employee-transactions-csv')
@login_required
def export_employee_transactions_csv():
    if current_user.role != 'admin':
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

        # Join with users to get employee names and filter by admin's managed employees
        transactions = db.session.query(
            Transaction,
            User.name.label('employee_name'),
            Expense.document_path.label('document_path')
        ).outerjoin(User, Transaction.sender_id == User.id)\
        .outerjoin(Expense, Transaction.expense_id == Expense.id)\
        .filter(
            or_(
                # Transactions where this admin is the sender (allocations to their employees)
                and_(Transaction.sender_id == current_user.id, Transaction.type == 'allocation'),
                # Transactions where an employee managed by this admin is the sender (expenses)
                and_(Transaction.type == 'expense', Expense.admin_id == current_user.id, Expense.employee_id == Transaction.sender_id)
            ),
            Transaction.timestamp >= start_date,
            Transaction.timestamp < end_date
        ).order_by(Transaction.timestamp.asc()).all()

        si = StringIO()
        cw = csv.writer(si)

        # CSV Header
        cw.writerow(['Serial No.', 'Date', 'Name (Labour)', 'Description', 'Amount', 'Supporting Document (Invoice/Bill) Link', 'Type', 'Site Name'])

        for i, (transaction, employee_name, document_path) in enumerate(transactions):
            # For allocations, the 'employee_name' from the join is the receiver.
            # For expenses, the 'employee_name' from the join is the sender.
            # Ensure the correct name is used.
            display_employee_name = employee_name if employee_name else 'N/A'

            document_link = ""
            if transaction.type == 'expense' and document_path:
                document_link = f"{request.url_root.rstrip('/')}/admin/documents/{os.path.basename(document_path)}"

            cw.writerow([
                i + 1, # Serial No.
                transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S'), # Date
                display_employee_name, # Name (Labour)
                transaction.description,
                str(transaction.amount),
                document_link,
                transaction.type.capitalize(), # Type (Allocated/Expense)
                transaction.site_name
            ])

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=employee_transactions_{start_date_str}_to_{end_date_str}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    except Exception as e:
        current_app.logger.error(f"Error exporting employee transactions CSV: {e}")
        return jsonify({'error': 'Failed to generate CSV report'}), 500