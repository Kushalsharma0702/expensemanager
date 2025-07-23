# routes/employee.py (or employee.py if in root)
import os
from flask import Blueprint, request, jsonify, current_app, make_response, send_from_directory
from flask_login import login_required, current_user
from app.models import User, Budget, Expense, Transaction, EmployeeFund
from extensions import db
from sqlalchemy import func, case
from decimal import Decimal
from datetime import datetime
from werkzeug.utils import secure_filename
import mimetypes

employee_bp = Blueprint('employee', __name__)

# Allowed extensions for document uploads
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@employee_bp.route('/admins')
@login_required
def get_admins():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403

    # Get admins who have budget allocated AND are managing this employee (created_by relationship)
    admins = db.session.query(
        User.id,
        User.name,
        User.email,
        Budget.remaining
    ).join(Budget, User.id == Budget.admin_id)\
    .filter(
        User.role == 'admin',
        Budget.remaining > 0,
        User.id == current_user.creator.id if current_user.creator else False # Filter for the employee's direct admin
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

@employee_bp.route('/dashboard')
@login_required
def get_employee_dashboard():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Get funds allocated to this employee by their admin
        # Assuming an employee is managed by only one admin for funding purposes
        employee_fund = EmployeeFund.query.filter_by(employee_id=current_user.id).first()
        
        # Get total expenses submitted by this employee
        total_expenses_submitted = db.session.query(func.sum(Expense.amount))\
            .filter_by(employee_id=current_user.id).scalar() or Decimal('0.00')
        
        # Get pending expenses count for this employee
        pending_expenses_count = Expense.query.filter_by(employee_id=current_user.id, status='pending').count()

        # Get the admin managing this employee
        managing_admin = None
        if current_user.created_by:
            managing_admin = User.query.get(current_user.created_by)

        return jsonify({
            'allocated_funds': float(employee_fund.amount_allocated) if employee_fund else 0.00,
            'remaining_balance': float(employee_fund.remaining_balance) if employee_fund else 0.00,
            'total_expenses_submitted': float(total_expenses_submitted),
            'pending_expenses_count': pending_expenses_count,
            'managing_admin': {
                'id': managing_admin.id,
                'name': managing_admin.name,
                'email': managing_admin.email
            } if managing_admin else None
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching employee dashboard data: {e}")
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500

@employee_bp.route('/submit-expense', methods=['POST'])
@login_required
def submit_expense():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if the employee has an associated admin and fund
    employee_fund = EmployeeFund.query.filter_by(employee_id=current_user.id).first()
    if not employee_fund or not employee_fund.admin_id:
        return jsonify({'error': 'No managing admin or fund found. Cannot submit expense.'}), 400

    admin_id_for_expense = employee_fund.admin_id

    # Handle file upload if present
    file = None
    if 'document' in request.files:
        file = request.files['document']
        if file.filename == '':
            file = None # No file selected
        elif not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: pdf, png, jpg, jpeg'}), 400

    title = request.form.get('title')
    amount = request.form.get('amount')
    site_name = request.form.get('site_name')
    description = request.form.get('description')

    if not all([title, amount]):
        return jsonify({'error': 'Missing required fields (title, amount)'}), 400
    try:
        amount = Decimal(str(amount))
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
        document_path = None
        if file:
            filename = secure_filename(file.filename)
            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            if not upload_folder:
                return jsonify({'error': 'Upload folder not configured'}), 500
            base, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            unique_filename = f"{base}_{timestamp}{ext}"
            file_save_path = os.path.join(upload_folder, unique_filename)
            file.save(file_save_path)
            document_path = unique_filename # Store only the filename
        new_expense = Expense(
            employee_id=current_user.id,
            admin_id=admin_id_for_expense,
            title=title,
            amount=amount,
            site_name=site_name,
            description=description,
            document_path=document_path,
            status='pending'
        )
        db.session.add(new_expense)
        db.session.commit()
        return jsonify({'message': 'Expense submitted successfully', 'expense_id': new_expense.id}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error submitting expense: {e}")
        return jsonify({'error': 'Failed to submit expense'}), 500

@employee_bp.route('/my-requests')
@login_required
def get_my_requests():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Get all expenses submitted by this employee
        expenses = Expense.query.filter_by(employee_id=current_user.id)\
            .order_by(Expense.created_at.desc()).all()
        
        request_list = []
        for expense in expenses:
            admin = User.query.get(expense.admin_id)
            request_list.append({
                'id': expense.id,
                'title': expense.title,
                'amount': float(expense.amount),
                'status': expense.status,
                'document_link': f"/employee/documents/{os.path.basename(expense.document_path)}" if expense.document_path else None,
                'site_name': expense.site_name,
                'submitted_at': expense.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'reviewed_at': expense.updated_at.strftime('%Y-%m-%d %H:%M:%S') if expense.updated_at else None,
                'admin_name': admin.name if admin else 'N/A'
            })
        return jsonify({'requests': request_list})
    except Exception as e:
        current_app.logger.error(f"Error fetching employee requests: {e}")
        return jsonify({'error': 'Failed to fetch requests'}), 500

@employee_bp.route('/documents/<filename>')
@login_required
def serve_document(filename):
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not upload_folder:
        return jsonify({'error': 'Upload folder not configured'}), 500

    safe_filename = secure_filename(filename)
    file_path = os.path.join(upload_folder, safe_filename)

    if not os.path.exists(file_path):
        return jsonify({'error': 'Document not found'}), 404

    # --- ROBUST AUTHORIZATION CHECK FOR EMPLOYEE ---
    # Check if this document_path belongs to an expense associated with current_user.id
    # Using os.path.basename for comparison as document_path in DB might be full path
    expense = Expense.query.filter_by(document_path=file_path).first() # Assuming document_path in DB is full path
    if not expense:
         # Try matching with just filename if document_path stores only filename
        expense = Expense.query.filter(Expense.document_path.like(f"%{safe_filename}")).first()


    if not expense: # If no expense record found for this document_path
        current_app.logger.warning(f"Attempt to access unlinked document: {safe_filename}")
        return jsonify({'error': 'Document access denied (not linked to an expense)'}), 403

    # Allow access only if it's the current employee's document
    if expense.employee_id == current_user.id:
        mimetype = mimetypes.guess_type(file_path)[0]
        if not mimetype:
            mimetype = 'application/octet-stream' # Default if type cannot be guessed
        return send_from_directory(upload_folder, safe_filename, mimetype=mimetype)
    else:
        return jsonify({'error': 'Unauthorized to view this document'}), 403