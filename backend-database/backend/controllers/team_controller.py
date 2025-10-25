from flask import jsonify, request
from flask_login import current_user
from models.workspace_model import Workspace
from models.workspace_member_model import WorkspaceMember
from models.project_model import Project
from models.user_model import User
from models.credits_log_model import CreditsLog
from models.workspace_activity_log_model import WorkspaceActivityLog
from models.lead_model import db
import uuid
from datetime import datetime

class TeamController:
    """Controller for team management operations"""
    
    @staticmethod
    def get_teams():
        """Get all teams the user is a member of"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Get all workspaces where user is a member (any role)
            memberships = WorkspaceMember.query.filter_by(
                user_id=current_user.user_id,
                is_active=True
            ).all()
            
            teams = []
            for membership in memberships:
                workspace = membership.get_workspace()
                if workspace and workspace.is_active:
                    team_data = {
                        'id': str(workspace.workspace_id),
                        'name': workspace.name,
                        'description': workspace.description,
                        'memberCount': workspace.get_member_count(),
                        'category': workspace.industry or 'General',
                        'userRole': membership.role  # Include user's role in this team
                    }
                    teams.append(team_data)
            
            return {"teams": teams}, 200
            
        except Exception as e:
            return {"error": f"Failed to get teams: {str(e)}"}, 500
    
    
    @staticmethod
    def update_team(team_id, data):
        """Update team"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate team_id
            try:
                team_uuid = uuid.UUID(team_id)
            except ValueError:
                return {"error": "Invalid team ID"}, 400
            
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
            
            # Check if user can manage team
            if not workspace.can_user_admin(current_user.user_id):
                return {"error": "Only admins can update team"}, 403
            
            # Track changes
            changes = {}
            allowed_fields = ['name', 'description', 'industry']
            
            for field in allowed_fields:
                if field in data:
                    old_value = getattr(workspace, field)
                    if old_value != data[field]:
                        changes[field] = {'old': old_value, 'new': data[field]}
                        setattr(workspace, field, data[field])
            
            if changes:
                workspace.update()
                
                # Log activity
                WorkspaceActivityLog.create(
                    workspace_id=workspace.workspace_id,
                    action='team_updated',
                    user_id=current_user.user_id,
                    entity_type='team',
                    entity_id=workspace.workspace_id,
                    changes=changes
                )
            
            team_data = {
                'id': str(workspace.workspace_id),
                'name': workspace.name,
                'description': workspace.description,
                'memberCount': workspace.get_member_count(),
                'category': workspace.industry or 'General'
            }
            
            return team_data, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update team: {str(e)}"}, 500
    
    @staticmethod
    def delete_team(team_id):
        """Delete team"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate team_id
            try:
                team_uuid = uuid.UUID(team_id)
            except ValueError:
                return {"error": "Invalid team ID"}, 400
            
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
            
            # Check if user can delete team
            if not workspace.can_user_admin(current_user.user_id):
                return {"error": "Only admins can delete team"}, 403
            
            # Log activity before deletion
            WorkspaceActivityLog.create(
                workspace_id=workspace.workspace_id,
                action='team_deleted',
                user_id=current_user.user_id,
                entity_type='team',
                entity_id=workspace.workspace_id,
                changes={'team_name': workspace.name}
            )
            
            # This prevents users from deleting and recreating workspace to get more credits
            workspace.is_active = False
            workspace.updated_at = datetime.utcnow()
            db.session.commit()
            
            return {"message": "Team deleted successfully"}, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to delete team: {str(e)}"}, 500
    
    @staticmethod
    def get_team_members(team_id):
        """Get all members of a team"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate team_id
            try:
                team_uuid = uuid.UUID(team_id)
            except ValueError:
                return {"error": "Invalid team ID"}, 400
            
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
            
            # Check if user is member
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get all active members
            members = workspace.get_members()
            
            members_data = []
            for member in members:
                user = member.get_user()
                if user:
                    member_data = {
                        'id': str(user.user_id),
                        'name': f"{user.username}",
                        'email': user.email,
                        'role': member.role,
                        'joinedAt': member.joined_at.isoformat() if member.joined_at else None,
                        'status': 'active' if member.is_active else 'inactive',
                        'credits': member.get_remaining_credits() # Use the helper method
                    }
                    members_data.append(member_data)
            
            return {"members": members_data}, 200
            
        except Exception as e:
            return {"error": f"Failed to get team members: {str(e)}"}, 500
    
    @staticmethod
    def invite_team_member(team_id, data):
        """Invite a member to team"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate team_id
            try:
                team_uuid = uuid.UUID(team_id)
            except ValueError:
                return {"error": "Invalid team ID"}, 400
            
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
            
            # Check if user can manage team
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can invite members"}, 403
            
            # Validate required fields
            if not data.get('email'):
                return {"error": "Email is required"}, 400
            
            email = data['email'].lower().strip()
            
            # Create invitation data with role from request
            role = data.get('role', 'member')  # Get role from request, default to member if not specified
            invitation_data = {
                'email': email,
                'role': role
            }
            
            # Use workspace invitation system
            from controllers.workspace_member_controller import WorkspaceMemberController
            return WorkspaceMemberController.invite_member(team_id, invitation_data)
            
        except Exception as e:
            return {"error": f"Failed to invite member: {str(e)}"}, 500
    
    @staticmethod
    def set_active_team(team_id):
        """Set the active team for the current user"""
        try:
            # Verify team exists and user is a member
            team = Workspace.query.get_or_404(team_id)
            member = WorkspaceMember.query.filter_by(
                workspace_id=team_id,
                user_id=current_user.user_id
            ).first()
            
            if not member:
                return {"error": "User is not a member of this team"}, 403
            
            # Update user's active team
            current_user.active_team_id = team_id
            db.session.commit()
            
            return {"success": True, "message": "Active team updated"}
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @staticmethod
    def get_team(team_id):
        """Get team details and set as active team"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate team_id
            try:
                team_uuid = uuid.UUID(team_id)
            except ValueError:
                return {"error": "Invalid team ID"}, 400
            
            # Get team details
            team = Workspace.query.get(team_uuid)
            if not team:
                return {"error": "Team not found"}, 404
            
            # Check if user is member
            if not team.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Set as active team
            current_user.active_team_id = team_id
            db.session.commit()
            
            return {
                "id": str(team.workspace_id),
                "name": team.name,
                "description": team.description,
                "created_at": team.created_at.isoformat() if team.created_at else None,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None,
                "memberCount": team.get_member_count(),
                "category": team.industry or 'General',
                "status": 'active' if team.is_active else 'inactive'
            }
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @staticmethod
    def get_member_credits(team_id, member_id):
        """Get credits summary for a member in a team"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            try:
                team_uuid = uuid.UUID(team_id)
                member_uuid = uuid.UUID(member_id)
            except ValueError:
                return {"error": "Invalid ID"}, 400
            
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
                
            member = workspace.get_member_by_user_id(member_uuid)
            if not member:
                return {"error": "Member not found"}, 404

            
            user = member.get_user()
            if not user:
                return {"error": "User not found"}, 404


            return {"credits": member.get_remaining_credits()}, 200
        except Exception as e:
            return {"error": f"Failed to get member credits: {str(e)}"}, 500

    @staticmethod
    def request_credit_change(team_id, member_id, data):
        """Request credit change for a member (manager flow)"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            try:
                team_uuid = uuid.UUID(team_id)
                member_uuid = uuid.UUID(member_id)
            except ValueError:
                return {"error": "Invalid ID"}, 400
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            member = workspace.get_member_by_user_id(member_uuid)
            if not member:
                return {"error": "Member not found"}, 404
            # Validate request
            amount = data.get('amount')
            reason = data.get('reason', '')
            if not amount:
                return {"error": "Amount is required"}, 400
            # Simpan request ke log/activity (atau ke table khusus jika ada)
            from models.workspace_activity_log_model import WorkspaceActivityLog
            WorkspaceActivityLog.create(
                workspace_id=team_uuid,
                action='credit_change_requested',
                user_id=current_user.user_id,
                entity_type='member',
                entity_id=member_uuid,
                changes={'amount': amount, 'reason': reason}
            )
            return {"message": "Credit change request submitted for admin approval"}, 201
        except Exception as e:
            return {"error": f"Failed to request credit change: {str(e)}"}, 500

    # --- Permission Enforcement for Manager ---
    @staticmethod
    def can_manager_assign_role(current_user_role, new_role):
        # Admin can assign any role
        if current_user_role == 'admin':
            return True
        # Manager cannot assign admin
        elif current_user_role == 'manager':
            return new_role in ['manager', 'member']
        # Members cannot assign roles
        else:
            return False

    @staticmethod
    def can_manager_remove_member(current_user_role, target_member_role):
        # Admin can remove anyone except themselves
        if current_user_role == 'admin':
            return True
        # Manager can only remove members, not other managers or admins
        elif current_user_role == 'manager':
            return target_member_role == 'member'
        # Members cannot remove anyone
        else:
            return False

    # --- Override update_member_role and remove_team_member for manager restrictions ---
    @staticmethod
    def update_member_role(team_id, member_id, data):
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            try:
                team_uuid = uuid.UUID(team_id)
                member_uuid = uuid.UUID(member_id)
            except ValueError:
                return {"error": "Invalid ID"}, 400
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
            # Only admin or manager can update
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can update member roles"}, 403
            member = workspace.get_member_by_user_id(member_uuid)
            if not member:
                return {"error": "Member not found"}, 404
            
            # Get current user's role
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            current_user_role = current_member.role if current_member else 'member'
            
            new_role = data.get('role')
            if not new_role or not TeamController.can_manager_assign_role(current_user_role, new_role):
                if current_user_role == 'manager':
                    return {"error": "Managers cannot assign admin role"}, 403
                else:
                    return {"error": "You don't have permission to assign this role"}, 403
            
            # Prevent changing own role if not admin
            if member.user_id == current_user.user_id and not workspace.can_user_admin(current_user.user_id):
                return {"error": "Cannot change your own role"}, 403
            old_role = member.role
            member.change_role(new_role)
            user = member.get_user()
            user_email = user.email if user else "Unknown"
            from models.workspace_activity_log_model import WorkspaceActivityLog
            WorkspaceActivityLog.log_role_changed(
                workspace_id=workspace.workspace_id,
                member_id=member.workspace_member_id,
                user_id=current_user.user_id,
                member_email=user_email,
                old_role=old_role,
                new_role=new_role
            )
            return member.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update member role: {str(e)}"}, 500

    @staticmethod
    def remove_team_member(team_id, member_id):
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            try:
                team_uuid = uuid.UUID(team_id)
                member_uuid = uuid.UUID(member_id)
            except ValueError:
                return {"error": "Invalid ID"}, 400
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can remove members"}, 403
            member = workspace.get_member_by_user_id(member_uuid)
            if not member:
                return {"error": "Member not found"}, 404
            
            # Get current user's role
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            current_user_role = current_member.role if current_member else 'member'
            
            # Check if current user can remove the target member
            if not TeamController.can_manager_remove_member(current_user_role, member.role):
                if current_user_role == 'manager':
                    return {"error": "Managers can only remove members, not other managers or admins"}, 403
                else:
                    return {"error": "You don't have permission to remove this member"}, 403
            
            if member.user_id == current_user.user_id:
                return {"error": "Cannot remove yourself from team"}, 403
            user = member.get_user()
            user_email = user.email if user else "Unknown"
            from models.workspace_activity_log_model import WorkspaceActivityLog
            WorkspaceActivityLog.log_member_removed(
                workspace_id=workspace.workspace_id,
                member_id=member.workspace_member_id,
                user_id=current_user.user_id,
                member_email=user_email
            )
            member.deactivate()
            return {"message": "Member removed successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to remove member: {str(e)}"}, 500

    @staticmethod
    def update_team_member(team_id, member_id, data):
        """Update team member (role and/or credits)"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
                
            try:
                team_uuid = uuid.UUID(team_id)
                member_uuid = uuid.UUID(member_id)
            except ValueError:
                return {"error": "Invalid ID"}, 400
                
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
                
            # Only admin or manager can update
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can update members"}, 403
                
            member = workspace.get_member_by_user_id(member_uuid)
            if not member:
                return {"error": "Member not found"}, 404
                
            # Update role if provided
            if 'role' in data:
                new_role = data.get('role')
                
                # Get current user's role
                current_member = workspace.get_member_by_user_id(current_user.user_id)
                current_user_role = current_member.role if current_member else 'member'
                
                if not new_role or not TeamController.can_manager_assign_role(current_user_role, new_role):
                    if current_user_role == 'manager':
                        return {"error": "Managers cannot assign admin role"}, 403
                    else:
                        return {"error": "You don't have permission to assign this role"}, 403
                    
                # Prevent changing own role if not admin
                if member.user_id == current_user.user_id and not workspace.can_user_admin(current_user.user_id):
                    return {"error": "Cannot change your own role"}, 403
                    
                old_role = member.role
                if old_role != new_role:
                    member.change_role(new_role)
                    
                    # Log role change
                    user = member.get_user()
                    user_email = user.email if user else "Unknown"
                    from models.workspace_activity_log_model import WorkspaceActivityLog
                    WorkspaceActivityLog.log_role_changed(
                        workspace_id=workspace.workspace_id,
                        member_id=member.workspace_member_id,
                        user_id=current_user.user_id,
                        member_email=user_email,
                        old_role=old_role,
                        new_role=new_role
                    )
            
            # Update credits if provided
            if 'credits' in data:
                credits_amount = data.get('credits', 0)
                
                # Use current_member from role section or get it if not already available
                if 'role' not in data:
                    current_member = workspace.get_member_by_user_id(current_user.user_id)
                
                if not current_member or not current_member.can_assign_credits():
                    return {"error": "Only admins can assign credits directly"}, 403
                
                # Update user subscription directly using SubscriptionController logic
                try:
                    from controllers.subscription_controller import SubscriptionController
                    from models.user_subscription_model import UserSubscription
                    from models.plan_model import Plan
                    from models.user_model import User
                    
                    # Get user object
                    target_user = User.query.get(member_uuid)
                    if not target_user:
                        return {"error": "Target user not found"}, 404

                    # Get admin's subscription to check available credits
                    admin_subscription = UserSubscription.query.filter_by(user_id=str(current_user.user_id)).first()
                    if not admin_subscription:
                        return {"error": "Admin subscription not found"}, 404

                    # Calculate total credits currently assigned to members (excluding admin)
                    total_member_credits = TeamController.get_team_member_credits(team_uuid)
                    
                    # Get current member's credits including initial credits
                    current_member_credits = 0
                    existing_subscription = UserSubscription.query.filter_by(user_id=str(member_uuid)).first()
                    
                    # Get user's plan and its initial credits
                    initial_credits = 0
                    if existing_subscription:
                        user_plan = Plan.query.get(existing_subscription.plan_id)
                        if user_plan:
                            initial_credits = user_plan.initial_credits
                        current_member_credits = existing_subscription.credits_remaining + initial_credits

                    # Calculate how many new credits we're trying to assign
                    new_credits_needed = credits_amount - current_member_credits

                    # Check if we have enough credits in the pool
                    if new_credits_needed > (admin_subscription.credits_remaining - (total_member_credits - current_member_credits)):
                        return {"error": "Not enough credits in the pool to assign"}, 400
                    
                    # Get or create user subscription
                    user_subscription = existing_subscription
                    
                    if not user_subscription:
                        # Get user's current plan from SubscriptionController
                        sub_info, status_code = SubscriptionController.get_current_user_subscription_info(target_user)
                        if status_code != 200:
                            return {"error": "Failed to get user's subscription info"}, 500
                            
                        subscription = sub_info.get('subscription', {})
                        plan_name = subscription.get('plan_name', 'Free')
                        
                        # Get the plan from database
                        user_plan = Plan.query.filter(Plan.plan_name.ilike(plan_name)).first()
                        if not user_plan:
                            return {"error": f"Plan {plan_name} not found in system"}, 404
                            
                        user_subscription = UserSubscription(
                            user_id=str(member_uuid),
                            plan_id=user_plan.plan_id,
                            plan_name=user_plan.plan_name,
                            credits_remaining=credits_amount,  # Only assigned credits (initial credits are added when displaying)
                            tier_start_timestamp=datetime.utcnow(),
                            payment_frequency=subscription.get('payment_frequency', 'monthly'),
                            username=target_user.username
                        )
                        db.session.add(user_subscription)
                    else:
                        # Update existing subscription
                        user_subscription.credits_remaining = credits_amount  # Only assigned credits
                    
                    db.session.commit()
                    
                except Exception as e:
                    db.session.rollback()
                    return {"error": f"Failed to update credits: {str(e)}"}, 500
            
            # Return updated member data
            user = member.get_user()
            
            # Get credits from user subscription (consistent with subscription info)
            credits_remaining = 0
            try:
                from controllers.subscription_controller import SubscriptionController
                # Get subscription info including plan details
                sub_info, status_code = SubscriptionController.get_current_user_subscription_info(user)
                if status_code == 200:
                    subscription = sub_info.get('subscription', {})
                    plan = sub_info.get('plan', {})
                    plan_name = subscription.get('plan_name', '')
                    
                    # For Platinum/Enterprise admin, show full credits
                    if member.role == 'admin' and plan_name.lower() in ['platinum', 'enterprise']:
                        credits_remaining = subscription.get('credits_remaining', 0)
                    else:
                        # For regular members, add initial credits if available
                        credits_remaining = subscription.get('credits_remaining', 0)
                        if plan and plan.get('initial_credits') is not None:
                            credits_remaining += plan.get('initial_credits', 0)
            except Exception as e:
                print(f"Error getting credits for user {user.user_id}: {e}")
            
            member_data = {
                'id': str(user.user_id),
                'name': f"{user.username}",
                'email': user.email,
                'role': member.role,
                'joinedAt': member.joined_at.isoformat() if member.joined_at else None,
                'status': 'active' if member.is_active else 'inactive',
                'credits': credits_remaining
            }
            
            return member_data, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update member: {str(e)}"}, 500

    @staticmethod
    def assign_credits(team_id, member_id, data):
        """Managers cannot assign credits directly, only admins can. Managers must use request_credit_change."""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            # Check if user is admin
            team_uuid = uuid.UUID(team_id)
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
            
            # Get current user's member record to check specific permissions
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or not current_member.can_assign_credits():
                return {"error": "Only admins can assign credits directly. Managers must use credit change request."}, 403
            
            if workspace.can_user_admin(current_user.user_id):
                # Admin can assign credits
                return TeamController._assign_credits_admin(team_id, member_id, data)
            else:
                # Manager cannot assign credits directly
                return {"error": "Managers cannot assign credits directly. Please use credit change request."}, 403
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to assign credits: {str(e)}"}, 500

    @staticmethod
    def _assign_credits_admin(team_id, member_id, data):
        """Internal: Only for admin credit assignment"""
        # (original assign_credits logic here, can be copied from previous version)
        try:
            team_uuid = uuid.UUID(team_id)
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
            # Validate required fields
            if 'amount' not in data:
                return {"error": "Amount is required"}, 400
            amount = data['amount']
            reason = data.get('reason', 'Credit assignment')
            member = workspace.get_member_by_user_id(member_id)
            if not member:
                return {"error": "Member not found"}, 404
            if amount > 0:
                from models.credits_log_model import CreditsLog
                CreditsLog.log_allocation(
                    team_id=team_uuid,
                    user_id=member_id,
                    amount=amount,
                    allocated_by=current_user.user_id,
                    notes=reason
                )
            else:
                from models.credits_log_model import CreditsLog
                CreditsLog.log_penalty(
                    team_id=team_uuid,
                    user_id=member_id,
                    amount=abs(amount),
                    reason=reason,
                    created_by=current_user.user_id
                )
            user = member.get_user()
            credits_summary = member.get_credits_summary()
            member_data = {
                'id': str(user.user_id),
                'name': f"{user.username}",
                'email': user.email,
                'role': member.role,
                'joinedAt': member.joined_at.isoformat() if member.joined_at else None,
                'status': 'active' if member.is_active else 'inactive',
                'credits': credits_summary.get('total_credits', 0)
            }
            return member_data, 200
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to assign credits: {str(e)}"}, 500
    
    @staticmethod
    def get_team_credits(team_id):
        """Get team's total credits, used credits, and remaining credits"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            workspace = Workspace.query.get(team_id)
            if not workspace:
                return {"error": "Team not found"}, 404

            admin_member = WorkspaceMember.query.filter_by(
                workspace_id=team_id,
                role='admin',
                is_active=True
            ).first()

            if not admin_member:
                return {"error": "Admin not found"}, 404

            # Sum up credits from all members
            total_allocated = db.session.query(
                db.func.sum(WorkspaceMember.credits_allocated),
            ).filter(
                WorkspaceMember.workspace_id == team_id
            ).scalar() or 0
            
            return {
                "total_credits": workspace.total_credit_pool,
                "used_credits": total_allocated,
                "remaining_credits": workspace.total_credit_pool - total_allocated
            }, 200

        except Exception as e:
            print(f"Error getting team credits: {e}")
            return {"error": f"Failed to get team credits: {str(e)}"}, 500

    @staticmethod
    def get_credit_requests(team_id):
        """Get all credit requests for a team"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            workspace = Workspace.query.get(team_id)
            if not workspace:
                return {"error": "Team not found"}, 404

            # Check if user is member of the team
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403

            # Get all pending credit requests for this team
            from models.credits_log_model import CreditsLog
            
            # If user is admin/manager, show only pending requests from all users
            # If user is member, show all their own requests (pending, approved, rejected)
            if workspace.can_user_manage(current_user.user_id):
                requests = CreditsLog.query.filter_by(
                    team_id=team_id,
                    reference_type='credit_request'
                ).order_by(CreditsLog.created_at.desc()).all()
            else:
                # Members can see all their own requests (pending, approved, rejected)
                requests = CreditsLog.query.filter(
                    CreditsLog.team_id == team_id,
                    CreditsLog.user_id == current_user.user_id,
                    CreditsLog.reference_type.in_(['credit_request', 'approved_request', 'rejected_request'])
                ).order_by(CreditsLog.created_at.desc()).all()

            requests_data = []
            for request in requests:
                # Get user data
                user = User.query.get(request.user_id)
                user_data = {
                    "username": user.username if user else "Unknown",
                    "email": user.email if user else "No email"
                } if user else None

                # Determine status based on reference_type
                status = "pending"
                if request.reference_type == 'approved_request':
                    status = "approved"
                elif request.reference_type == 'rejected_request':
                    status = "rejected"
                
                request_data = {
                    "request_id": str(request.id),
                    "user_id": str(request.user_id),
                    "user_data": user_data,
                    "amount": request.amount,
                    "reason": request.notes,
                    "status": status,
                    "created_at": request.created_at.isoformat() if request.created_at else None
                }
                requests_data.append(request_data)

            return {
                "requests": requests_data,
                "count": len(requests_data)
            }, 200

        except Exception as e:
            print(f"Error getting credit requests: {e}")
            return {"error": f"Failed to get credit requests: {str(e)}"}, 500

    @staticmethod
    def request_credits(team_id, data):
        """Request credits from team pool"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            workspace = Workspace.query.get(team_id)
            if not workspace:
                return {"error": "Team not found"}, 404

            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403

            amount = data.get('amount')
            reason = data.get('reason', '')

            if not amount or amount <= 0:
                return {"error": "Invalid amount"}, 400

            # Create credit request log
            from models.credits_log_model import CreditsLog
            request = CreditsLog.log_credit_request(
                team_id=team_id,
                user_id=current_user.user_id,
                amount=amount,
                notes=reason
            )

            return {
                "request_id": str(request.id),
                "message": "Credit request submitted successfully"
            }, 201

        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to request credits: {str(e)}"}, 500

    @staticmethod
    def approve_credit_request(team_id, request_id):
        """Approve credit request"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            workspace = Workspace.query.get(team_id)
            if not workspace:
                return {"error": "Team not found"}, 404

            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can approve requests"}, 403

            # Get the request
            from models.credits_log_model import CreditsLog
            
            # Convert request_id to UUID
            try:
                request_uuid = uuid.UUID(request_id)
            except ValueError:
                return {"error": "Invalid request ID format"}, 400
                
            request = CreditsLog.query.get(request_uuid)
            if not request:
                return {"error": "Request not found"}, 404
            
            # Convert team_id to UUID for comparison
            try:
                team_uuid = uuid.UUID(team_id)
            except ValueError:
                return {"error": "Invalid team ID format"}, 400
                
            if request.team_id != team_uuid:
                return {"error": "Request not found"}, 404

            if request.reference_type != 'credit_request':
                return {"error": "Not a credit request"}, 400

            # Check if admin has enough credits
            admin_member = WorkspaceMember.query.filter_by(
                workspace_id=team_id,
                role='admin',
                is_active=True
            ).first()

            if not admin_member:
                return {"error": "Admin not found"}, 404

            # Check if the team's unallocated pool has enough credits
            total_allocated = db.session.query(
                db.func.sum(WorkspaceMember.credits_allocated)
            ).filter(WorkspaceMember.workspace_id == team_id).scalar() or 0
            
            available_pool = workspace.total_credit_pool - total_allocated
            
            if request.amount > available_pool:
                return {"error": f"Not enough credits in the pool. Requested: {request.amount}, Available: {available_pool}"}, 400

            target_member = WorkspaceMember.query.filter_by(
                workspace_id=team_id, user_id=request.user_id, is_active=True
            ).first()
            
            if target_member:
                target_member.credits_allocated += request.amount
            else:
                return {"error": "Target member not found in workspace"}, 404
            
            # Create credit allocation log
            CreditsLog.log_allocation(
                team_id=team_id,
                user_id=request.user_id,
                amount=request.amount,
                allocated_by=current_user.user_id,
                notes=f"Approved credit request: {request.notes}"
            )

            # Update request reference type to approved
            request.reference_type = 'approved_request'
            request.created_by = current_user.user_id
            db.session.commit()

            return {"message": "Credit request approved successfully"}, 200

        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to approve request: {str(e)}"}, 500

    @staticmethod
    def reject_credit_request(team_id, request_id, data):
        """Reject credit request"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            workspace = Workspace.query.get(team_id)
            if not workspace:
                return {"error": "Team not found"}, 404

            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can reject requests"}, 403

            # Get the request
            from models.credits_log_model import CreditsLog
            
            # Convert request_id to UUID
            try:
                request_uuid = uuid.UUID(request_id)
            except ValueError:
                return {"error": "Invalid request ID format"}, 400
                
            request = CreditsLog.query.get(request_uuid)
            if not request:
                return {"error": "Request not found"}, 404
            
            # Convert team_id to UUID for comparison
            try:
                team_uuid = uuid.UUID(team_id)
            except ValueError:
                return {"error": "Invalid team ID format"}, 400
                
            if request.team_id != team_uuid:
                return {"error": "Request not found"}, 404

            if request.reference_type != 'credit_request':
                return {"error": "Not a credit request"}, 400

            # Update request reference type to rejected and add rejection note
            request.reference_type = 'rejected_request'
            request.created_by = current_user.user_id
            request.notes = f"Rejected: {data.get('reason', 'No reason provided')}"

            db.session.commit()

            return {"message": "Credit request rejected successfully"}, 200

        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to reject request: {str(e)}"}, 500

    @staticmethod
    def assign_team_credits(team_id, data):
        """Adding or subtracting member's credit"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            workspace = Workspace.query.get(team_id)
            if not workspace:
                return {"error": "Team not found"}, 404

            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can assign credits"}, 403

            member_id = data.get('member_id')
            amount = data.get('amount', 0)
            action = data.get('action')

            if not member_id:
                return {"error": "Member ID is required"}, 400

            if amount <= 0:
                return {"error": "Amount must be greater than 0"}, 400

            if action not in ['add', 'subtract']:
                return {"error": "Action must be either 'add' or 'subtract'"}, 400
            
            admin_member = WorkspaceMember.query.filter_by(
                workspace_id=team_id,
                role='admin',
                is_active=True
            ).first()

            if not admin_member:
                return {"error": "Admin not found"}, 404

            # Sum of credits already allocated to ALL members in this workspace
            total_allocated_in_team = db.session.query(
                db.func.sum(WorkspaceMember.credits_allocated)
            ).filter(WorkspaceMember.workspace_id == team_id).scalar() or 0
            
            available_pool = workspace.total_credit_pool - total_allocated_in_team
            
            target_member_record = WorkspaceMember.query.filter_by(
                workspace_id=team_id, user_id=member_id, is_active=True
            ).first()
            if not target_member_record:
                return {"error": "Member not found in this team"}, 404

            if action == 'add':
                if amount > available_pool:
                    return {"error": f"Insufficient team credits. Only {available_pool} available to assign."}, 400
                target_member_record.credits_allocated += amount
                log_reason = f"Admin added {amount} credits."
            
            elif action == 'subtract':
                member_remaining = target_member_record.get_remaining_credits()
                if amount > member_remaining:
                    return {"error": f"Cannot subtract {amount}. Member only has {member_remaining} available credits."}, 400
                
                target_member_record.credits_allocated -= amount
                log_reason = f"Admin subtracted {amount} credits."

            # Create credit allocation log
            CreditsLog.log_allocation(
                team_id=team_id,
                user_id=member_id,
                amount=amount,
                allocated_by=current_user.user_id,
                notes=log_reason
            )

            db.session.commit()

            return {"message": "Credits assigned successfully"}, 200

        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to assign credits: {str(e)}"}, 500


    @staticmethod
    def get_team_member_credits(team_id):
        """Get total credits assigned to team members (excluding admin)"""
        try:
            workspace = Workspace.query.get(team_id)
            if not workspace:
                return 0
                
            # Get all active members except admins
            members = WorkspaceMember.query.filter_by(
                workspace_id=team_id,
                is_active=True
            ).filter(WorkspaceMember.role != 'admin').all()
            
            total_credits = 0
            for member in members:
                try:
                    from models.user_subscription_model import UserSubscription
                    from controllers.subscription_controller import SubscriptionController
                    from models.user_model import User
                    
                    user = User.query.get(member.user_id)
                    if not user:
                        continue
                        
                    # Get subscription info including plan details
                    sub_info, status_code = SubscriptionController.get_current_user_subscription_info(user)
                    if status_code == 200:
                        subscription = sub_info.get('subscription', {})
                        plan = sub_info.get('plan', {})
                        
                        # Add base credits
                        total_credits += subscription.get('credits_remaining', 0)
                        
                        # Add initial credits if available and not Platinum/Enterprise
                        plan_name = subscription.get('plan_name', '').lower()
                        if plan_name not in ['platinum', 'enterprise'] and plan.get('initial_credits') is not None:
                            total_credits += plan.get('initial_credits', 0)
                            
                except Exception as e:
                    print(f"Error getting credits for user {member.user_id}: {e}")
                    
            return total_credits
        except Exception as e:
            print(f"Error calculating team member credits: {e}")
            return 0

    @staticmethod
    def get_team_activity(team_id):
        """Get team activity logs"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate team_id
            try:
                team_uuid = uuid.UUID(team_id)
            except ValueError:
                return {"error": "Invalid team ID"}, 400
            
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
            
            # Check if user is member
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get activity logs
            logs = WorkspaceActivityLog.get_workspace_activity(
                workspace_id=team_uuid,
                limit=50
            )
            
            activity_data = []
            for log in logs:
                activity_data.append(log.to_dict())
            
            return {"activity": activity_data}, 200
            
        except Exception as e:
            return {"error": f"Failed to get team activity: {str(e)}"}, 500

    @staticmethod
    def get_my_team_credits(team_id):
        """Get my credits in a specific team (member flow)"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate team_id
            try:
                team_uuid = uuid.UUID(team_id)
            except ValueError:
                return {"error": "Invalid team ID"}, 400
            
            workspace = Workspace.query.get(team_uuid)
            if not workspace:
                return {"error": "Team not found"}, 404
            
            # Check if user is member
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get user's membership
            membership = WorkspaceMember.query.filter_by(
                workspace_id=workspace.workspace_id,
                user_id=current_user.user_id,
                is_active=True
            ).first()
            
            if not membership:
                return {"error": "User is not a member of this team"}, 404
            
            # Get credits from user subscription (consistent with subscription info)
            credits_remaining = 0
            try:
                from models.user_subscription_model import UserSubscription
                user_subscription = UserSubscription.query.filter_by(user_id=str(current_user.user_id)).first()
                if user_subscription:
                    credits_remaining = user_subscription.credits_remaining
                else:
                    # Fallback: get from SubscriptionController (includes default Free plan logic)
                    from controllers.subscription_controller import SubscriptionController
                    sub_info, status_code = SubscriptionController.get_current_user_subscription_info(current_user)
                    if status_code == 200:
                        credits_remaining = sub_info.get('subscription', {}).get('credits_remaining', 0)
            except Exception as e:
                print(f"Error getting user subscription: {e}")
            
            credits_data = {
                'credits': credits_remaining,
                'credits_allocated': credits_remaining,  # For compatibility
                'credits_used': 0,  # Not tracked at team level
                'team_id': str(workspace.workspace_id),
                'team_name': workspace.name
            }
            
            return credits_data, 200
            
        except Exception as e:
            return {"error": f"Failed to get team credits: {str(e)}"}, 500 