# admin_dashboard.py
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
import os
import datetime
from functools import wraps
import logging

# Import MongoDB functions
from utils.db import check_db_connection
from utils.analytics import (
    get_dashboard_summary,
    get_platform_usage_stats,
    get_popular_interests,
    get_user_engagement_metrics,
    get_recent_active_users,
    get_user_activity_over_time,
    get_popular_chat_topics
)

# Set up logging
logger = logging.getLogger(__name__)

# Create Blueprint
admin = Blueprint('admin', __name__, url_prefix='/admin')

# Admin authentication
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Simple password protection
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if not admin_password:
            return "Admin password not configured", 500
        
        # Check for session auth
        if request.cookies.get('admin_auth') != admin_password:
            # Not authenticated
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Login route
@admin.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        
        if password == admin_password:
            response = redirect(request.args.get('next') or url_for('admin.dashboard'))
            # Set a cookie with the password
            response.set_cookie('admin_auth', admin_password)
            return response
        else:
            error = "Invalid password"
    
    return render_template('admin/login.html', error=error)

# Dashboard main page
@admin.route('/')
@admin_required
def dashboard():
    # Check MongoDB connection
    db_connected = check_db_connection()
    
    # Get summary data for dashboard display
    try:
        summary = get_dashboard_summary() if db_connected else {}
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        summary = {'error': str(e)}
    
    return render_template(
        'admin/dashboard.html',
        db_connected=db_connected,
        summary=summary,
        current_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

# API routes for dashboard data
@admin.route('/api/platform-stats')
@admin_required
def api_platform_stats():
    try:
        stats = get_platform_usage_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error in platform stats API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin.route('/api/interests')
@admin_required
def api_interests():
    try:
        min_confidence = request.args.get('confidence', 0.5, type=float)
        interests = get_popular_interests(min_confidence=min_confidence)
        return jsonify(interests)
    except Exception as e:
        logger.error(f"Error in interests API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin.route('/api/engagement')
@admin_required
def api_engagement():
    try:
        metrics = get_user_engagement_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error in engagement API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin.route('/api/recent-users')
@admin_required
def api_recent_users():
    try:
        days = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', 20, type=int)
        users = get_recent_active_users(days=days, limit=limit)
        return jsonify(users)
    except Exception as e:
        logger.error(f"Error in recent users API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin.route('/api/activity-over-time')
@admin_required
def api_activity_over_time():
    try:
        days = request.args.get('days', 30, type=int)
        activity = get_user_activity_over_time(days=days)
        return jsonify(activity)
    except Exception as e:
        logger.error(f"Error in activity over time API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin.route('/api/chat-topics')
@admin_required
def api_chat_topics():
    try:
        topics = get_popular_chat_topics()
        return jsonify(topics)
    except Exception as e:
        logger.error(f"Error in chat topics API: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Database connection test route
@admin.route('/api/db-status')
@admin_required
def api_db_status():
    try:
        connected = check_db_connection()
        return jsonify({
            'connected': connected,
            'timestamp': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error checking DB status: {str(e)}")
        return jsonify({
            'connected': False,
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500