from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models import User, Budget, Expense, Transaction, EmployeeFund
from extensions import db
from sqlalchemy import func, case, extract, and_, or_
from datetime import datetime, timedelta
from decimal import Decimal
import calendar

ai_insights_bp = Blueprint('ai_insights', __name__)

@ai_insights_bp.route('/admin/spending-trends')
@login_required
def get_admin_spending_trends():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Get last 12 months of data
        end_date = datetime.now()
        # Set start_date to the beginning of the month 11 months ago to cover 12 full months
        start_date = (end_date.replace(day=1) - timedelta(days=365/12 * 11)).replace(day=1)

        # Monthly spending trends (using created_at for spending origination)
        monthly_data = db.session.query(
            extract('year', Expense.created_at).label('year'),
            extract('month', Expense.created_at).label('month'),
            func.sum(Expense.amount).label('total_spent'),
            func.count(Expense.id).label('expense_count'),
            func.avg(Expense.amount).label('avg_expense')
        ).filter(
            Expense.admin_id == current_user.id,
            Expense.status == 'approved',
            Expense.created_at >= start_date
        ).group_by(
            extract('year', Expense.created_at),
            extract('month', Expense.created_at)
        ).order_by(
            extract('year', Expense.created_at),
            extract('month', Expense.created_at)
        ).all()

        trends_data = []
        for year, month, total_spent, expense_count, avg_expense in monthly_data:
            month_name = calendar.month_abbr[int(month)]
            trends_data.append({
                'period': f"{month_name} {int(year)}",
                'total_spent': float(total_spent) if total_spent else 0.0,
                'expense_count': int(expense_count) if expense_count else 0,
                'avg_expense': float(avg_expense) if avg_expense else 0.0
            })
        
        return jsonify({'spending_trends': trends_data})
    except Exception as e:
        current_app.logger.error(f"Error fetching admin spending trends: {e}")
        return jsonify({'error': 'Failed to fetch spending trends'}), 500

@ai_insights_bp.route('/admin/employee-performance')
@login_required
def get_admin_employee_performance():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Get employees managed by this admin
        managed_employees = User.query.filter_by(created_by=current_user.id, role='employee').all()

        performance_data = []
        for employee in managed_employees:
            # Total expenses submitted by this employee to this admin
            total_submitted = Expense.query.filter_by(employee_id=employee.id, admin_id=current_user.id).count()
            
            # Approved expenses
            approved_expenses = Expense.query.filter_by(employee_id=employee.id, admin_id=current_user.id, status='approved').count()
            
            # Rejected expenses
            rejected_expenses = Expense.query.filter_by(employee_id=employee.id, admin_id=current_user.id, status='rejected').count()

            # Approval rate
            approval_rate = (approved_expenses / total_submitted * 100) if total_submitted > 0 else 0

            # Average processing time (using updated_at as review timestamp)
            processed_expenses = Expense.query.filter(
                Expense.employee_id == employee.id,
                Expense.admin_id == current_user.id,
                or_(Expense.status == 'approved', Expense.status == 'rejected'),
                Expense.created_at.isnot(None),
                Expense.updated_at.isnot(None)
            ).all()

            total_response_time_seconds = 0
            count_processed = 0
            for exp in processed_expenses:
                if exp.updated_at and exp.created_at:
                    time_diff = exp.updated_at - exp.created_at
                    total_response_time_seconds += time_diff.total_seconds()
                    count_processed += 1

            avg_response_hours = (total_response_time_seconds / count_processed / 3600) if count_processed > 0 else 0

            performance_data.append({
                'employee_id': employee.id,
                'employee_name': employee.name,
                'total_submitted': total_submitted,
                'approved_count': approved_expenses,
                'rejected_count': rejected_expenses,
                'approval_rate': round(approval_rate, 2),
                'avg_processing_time_hours': round(avg_response_hours, 2)
            })
        
        return jsonify({'employee_performance': performance_data})
    except Exception as e:
        current_app.logger.error(f"Error fetching admin employee performance: {e}")
        return jsonify({'error': 'Failed to fetch employee performance'}), 500

@ai_insights_bp.route('/admin/day-patterns')
@login_required
def get_admin_day_patterns():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Day of week patterns for expense submission (using created_at)
        day_of_week_data = db.session.query(
            extract('dow', Expense.created_at).label('day_of_week'), # 0=Sunday, 1=Monday, ...
            func.count(Expense.id).label('expense_count'),
            func.sum(Expense.amount).label('total_amount')
        ).filter(
            Expense.admin_id == current_user.id,
            Expense.status == 'approved' # Consider approved expenses for spending patterns
        ).group_by(
            extract('dow', Expense.created_at)
        ).order_by(
            extract('dow', Expense.created_at)
        ).all()

        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day_patterns = [{'day': day_names[int(d)], 'count': int(c), 'total_amount': float(t) if t else 0.0} for d, c, t in day_of_week_data]

        # Hour of day patterns for expense submission (using created_at)
        hour_of_day_data = db.session.query(
            extract('hour', Expense.created_at).label('hour_of_day'),
            func.count(Expense.id).label('expense_count'),
            func.sum(Expense.amount).label('total_amount')
        ).filter(
            Expense.admin_id == current_user.id,
            Expense.status == 'approved'
        ).group_by(
            extract('hour', Expense.created_at)
        ).order_by(
            extract('hour', Expense.created_at)
        ).all()

        hour_patterns = [{'hour': int(h), 'count': int(c), 'total_amount': float(t) if t else 0.0} for h, c, t in hour_of_day_data]

        return jsonify({
            'day_of_week_patterns': day_patterns,
            'hour_of_day_patterns': hour_patterns
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching admin day patterns: {e}")
        return jsonify({'error': 'Failed to fetch day patterns'}), 500

@ai_insights_bp.route('/employee/spending-insights')
@login_required
def get_employee_spending_insights():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        insights = []

        # Approval Rate
        total_requests = Expense.query.filter_by(employee_id=current_user.id).count()
        approved_requests = Expense.query.filter_by(employee_id=current_user.id, status='approved').count()

        approval_rate = (approved_requests / total_requests * 100) if total_requests > 0 else 0

        if total_requests > 0:
            if approval_rate > 90:
                insights.append({
                    'type': 'success',
                    'title': 'High Approval Rate',
                    'message': f'{approval_rate:.1f}% of your expenses are approved.',
                    'recommendation': 'Keep up the good expense reporting practices!'
                })
            elif approval_rate < 70:
                insights.append({
                    'type': 'warning',
                    'title': 'Low Approval Rate',
                    'message': f'Only {approval_rate:.1f}% of your expenses are approved.',
                    'recommendation': 'Review expense policies and improve documentation.'
                })
            else:
                 insights.append({
                    'type': 'info',
                    'title': 'Moderate Approval Rate',
                    'message': f'Your approval rate is {approval_rate:.1f}%.',
                    'recommendation': 'Continue to ensure clear documentation for all expenses.'
                })
        else:
            insights.append({
                'type': 'info',
                'title': 'No Expenses Submitted Yet',
                'message': 'Submit your first expense to get personalized insights!',
                'recommendation': 'Start by submitting an expense today.'
            })
    
        # Average processing time (using updated_at as review timestamp)
        # Only consider approved/rejected expenses for processing time calculation
        processed_expenses = Expense.query.filter(
            Expense.employee_id == current_user.id,
            or_(Expense.status == 'approved', Expense.status == 'rejected'),
            Expense.created_at.isnot(None), # Ensure created_at is not null
            Expense.updated_at.isnot(None)  # Ensure updated_at (review timestamp) is not null
        ).all()

        total_response_time_seconds = 0
        count_processed = 0
        for exp in processed_expenses:
            # Calculate difference between updated_at (review time) and created_at
            if exp.updated_at and exp.created_at:
                time_diff = exp.updated_at - exp.created_at
                total_response_time_seconds += time_diff.total_seconds()
                count_processed += 1

        avg_response_hours = (total_response_time_seconds / count_processed / 3600) if count_processed > 0 else 0 # Convert to hours

        if count_processed > 0:
            if avg_response_hours < 24:
                insights.append({
                    'type': 'success',
                    'title': 'Quick Processing',
                    'message': f'Your expenses are processed in {avg_response_hours:.1f} hours on average.',
                    'recommendation': 'Excellent! Your requests are processed quickly.'
                })
            elif avg_response_hours > 72:
                insights.append({
                    'type': 'info',
                    'title': 'Processing Time',
                    'message': f'Your expenses take {avg_response_hours:.1f} hours to process on average.',
                    'recommendation': 'Consider following up on pending requests if needed.'
                })
            else:
                 insights.append({
                    'type': 'info',
                    'title': 'Moderate Processing Time',
                    'message': f'Your expenses are processed in {avg_response_hours:.1f} hours on average.',
                    'recommendation': 'Ensure all necessary documentation is provided for faster review.'
                })

        # Top spending categories (e.g., site_name or general description if categories were used)
        # Assuming site_name can act as a category here
        top_sites_spending = db.session.query(
            Expense.site_name,
            func.sum(Expense.amount).label('total_spent')
        ).filter(
            Expense.employee_id == current_user.id,
            Expense.status == 'approved',
            Expense.site_name.isnot(None) # Only include expenses with a site name
        ).group_by(
            Expense.site_name
        ).order_by(
            func.sum(Expense.amount).desc()
        ).limit(3).all()

        if top_sites_spending:
            message_parts = [f"{site}: ${float(total_spent):.2f}" for site, total_spent in top_sites_spending]
            insights.append({
                'type': 'info',
                'title': 'Top Spending Areas',
                'message': 'Your top spending areas are: ' + ', '.join(message_parts) + '.',
                'recommendation': 'Review spending in these areas for potential cost savings.'
            })
        
        return jsonify({'insights': insights})
    except Exception as e:
        current_app.logger.error(f"Error fetching employee insights: {e}")
        return jsonify({'error': 'Failed to fetch insights'}), 500