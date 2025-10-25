from flask import jsonify, request, current_app
from flask_login import current_user
from models.workspace_model import Workspace
from models.workspace_member_model import WorkspaceMember
from models.workspace_settings_model import WorkspaceSettings
from models.workspace_invitation_model import WorkspaceInvitation
from models.workspace_activity_log_model import WorkspaceActivityLog
from models.workspace_task_model import WorkspaceTask
from models.project_model import Project
from models.project_member_model import ProjectMember
from models.lead_model import db
import uuid
from datetime import datetime

class WorkspaceController:
    """Controller for workspace operations"""
    
    @staticmethod
    def create_workspace(data):
        """Create a new workspace"""
        try:
            # Validate required fields
            if not data.get('name'):
                return {"error": "Workspace name is required"}, 400
            
            # Check if user can create workspace
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Check subscription tier
            allowed_tiers = ['platinum', 'enterprise', 'platinum_annual']
            user_tier = current_user.tier.lower()
            
            if user_tier not in allowed_tiers:
                return {
                    "error": f"Workspace creation requires Platinum or Enterprise tier. Current tier: {current_user.tier}"
                }, 403
            
            # Check if user already has a workspace (active or deleted)
            existing_workspace = Workspace.query.filter_by(
                created_by=current_user.user_id,
                is_active=True
            ).first()
            
            if existing_workspace:
                return {
                    "error": "You can only create one workspace. You already have an active workspace."
                }, 400
            
            # Check if user has previously created a workspace (for credit calculation)
            previous_workspace = Workspace.query.filter_by(
                created_by=current_user.user_id
            ).first()
            
            # Allow workspace recreation but with proper credit management
            # No blocking, just smart credit allocation
            
            print(f"User {current_user.email} (tier: {current_user.tier}) creating workspace")
            
            # Create workspace
            workspace = Workspace.create(
                name=data['name'],
                description=data.get('description'),
                domain=data.get('domain'),
                industry=data.get('industry'),
                size=data.get('size', 'medium'),
                created_by=current_user.user_id,
                company_id=current_user.company_id
            )
            
            # Add creator as admin
            WorkspaceMember.create(
                workspace_id=workspace.workspace_id,
                user_id=current_user.user_id,
                role='admin'
            )
            
            # Create default settings
            WorkspaceSettings.create(
                workspace_id=workspace.workspace_id,
                updated_by=current_user.user_id
            )
            
            # Set admin credits - restore previous credits or give 2000 for first time
            from models.user_subscription_model import UserSubscription
            admin_subscription = UserSubscription.query.filter_by(user_id=str(current_user.user_id)).first()
            
            # Check if user had previous workspace and remaining credits
            credits_to_assign = 2000  # Default for first-time users
            
            if previous_workspace:
                # User is recreating workspace - check their current credits
                if admin_subscription and admin_subscription.credits_remaining > 0:
                    # User has remaining credits, keep them
                    credits_to_assign = admin_subscription.credits_remaining
                    print(f"Restoring {credits_to_assign} credits for returning workspace creator")
                else:
                    # User had workspace before but no credits left, still give 2000 for legitimate recreate
                    credits_to_assign = 2000
                    print(f"Previous workspace user with no credits, giving {credits_to_assign} credits")
            
            if admin_subscription:
                # Update existing subscription with appropriate credits
                admin_subscription.credits_remaining = credits_to_assign
            else:
                # Create new subscription 
                from models.plan_model import Plan
                # Get Platinum plan for workspace creators
                user_plan = Plan.query.filter(Plan.plan_name.ilike('Platinum')).first()
                if not user_plan:
                    user_plan = Plan.query.filter(Plan.plan_name.ilike('Enterprise')).first()
                
                if user_plan:
                    admin_subscription = UserSubscription(
                        user_id=str(current_user.user_id),
                        plan_id=user_plan.plan_id,
                        plan_name=user_plan.plan_name,
                        credits_remaining=credits_to_assign,
                        tier_start_timestamp=datetime.utcnow(),
                        payment_frequency='monthly',
                        username=current_user.username
                    )
                    db.session.add(admin_subscription)
            
            # Create allocation log for tracking
            from models.credits_log_model import CreditsLog
            CreditsLog.log_allocation(
                team_id=workspace.workspace_id,
                user_id=current_user.user_id,
                amount=credits_to_assign,
                allocated_by=current_user.user_id,
                notes=f"Workspace credit allocation: {credits_to_assign} credits ({'restored' if previous_workspace and credits_to_assign < 2000 else 'initial'})"
            )
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=workspace.workspace_id,
                action='workspace_created',
                user_id=current_user.user_id,
                entity_type='workspace',
                entity_id=workspace.workspace_id,
                changes={'workspace_name': workspace.name}
            )
            
            db.session.commit()
            
            return workspace.to_dict(), 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to create workspace: {str(e)}"}, 500
    
    @staticmethod
    def create_workspace_v2(data):
        """Create a new workspace"""
        try:
            # Validate required fields
            if not data.get('name'):
                return {"error": "Workspace name is required"}, 400
            
            # Check if user can create workspace
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            
            # Check if user already has a workspace (active or deleted)
            previous_workspace = Workspace.query.filter_by(
                created_by=current_user.user_id,
            ).order_by(Workspace.created_at).first()
            
            if previous_workspace and previous_workspace.is_active:
                return {"error": "You can only have one active workspace."}, 400
                
            credit_pool_amount = 2000
            if previous_workspace and previous_workspace.total_credit_pool > 0:
                # Rule: If a previous workspace exists, copy its credit pool minus allocated credit.
                total_allocated = db.session.query(
                    db.func.sum(WorkspaceMember.credits_allocated),
                ).filter(
                    WorkspaceMember.workspace_id == previous_workspace.workspace_id
                ).scalar() or 0
                credit_pool_amount = previous_workspace.total_credit_pool - total_allocated
                log_note = f"Workspace credit pool restored from previous workspace: {credit_pool_amount} credits."
            else:
                # Rule: For a brand new workspace, the pool is the admin's current credit balance.
                log_note = f"Initial workspace credit pool set from admin's subscription: {credit_pool_amount} credits."
                
            
            # Create workspace
            workspace = Workspace.create(
                name=data['name'],
                description=data.get('description'),
                domain=data.get('domain'),
                industry=data.get('industry'),
                size=data.get('size', 'medium'),
                created_by=current_user.user_id,
                company_id=current_user.company_id,
                total_credit_pool=credit_pool_amount 
            )
            
            # Add creator as admin
            WorkspaceMember.create(
                workspace_id=workspace.workspace_id,
                user_id=current_user.user_id,
                role='admin'
            )
            
            # Create default settings
            WorkspaceSettings.create(
                workspace_id=workspace.workspace_id,
                updated_by=current_user.user_id
            )
            

            from models.credits_log_model import CreditsLog
            CreditsLog.log_allocation(
                team_id=workspace.workspace_id,
                user_id=current_user.user_id,
                amount=credit_pool_amount,
                allocated_by=current_user.user_id,
                notes=f"Workspace credit allocation: {credit_pool_amount} credits ({'restored' if previous_workspace and credit_pool_amount < 2000 else 'initial'})"
            )
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=workspace.workspace_id,
                action='workspace_created',
                user_id=current_user.user_id,
                entity_type='workspace',
                entity_id=workspace.workspace_id,
                changes={'workspace_name': workspace.name, 'credit_pool': credit_pool_amount}
            )

            if previous_workspace:
                WorkspaceController.delete_workspace(previous_workspace.workspace_id)
            
            db.session.commit()
            
            return workspace.to_dict(), 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to create workspace: {str(e)}"}, 500

    @staticmethod
    def get_user_workspaces():
        """Get all workspaces for current user"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            print(f"Getting workspaces for user: {current_user.email} (ID: {current_user.user_id})")
            
            # Get workspaces where user is a member
            memberships = WorkspaceMember.query.filter_by(
                user_id=current_user.user_id,
                is_active=True
            ).all()
            
            print(f"Found {len(memberships)} memberships")
            
            workspaces = []
            for membership in memberships:
                workspace = membership.get_workspace()
                if workspace and workspace.is_active:
                    workspace_data = workspace.to_dict()
                    workspace_data['user_role'] = membership.role
                    workspace_data['joined_at'] = membership.joined_at.isoformat() if membership.joined_at else None
                    
                    # Calculate additional statistics
                    projects = workspace.get_projects()
                    total_tasks = 0
                    completed_tasks = 0
                    active_tasks = 0
                    
                    for project in projects:
                        # Get project tasks (this would need to be implemented)
                        # For now, using placeholder values
                        project_tasks = 10  # Placeholder
                        project_completed = 5  # Placeholder
                        total_tasks += project_tasks
                        completed_tasks += project_completed
                        active_tasks += (project_tasks - project_completed)
                    
                    workspace_data['completion_rate'] = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                    workspace_data['active_tasks'] = active_tasks
                    
                    workspaces.append(workspace_data)
            
            # Always get workspaces created by user (in addition to memberships)
            print("Getting workspaces created by user")
            created_workspaces = Workspace.query.filter_by(
                created_by=current_user.user_id,
                is_active=True
            ).all()
            
            print(f"Found {len(created_workspaces)} workspaces created by user")
            
            for workspace in created_workspaces:
                # Check if already added via membership
                already_added = any(w.get('workspace_id') == str(workspace.workspace_id) for w in workspaces)
                
                if not already_added:
                    workspace_data = workspace.to_dict()
                    workspace_data['user_role'] = 'admin'  # Creator is admin
                    workspace_data['joined_at'] = workspace.created_at.isoformat() if workspace.created_at else None
                    
                    # Calculate additional statistics
                    projects = workspace.get_projects()
                    total_tasks = 0
                    completed_tasks = 0
                    active_tasks = 0
                    
                    for project in projects:
                        # Get project tasks (this would need to be implemented)
                        # For now, using placeholder values
                        project_tasks = 10  # Placeholder
                        project_completed = 5  # Placeholder
                        total_tasks += project_tasks
                        completed_tasks += project_completed
                        active_tasks += (project_tasks - project_completed)
                    
                    workspace_data['completion_rate'] = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                    workspace_data['active_tasks'] = active_tasks
                    
                    workspaces.append(workspace_data)
                    print(f"Added created workspace: {workspace.name}")
            
            print(f"Returning {len(workspaces)} workspaces")
            return {"workspaces": workspaces}, 200
            
        except Exception as e:
            print(f"Error in get_user_workspaces: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to get workspaces: {str(e)}"}, 500
    
    @staticmethod
    def get_workspace(workspace_id):
        """Get workspace details"""
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
            
            workspace_data = workspace.to_dict()
            workspace_data['user_role'] = user_role
            workspace_data['can_manage'] = workspace.can_user_manage(current_user.user_id)
            workspace_data['can_admin'] = workspace.can_user_admin(current_user.user_id)
            
            # Calculate additional statistics
            projects = workspace.get_projects()
            total_tasks = 0
            completed_tasks = 0
            active_tasks = 0
            
            for project in projects:
                # Get project tasks (this would need to be implemented)
                # For now, using placeholder values
                project_tasks = 10  # Placeholder
                project_completed = 5  # Placeholder
                total_tasks += project_tasks
                completed_tasks += project_completed
                active_tasks += (project_tasks - project_completed)
            
            workspace_data['completion_rate'] = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            workspace_data['active_tasks'] = active_tasks
            
            # Add company subscription information
            company = workspace.get_company()
            if company:
                workspace_data['subscription_tier'] = company.subscription_tier
                workspace_data['total_credits'] = company.total_credits
                workspace_data['credits_used'] = company.credits_used
                workspace_data['max_members'] = company.max_members
                # Add a placeholder plan price (this would come from a plan model)
                workspace_data['plan_price'] = 29  # Placeholder
            else:
                # Default values if no company
                workspace_data['subscription_tier'] = 'free'
                workspace_data['total_credits'] = 0
                workspace_data['credits_used'] = 0
                workspace_data['max_members'] = 1
                workspace_data['plan_price'] = 0
            
            return workspace_data, 200
            
        except Exception as e:
            return {"error": f"Failed to get workspace: {str(e)}"}, 500
    
    @staticmethod
    def update_workspace(workspace_id, data):
        """Update workspace"""
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
                return {"error": "Only admins can update workspace"}, 403
            
            # Track changes
            changes = {}
            allowed_fields = ['name', 'description', 'domain', 'industry', 'size']
            
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
                    action='workspace_updated',
                    user_id=current_user.user_id,
                    entity_type='workspace',
                    entity_id=workspace.workspace_id,
                    changes=changes
                )
            
            return workspace.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update workspace: {str(e)}"}, 500
    
    @staticmethod
    def delete_workspace(workspace_id):
        """Delete workspace"""
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
            
            # Check if user can delete workspace
            if not workspace.can_user_admin(current_user.user_id):
                return {"error": "Only admins can delete workspace"}, 403
            
            # Log activity before deletion
            WorkspaceActivityLog.create(
                workspace_id=workspace.workspace_id,
                action='workspace_deleted',
                user_id=current_user.user_id,
                entity_type='workspace',
                entity_id=workspace.workspace_id,
                changes={'workspace_name': workspace.name}
            )
            
            # Delete workspace (cascade will handle related data)
            workspace.delete_workspace()
            
            return {"message": "Workspace deleted successfully"}, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to delete workspace: {str(e)}"}, 500
    
    @staticmethod
    def archive_workspace(workspace_id):
        """Archive workspace"""
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
            
            # Check if user can archive workspace
            if not workspace.can_user_admin(current_user.user_id):
                return {"error": "Only admins can archive workspace"}, 403
            
            # Archive workspace by setting is_active to False
            workspace.is_active = False
            workspace.update()
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=workspace.workspace_id,
                action='workspace_archived',
                user_id=current_user.user_id,
                entity_type='workspace',
                entity_id=workspace.workspace_id,
                changes={'workspace_name': workspace.name}
            )
            
            return {"message": "Workspace archived successfully"}, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to archive workspace: {str(e)}"}, 500
    
    @staticmethod
    def get_workspace_overview(workspace_id):
        """Get workspace overview with statistics"""
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
            
            # Get recent activity
            recent_activity = WorkspaceActivityLog.get_workspace_activity(
                workspace_id=workspace.workspace_id,
                limit=10
            )
            
            # Get active members
            active_members = workspace.get_members()
            
            # Get projects summary
            projects = workspace.get_projects()
            project_stats = {
                'total': len(projects),
                'active': len([p for p in projects if p.status == 'active']),
                'completed': len([p for p in projects if p.status == 'completed']),
                'archived': len([p for p in projects if p.status == 'archived']),
                'paused': len([p for p in projects if p.status == 'paused'])
            }
            
            overview = {
                'workspace': workspace.to_dict(),
                'statistics': {
                    'member_count': workspace.get_member_count(),
                    'project_stats': project_stats,
                    'active_projects': workspace.get_active_project_count()
                },
                'recent_activity': [log.to_dict() for log in recent_activity],
                'active_members': [member.to_dict() for member in active_members[:5]]  # Top 5
            }
            
            return overview, 200
            
        except Exception as e:
            return {"error": f"Failed to get workspace overview: {str(e)}"}, 500
    
    @staticmethod
    def search_workspaces(query):
        """Search workspaces by name or description"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            if not query or len(query.strip()) < 2:
                return {"error": "Search query must be at least 2 characters"}, 400
            
            # Get user's workspaces
            memberships = WorkspaceMember.query.filter_by(
                user_id=current_user.user_id,
                is_active=True
            ).all()
            
            workspace_ids = [m.workspace_id for m in memberships]
            
            # Search in user's workspaces
            workspaces = Workspace.query.filter(
                Workspace.workspace_id.in_(workspace_ids),
                Workspace.is_active == True,
                (Workspace.name.ilike(f'%{query}%') | 
                 Workspace.description.ilike(f'%{query}%'))
            ).all()
            
            results = []
            for workspace in workspaces:
                membership = next(m for m in memberships if m.workspace_id == workspace.workspace_id)
                workspace_data = workspace.to_dict()
                workspace_data['user_role'] = membership.role
                results.append(workspace_data)
            
            return {"workspaces": results, "query": query}, 200
            
        except Exception as e:
            return {"error": f"Failed to search workspaces: {str(e)}"}, 500 

    @staticmethod
    def get_member_project_and_task_info(workspace_id, workspace_member_id):
        """
        Retrieves a workspace member's info, including a list of projects
        they are a member of and all tasks assigned to them in that workspace.
        """
        try:
            workspace = Workspace.query.get(workspace_id)
            if not workspace:
                return {"error": "Workspace not found"}, 404

            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied: You are not a member of this workspace."}, 403
            
            target_member = WorkspaceMember.query.get(workspace_member_id)
            if not target_member or str(target_member.workspace_id) != workspace_id:
                return {"error": "Workspace member not found in this workspace."}, 404

            # Find all ProjectMember entries linking this member to projects
            project_memberships = ProjectMember.query.filter_by(
                workspace_member_id=target_member.workspace_member_id
            ).all()
            project_ids = [pm.project_id for pm in project_memberships]

            # Fetch all associated projects in a single query
            projects = Project.query.filter(Project.project_id.in_(project_ids)).all()
            
            # Fetch all tasks assigned to this member within the workspace in a single query
            tasks = WorkspaceTask.query.filter_by(
                workspace_id=workspace.workspace_id,
                assigned_to=target_member.user_id
            ).all()

            # Convert projects and tasks to dictionaries to be inserted into response body
            projects_data = [p.to_dict() for p in projects]
            tasks_data = [t.to_dict() for t in tasks]

            member_data = target_member.to_dict()

            member_data['projects'] = projects_data
            member_data['tasks'] = tasks_data
            
            return member_data, 200

        except Exception as e:
            current_app.logger.error(f"Error fetching member info: {e}", exc_info=True)
            return {"error": "An internal server error occurred."}, 500
