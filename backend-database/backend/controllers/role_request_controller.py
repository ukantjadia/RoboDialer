from flask import jsonify
from flask_login import current_user
from models.workspace_join_request_model import WorkspaceJoinRequest
from models.workspace_member_model import WorkspaceMember
from models.workspace_model import Workspace
from models.user_model import User
from models.lead_model import db
import uuid

class RoleRequestController:
    """Controller for role change requests using WorkspaceJoinRequest model"""
    
    @staticmethod
    def request_role_change(workspace_id, data):
        """Request a role change in workspace"""
        try:
            # Validate input
            requested_role = data.get('requested_role')
            message = data.get('message', '')
            
            if not requested_role:
                return {"error": "Requested role is required"}, 400
            
            if requested_role not in ['manager', 'member']:
                return {"error": "Invalid requested role. Must be 'manager' or 'member'"}, 400
            
            # Convert workspace_id to UUID
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID format"}, 400
            
            # Check if workspace exists
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user is already a member
            current_member = WorkspaceMember.query.filter_by(
                workspace_id=workspace_uuid,
                user_id=current_user.user_id,
                is_active=True
            ).first()
            
            if not current_member:
                return {"error": "You are not a member of this workspace"}, 403
            
            # Check if user already has the requested role
            if current_member.role == requested_role:
                return {"error": f"You already have the '{requested_role}' role"}, 400
            
            # Check if there's already a pending request
            existing_request = WorkspaceJoinRequest.query.filter_by(
                workspace_id=workspace_uuid,
                user_id=current_user.user_id,
                status='pending'
            ).first()
            
            if existing_request:
                return {"error": "You already have a pending role change request"}, 400
            
            # Create role change request
            request = WorkspaceJoinRequest(
                workspace_id=workspace_uuid,
                user_id=current_user.user_id,
                requested_role=requested_role,
                message=message
            )
            
            db.session.add(request)
            db.session.commit()
            
            return {
                "success": True,
                "message": "Role change request submitted successfully",
                "request": request.to_dict()
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to submit role change request: {str(e)}"}, 500
    
    @staticmethod
    def get_pending_role_requests(workspace_id):
        """Get pending role change requests for workspace (admin/manager only)"""
        try:
            # Convert workspace_id to UUID
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID format"}, 400
            
            # Check if workspace exists
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user has permission (admin or manager)
            current_member = WorkspaceMember.query.filter_by(
                workspace_id=workspace_uuid,
                user_id=current_user.user_id,
                is_active=True
            ).first()
            
            if not current_member or current_member.role not in ['admin', 'manager']:
                return {"error": "Permission denied. Only admins and managers can view role requests"}, 403
            
            # Get pending requests
            requests = WorkspaceJoinRequest.get_pending_requests(workspace_uuid)
            
            # Filter only members requesting role changes (not new join requests)
            role_change_requests = []
            for req in requests:
                # Check if requester is already a member
                member = WorkspaceMember.query.filter_by(
                    workspace_id=workspace_uuid,
                    user_id=req.user_id,
                    is_active=True
                ).first()
                
                if member:  # This is a role change request, not a join request
                    req_dict = req.to_dict()
                    req_dict['current_role'] = member.role
                    role_change_requests.append(req_dict)
            
            return {
                "success": True,
                "requests": role_change_requests,
                "count": len(role_change_requests)
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get role requests: {str(e)}"}, 500
    
    @staticmethod
    def review_role_request(request_id, data):
        """Approve or reject a role change request"""
        try:
            # Validate input
            action = data.get('action')  # 'approve' or 'reject'
            reason = data.get('reason', '')
            
            if action not in ['approve', 'reject']:
                return {"error": "Action must be 'approve' or 'reject'"}, 400
            
            # Convert request_id to UUID
            try:
                request_uuid = uuid.UUID(request_id)
            except ValueError:
                return {"error": "Invalid request ID format"}, 400
            
            # Get the request
            request = WorkspaceJoinRequest.query.get(request_uuid)
            if not request:
                return {"error": "Role request not found"}, 404
            
            if request.status != 'pending':
                return {"error": "Request is not pending"}, 400
            
            # Check if user has permission (admin or manager)
            current_member = WorkspaceMember.query.filter_by(
                workspace_id=request.workspace_id,
                user_id=current_user.user_id,
                is_active=True
            ).first()
            
            if not current_member or current_member.role not in ['admin', 'manager']:
                return {"error": "Permission denied. Only admins and managers can review role requests"}, 403
            
            # Check if requester is still a member
            requester_member = WorkspaceMember.query.filter_by(
                workspace_id=request.workspace_id,
                user_id=request.user_id,
                is_active=True
            ).first()
            
            if not requester_member:
                return {"error": "Requester is no longer a member of this workspace"}, 400
            
            if action == 'approve':
                # Update member role instead of creating new member
                old_role = requester_member.role
                requester_member.change_role(request.requested_role)
                
                # Update request status
                request.status = 'approved'
                request.reviewed_by = current_user.user_id
                request.reviewed_at = db.func.now()
                
                db.session.commit()
                
                # Log activity
                from models.workspace_activity_log_model import WorkspaceActivityLog
                WorkspaceActivityLog.create(
                    workspace_id=request.workspace_id,
                    action='role_change_approved',
                    user_id=current_user.user_id,
                    entity_type='role_request',
                    entity_id=request.request_id,
                    changes={
                        'requester_email': request.get_user().email if request.get_user() else 'Unknown',
                        'old_role': old_role,
                        'new_role': request.requested_role
                    }
                )
                
                return {
                    "success": True,
                    "message": "Role change request approved successfully",
                    "request": request.to_dict()
                }, 200
                
            elif action == 'reject':
                success, message = request.reject(current_user.user_id, reason)
                if success:
                    return {
                        "success": True,
                        "message": message,
                        "request": request.to_dict()
                    }, 200
                else:
                    return {"error": message}, 400
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to review role request: {str(e)}"}, 500
    
    @staticmethod
    def get_user_role_requests(user_id=None):
        """Get role requests made by a user"""
        try:
            target_user_id = user_id if user_id else current_user.user_id
            
            # If requesting another user's requests, check permission
            if user_id and user_id != str(current_user.user_id):
                return {"error": "Permission denied. You can only view your own requests"}, 403
            
            requests = WorkspaceJoinRequest.get_user_requests(target_user_id)
            
            # Filter only role change requests (where user is already a member)
            role_change_requests = []
            for req in requests:
                member = WorkspaceMember.query.filter_by(
                    workspace_id=req.workspace_id,
                    user_id=req.user_id,
                    is_active=True
                ).first()
                
                if member:  # This is a role change request
                    req_dict = req.to_dict()
                    req_dict['current_role'] = member.role
                    role_change_requests.append(req_dict)
            
            return {
                "success": True,
                "requests": role_change_requests,
                "count": len(role_change_requests)
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get user role requests: {str(e)}"}, 500
    
    @staticmethod
    def cancel_role_request(request_id):
        """Cancel a role change request (by requester)"""
        try:
            # Convert request_id to UUID
            try:
                request_uuid = uuid.UUID(request_id)
            except ValueError:
                return {"error": "Invalid request ID format"}, 400
            
            # Get the request
            request = WorkspaceJoinRequest.query.get(request_uuid)
            if not request:
                return {"error": "Role request not found"}, 404
            
            # Check if current user is the requester
            if request.user_id != current_user.user_id:
                return {"error": "Permission denied. You can only cancel your own requests"}, 403
            
            success, message = request.cancel()
            if success:
                return {
                    "success": True,
                    "message": message,
                    "request": request.to_dict()
                }, 200
            else:
                return {"error": message}, 400
                
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to cancel role request: {str(e)}"}, 500