from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import User
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Log in the user with session management
    login_user(user, remember=True)
    
    # Store additional session data
    session['user_id'] = user.id
    session['user_role'] = user.role
    session['login_time'] = datetime.utcnow().isoformat()
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role
        },
        'redirect_url': f'/dashboard/{user.role}'
    })

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    # Clear session data
    session.clear()
    logout_user()
    
    return jsonify({'message': 'Logged out successfully'})

@auth_bp.route('/me')
@login_required
def get_current_user():
    return jsonify({
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'role': current_user.role,
        'session_active': True
    })

@auth_bp.route('/check-session')
def check_session():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'name': current_user.name,
                'email': current_user.email,
                'role': current_user.role
            }
        })
    else:
        return jsonify({'authenticated': False}), 401