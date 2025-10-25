from flask import jsonify, request
from flask_login import current_user
from models.workspace_model import Workspace
from models.workspace_settings_model import WorkspaceSettings
from models.workspace_activity_log_model import WorkspaceActivityLog
from models.lead_model import db
import uuid

class WorkspaceSettingsController:
    """Controller for workspace settings operations"""
    
    @staticmethod
    def get_workspace_settings(workspace_id):
        """Get workspace settings"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user is member
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get settings
            settings = workspace.get_settings()
            if not settings:
                # Create default settings if not exists
                settings = WorkspaceSettings.create(
                    workspace_id=workspace.workspace_id,
                    updated_by=current_user.user_id
                )
            
            return settings.to_dict(), 200
            
        except Exception as e:
            return {"error": f"Failed to get workspace settings: {str(e)}"}, 500
    
    @staticmethod
    def update_workspace_settings(workspace_id, data):
        """Update workspace settings"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user can manage workspace
            if not workspace.can_user_admin(current_user.user_id):
                return {"error": "Only admins can update workspace settings"}, 403
            
            # Get or create settings
            settings = workspace.get_settings()
            if not settings:
                settings = WorkspaceSettings.create(
                    workspace_id=workspace.workspace_id,
                    updated_by=current_user.user_id
                )
            
            # Track changes
            changes = {}
            allowed_fields = [
                'default_project_template',
                'auto_assign_tasks',
                'task_approval_required',
                'member_approval_required',
                'email_notifications',
                'slack_integration',
                'time_tracking_enabled',
                'file_sharing_enabled',
                'comment_moderation',
                'custom_fields_enabled',
                'theme_color',
                'welcome_message',
                'project_creation_restricted',
                'task_creation_restricted',
                'member_invitation_restricted'
            ]
            
            for field in allowed_fields:
                if field in data:
                    old_value = getattr(settings, field)
                    if old_value != data[field]:
                        changes[field] = {'old': old_value, 'new': data[field]}
                        setattr(settings, field, data[field])
            
            if changes:
                settings.update(updated_by=current_user.user_id)
                
                # Log activity
                WorkspaceActivityLog.create(
                    workspace_id=workspace.workspace_id,
                    action='settings_updated',
                    user_id=current_user.user_id,
                    entity_type='workspace_settings',
                    entity_id=settings.settings_id,
                    changes=changes
                )
            
            return settings.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update workspace settings: {str(e)}"}, 500
    
    @staticmethod
    def reset_workspace_settings(workspace_id):
        """Reset workspace settings to default"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user can manage workspace
            if not workspace.can_user_admin(current_user.user_id):
                return {"error": "Only admins can reset workspace settings"}, 403
            
            # Get settings
            settings = workspace.get_settings()
            if not settings:
                return {"error": "No settings found to reset"}, 404
            
            # Store old settings for logging
            old_settings = settings.to_dict()
            
            # Reset to default
            settings.reset_to_default()
            settings.update(updated_by=current_user.user_id)
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=workspace.workspace_id,
                action='settings_reset',
                user_id=current_user.user_id,
                entity_type='workspace_settings',
                entity_id=settings.settings_id,
                changes={'old_settings': old_settings, 'new_settings': 'default'}
            )
            
            return settings.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to reset workspace settings: {str(e)}"}, 500
    
    @staticmethod
    def get_workspace_permissions(workspace_id):
        """Get workspace permission matrix"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user is member
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get user role
            user_role = workspace.get_user_role(current_user.user_id)
            
            # Define permission matrix
            permissions = {
                'admin': {
                    'workspace_management': True,
                    'member_management': True,
                    'project_management': True,
                    'task_management': True,
                    'settings_management': True,
                    'invitation_management': True,
                    'activity_view': True,
                    'file_management': True,
                    'comment_management': True,
                    'credit_assignment': True,
                    'profile_management': True
                },
                'manager': {
                    'workspace_management': False,
                    'member_management': True,
                    'project_management': True,
                    'task_management': True,
                    'settings_management': False,
                    'invitation_management': True,
                    'activity_view': True,
                    'file_management': True,
                    'comment_management': True,
                    'credit_assignment': False,
                    'profile_management': True
                },
                'member': {
                    'workspace_management': False,
                    'member_management': False,
                    'project_management': False,
                    'task_management': True,
                    'settings_management': False,
                    'invitation_management': False,
                    'activity_view': True,
                    'file_management': True,
                    'comment_management': True,
                    'credit_assignment': False,
                    'profile_management': True
                }
            }
            
            return {
                'user_role': user_role,
                'permissions': permissions.get(user_role, permissions['member']),
                'can_manage': workspace.can_user_manage(current_user.user_id),
                'can_admin': workspace.can_user_admin(current_user.user_id)
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get workspace permissions: {str(e)}"}, 500
    
    @staticmethod
    def get_workspace_activity_logs(workspace_id):
        """Get workspace activity logs"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user is member
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get query parameters for pagination and filtering
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)  # Max 100 per page
            action_filter = request.args.get('action')
            user_filter = request.args.get('user_id')
            entity_type_filter = request.args.get('entity_type')
            search = request.args.get('search', '').strip()
            
            # Get activity logs (simplified approach)
            limit = per_page
            offset = (page - 1) * per_page
            
            # Build query with filters
            query = WorkspaceActivityLog.query.filter_by(workspace_id=workspace.workspace_id)
            
            if action_filter:
                query = query.filter(WorkspaceActivityLog.action == action_filter)
            
            if user_filter:
                query = query.filter(WorkspaceActivityLog.user_id == user_filter)
            
            if entity_type_filter:
                query = query.filter(WorkspaceActivityLog.entity_type == entity_type_filter)
            
            # Get total count and paginated results
            total = query.count()
            logs = query.order_by(WorkspaceActivityLog.created_at.desc())\
                .offset(offset)\
                .limit(limit)\
                .all()
            
            # Convert to dict and apply search filter if provided
            activities = [log.to_dict() for log in logs]
            if search:
                activities = [
                    activity for activity in activities
                    if search.lower() in activity.get('action', '').lower() or
                       (activity.get('changes') and search.lower() in str(activity.get('changes')).lower())
                ]
            
            return {
                'activities': activities,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page,
                    'has_next': offset + limit < total,
                    'has_prev': page > 1
                },
                'filters': {
                    'action': action_filter,
                    'user_id': user_filter,
                    'entity_type': entity_type_filter,
                    'search': search
                }
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get activity logs: {str(e)}"}, 500
    
    @staticmethod
    def export_workspace_data(workspace_id):
        """Export workspace data"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user can admin workspace
            if not workspace.can_user_admin(current_user.user_id):
                return {"error": "Only admins can export workspace data"}, 403
            
            # Get export format
            export_format = request.args.get('format', 'json')
            if export_format not in ['json', 'csv']:
                return {"error": "Invalid export format. Use 'json' or 'csv'"}, 400
            
            # Export data
            export_data = workspace.export_data(format=export_format)
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=workspace.workspace_id,
                action='data_exported',
                user_id=current_user.user_id,
                entity_type='workspace',
                entity_id=workspace.workspace_id,
                changes={'export_format': export_format}
            )
            
            return export_data, 200
            
        except Exception as e:
            return {"error": f"Failed to export workspace data: {str(e)}"}, 500
    
    @staticmethod
    def get_workspace_analytics(workspace_id):
        """Get workspace analytics and insights"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user is member
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get analytics data
            analytics = workspace.get_analytics()
            
            return analytics, 200
            
        except Exception as e:
            return {"error": f"Failed to get workspace analytics: {str(e)}"}, 500 