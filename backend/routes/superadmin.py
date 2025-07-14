from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from models import User, Budget, Expense, Transaction, EmployeeFund
from extensions import db
from sqlalchemy import func, case
from sqlalchemy.orm import aliased
from decimal import Decimal  # ADD THIS IMPORT
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

superadmin_bp = Blueprint('superadmin', __name__)
@superadmin_bp.route('/dashboard-stats', methods=['GET'])
@login_required
def get_superadmin_dashboard_stats():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Total Budget Allocated (across all admins)
        total_budget_allocated = db.session.query(func.sum(Budget.total_budget)).scalar() or Decimal('0')

        # Total Remaining Budget (across all admins)
        total_remaining_budget = db.session.query(func.sum(Budget.remaining)).scalar() or Decimal('0')

        # Total Spent (across all admins)
        # This considers approved expenses and allocations from admins to employees
        total_spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.type.in_(['expense', 'allocation_to_employee']) # Assuming you have a type for employee allocations
        ).scalar() or Decimal('0')


        # You might want to refine 'total_spent' calculation based on your Transaction types
        # For example, if you want total money moved out of the system or approved expenses.
        # Let's consider total approved expenses as a primary "spent" metric for now.
        total_approved_expenses = db.session.query(func.sum(Expense.amount)).filter(
            Expense.status == 'approved'
        ).scalar() or Decimal('0')

        # Total Admins
        total_admins = User.query.filter_by(role='admin').count()

        # Total Employees
        total_employees = User.query.filter_by(role='employee').count()

        # Total Pending Expenses (for all admins/employees)
        total_pending_expenses = Expense.query.filter_by(status='pending').count()

        # Aggregate employee funds (total allocated, total spent by employees)
        total_employee_fund_allocated = db.session.query(func.sum(EmployeeFund.allocated)).scalar() or Decimal('0')
        total_employee_fund_spent = db.session.query(func.sum(EmployeeFund.spent)).scalar() or Decimal('0')


        return jsonify({
            'total_budget_allocated': float(total_budget_allocated),
            'total_remaining_budget': float(total_remaining_budget),
            'total_approved_expenses': float(total_approved_expenses),
            'total_admins': total_admins,
            'total_employees': total_employees,
            'total_pending_expenses': total_pending_expenses,
            'total_employee_fund_allocated': float(total_employee_fund_allocated),
            'total_employee_fund_spent': float(total_employee_fund_spent)
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching superadmin dashboard stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

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
    amount = data.get('amount')
    
    if not admin_id or not amount:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # CRITICAL FIX: Convert to Decimal
        amount_decimal = Decimal(str(amount))
        
        admin = User.query.filter_by(id=admin_id, role='admin').first()
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
        
        # Check if budget already exists for this admin
        existing_budget = Budget.query.filter_by(admin_id=admin_id).first()
        
        if existing_budget:
            # Add to existing budget
            existing_budget.allocated += amount_decimal
            existing_budget.remaining += amount_decimal
        else:
            # Create new budget - FIXED: Set remaining = allocated
            budget = Budget(
                admin_id=admin_id, 
                allocated=amount_decimal,
                spent=Decimal('0'),
                remaining=amount_decimal
            )
            db.session.add(budget)
        
        # Create transaction record
        transaction = Transaction(
            sender_id=current_user.id,
            receiver_id=admin_id,
            amount=amount_decimal,
            type='allocation',
            description=f'Budget allocation to {admin.name}'
        )
        db.session.add(transaction)
        
        db.session.commit()
        # Return updated dashboard stats so frontend can refresh
        # (fetch latest budget/overview after allocation)
        # Optionally, you can call get_overview() directly here
        from flask import url_for
        overview_url = url_for('superadmin.get_overview')
        # Fetch updated stats
        try:
            with current_app.test_request_context(overview_url):
                resp = get_overview()
                if hasattr(resp, 'json'):
                    stats = resp.json
                else:
                    stats = resp.get_json()
        except Exception:
            stats = None
        return jsonify({'message': 'Budget allocated successfully', 'stats': stats})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Allocate budget error: {str(e)}")
        return jsonify({'error': 'Failed to allocate budget'}), 500

@superadmin_bp.route('/overview')
@login_required
def get_overview():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403

    # LEFT OUTER JOIN to include all admins, even those without budgets
    admins = db.session.query(
        User.id,
        User.name,
        User.email,
        User.phone,
        User.is_active,
        Budget.allocated,
        Budget.spent,
        Budget.remaining
    ).outerjoin(Budget, User.id == Budget.admin_id).filter(
        User.role == 'admin'
    ).all()

    employees = db.session.query(
        User.id,
        User.name,
        User.email,
        User.is_active,
        User.created_by
    ).filter(User.role == 'employee').all()

    # Admins summary
    admins_overview = []
    total_allocated = 0
    total_spent = 0
    for admin in admins:
        allocated = float(admin.allocated or 0)
        spent = float(admin.spent or 0)
        admins_overview.append({
            'id': admin.id,
            'name': admin.name,
            'email': admin.email,
            'allocated': allocated,
            'spent': spent,
            'is_active': admin.is_active
        })
        total_allocated += allocated
        total_spent += spent

    # Employees summary
    employees_overview = []
    admin_id_to_name = {a.id: a.name for a in admins}
    for emp in employees:
        employees_overview.append({
            'id': emp.id,
            'name': emp.name,
            'email': emp.email,
            'admin_name': admin_id_to_name.get(emp.created_by, None),
            'is_active': emp.is_active
        })

    # Get active admins count (admins with allocated budget)
    active_admins = Budget.query.filter(Budget.allocated > 0).count()

    return jsonify({
        'total_allocated': total_allocated,
        'total_spent': total_spent,
        'remaining_funds': total_allocated - total_spent,
        'active_admins': active_admins,
        'admins_overview': admins_overview,
        'employees_overview': employees_overview
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
        Transaction.description,
        Transaction.timestamp,
        User.name.label('sender_name'),
        User.email.label('sender_email')
    ).join(User, Transaction.sender_id == User.id).order_by(Transaction.timestamp.desc()).limit(100).all()
    
    transaction_data = []
    
    # Process transactions
    for trans in transactions:
        # Get receiver details
        receiver_query = db.session.query(Transaction, User).join(
            User, Transaction.receiver_id == User.id
        ).filter(Transaction.id == trans.id).first()
        
        receiver_name = receiver_query[1].name if receiver_query else 'Unknown'
        
        transaction_data.append({
            'id': trans.id,
            'timestamp': trans.timestamp,
            'sender_name': trans.sender_name,
            'receiver_name': receiver_name,
            'amount': float(trans.amount),
            'type': trans.type,
            'reason': trans.description or ('Budget Allocation' if trans.type == 'allocation' else 'Expense Payment')
        })
    
    return jsonify({'transactions': transaction_data})

@superadmin_bp.route('/reports')
@login_required
def get_reports():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get date range (default to last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Get all transactions
    transactions = db.session.query(
        Transaction.id,
        Transaction.amount,
        Transaction.type,
        Transaction.description,
        Transaction.timestamp,
        User.name.label('sender_name'),
        User.email.label('sender_email')
    ).join(User, Transaction.sender_id == User.id).filter(
        Transaction.timestamp >= start_date
    ).order_by(Transaction.timestamp.desc()).all()
    
    # Get total allocations today
    today_allocations = db.session.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.type == 'allocation',
        func.date(Transaction.timestamp) == datetime.now().date()
    ).scalar() or 0

    # Get total expenses today
    today_expenses = db.session.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.type == 'expense',
        func.date(Transaction.timestamp) == datetime.now().date()
    ).scalar() or 0

    # Get monthly summary (only valid enum values)
    monthly_summary = db.session.query(
        func.extract('month', Transaction.timestamp).label('month'),
        func.extract('year', Transaction.timestamp).label('year'),
        func.sum(case((Transaction.type == 'allocation', Transaction.amount), else_=0)).label('total_allocations'),
        func.sum(case((Transaction.type == 'expense', Transaction.amount), else_=0)).label('total_expenses')
    ).filter(
        Transaction.timestamp >= start_date,
        Transaction.type.in_(['allocation', 'expense', 'refund'])
    ).group_by(
        func.extract('month', Transaction.timestamp),
        func.extract('year', Transaction.timestamp)
    ).all()
    
    return jsonify({
        'today_summary': {
            'allocations': float(today_allocations),
            'expenses': float(today_expenses)
        },
        'transactions': [{
            'id': t.id,
            'sender_name': t.sender_name,
            'sender_email': t.sender_email,
            'amount': float(t.amount),
            'type': t.type,
            'description': t.description,
            'date': t.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        } for t in transactions],
        'monthly_summary': [{
            'month': int(m.month),
            'year': int(m.year),
            'total_allocations': float(m.total_allocations),
            'total_expenses': float(m.total_expenses)
        } for m in monthly_summary]
    })



@superadmin_bp.route('/add-employee', methods=['POST'])
@login_required
def add_employee():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    initial_fund = data.get('initial_fund')

    # Validate required fields
    if not all([name, email, password]):
        return jsonify({'error': 'Name, email, and password are required'}), 400

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400

    # Get the latest created supervisor (admin)
    supervisor = User.query.filter_by(role='admin').order_by(User.created_at.desc()).first()
    if not supervisor:
        return jsonify({'error': 'No supervisor (admin) found. Please create one first.'}), 400

    try:
        user = User(
            name=name,
            email=email,
            phone=phone,
            password=generate_password_hash(password),
            role='employee',
            created_by=supervisor.id
        )
        db.session.add(user)
        db.session.flush()  # To get user.id

        # Optional: Allocate initial fund if provided
        if initial_fund:
            fund = Decimal(str(initial_fund))
            emp_fund = EmployeeFund(
                employee_id=user.id,
                admin_id=supervisor.id,  # ✅ Required to satisfy NOT NULL constraint
                allocated=fund,
                spent=Decimal('0'),
                remaining=fund
            )
            db.session.add(emp_fund)
        

        db.session.commit()
        return jsonify({'message': 'Employee added successfully'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add employee error: {str(e)}")
        return jsonify({'error': 'Failed to add employee'}), 500

@superadmin_bp.route('/edit-employee', methods=['PUT'])
@login_required
def edit_employee():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    employee = User.query.filter_by(email=email, role='employee').first()
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    try:
        # Update basic details
        employee.name = data.get('name', employee.name)
        employee.phone = data.get('phone', employee.phone)
        password = data.get('password')
        if password:
            employee.password = generate_password_hash(password)

        # Update status
        status = data.get('status')
        if status:
            employee.is_active = True if status == 'active' else False

        employee.updated_at = datetime.utcnow()

        # Update fund if provided
        initial_fund = data.get('initial_fund')
        if initial_fund is not None:
            fund = Decimal(str(initial_fund))
            emp_fund = EmployeeFund.query.filter_by(employee_id=employee.id).first()

            if emp_fund:
                diff = fund - emp_fund.allocated
                emp_fund.allocated = fund
                emp_fund.remaining += diff
                emp_fund.updated_at = datetime.utcnow()
            else:
                emp_fund = EmployeeFund(
                    employee_id=employee.id,
                    admin_id=employee.created_by,
                    allocated=fund,
                    spent=Decimal('0'),
                    remaining=fund,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(emp_fund)

        db.session.commit()

        return jsonify({'message': 'Employee updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Edit employee error: {str(e)}")
        return jsonify({'error': 'Failed to update employee'}), 500



@superadmin_bp.route('/add-client', methods=['POST'])
@login_required
def add_client():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    initial_fund = data.get('initial_fund')  # NEW FIELD
    
    if not all([name, email, password]):
        return jsonify({'error': 'Name, email, and password are required'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User(
        name=name,
        email=email,
        phone=phone,
        password=generate_password_hash(password),
        role='admin',
        created_by=current_user.id
    )
    db.session.add(user)
    db.session.flush()  # To get user.id

    # Create initial budget if provided
    if initial_fund:
        fund = Decimal(str(initial_fund))
        budget = Budget(
            admin_id=user.id,
            allocated=fund,
            spent=Decimal('0'),
            remaining=fund
        )
        db.session.add(budget)

    db.session.commit()
    return jsonify({'message': 'Supervisor (Admin) added successfully'})


@superadmin_bp.route('/employees')
@login_required
def get_employees():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Get all employees with their admin info and fund details
        admin_user = aliased(User)
        
        employees_data = db.session.query(
            User.id,
            User.name,
            User.email,
            User.phone,
            User.is_active,
            User.created_at,
            User.last_login.label('last_activity'),
            User.created_by.label('admin_id'),
            # Admin info
            func.coalesce(admin_user.name, 'No Admin').label('admin_name'),
            func.coalesce(admin_user.email, 'No Email').label('admin_email'),
            # Fund info
            func.coalesce(EmployeeFund.allocated, 0).label('allocated_amount'),
            func.coalesce(EmployeeFund.spent, 0).label('spent_amount'),
            # Expense counts
            func.count(case((Expense.status == 'approved', 1))).label('approved_expenses'),
            func.count(case((Expense.status == 'pending', 1))).label('pending_expenses'),
            func.count(Expense.id).label('total_expenses')
        ).outerjoin(
            admin_user, User.created_by == admin_user.id
        ).outerjoin(
            EmployeeFund, EmployeeFund.employee_id == User.id
        ).outerjoin(
            Expense, Expense.employee_id == User.id
        ).filter(
            User.role == 'employee'
        ).group_by(
            User.id, User.name, User.email, User.phone, User.is_active, 
            User.created_at, User.last_login, User.created_by,
            admin_user.name, admin_user.email,
            EmployeeFund.allocated, EmployeeFund.spent
        ).all()

        employees = []
        for emp in employees_data:
            employees.append({
                'id': emp.id,
                'name': emp.name,
                'email': emp.email,
                'phone': emp.phone,
                'status': 'active' if emp.is_active else 'inactive',
                'admin_id': emp.admin_id,
                'admin_name': emp.admin_name,
                'admin_email': emp.admin_email,
                'allocated_amount': float(emp.allocated_amount),
                'spent_amount': float(emp.spent_amount),
                'approved_expenses': emp.approved_expenses,
                'pending_expenses': emp.pending_expenses,
                'total_expenses': emp.total_expenses,
                'last_activity': emp.last_activity.isoformat() if emp.last_activity else None,
                'created_at': emp.created_at.isoformat() if emp.created_at else None
            })

        return jsonify({'employees': employees})

    except Exception as e:
        current_app.logger.error(f"Error getting employees: {str(e)}")
        return jsonify({'error': 'Failed to fetch employees'}), 500

@superadmin_bp.route('/employee/<int:employee_id>/toggle-status', methods=['POST'])
@login_required
def toggle_employee_status(employee_id):
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['active', 'inactive']:
            return jsonify({'error': 'Invalid status. Must be active or inactive'}), 400
        
        # Find the employee
        employee = User.query.filter_by(id=employee_id, role='employee').first()
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Update the is_active status
        employee.is_active = (new_status == 'active')
        employee.updated_at = datetime.utcnow()
        
        # If deactivating, you might want to handle cleanup here
        if new_status == 'inactive':
            # Mark for deletion or handle deactivation logic
            # For now, we'll just change the status
            pass
        
        db.session.commit()
        
        action = 'activated' if new_status == 'active' else 'deactivated'
        return jsonify({'message': f'Employee {action} successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling employee status: {str(e)}")
        return jsonify({'error': 'Failed to update employee status'}), 500