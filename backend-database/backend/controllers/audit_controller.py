from models.audit_logs_model import AuditLog
from models.search_logs_model import SearchLog
from models.edit_lead_drafts_model import EditLeadDraft
from models.user_lead_drafts_model import UserLeadDraft
from models.lead_model import db
from flask import request

class AuditController:
    """Controller for managing audits and logs"""
    
    @staticmethod
    def log_action(user_id, action_type, table_affected, record_id, old_values=None, new_values=None):
        """Log an action to the audit logs"""
        try:
            # Get IP and user agent
            ip_address = request.remote_addr if request and hasattr(request, 'remote_addr') else None
            user_agent = request.user_agent.string if request and hasattr(request, 'user_agent') else None
            
            # Create audit log
            log = AuditLog(
                user_id=user_id,
                action_type=action_type,
                table_affected=table_affected,
                record_id=record_id,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.session.add(log)
            return log
        except Exception as e:
            print(f"Error logging action: {e}")
            return None
    