from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import User, Budget, Expense, Transaction, EmployeeFund
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
        start_date = end_date.replace(month=1, day=1) - timedelta(days=365)

        # Monthly spending trends
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

        # Employee spending patterns
        employee_patterns = db.session.query(
            User.name,
            User.id,
            func.sum(Expense.amount).label('total_spent'),
            func.count(Expense.id).label('total_requests'),
            func.avg(Expense.amount).label('avg_request'),
            func.max(Expense.amount).label('max_expense'),
            func.min(Expense.amount).label('min_expense')
        ).join(
            Expense, User.id == Expense.employee_id
        ).filter(
            Expense.admin_id == current_user.id,
            Expense.status == 'approved',
            Expense.created_at >= start_date
        ).group_by(User.id, User.name).all()

        # Category analysis (based on expense reasons)
        category_analysis = db.session.query(
            func.sum(Expense.amount).label('amount'),
            func.count(Expense.id).label('count')
        ).filter(
            Expense.admin_id == current_user.id,
            Expense.status == 'approved',
            Expense.created_at >= start_date
        ).all()

        # Peak spending days (day of week analysis)
        day_analysis = db.session.query(
            extract('dow', Expense.created_at).label('day_of_week'),
            func.sum(Expense.amount).label('total_amount'),
            func.count(Expense.id).label('count')
        ).filter(
            Expense.admin_id == current_user.id,
            Expense.status == 'approved',
            Expense.created_at >= start_date
        ).group_by(extract('dow', Expense.created_at)).all()

        # Format data for frontend
        monthly_trends = []
        for data in monthly_data:
            month_name = calendar.month_name[int(data.month)]
            monthly_trends.append({
                'period': f"{month_name} {int(data.year)}",
                'total_spent': float(data.total_spent or 0),
                'expense_count': data.expense_count or 0,
                'avg_expense': float(data.avg_expense or 0)
            })

        employee_insights = []
        for emp in employee_patterns:
            efficiency_score = calculate_efficiency_score(emp.total_requests, float(emp.total_spent))
            employee_insights.append({
                'name': emp.name,
                'total_spent': float(emp.total_spent or 0),
                'total_requests': emp.total_requests or 0,
                'avg_request': float(emp.avg_request or 0),
                'max_expense': float(emp.max_expense or 0),
                'min_expense': float(emp.min_expense or 0),
                'efficiency_score': efficiency_score
            })

        day_patterns = []
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        for day in day_analysis:
            day_patterns.append({
                'day': day_names[int(day.day_of_week)],
                'total_amount': float(day.total_amount or 0),
                'count': day.count or 0
            })

        return jsonify({
            'monthly_trends': monthly_trends,
            'employee_insights': employee_insights,
            'day_patterns': day_patterns,
            'insights': generate_admin_insights(monthly_trends, employee_insights, day_patterns)
        })

    except Exception as e:
        current_app.logger.error(f"AI insights error: {str(e)}")
        return jsonify({'error': 'Failed to generate insights'}), 500

@ai_insights_bp.route('/superadmin/system-analytics')
@login_required
def get_system_analytics():
    if current_user.role != 'superadmin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # System-wide analytics
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # Last 3 months

        # Budget utilization across all admins
        budget_utilization = db.session.query(
            User.name,
            Budget.allocated,
            Budget.spent,
            Budget.remaining,
            func.count(Expense.id).label('total_expenses')
        ).join(
            Budget, User.id == Budget.admin_id
        ).outerjoin(
            Expense, and_(Expense.admin_id == User.id, Expense.status == 'approved')
        ).filter(
            User.role == 'admin'
        ).group_by(User.id, User.name, Budget.allocated, Budget.spent, Budget.remaining).all()

        # System performance metrics
        total_transactions = Transaction.query.filter(
            Transaction.created_at >= start_date
        ).count()

        approval_rates = db.session.query(
            Expense.status,
            func.count(Expense.id).label('count')
        ).filter(
            Expense.created_at >= start_date
        ).group_by(Expense.status).all()

        # Time series data for system trends
        daily_activity = db.session.query(
            func.date(Transaction.created_at).label('date'),
            func.sum(Transaction.amount).label('total_amount'),
            func.count(Transaction.id).label('transaction_count')
        ).filter(
            Transaction.created_at >= start_date
        ).group_by(func.date(Transaction.created_at)).order_by(func.date(Transaction.created_at)).all()

        # Admin performance comparison
        admin_performance = []
        for admin in budget_utilization:
            utilization_rate = (float(admin.spent) / float(admin.allocated)) * 100 if admin.allocated > 0 else 0
            efficiency_score = calculate_admin_efficiency(admin.total_expenses, float(admin.spent))
            
            admin_performance.append({
                'admin_name': admin.name,
                'allocated': float(admin.allocated or 0),
                'spent': float(admin.spent or 0),
                'remaining': float(admin.remaining or 0),
                'utilization_rate': round(utilization_rate, 2),
                'total_expenses': admin.total_expenses or 0,
                'efficiency_score': efficiency_score
            })

        # Format approval rates
        approval_data = {}
        total_requests = sum([ar.count for ar in approval_rates])
        for ar in approval_rates:
            approval_data[ar.status] = {
                'count': ar.count,
                'percentage': round((ar.count / total_requests) * 100, 2) if total_requests > 0 else 0
            }

        # Daily activity trends
        activity_trends = []
        for activity in daily_activity:
            activity_trends.append({
                'date': activity.date.isoformat(),
                'total_amount': float(activity.total_amount or 0),
                'transaction_count': activity.transaction_count or 0
            })

        return jsonify({
            'admin_performance': admin_performance,
            'approval_rates': approval_data,
            'activity_trends': activity_trends,
            'system_metrics': {
                'total_transactions': total_transactions,
                'total_admins': len(admin_performance),
                'avg_utilization': round(sum([ap['utilization_rate'] for ap in admin_performance]) / len(admin_performance), 2) if admin_performance else 0
            },
            'insights': generate_system_insights(admin_performance, approval_data, activity_trends)
        })

    except Exception as e:
        current_app.logger.error(f"System analytics error: {str(e)}")
        return jsonify({'error': 'Failed to generate system analytics'}), 500

@ai_insights_bp.route('/employee/spending-insights')
@login_required
def get_employee_insights():
    if current_user.role != 'employee':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Get employee's expense history
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)  # Last 6 months

        # Monthly expense trends
        monthly_expenses = db.session.query(
            extract('year', Expense.created_at).label('year'),
            extract('month', Expense.created_at).label('month'),
            func.sum(Expense.amount).label('total_amount'),
            func.count(Expense.id).label('count'),
            func.avg(Expense.amount).label('avg_amount')
        ).filter(
            Expense.employee_id == current_user.id,
            Expense.created_at >= start_date
        ).group_by(
            extract('year', Expense.created_at),
            extract('month', Expense.created_at)
        ).order_by(
            extract('year', Expense.created_at),
            extract('month', Expense.created_at)
        ).all()

        # Status breakdown
        status_breakdown = db.session.query(
            Expense.status,
            func.count(Expense.id).label('count'),
            func.sum(Expense.amount).label('total_amount')
        ).filter(
            Expense.employee_id == current_user.id,
            Expense.created_at >= start_date
        ).group_by(Expense.status).all()

        # Average response time (for approved/rejected expenses)
        response_times = db.session.query(
            func.avg(
                func.extract('epoch', Expense.reviewed_at) - func.extract('epoch', Expense.created_at)
            ).label('avg_response_seconds')
        ).filter(
            Expense.employee_id == current_user.id,
            Expense.reviewed_at.isnot(None),
            Expense.created_at >= start_date
        ).scalar()

        # Format monthly data
        monthly_data = []
        for month in monthly_expenses:
            month_name = calendar.month_name[int(month.month)]
            monthly_data.append({
                'period': f"{month_name} {int(month.year)}",
                'total_amount': float(month.total_amount or 0),
                'count': month.count or 0,
                'avg_amount': float(month.avg_amount or 0)
            })

        # Format status data
        status_data = {}
        for status in status_breakdown:
            status_data[status.status] = {
                'count': status.count,
                'total_amount': float(status.total_amount or 0)
            }

        avg_response_hours = (response_times / 3600) if response_times else 0

        return jsonify({
            'monthly_trends': monthly_data,
            'status_breakdown': status_data,
            'avg_response_time_hours': round(avg_response_hours, 2),
            'insights': generate_employee_insights(monthly_data, status_data, avg_response_hours)
        })

    except Exception as e:
        current_app.logger.error(f"Employee insights error: {str(e)}")
        return jsonify({'error': 'Failed to generate insights'}), 500

# Helper functions for AI insights
def calculate_efficiency_score(request_count, total_spent):
    """Calculate efficiency score based on request frequency and amounts"""
    if request_count == 0:
        return 0
    
    avg_per_request = total_spent / request_count
    
    # Score based on reasonable expense amounts (lower is better for efficiency)
    if avg_per_request < 100:
        return 95
    elif avg_per_request < 500:
        return 85
    elif avg_per_request < 1000:
        return 75
    elif avg_per_request < 2000:
        return 65
    else:
        return 50

def calculate_admin_efficiency(expense_count, total_spent):
    """Calculate admin efficiency based on expense processing"""
    if expense_count == 0:
        return 0
    
    avg_expense = total_spent / expense_count
    
    # Higher efficiency for processing more expenses with reasonable amounts
    efficiency = min(90, (expense_count * 5) + (50 if avg_expense < 1000 else 30))
    return round(efficiency, 2)

def generate_admin_insights(monthly_trends, employee_insights, day_patterns):
    """Generate AI insights for admin dashboard"""
    insights = []
    
    if monthly_trends:
        # Trend analysis
        recent_months = monthly_trends[-3:]  # Last 3 months
        if len(recent_months) >= 2:
            trend = recent_months[-1]['total_spent'] - recent_months[-2]['total_spent']
            if trend > 0:
                insights.append({
                    'type': 'warning',
                    'title': 'Spending Increase Detected',
                    'message': f'Spending increased by ₹{abs(trend):.2f} compared to last month.',
                    'recommendation': 'Review recent expenses and consider budget adjustments.'
                })
            else:
                insights.append({
                    'type': 'success',
                    'title': 'Spending Under Control',
                    'message': f'Spending decreased by ₹{abs(trend):.2f} compared to last month.',
                    'recommendation': 'Good budget management! Consider reallocating savings.'
                })
    
    # Employee efficiency insights
    if employee_insights:
        top_performer = max(employee_insights, key=lambda x: x['efficiency_score'])
        insights.append({
            'type': 'info',
            'title': 'Top Performing Employee',
            'message': f'{top_performer["name"]} has the highest efficiency score of {top_performer["efficiency_score"]}.',
            'recommendation': 'Consider this employee\'s expense patterns as a benchmark.'
        })
        
        high_spenders = [emp for emp in employee_insights if emp['total_spent'] > 5000]
        if high_spenders:
            insights.append({
                'type': 'warning',
                'title': 'High Spending Employees',
                'message': f'{len(high_spenders)} employees have spent over ₹5,000.',
                'recommendation': 'Review expense patterns of high-spending employees.'
            })
    
    # Day pattern insights
    if day_patterns:
        peak_day = max(day_patterns, key=lambda x: x['total_amount'])
        insights.append({
            'type': 'info',
            'title': 'Peak Spending Day',
            'message': f'Most expenses occur on {peak_day["day"]} (₹{peak_day["total_amount"]:.2f}).',
            'recommendation': 'Consider implementing approval workflows for high-spending days.'
        })
    
    return insights

def generate_system_insights(admin_performance, approval_rates, activity_trends):
    """Generate AI insights for superadmin dashboard"""
    insights = []
    
    # Budget utilization insights
    if admin_performance:
        high_utilizers = [admin for admin in admin_performance if admin['utilization_rate'] > 80]
        low_utilizers = [admin for admin in admin_performance if admin['utilization_rate'] < 30]
        
        if high_utilizers:
            insights.append({
                'type': 'warning',
                'title': 'High Budget Utilization',
                'message': f'{len(high_utilizers)} admins have used over 80% of their budget.',
                'recommendation': 'Consider budget reallocation or additional funding.'
            })
        
        if low_utilizers:
            insights.append({
                'type': 'info',
                'title': 'Under-utilized Budgets',
                'message': f'{len(low_utilizers)} admins have used less than 30% of their budget.',
                'recommendation': 'Review budget allocation or redistribute unused funds.'
            })
    
    # Approval rate insights
    if approval_rates:
        if 'rejected' in approval_rates and approval_rates['rejected']['percentage'] > 20:
            insights.append({
                'type': 'warning',
                'title': 'High Rejection Rate',
                'message': f"{approval_rates['rejected']['percentage']}% of expenses are being rejected.",
                'recommendation': 'Review expense policies or provide employee training.'
            })
        
        if 'pending' in approval_rates and approval_rates['pending']['percentage'] > 15:
            insights.append({
                'type': 'warning',
                'title': 'Pending Backlog',
                'message': f"{approval_rates['pending']['percentage']}% of expenses are pending approval.",
                'recommendation': 'Encourage admins to process expenses more quickly.'
            })
    
    # Activity trend insights
    if len(activity_trends) >= 7:
        recent_week = activity_trends[-7:]
        week_total = sum([day['total_amount'] for day in recent_week])
        insights.append({
            'type': 'info',
            'title': 'Weekly Activity',
            'message': f'Total system activity this week: ₹{week_total:.2f}.',
            'recommendation': 'Monitor for unusual spikes in activity.'
        })
    
    return insights

def generate_employee_insights(monthly_data, status_data, avg_response_hours):
    """Generate AI insights for employee dashboard"""
    insights = []
    
    # Spending trend analysis
    if len(monthly_data) >= 2:
        recent_trend = monthly_data[-1]['total_amount'] - monthly_data[-2]['total_amount']
        if recent_trend > 0:
            insights.append({
                'type': 'info',
                'title': 'Spending Increase',
                'message': f'Your expenses increased by ₹{recent_trend:.2f} this month.',
                'recommendation': 'Review your recent expenses and budget accordingly.'
            })
        elif recent_trend < 0:
            insights.append({
                'type': 'success',
                'title': 'Spending Reduction',
                'message': f'Your expenses decreased by ₹{abs(recent_trend):.2f} this month.',
                'recommendation': 'Great job managing your expenses!'
            })
    
    # Approval rate insights
    if status_data:
        total_requests = sum([data['count'] for data in status_data.values()])
        if 'approved' in status_data:
            approval_rate = (status_data['approved']['count'] / total_requests) * 100
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
    
    # Response time insights
    if avg_response_hours > 0:
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
    
    return insights