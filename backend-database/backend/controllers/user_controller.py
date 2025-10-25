from flask import jsonify, request
from flask_login import current_user
from models.user_model import User
from models.workspace_member_model import WorkspaceMember
from models.workspace_activity_log_model import WorkspaceActivityLog
from models.credits_log_model import CreditsLog
from models.lead_model import db
import uuid
from datetime import datetime, timedelta

class UserController:
    """Controller for user operations (member flow)"""

    @staticmethod
    def get_my_profile():
        """Get current user's profile"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            # Get user's workspace memberships
            workspace_memberships = WorkspaceMember.query.filter_by(
                user_id=current_user.user_id,
                is_active=True
            ).all()

            # Get user's credits from all workspaces
            total_credits = 0
            workspace_credits = []

            for membership in workspace_memberships:
                workspace_credits.append({
                    'workspace_id': str(membership.workspace_id),
                    'workspace_name': membership.get_workspace().name if membership.get_workspace() else 'Unknown',
                    'credits': membership.credits_allocated,
                    'credits_used': membership.credits_used,
                    'credits_remaining': membership.credits_allocated - membership.credits_used
                })
                total_credits += (membership.credits_allocated - membership.credits_used)

            profile_data = {
                'id': str(current_user.user_id),
                'name': current_user.username,
                'email': current_user.email,
                'role': 'member',  # For member flow, user is always member
                'joined_at': current_user.created_at.isoformat() if current_user.created_at else None,
                'status': 'active' if current_user.is_active else 'inactive',
                'credits': total_credits,
                'workspace_credits': workspace_credits,
                'total_workspaces': len(workspace_memberships)
            }

            return profile_data, 200

        except Exception as e:
            return {"error": f"Failed to get user profile: {str(e)}"}, 500

    @staticmethod
    def update_my_profile(data):
        """Update current user's profile"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            # Users can only update their own profile
            # This is already enforced by the fact that we're using current_user

            # Validate required fields
            if not data.get('username'):
                return {"error": "Username is required"}, 400

            # Check if username is already taken by another user
            existing_user = User.query.filter(
                User.username == data['username'],
                User.user_id != current_user.user_id
            ).first()
            if existing_user:
                return {"error": "Username already taken"}, 400

            # Update user profile
            current_user.username = data['username']
            if data.get('email'):
                current_user.email = data['email']
            if data.get('linkedin_url'):
                current_user.linkedin_url = data['linkedin_url']

            db.session.commit()

            return current_user.to_dict(), 200

        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update profile: {str(e)}"}, 500

    @staticmethod
    def get_my_activity():
        """Get current user's activity logs"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            # Get query parameters
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            team_filter = request.args.get('team_id')
            action_filter = request.args.get('action')

            # Get user's activity logs
            logs = WorkspaceActivityLog.get_user_activity(
                user_id=current_user.user_id,
                limit=per_page,
                offset=(page - 1) * per_page
            )

            return {
                'activities': [log.to_dict() for log in logs],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': len(logs),
                    'has_more': len(logs) == per_page
                }
            }, 200

        except Exception as e:
            return {"error": f"Failed to get user activity: {str(e)}"}, 500

    @staticmethod
    def get_my_credit_history():
        """Get current user's credit history"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            # Get query parameters
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            team_filter = request.args.get('team_id')
            transaction_type_filter = request.args.get('transaction_type')
            time_period = request.args.get('time_period')

            # Build query
            query = CreditsLog.query.filter_by(user_id=current_user.user_id)

            # Apply filters
            if team_filter:
                query = query.filter_by(team_id=team_filter)

            if transaction_type_filter:
                query = query.filter_by(transaction_type=transaction_type_filter)

            # Time period filters
            if time_period:
                now = datetime.utcnow()
                if time_period == 'last_hour':
                    query = query.filter(CreditsLog.created_at >= now - timedelta(hours=1))
                elif time_period == 'last_2_hours':
                    query = query.filter(CreditsLog.created_at >= now - timedelta(hours=2))
                elif time_period == 'last_6_hours':
                    query = query.filter(CreditsLog.created_at >= now - timedelta(hours=6))
                elif time_period == 'today':
                    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    query = query.filter(CreditsLog.created_at >= today_start)
                elif time_period == 'yesterday':
                    yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    yesterday_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    query = query.filter(CreditsLog.created_at >= yesterday_start, CreditsLog.created_at < yesterday_end)
                elif time_period == 'this_week':
                    week_start = now - timedelta(days=now.weekday())
                    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                    query = query.filter(CreditsLog.created_at >= week_start)
                elif time_period == 'last_week':
                    last_week_end = now - timedelta(days=now.weekday())
                    last_week_start = last_week_end - timedelta(days=7)
                    query = query.filter(CreditsLog.created_at >= last_week_start, CreditsLog.created_at < last_week_end)
                elif time_period == 'this_month':
                    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    query = query.filter(CreditsLog.created_at >= month_start)
                elif time_period == 'last_month':
                    first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    last_month_end = first_this_month - timedelta(days=1)
                    last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    query = query.filter(CreditsLog.created_at >= last_month_start, CreditsLog.created_at < first_this_month)

            # Get total count
            total_count = query.count()

            # Apply pagination and ordering
            logs = query.order_by(CreditsLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

            # Get credit summary
            summary = CreditsLog.get_user_credits_summary(current_user.user_id, team_filter)

            return {
                'credit_history': [log.to_dict() for log in logs],
                'summary': summary,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'has_more': (page * per_page) < total_count
                }
            }, 200

        except Exception as e:
            return {"error": f"Failed to get credit history: {str(e)}"}, 500