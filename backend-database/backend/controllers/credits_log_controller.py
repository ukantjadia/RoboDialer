from flask import jsonify, request, current_app
from flask_login import current_user
from models.credits_log_model import CreditsLog
from models.user_model import User
from models.workspace_model import Workspace
from models.lead_model import db
from sqlalchemy import cast, String
from datetime import datetime, timedelta

class CreditsLogController:
    @staticmethod
    def get_log_filters():
        """Fetches distinct values for the log page filters."""
        try:
            # Join to get user and workspace names instead of just IDs
            workspaces = db.session.query(CreditsLog.team_id, Workspace.name)\
                .join(Workspace, CreditsLog.team_id == Workspace.workspace_id)\
                .distinct().all()

            users = db.session.query(CreditsLog.user_id, User.username)\
                .join(User, CreditsLog.user_id == User.user_id)\
                .distinct().all()

            transaction_types = db.session.query(CreditsLog.transaction_type).distinct().all()
            reference_types = db.session.query(CreditsLog.reference_type).filter(CreditsLog.reference_type.isnot(None)).distinct().all()

            return {
                "workspaces": [{"id": str(w[0]), "name": w[1]} for w in workspaces],
                "users": [{"id": str(u[0]), "name": u[1]} for u in users],
                "transaction_types": [t[0] for t in transaction_types],
                "reference_types": [r[0] for r in reference_types]
            }
        except Exception as e:
            current_app.logger.error(f"Error fetching log filters: {e}", exc_info=True)
            return {}

    @staticmethod
    def get_logs_paginated():
        """Provides a paginated, searchable, and filterable JSON response for DataTables."""
        try:
            params = request.values  # supports both GET and POST
            draw = int(params.get('draw', 0))
            start = int(params.get('start', 0))
            length = int(params.get('length', 10))
            search_value = params.get('search[value]', '').strip()

            # Custom filters
            workspace_id = params.get('workspace_id')
            user_id = params.get('user_id')
            transaction_type = params.get('transaction_type')
            reference_type = params.get('reference_type')
            date_from = params.get('date_from')
            date_to = params.get('date_to')
            time_period = params.get('time_period')  # last_hour, last_2_hours, today, weekend, etc.

            # Base query joining with User and Workspace for names
            query = db.session.query(CreditsLog, User.username, Workspace.name)\
                .join(User, CreditsLog.user_id == User.user_id)\
                .outerjoin(Workspace, CreditsLog.team_id == Workspace.workspace_id)

            total_records = query.count()


            # Apply custom filters
            if workspace_id:
                if workspace_id == 'NULL':
                    query = query.filter(CreditsLog.team_id.is_(None))
                else:
                    query = query.filter(CreditsLog.team_id == workspace_id)

            if user_id:
                query = query.filter(CreditsLog.user_id == user_id)

            if transaction_type:
                query = query.filter(CreditsLog.transaction_type == transaction_type)

            if reference_type:
                if reference_type == 'NULL':
                    query = query.filter(CreditsLog.reference_type.is_(None))
                else:
                    query = query.filter(CreditsLog.reference_type == reference_type)

            # Date range filters
            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                    query = query.filter(CreditsLog.created_at >= date_from_obj)
                except ValueError:
                    pass

            if date_to:
                try:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                    # Add one day to include the entire day
                    date_to_obj = date_to_obj + timedelta(days=1)
                    query = query.filter(CreditsLog.created_at < date_to_obj)
                except ValueError:
                    pass

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

            # Apply global search
            if search_value:
                query = query.filter(
                    db.or_(
                        User.username.ilike(f"%{search_value}%"),
                        Workspace.name.ilike(f"%{search_value}%"),
                        CreditsLog.reason.ilike(f"%{search_value}%"),
                        cast(CreditsLog.transaction_type, String).ilike(f"%{search_value}%"),
                        CreditsLog.reference_type.ilike(f"%{search_value}%")
                    )
                )

            records_filtered = query.count()

            # Apply ordering and pagination
            logs = query.order_by(CreditsLog.created_at.desc()).offset(start).limit(length).all()

            data = []
            for log, username, workspace_name in logs:
                # Build dict manually to avoid extra DB queries inside to_dict
                data.append({
                    'id': str(log.id),
                    'team_id': str(log.team_id) if log.team_id else None,
                    'user_id': str(log.user_id),
                    'amount': log.amount,
                    'reason': log.reason,
                    'created_at': log.created_at.isoformat() if log.created_at else None,
                    'created_by': str(log.created_by) if log.created_by else None,
                    'transaction_type': log.transaction_type,
                    'reference_id': str(log.reference_id) if log.reference_id else None,
                    'reference_type': log.reference_type,
                    'notes': log.notes,
                    'username': username,
                    'workspace_name': workspace_name or "N/A (Personal)"
                })

            return {
                "draw": draw,
                "recordsTotal": total_records,
                "recordsFiltered": records_filtered,
                "data": data
            }

        except Exception as e:
            current_app.logger.error(f"Error fetching paginated logs: {e}", exc_info=True)
            return {"error": "Failed to fetch credit logs"}, 500