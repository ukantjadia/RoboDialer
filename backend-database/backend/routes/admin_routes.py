from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.decorators import admin_required, developer_required
from models.user_model import User
from datetime import datetime, timedelta

bp = Blueprint('admin', __name__)

@bp.route('/admin/release-notes')
@login_required
@developer_required
def manage_release_notes():
    """Admin page for managing release notes"""
    return render_template('admin/manage_release_notes.html')

@bp.route('/admin/companies')
@login_required
@admin_required
def companies():
    from models.company_model import Company
    companies = Company.query.all()
    return render_template('admin/companies.html', companies=companies)

@bp.route('/api/admin/users/active-stats')
@login_required
# @admin_required
def get_active_user_stats():
    """Get active user statistics for admin dashboard (no status/role filter)."""
    try:
        days = request.args.get('days', 100, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        total_users = User.query.count()
        active_users = User.query.filter(User.last_login_at.isnot(None), User.last_login_at >= cutoff_date).count()
        inactive_users = User.query.filter((User.last_login_at.is_(None)) | (User.last_login_at < cutoff_date)).count()

        activity_rate = 0
        if total_users > 0:
            activity_rate = round((active_users / total_users) * 100, 2)

        return jsonify({
            'success': True,
            'data': {
                'active_users': active_users,
                'inactive_users': inactive_users,
                'total_active_users': total_users,
                'total_users_all_statuses': total_users,
                'activity_rate_percentage': activity_rate,
                'days_analyzed': days,
                'last_updated': datetime.utcnow().isoformat()
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/admin/users/login-activity')
@login_required
# @admin_required
def get_user_login_activity():
    """Get detailed user login activity for admin dashboard (no status/role filter)."""
    try:
        days = request.args.get('days', 1, type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        active_users = User.query.filter(
            User.last_login_at.isnot(None),
            User.last_login_at >= cutoff_date
        ).order_by(User.last_login_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        inactive_users = User.query.filter(
            (User.last_login_at.is_(None)) | (User.last_login_at < cutoff_date)
        ).order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        def format_user_data(user):
            return {
                'user_id': str(user.user_id),
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'tier': user.tier,
                'company': user.company,
                'status': user.status,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
                'days_since_last_login': (datetime.utcnow() - user.last_login_at).days if user.last_login_at else None
            }

        return jsonify({
            'success': True,
            'data': {
                'active_users': {
                    'users': [format_user_data(user) for user in active_users.items],
                    'pagination': {
                        'page': active_users.page,
                        'pages': active_users.pages,
                        'per_page': active_users.per_page,
                        'total': active_users.total,
                        'has_next': active_users.has_next,
                        'has_prev': active_users.has_prev
                    }
                },
                'inactive_users': {
                    'users': [format_user_data(user) for user in inactive_users.items],
                    'pagination': {
                        'page': inactive_users.page,
                        'pages': inactive_users.pages,
                        'per_page': inactive_users.per_page,
                        'total': inactive_users.total,
                        'has_next': inactive_users.has_next,
                        'has_prev': inactive_users.has_prev
                    }
                },
                'days_analyzed': days
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/admin/users/export-login-data')
@login_required
# @admin_required
def export_user_login_data():
    """Export user login data for analysis (no status filter)."""
    try:
        users = User.query.all()

        export_data = []
        for user in users:
            export_data.append({
                'user_id': str(user.user_id),
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'tier': user.tier,
                'company': user.company,
                'status': user.status,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
                'days_since_last_login': (datetime.utcnow() - user.last_login_at).days if user.last_login_at else None,
                'is_recently_active': bool(user.last_login_at and (datetime.utcnow() - user.last_login_at).days <= 30)
            })

        return jsonify({'success': True, 'data': export_data, 'total_users': len(export_data), 'exported_at': datetime.utcnow().isoformat()})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/admin/users/active-list')
@login_required
# @admin_required
def get_active_user_list():
    """List users who logged in within the last N days (no status/role filter)."""
    try:
        days = request.args.get('days', 1, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        users = User.query.filter(
            User.last_login_at.isnot(None),
            User.last_login_at >= cutoff_date
        ).order_by(User.last_login_at.desc()).all()

        def fmt(u):
            return {
                'user_id': str(u.user_id),
                'username': u.username,
                'email': u.email,
                'role': u.role,
                'last_login_at': u.last_login_at.isoformat() if u.last_login_at else None
            }

        return jsonify({'success': True, 'days_analyzed': days, 'total': len(users), 'users': [fmt(u) for u in users]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500