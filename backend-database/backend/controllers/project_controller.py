from flask import jsonify, request, current_app
from flask_login import current_user
from models.workspace_model import Workspace
from models.project_model import Project
from models.workspace_member_model import WorkspaceMember
from models.workspace_task_model import WorkspaceTask

from models.workspace_activity_log_model import WorkspaceActivityLog
from models.project_member_model import ProjectMember
from models.user_model import User
from models.lead_model import db
import uuid
from datetime import datetime
from collections import defaultdict
from sqlalchemy import func, case

class ProjectController:
    """Controller for project operations"""
    
    @staticmethod
    def get_workspace_projects(workspace_id):
        """Get all projects in a workspace"""
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
            
            # Get all projects
            projects = workspace.get_projects()
            
            # Filter by status if provided
            status_filter = request.args.get('status')
            if status_filter:
                projects = [p for p in projects if p.status == status_filter]
            
            # Sort projects
            sort_by = request.args.get('sort_by', 'created_at')
            sort_order = request.args.get('sort_order', 'desc')
            
            if sort_by == 'name':
                projects.sort(key=lambda x: x.name.lower(), reverse=(sort_order == 'desc'))
            elif sort_by == 'due_date':
                projects.sort(key=lambda x: x.due_date or datetime.max, reverse=(sort_order == 'desc'))
            elif sort_by == 'priority':
                priority_order = {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}
                projects.sort(key=lambda x: priority_order.get(x.priority, 0), reverse=(sort_order == 'desc'))
            else:  # created_at
                projects.sort(key=lambda x: x.created_at, reverse=(sort_order == 'desc'))
            
            # Add task information to each project
            projects_with_tasks = []
            for project in projects:
                project_data = project.to_dict()
                
                # Get project tasks
                tasks = project.get_tasks()
                project_data['task_count'] = len(tasks)
                project_data['completed_task_count'] = len([task for task in tasks if task.status == 'completed'])
                project_data['completion_rate'] = (project_data['completed_task_count'] / project_data['task_count'] * 100) if project_data['task_count'] > 0 else 0
                
                projects_with_tasks.append(project_data)
            
            return {"projects": projects_with_tasks}, 200
            
        except Exception as e:
            return {"error": f"Failed to get projects: {str(e)}"}, 500
    
    @staticmethod
    def get_workspace_projects_v2(workspace_id):
        """Get all projects in a workspace"""
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

            # Get all projects
            projects = workspace.get_projects()
            if not projects:
                return {"projects": []}, 200
            
            project_ids = [p.project_id for p in projects]

            project_memberships = ProjectMember.query.filter(
                ProjectMember.project_id.in_(project_ids)
            ).all()

            # Get all workspace members in this workspace for a fast lookup map.
            workspace_members = WorkspaceMember.query.filter_by(workspace_id=workspace_id).all()
            member_details_map = {
                str(member.workspace_member_id): {
                    "workspace_member_id": str(member.workspace_member_id),
                    "name": member.get_user().username if member.get_user() else "Unknown User",
                    "role": member.role
                }
                for member in workspace_members
            }

            # Get task counts for all projects 
            task_counts_query = db.session.query(
                WorkspaceTask.project_id,
                func.count(WorkspaceTask.task_id).label("total_tasks"),
                func.sum(case((WorkspaceTask.status == 'completed', 1), else_=0)).label("completed_tasks")
            ).filter(
                WorkspaceTask.project_id.in_(project_ids)
            ).group_by(
                WorkspaceTask.project_id
            ).all()

            # Create a lookup map for project memberships
            members_by_project = defaultdict(list)
            for pm in project_memberships:
                member_detail = member_details_map.get(str(pm.workspace_member_id))
                if member_detail:
                    members_by_project[str(pm.project_id)].append(member_detail)
            
            # Create a lookup map for task counts
            task_counts_map = {
                str(pid): {"total": total, "completed": completed}
                for pid, total, completed in task_counts_query
            }

            
            # Filter by status if provided
            status_filter = request.args.get('status')
            if status_filter:
                projects = [p for p in projects if p.status == status_filter]
            
            # Sort projects
            sort_by = request.args.get('sort_by', 'created_at')
            sort_order = request.args.get('sort_order', 'desc')
            
            if sort_by == 'name':
                projects.sort(key=lambda x: x.name.lower(), reverse=(sort_order == 'desc'))
            elif sort_by == 'due_date':
                projects.sort(key=lambda x: x.due_date or datetime.max, reverse=(sort_order == 'desc'))
            elif sort_by == 'priority':
                priority_order = {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}
                projects.sort(key=lambda x: priority_order.get(x.priority, 0), reverse=(sort_order == 'desc'))
            else:  # created_at
                projects.sort(key=lambda x: x.created_at, reverse=(sort_order == 'desc'))

            projects_with_details = []
            for project in projects:
                project_data = project.to_dict() 

                # Add the members
                project_data['members'] = members_by_project.get(project_data['project_id'], [])


                # Update task counts using the pre-fetched data
                counts = task_counts_map.get(project_data['project_id'], {"total": 0, "completed": 0})
                project_data['task_count'] = counts['total']
                project_data['completed_task_count'] = counts['completed']
                project_data['completion_rate'] = (counts['completed'] / counts['total'] * 100) if counts['total'] > 0 else 0
                
                projects_with_details.append(project_data)
            
            return {"projects": projects_with_details}, 200

        except Exception as e:
            return {"error": f"Failed to get projects: {str(e)}"}, 500

    
    @staticmethod
    def create_project(workspace_id, data):
        """Create a new project"""
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
            
            # Check if user can create projects (admin or manager only)
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or current_member.role not in ['admin', 'manager']:
                return {"error": "Only admins and managers can create projects"}, 403
            
            # Validate required fields
            if not data.get('name'):
                return {"error": "Project name is required"}, 400
            
            # Validate status and priority
            status = data.get('status', 'active')
            if status not in ['active', 'completed', 'archived', 'paused']:
                return {"error": "Invalid status"}, 400
            
            priority = data.get('priority', 'medium')
            if priority not in ['low', 'medium', 'high', 'urgent']:
                return {"error": "Invalid priority"}, 400
            
            # Parse dates
            start_date = None
            due_date = None
            
            if data.get('start_date'):
                try:
                    start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
                except ValueError:
                    return {"error": "Invalid start date format. Use YYYY-MM-DD"}, 400
            
            if data.get('due_date'):
                try:
                    due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
                except ValueError:
                    return {"error": "Invalid due date format. Use YYYY-MM-DD"}, 400

            # Validate all provided team members in a single, efficient query.
            team_member_ids_str = data.get('team_members', [])
            team_member_ids_str.append(str(current_member.workspace_member_id))
            team_member_ids_str = list(set(team_member_ids_str))

            valid_members = []
            if team_member_ids_str:
                member_uuids = [uuid.UUID(mid) for mid in team_member_ids_str]
                
                valid_members = WorkspaceMember.query.filter(
                    WorkspaceMember.workspace_id == workspace.workspace_id,
                    WorkspaceMember.workspace_member_id.in_(member_uuids)
                ).all()

                # If the count doesn't match, some IDs were invalid.
                if len(valid_members) != len(team_member_ids_str):
                    return {"error": "One or more team members are invalid or do not belong to this workspace."}, 400
            
            # Create project
            project = Project.create(
                workspace_id=workspace.workspace_id,
                name=data['name'],
                description=data.get('description'),
                status=status,
                priority=priority,
                start_date=start_date,
                due_date=due_date,
                created_by=current_user.user_id,
                assigned_to=data.get('assigned_to'),
                revenue=data.get('revenue'),        
                location=data.get('location'),      
                employees=data.get('employees'),    
                progress=data.get('progress', 0)    
            )

            db.session.flush()
            
            if valid_members:
                for member in valid_members:
                    project_member = ProjectMember(
                        project_id=project.project_id,
                        workspace_member_id=member.workspace_member_id,
                        added_by=current_user.user_id
                    )
                    db.session.add(project_member)
    
            # Add metrics if provided
            if 'metrics' in data:
                from models.project_metrics_model import ProjectMetrics
                for metric_data in data['metrics']:
                    ProjectMetrics.create(
                        project_id=project.project_id,
                        name=metric_data['name'],
                        value=metric_data['value'],
                        created_by=current_user.user_id
                    )
            
            # Log activity
            WorkspaceActivityLog.log_project_created(
                workspace_id=workspace.workspace_id,
                project_id=project.project_id,
                user_id=current_user.user_id,
                project_name=project.name
            )

            db.session.commit()
            
            project_data = project.to_dict()

            project_data['members'] = [str(mem.workspace_member_id) for mem in valid_members]
            
            # Get project metrics
            if 'metrics' in data:
                from models.project_metrics_model import ProjectMetrics
                metrics = ProjectMetrics.get_project_metrics(project.project_id)
                project_data['metrics'] = [metric.to_dict() for metric in metrics]
            
            return project_data, 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to create project: {str(e)}"}, 500
    
    @staticmethod
    def get_project(project_id):
        """Get project details"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate project_id
            try:
                project_uuid = uuid.UUID(project_id)
            except ValueError:
                return {"error": "Invalid project ID"}, 400
            
            project = Project.query.get(project_uuid)
            if not project:
                return {"error": "Project not found"}, 404
            
            # Check if user is member of workspace
            workspace = project.get_workspace()
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get project data with additional info
            project_data = project.to_dict()
            project_data['workspace'] = workspace.to_dict()
            
            # Get project metrics
            from models.project_metrics_model import ProjectMetrics
            metrics = ProjectMetrics.get_project_metrics(project.project_id)
            project_data['metrics'] = [metric.to_dict() for metric in metrics]
            
            # Get project members
            members_query = db.session.query(
                ProjectMember,
                WorkspaceMember,
                User
            ).join(
                WorkspaceMember, ProjectMember.workspace_member_id == WorkspaceMember.workspace_member_id
            ).join(
                User, WorkspaceMember.user_id == User.user_id
            ).filter(
                ProjectMember.project_id == project.project_id
            ).all()

            members_list = []
            for project_member, workspace_member, user in members_query:
                members_list.append({
                    "project_member_id": str(project_member.project_member_id),
                    "workspace_member_id": str(workspace_member.workspace_member_id),
                    "user_id": str(user.user_id),
                    "username": user.username,
                    "workspace_role": workspace_member.role, # Role within the workspace
                    "added_at": project_member.added_at.isoformat()
                })

            project_data['members'] = members_list
            return project_data, 200
            
        except Exception as e:
            return {"error": f"Failed to get project: {str(e)}"}, 500
    
    @staticmethod
    def update_project(project_id, data):
        """Update project"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate project_id
            try:
                project_uuid = uuid.UUID(project_id)
            except ValueError:
                return {"error": "Invalid project ID"}, 400
            
            project = Project.query.get(project_uuid)
            if not project:
                return {"error": "Project not found"}, 404
            
            # Check if user can manage projects
            workspace = project.get_workspace()
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can update projects"}, 403
            
            # Get current user's member record to check specific permissions
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or not current_member.can_edit_projects():
                return {"error": "You don't have permission to edit projects"}, 403
            
            # Track changes
            changes = {}
            allowed_fields = ['name', 'description', 'status', 'priority', 'assigned_to']
            
            for field in allowed_fields:
                if field in data:
                    old_value = getattr(project, field)
                    if old_value != data[field]:
                        changes[field] = {'old': old_value, 'new': data[field]}
                        setattr(project, field, data[field])
            
            # Handle date fields
            if data.get('start_date'):
                try:
                    new_start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
                    if project.start_date != new_start_date:
                        changes['start_date'] = {'old': project.start_date, 'new': new_start_date}
                        project.start_date = new_start_date
                except ValueError:
                    return {"error": "Invalid start date format. Use YYYY-MM-DD"}, 400
            
            if data.get('due_date'):
                try:
                    new_due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
                    if project.due_date != new_due_date:
                        changes['due_date'] = {'old': project.due_date, 'new': new_due_date}
                        project.due_date = new_due_date
                except ValueError:
                    return {"error": "Invalid due date format. Use YYYY-MM-DD"}, 400
            
            if changes:
                project.update()
                
                # Log activity
                WorkspaceActivityLog.log_project_updated(
                    workspace_id=workspace.workspace_id,
                    project_id=project.project_id,
                    user_id=current_user.user_id,
                    changes=changes
                )
            
            return project.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update project: {str(e)}"}, 500
    
    @staticmethod
    def delete_project(project_id):
        """Delete project"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate project_id
            try:
                project_uuid = uuid.UUID(project_id)
            except ValueError:
                return {"error": "Invalid project ID"}, 400
            
            project = Project.query.get(project_uuid)
            if not project:
                return {"error": "Project not found"}, 404
            
            # Check if user can manage projects
            workspace = project.get_workspace()
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can delete projects"}, 403
            
            # Get current user's member record to check specific permissions
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or not current_member.can_edit_projects():
                return {"error": "You don't have permission to delete projects"}, 403
            
            # Log activity before deletion
            WorkspaceActivityLog.create(
                workspace_id=workspace.workspace_id,
                action='project_deleted',
                user_id=current_user.user_id,
                entity_type='project',
                entity_id=project.project_id,
                changes={'project_name': project.name}
            )
            
            # Delete project (cascade will handle related data)
            db.session.delete(project)
            db.session.commit()
            
            return {"message": "Project deleted successfully"}, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to delete project: {str(e)}"}, 500
    
    @staticmethod
    def get_project_statistics(workspace_id):
        """Get project statistics for workspace"""
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
            
            # Get all projects
            projects = workspace.get_projects()
            
            # Calculate statistics
            total_projects = len(projects)
            active_projects = len([p for p in projects if p.status == 'active'])
            completed_projects = len([p for p in projects if p.status == 'completed'])
            archived_projects = len([p for p in projects if p.status == 'archived'])
            paused_projects = len([p for p in projects if p.status == 'paused'])
            
            # Priority breakdown
            priority_stats = {
                'urgent': len([p for p in projects if p.priority == 'urgent']),
                'high': len([p for p in projects if p.priority == 'high']),
                'medium': len([p for p in projects if p.priority == 'medium']),
                'low': len([p for p in projects if p.priority == 'low'])
            }
            
            # Overdue projects
            overdue_projects = [p for p in projects if p.is_overdue()]
            
            # Recent projects (last 30 days)
            from datetime import timedelta
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_projects = [p for p in projects if p.created_at >= thirty_days_ago]
            
            statistics = {
                'total_projects': total_projects,
                'status_breakdown': {
                    'active': active_projects,
                    'completed': completed_projects,
                    'archived': archived_projects,
                    'paused': paused_projects
                },
                'priority_breakdown': priority_stats,
                'overdue_projects': len(overdue_projects),
                'recent_projects': len(recent_projects),
                'completion_rate': (completed_projects / total_projects * 100) if total_projects > 0 else 0
            }
            
            return statistics, 200
            
        except Exception as e:
            return {"error": f"Failed to get project statistics: {str(e)}"}, 500
    
    @staticmethod
    def search_projects(workspace_id, query):
        """Search projects in workspace"""
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
            
            if not query or len(query.strip()) < 2:
                return {"error": "Search query must be at least 2 characters"}, 400
            
            # Get all projects and filter
            projects = workspace.get_projects()
            
            # Search in project names and descriptions
            results = []
            query_lower = query.lower()
            
            for project in projects:
                if (query_lower in project.name.lower() or 
                    (project.description and query_lower in project.description.lower())):
                    results.append(project.to_dict())
            
            return {"projects": results, "query": query}, 200
            
        except Exception as e:
            return {"error": f"Failed to search projects: {str(e)}"}, 500
    
    @staticmethod
    def leave_project(project_id):
        """Leave project (for members)"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate project_id
            try:
                project_uuid = uuid.UUID(project_id)
            except ValueError:
                return {"error": "Invalid project ID"}, 400
            
            project = Project.query.get(project_uuid)
            if not project:
                return {"error": "Project not found"}, 404
            
            # Check if user is a member of the workspace
            workspace = project.get_workspace()
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            member = workspace.get_member_by_user_id(current_user.user_id)
            if not member:
                return {"error": "You are not a member of this workspace"}, 403
            
            # Check if user is the project creator (admin) - they cannot leave
            if project.created_by == current_user.user_id and member.role == 'admin':
                return {"error": "Project creator cannot leave the project. Please transfer ownership or delete the project."}, 403

            # Find the specific ProjectMember link for this user and project.
            project_member = ProjectMember.query.filter_by(
                project_id=project.project_id,
                workspace_member_id=member.workspace_member_id
            ).first()

            if not project_member:
                return {"error": "You are not a member of this project."}, 403

            
            # Get user email for logging
            user = member.get_user()
            user_email = user.email if user else "Unknown"
            
            # Log activity before removing
            WorkspaceActivityLog.log_project_member_left(
                workspace_id=workspace.workspace_id,
                project_id=project.project_id,
                user_id=current_user.user_id,
                member_email=user_email,
                project_name=project.name
            )

            # Delete the membership record from the database.
            db.session.delete(project_member)
            db.session.commit()
            
            # Note: In current implementation, projects don't have separate member management
            # This is more of a workspace-level action, but we log it as project activity
            # In a more complex system, you might have ProjectMember model
            
            return {"message": "You have successfully left the project"}, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to leave project: {str(e)}"}, 500 
    
    @staticmethod
    def add_member_to_project(project_id, workspace_member_id):
        try:
            project = Project.query.get(uuid.UUID(project_id))
            if not project:
                return {"error": "Project not found"}, 404

            workspace = project.get_workspace()
            if not workspace:
                return {"error": "Associated workspace not found"}, 404

            # Check if the current user can manage the project.
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or not current_member.can_manage_projects():
                return {"error": "You do not have permission to add members to this project"}, 403

            # Validation: Check if the member to be added exists and belongs to this workspace.
            member_to_add = WorkspaceMember.query.get(uuid.UUID(workspace_member_id))
            if not member_to_add or member_to_add.workspace_id != workspace.workspace_id:
                return {"error": "Member not found in this workspace"}, 404

            # Validation: Check if the member is already in the project.
            existing_project_member = ProjectMember.query.filter_by(
                project_id=project.project_id,
                workspace_member_id=member_to_add.workspace_member_id
            ).first()
            if existing_project_member:
                return {"error": "This user is already a member of the project"}, 409 # 409 Conflict

            new_project_member = ProjectMember(
                project_id=project.project_id,
                workspace_member_id=member_to_add.workspace_member_id,
                added_by=current_user.user_id
            )

            db.session.add(new_project_member)
            
            db.session.commit()
            
            return new_project_member.to_dict(), 201

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding member to project {project_id}: {e}", exc_info=True)
            return {"error": "An internal server error occurred"}, 500

    @staticmethod
    def remove_member_from_project(project_id, workspace_member_id):
        try:
            project = Project.query.get(uuid.UUID(project_id))
            if not project:
                return {"error": "Project not found"}, 404

            workspace = project.get_workspace()
            if not workspace:
                return {"error": "Associated workspace not found"}, 404

            # Check if the current user can manage the project.
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or not current_member.can_manage_projects():
                return {"error": "You do not have permission to remove members from this project"}, 403

            # Find the specific ProjectMember record to delete.
            project_member_to_remove = ProjectMember.query.filter_by(
                project_id=project.project_id,
                workspace_member_id=uuid.UUID(workspace_member_id)
            ).first()

            if not project_member_to_remove:
                return {"error": "This user is not a member of the project"}, 404
            
            db.session.delete(project_member_to_remove)
            db.session.commit()

            return {"message": "Member successfully removed from the project"}, 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error removing member from project {project_id}: {e}", exc_info=True)
            return {"error": "An internal server error occurred"}, 500