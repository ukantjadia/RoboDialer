from flask import jsonify, request
from flask_login import current_user
from models.workspace_model import Workspace
from models.workspace_join_request_model import WorkspaceJoinRequest
from models.workspace_member_model import WorkspaceMember
from models.lead_model import db
import uuid

class WorkspaceJoinRequestController:
    """Controller for workspace join request operations"""
    
    @staticmethod
    def create_join_request(data):
        """Create a new join request"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate required fields
            if not data.get('owner_email'):
                return {"error": "Workspace owner email is required"}, 400
            
            owner_email = data['owner_email'].lower().strip()
            
            # Find workspace by owner email
            from models.user_model import User
            owner_user = User.query.filter_by(email=owner_email).first()
            if not owner_user:
                return {"error": "No user found with that email address"}, 404
            
            # Find workspace where this user is the creator or admin
            workspace = Workspace.query.filter_by(
                created_by=owner_user.user_id,
                is_active=True
            ).first()
            
            if not workspace:
                # Also check if user is admin in any workspace
                admin_member = WorkspaceMember.query.filter_by(
                    user_id=owner_user.user_id,
                    role='admin',
                    is_active=True
                ).first()
                
                if admin_member:
                    workspace = Workspace.query.get(admin_member.workspace_id)
                
                if not workspace:
                    return {"error": "No active workspace found for that user"}, 404
            
            # Get request data
            requested_role = data.get('requested_role', 'member')
            message = data.get('message', '')
            
            # Validate requested role
            if requested_role not in ['member', 'manager']:
                return {"error": "Invalid role. Can only request 'member' or 'manager'"}, 400
            
            # Create join request
            join_request, message_result = WorkspaceJoinRequest.create(
                workspace_id=workspace.workspace_id,
                user_id=current_user.user_id,
                requested_role=requested_role,
                message=message
            )
            
            if not join_request:
                return {"error": message_result}, 400
            
            result = join_request.to_dict()
            result['workspace_name'] = workspace.name
            result['owner_email'] = owner_email
            
            return result, 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to create join request: {str(e)}"}, 500
    
    @staticmethod
    def get_public_workspaces():
        """Get list of public/discoverable workspaces that user can request to join"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Get all active workspaces that user is not already a member of
            user_workspace_ids = db.session.query(WorkspaceMember.workspace_id).filter_by(
                user_id=current_user.user_id,
                is_active=True
            ).subquery()
            
            # Get workspaces user hasn't joined and doesn't have pending requests for
            user_pending_request_ids = db.session.query(WorkspaceJoinRequest.workspace_id).filter_by(
                user_id=current_user.user_id,
                status='pending'
            ).subquery()
            
            workspaces = Workspace.query.filter(
                Workspace.is_active == True,
                ~Workspace.workspace_id.in_(user_workspace_ids),
                ~Workspace.workspace_id.in_(user_pending_request_ids)
            ).order_by(Workspace.created_at.desc()).limit(20).all()
            
            workspace_list = []
            for workspace in workspaces:
                workspace_data = workspace.to_dict()
                # Add some basic info but not sensitive data
                workspace_data['can_request_join'] = True
                workspace_list.append(workspace_data)
            
            return {"workspaces": workspace_list}, 200
            
        except Exception as e:
            return {"error": f"Failed to get public workspaces: {str(e)}"}, 500
    
    @staticmethod
    def get_my_join_requests():
        """Get current user's join requests"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Get user's join requests
            requests = WorkspaceJoinRequest.get_user_requests(current_user.user_id)
            
            return {
                "requests": [req.to_dict() for req in requests],
                "total": len(requests)
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get join requests: {str(e)}"}, 500
    
    @staticmethod
    def cancel_join_request(request_id):
        """Cancel a join request (by the requester)"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate request_id
            try:
                request_uuid = uuid.UUID(request_id)
            except ValueError:
                return {"error": "Invalid request ID"}, 400
            
            join_request = WorkspaceJoinRequest.query.get(request_uuid)
            if not join_request:
                return {"error": "Join request not found"}, 404
            
            # Check if user can cancel this request
            if join_request.user_id != current_user.user_id:
                return {"error": "You can only cancel your own requests"}, 403
            
            # Cancel request
            success, message = join_request.cancel()
            if success:
                return {"message": message}, 200
            else:
                return {"error": message}, 400
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to cancel join request: {str(e)}"}, 500
    
    @staticmethod
    def get_workspace_join_requests(workspace_id):
        """Get join requests for a workspace (for admins/managers)"""
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
            
            # Check if user can manage this workspace (admin or manager only)
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or current_member.role not in ['admin', 'manager']:
                return {"error": "Only admins and managers can view join requests"}, 403
            
            # Get pending requests
            requests = WorkspaceJoinRequest.get_pending_requests(workspace_uuid)
            
            return {
                "requests": [req.to_dict() for req in requests],
                "total": len(requests)
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get workspace join requests: {str(e)}"}, 500
    
    @staticmethod
    def approve_join_request(workspace_id, request_id):
        """Approve a join request"""
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
            
            # Check if user can manage this workspace (admin or manager only)
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or current_member.role not in ['admin', 'manager']:
                return {"error": "Only admins and managers can approve join requests"}, 403
            
            # Validate request_id
            try:
                request_uuid = uuid.UUID(request_id)
            except ValueError:
                return {"error": "Invalid request ID"}, 400
            
            join_request = WorkspaceJoinRequest.query.get(request_uuid)
            if not join_request:
                return {"error": "Join request not found"}, 404
            
            if join_request.workspace_id != workspace_uuid:
                return {"error": "Request does not belong to this workspace"}, 400
            
            # Check role permissions for approval
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if current_member and current_member.role == 'manager':
                # Managers can only approve member requests
                if join_request.requested_role != 'member':
                    return {"error": "Managers can only approve member requests"}, 403
            
            # Approve request
            success, message = join_request.approve(current_user.user_id)
            if success:
                return {"message": message}, 200
            else:
                return {"error": message}, 400
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to approve join request: {str(e)}"}, 500
    
    @staticmethod
    def reject_join_request(workspace_id, request_id, data):
        """Reject a join request"""
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
            
            # Check if user can manage this workspace (admin or manager only)
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or current_member.role not in ['admin', 'manager']:
                return {"error": "Only admins and managers can reject join requests"}, 403
            
            # Validate request_id
            try:
                request_uuid = uuid.UUID(request_id)
            except ValueError:
                return {"error": "Invalid request ID"}, 400
            
            join_request = WorkspaceJoinRequest.query.get(request_uuid)
            if not join_request:
                return {"error": "Join request not found"}, 404
            
            if join_request.workspace_id != workspace_uuid:
                return {"error": "Request does not belong to this workspace"}, 400
            
            # Get rejection reason
            reason = data.get('reason', 'No reason provided')
            
            # Reject request
            success, message = join_request.reject(current_user.user_id, reason)
            if success:
                return {"message": message}, 200
            else:
                return {"error": message}, 400
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to reject join request: {str(e)}"}, 500 