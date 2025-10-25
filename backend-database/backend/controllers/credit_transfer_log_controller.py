from flask import jsonify, request, current_app
from flask_login import current_user
from models.credit_transfer_log_model import CreditTransferLog
from models.user_model import User
from models.company_model import Company
from models.lead_model import db
from sqlalchemy import cast, String
from sqlalchemy.orm import aliased
from datetime import datetime, timedelta

class CreditTransferLogController:
    @staticmethod
    def get_transfer_filters():
        """Fetches distinct values for the transfer log page filters."""
        try:
            # Get companies
            companies = db.session.query(Company.company_id, Company.name).distinct().all()

            # Get users who have received transfers
            users = db.session.query(CreditTransferLog.to_user_id, User.username)\
                .join(User, CreditTransferLog.to_user_id == User.user_id)\
                .distinct().all()

            # Get admins who have made transfers
            admins = db.session.query(CreditTransferLog.from_user_id, User.username)\
                .join(User, CreditTransferLog.from_user_id == User.user_id)\
                .distinct().all()

            return {
                "companies": [{"id": str(c[0]), "name": c[1]} for c in companies],
                "users": [{"id": str(u[0]), "name": u[1]} for u in users],
                "admins": [{"id": str(a[0]), "name": a[1]} for a in admins]
            }
        except Exception as e:
            current_app.logger.error(f"Error fetching transfer filters: {e}", exc_info=True)
            return {}

    @staticmethod
    def get_transfers_paginated():
        """Provides a paginated, searchable, and filterable JSON response for DataTables."""
        try:
            params = request.values
            draw = int(params.get('draw', 0))
            start = int(params.get('start', 0))
            length = int(params.get('length', 10))
            search_value = params.get('search[value]', '').strip()

            # Custom filters
            company_id = params.get('company_id')
            user_id = params.get('user_id')
            admin_id = params.get('admin_id')
            date_from = params.get('date_from')
            date_to = params.get('date_to')

            # Alias users table for to_user and from_user to avoid duplicate alias error
            ToUser = aliased(User)
            FromUser = aliased(User)

            # Base query joining with aliased User and Company for names
            query = db.session.query(
                CreditTransferLog,
                ToUser.username.label('to_username'),
                ToUser.email.label('to_email'),
                FromUser.username.label('from_username'),
                Company.name.label('company_name')
            )\
                .join(ToUser, CreditTransferLog.to_user_id == ToUser.user_id)\
                .join(FromUser, CreditTransferLog.from_user_id == FromUser.user_id)\
                .outerjoin(Company, CreditTransferLog.company_id == Company.company_id)

            total_records = query.count()

            # Apply custom filters
            if company_id:
                if company_id == 'NULL':
                    query = query.filter(CreditTransferLog.company_id.is_(None))
                else:
                    query = query.filter(CreditTransferLog.company_id == company_id)

            if user_id:
                query = query.filter(CreditTransferLog.to_user_id == user_id)

            if admin_id:
                query = query.filter(CreditTransferLog.from_user_id == admin_id)

            # Date range filters
            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                    query = query.filter(CreditTransferLog.transferred_at >= date_from_obj)
                except ValueError:
                    pass

            if date_to:
                try:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                    # Add one day to include the entire day
                    date_to_obj = date_to_obj + timedelta(days=1)
                    query = query.filter(CreditTransferLog.transferred_at < date_to_obj)
                except ValueError:
                    pass

            # Apply global search
            if search_value:
                query = query.filter(
                    db.or_(
                        ToUser.username.ilike(f"%{search_value}%"),
                        FromUser.username.ilike(f"%{search_value}%"),
                        Company.name.ilike(f"%{search_value}%"),
                        CreditTransferLog.note.ilike(f"%{search_value}%")
                    )
                )

            records_filtered = query.count()

            # Apply ordering and pagination
            transfers = query.order_by(CreditTransferLog.transferred_at.desc()).offset(start).limit(length).all()

            data = []
            for transfer, to_username, to_email, from_username, company_name in transfers:
                transfer_dict = transfer.to_dict()
                transfer_dict['to_username'] = to_username
                transfer_dict['to_email'] = to_email
                transfer_dict['from_username'] = from_username
                transfer_dict['company_name'] = company_name or "N/A"
                data.append(transfer_dict)

            return {
                "draw": draw,
                "recordsTotal": total_records,
                "recordsFiltered": records_filtered,
                "data": data
            }

        except Exception as e:
            current_app.logger.error(f"Error fetching paginated transfers: {e}", exc_info=True)
            return {"error": "Failed to fetch credit transfer logs"}, 500

    @staticmethod
    def get_user_transfer_summary(user_id, company_id=None):
        """Get transfer summary for a user"""
        query = db.session.query(
            db.func.sum(CreditTransferLog.amount).label('total_received'),
            db.func.count(CreditTransferLog.id).label('transfer_count')
        ).filter(CreditTransferLog.to_user_id == user_id)

        if company_id:
            query = query.filter(CreditTransferLog.company_id == company_id)

        result = query.first()
        return {
            'total_received': result.total_received or 0,
            'transfer_count': result.transfer_count or 0
        }

    @staticmethod
    def get_company_transfer_summary(company_id):
        """Get transfer summary for a company"""
        query = db.session.query(
            db.func.sum(CreditTransferLog.amount).label('total_transferred'),
            db.func.count(CreditTransferLog.id).label('transfer_count')
        ).filter(CreditTransferLog.company_id == company_id)

        result = query.first()
        return {
            'total_transferred': result.total_transferred or 0,
            'transfer_count': result.transfer_count or 0
        }
