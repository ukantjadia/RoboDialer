from flask import jsonify, request, current_app
from flask_login import current_user
from models.workspace_task_model import WorkspaceTask
from models.workspace_model import Workspace
from models.workspace_member_model import WorkspaceMember
from models.workspace_activity_log_model import WorkspaceActivityLog
from datetime import datetime
import uuid
from models.lead_model import db

class WorkspaceTaskController:
    """Controller for workspace task operations"""
    
    @staticmethod
    def create_task(workspace_id, data):
        """Create a new task in workspace"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            # Get workspace and check membership
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Validate required fields
            if not data.get('title'):
                return {"error": "Task title is required"}, 400
            
            # Convert assigned_to to UUID if provided
            assigned_to_uuid = None
            if data.get('assigned_to') and data['assigned_to'].strip():
                try:
                    assigned_to_uuid = uuid.UUID(data['assigned_to'])
                except ValueError:
                    # If it's not a valid UUID, just set to None (unassigned)
                    assigned_to_uuid = None
            
            # Convert project_id to UUID if provided and validate it belongs to workspace
            project_id_uuid = None
            if data.get('project_id'):
                try:
                    project_id_uuid = uuid.UUID(data['project_id'])
                    
                    # Validate that the project belongs to this workspace
                    from models.project_model import Project
                    project = Project.query.get(project_id_uuid)
                    if not project:
                        return {"error": "Project not found"}, 404
                    
                    if project.workspace_id != workspace_uuid:
                        return {"error": "Project does not belong to this workspace"}, 403
                        
                except ValueError:
                    return {"error": "Invalid project ID"}, 400
            
            # Convert parent_task_id to UUID if provided
            parent_task_id_uuid = None
            if data.get('parent_task_id'):
                try:
                    parent_task_id_uuid = uuid.UUID(data['parent_task_id'])
                except ValueError:
                    return {"error": "Invalid parent task ID"}, 400
            
            # Create task
            task = WorkspaceTask.create(
                workspace_id=workspace_uuid,
                title=data['title'],
                description=data.get('description'),
                project_id=project_id_uuid,
                status=data.get('status', 'todo'),
                priority=data.get('priority', 'medium'),
                due_date=datetime.strptime(data['due_date'], '%Y-%m-%d') if data.get('due_date') else None,
                assigned_to=assigned_to_uuid,
                created_by=current_user.user_id,
                estimated_hours=data.get('estimated_hours'),
                tags=data.get('tags'),
                target_leads=data.get('target_leads', 10),
                parent_task_id=parent_task_id_uuid
            )
            
            return task.to_dict(), 201
            
        except Exception as e:
            return {"error": f"Failed to create task: {str(e)}"}, 500
    
    @staticmethod
    def get_workspace_tasks(workspace_id):
        """Get all tasks in workspace"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            # Get workspace and check membership
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get tasks with optional filters from query params
            status = request.args.get('status')
            assigned_to = request.args.get('assigned_to')
            project_id = request.args.get('project_id')
            
            # Convert project_id to UUID if provided
            project_id_uuid = None
            if project_id:
                try:
                    project_id_uuid = uuid.UUID(project_id)
                except ValueError:
                    return {"error": "Invalid project ID in query"}, 400
            
            tasks = WorkspaceTask.get_workspace_tasks(
                workspace_id=workspace_uuid,
                status=status,
                assigned_to=assigned_to,
                project_id=project_id_uuid
            )
            
            # Format tasks for frontend
            formatted_tasks = []
            for task in tasks:
                task_dict = task.to_dict()
                
                # Safely handle assignee data
                assignee_data = task_dict.get('assignee_data') or {}
                username = assignee_data.get('username', 'Unknown')
                task_dict['assignee'] = {
                    'name': username,
                    'initials': username[:2].upper() if username != 'Unknown' else 'U'
                }
                
                # Safely handle due date
                if task_dict.get('due_date'):
                    try:
                        task_dict['due_date'] = datetime.fromisoformat(task_dict['due_date'])
                    except:
                        task_dict['due_date'] = datetime.now()
                else:
                    task_dict['due_date'] = datetime.now()
                
                formatted_tasks.append(task_dict)
            
            return {
                "tasks": formatted_tasks,
                "total": len(tasks),
                "filters": {
                    "status": status,
                    "assigned_to": assigned_to,
                    "project_id": project_id
                }
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get tasks: {str(e)}"}, 500
    
    @staticmethod
    def get_project_tasks(project_id):
        """Get all tasks for a specific project"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate project_id
            try:
                project_uuid = uuid.UUID(project_id)
            except ValueError:
                return {"error": "Invalid project ID"}, 400
            
            # Get project and validate access
            from models.project_model import Project
            project = Project.query.get(project_uuid)
            if not project:
                return {"error": "Project not found"}, 404
            
            # Check if user has access to the workspace
            workspace = project.get_workspace()
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get tasks for this project only
            tasks = WorkspaceTask.query.filter_by(project_id=project_uuid).all()
            
            # Group tasks by status
            task_groups = {
                'todo': [],
                'in_progress': [],
                'review': [],
                'done': []
            }
            
            for task in tasks:
                status = task.status
                if status == 'completed':
                    status = 'done'
                elif status == 'todo':
                    status = 'todo'
                elif status == 'in_progress':
                    status = 'in_progress'
                elif status == 'review':
                    status = 'review'
                
                if status in task_groups:
                    task_dict = task.to_dict()
                    # Format for frontend
                    task_dict['id'] = task_dict['task_id']
                    
                    # Safely handle assignee data
                    assignee_data = task_dict.get('assignee_data') or {}
                    username = assignee_data.get('username', 'Unknown')
                    task_dict['assignee'] = {
                        'name': username,
                        'initials': username[:2].upper() if username != 'Unknown' else 'U'
                    }
                    
                    # Safely handle due date
                    if task_dict.get('due_date'):
                        try:
                            task_dict['due_date'] = datetime.fromisoformat(task_dict['due_date'])
                        except:
                            task_dict['due_date'] = datetime.now()
                    else:
                        task_dict['due_date'] = datetime.now()
                    
                    task_groups[status].append(task_dict)
            
            # Get project info
            from models.project_model import Project
            project = Project.query.get(project_uuid)
            project_data = project.to_dict() if project else None
            
            return {
                "project": project_data,
                "tasks": task_groups,
                "total_tasks": len(tasks)
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get project tasks: {str(e)}"}, 500
    
    @staticmethod
    def get_task(task_id):
        """Get task details with optional submission data"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID"}, 400
            
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                return {"error": "Task not found"}, 404
            
            # Check workspace membership
            workspace = task.get_workspace()
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get query parameters for submission details
            from flask import request
            include_submissions = request.args.get('include_submissions', 'true').lower() == 'true'
            detailed_submissions = request.args.get('detailed_submissions', 'false').lower() == 'true'
            
            return task.to_dict(
                include_submissions=include_submissions,
                detailed_submissions=detailed_submissions
            ), 200
            
        except Exception as e:
            return {"error": f"Failed to get task: {str(e)}"}, 500
    
    @staticmethod
    def update_task(task_id, data):
        """Update task"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID"}, 400
            
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                return {"error": "Task not found"}, 404
            
            # Check if user is member of workspace
            workspace = task.get_workspace()
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get current user's member record to check specific permissions
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member:
                return {"error": "You are not a member of this workspace"}, 403
            
            # Check if user can update this task
            # Members and interns can only update their own tasks
            if current_member.can_update_own_tasks_only():
                if task.assigned_to != current_user.user_id and task.created_by != current_user.user_id:
                    return {"error": "You can only update your own tasks"}, 403
            
            # Track changes
            changes = {}
            allowed_fields = ['title', 'description', 'status', 'priority', 'due_date', 'estimated_hours', 'tags', 'assigned_to']
            
            for field in allowed_fields:
                if field in data:
                    old_value = getattr(task, field)
                    new_value = data[field]
                    
                    # Handle special cases
                    if field == 'assigned_to':
                        if new_value == '' or new_value == 'null' or new_value == 'undefined':
                            new_value = None
                        else:
                            try:
                                new_value = uuid.UUID(new_value)
                            except (ValueError, TypeError):
                                new_value = None
                    elif field == 'due_date':
                        if new_value == '' or new_value == 'null' or new_value == 'undefined':
                            new_value = None
                        elif new_value:
                            try:
                                # Handle different date formats
                                if 'T' in str(new_value):
                                    # ISO format: 2025-08-15T00:00:00
                                    new_value = datetime.strptime(str(new_value).split('T')[0], '%Y-%m-%d')
                                else:
                                    # Standard format: 2025-08-15
                                    new_value = datetime.strptime(str(new_value), '%Y-%m-%d')
                            except ValueError:
                                new_value = None
                    elif field == 'estimated_hours':
                        if new_value == '' or new_value == 'null' or new_value == 'undefined':
                            new_value = None
                        else:
                            try:
                                new_value = float(new_value)
                            except (ValueError, TypeError):
                                new_value = None
                    elif field == 'tags':
                        # Handle tags as either string or list
                        if isinstance(new_value, list):
                            # Convert list to comma-separated string
                            new_value = ','.join(str(tag).strip() for tag in new_value if tag) if new_value else None
                        elif isinstance(new_value, str):
                            # Clean up string format
                            new_value = new_value.strip() if new_value else None
                        else:
                            new_value = None
                    elif field == 'target_leads':
                        if new_value == '' or new_value == 'null' or new_value == 'undefined' or new_value is None:
                            new_value = 10 # Default value
                        else:
                            try:
                                new_value = int(new_value)
                            except (ValueError, TypeError):
                                new_value = 10 
                    
                    if old_value != new_value:
                        changes[field] = {'old': old_value, 'new': new_value}
                        setattr(task, field, new_value)
            
            if changes:
                task.update(updated_by=current_user.user_id)
                db.session.commit()
            
            return task.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update task: {str(e)}"}, 500
    
    @staticmethod
    def delete_task(task_id):
        """Delete task"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID"}, 400
            
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                return {"error": "Task not found"}, 404
            
            # Check workspace membership and permissions
            workspace = task.get_workspace()
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Check if user can delete this task
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member:
                return {"error": "You are not a member of this workspace"}, 403
            
            # Only admins, managers, or task creator can delete tasks
            if current_member.role not in ['admin', 'manager'] and task.created_by != current_user.user_id:
                return {"error": "Only admins, managers, or task creator can delete tasks"}, 403
            
            # Store task info before deletion
            task_title = task.title
            task_workspace_id = task.workspace_id
            task_id = task.task_id
            
            # Check for related records
            from models.task_lead_model import TaskLead
            from models.task_submission_model import TaskSubmission
            
            task_leads = TaskLead.query.filter_by(task_id=task_id).count()
            task_submissions = TaskSubmission.query.filter_by(task_id=task_id).count()
            subtasks = WorkspaceTask.query.filter_by(parent_task_id=task_id).count()
            
      
            # Update subtasks to remove parent reference first
            WorkspaceTask.query.filter_by(parent_task_id=task_id).update({'parent_task_id': None})
            db.session.flush()  # Apply subtask updates
            
            # Delete using raw SQL to bypass ORM relationship handling
            from sqlalchemy import text
            db.session.execute(text("DELETE FROM workspace_tasks WHERE task_id = :task_id"), {"task_id": task_id})
            db.session.commit()
            
            # Log activity after successful deletion
            try:
                WorkspaceActivityLog.create(
                    workspace_id=task_workspace_id,
                    action='task_deleted',
                    user_id=current_user.user_id,
                    entity_type='task',
                    entity_id=task_id,
                    changes={'task_title': task_title}
                )
            except Exception as log_error:
                # Don't fail the deletion if logging fails
                print(f"Failed to log task deletion: {log_error}")
            
            return {"message": "Task deleted successfully"}, 200
            
        except Exception as e:
            db.session.rollback()
            import traceback
            error_details = traceback.format_exc()
            print(f"Delete task error: {error_details}")  # Keep for debugging
            return {"error": f"Failed to delete task: {str(e)}"}, 500
    
    @staticmethod
    def complete_task(task_id, data):
        """Complete a task"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID"}, 400
            
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                return {"error": "Task not found"}, 404
            
            # Check if user is member of workspace
            workspace = task.get_workspace()
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get current user's member record to check specific permissions
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member:
                return {"error": "You are not a member of this workspace"}, 403
            
            # Check if user can complete this task
            # Members and interns can only complete their own tasks
            if current_member.can_update_own_tasks_only():
                if task.assigned_to != current_user.user_id and task.created_by != current_user.user_id:
                    return {"error": "You can only complete your own tasks"}, 403
            
            # Complete the task
            actual_hours = data.get('actual_hours')
            task.complete_task(current_user.user_id, actual_hours)
            
            return task.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to complete task: {str(e)}"}, 500
    
    @staticmethod
    def get_user_tasks():
        """Get tasks assigned to current user"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Get tasks with optional workspace filter
            workspace_id = request.args.get('workspace_id')
            status = request.args.get('status')
            seen_filter_str = request.args.get('seen')
            seen_filter_bool = None
            
            # Convert the string "true" or "false" to a boolean
            if seen_filter_str is not None:
                if seen_filter_str.lower() == 'true':
                    seen_filter_bool = True
                elif seen_filter_str.lower() == 'false':
                    seen_filter_bool = False
            
            tasks = WorkspaceTask.get_user_tasks(
                user_id=current_user.user_id,
                workspace_id=workspace_id,
                seen=seen_filter_bool,
                status=status
            )
            
            return {
                "tasks": [task.to_dict() for task in tasks],
                "total": len(tasks),
                "filters": {
                    "workspace_id": workspace_id,
                    "seen": seen_filter_str,
                    "status": status
                }
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get user tasks: {str(e)}"}, 500
    
    @staticmethod
    def get_overdue_tasks(workspace_id=None):
        """Get overdue tasks"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            if workspace_id:
                # Validate workspace_id and membership
                try:
                    workspace_uuid = uuid.UUID(workspace_id)
                except ValueError:
                    return {"error": "Invalid workspace ID"}, 400
                
                workspace = Workspace.query.get(workspace_uuid)
                if not workspace:
                    return {"error": "Workspace not found"}, 404
                
                if not workspace.is_user_member(current_user.user_id):
                    return {"error": "Access denied"}, 403
            
            tasks = WorkspaceTask.get_overdue_tasks(workspace_id)
            
            return {
                "tasks": [task.to_dict() for task in tasks],
                "total": len(tasks)
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get overdue tasks: {str(e)}"}, 500 

 

    @staticmethod
    def forward_user_lead_draft_to_task(workspace_id, data):
        """Forward user lead draft to create a task"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            # Get workspace and check membership
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Validate required fields
            if not data.get('draft_id'):
                return {"error": "Draft ID is required"}, 400
            
            # Get user lead draft
            from models.user_lead_drafts_model import UserLeadDraft
            draft = UserLeadDraft.query.filter_by(
                draft_id=data['draft_id'],
                user_id=current_user.user_id,
                is_deleted=False
            ).first()
            
            if not draft:
                return {"error": "Draft not found"}, 404
            
            draft_data = draft.draft_data or {}
            
            # Generate task title and description from draft data
            task_title = data.get('title')
            task_description = data.get('description')
            
            if not task_title:
                company = draft_data.get('company', 'Unknown Company')
                task_title = f"Follow up on {company} lead"
            
            if not task_description:
                contact_name = f"{draft_data.get('owner_first_name', '')} {draft_data.get('owner_last_name', '')}".strip()
                email = draft_data.get('owner_email', 'N/A')
                phone = draft_data.get('owner_phone_number', 'N/A')
                position = draft_data.get('owner_title', 'N/A')
                
                task_description = f"Company: {draft_data.get('company', 'N/A')}\nContact: {contact_name or 'N/A'}\nEmail: {email}\nPhone: {phone}\nPosition: {position}\nLocation: {draft_data.get('city', 'N/A')}, {draft_data.get('state', 'N/A')}\nSource: {draft_data.get('source', 'N/A')}"
                
                if draft.notes:
                    task_description += f"\n\nNotes: {draft.notes}"
            
            # Convert assigned_to to UUID if provided
            assigned_to_uuid = None
            if data.get('assigned_to') and data['assigned_to'].strip():
                try:
                    assigned_to_uuid = uuid.UUID(data['assigned_to'])
                except ValueError:
                    assigned_to_uuid = None
            
            # Convert project_id to UUID if provided
            project_id_uuid = None
            if data.get('project_id'):
                try:
                    project_id_uuid = uuid.UUID(data['project_id'])
                    
                    # Validate that the project belongs to this workspace
                    from models.project_model import Project
                    project = Project.query.get(project_id_uuid)
                    if not project:
                        return {"error": "Project not found"}, 404
                    
                    if project.workspace_id != workspace_uuid:
                        return {"error": "Project does not belong to this workspace"}, 403
                        
                except ValueError:
                    return {"error": "Invalid project ID"}, 400
            
            # Get existing task instead of creating new one
            task_id = data.get('task_id')
            if task_id:
                try:
                    task_uuid = uuid.UUID(task_id)
                    task = WorkspaceTask.query.get(task_uuid)
                    if not task:
                        return {"error": "Task not found"}, 404
                    if task.workspace_id != workspace_uuid:
                        return {"error": "Task does not belong to this workspace"}, 403
                except ValueError:
                    return {"error": "Invalid task ID"}, 400
            else:
                # Create new task if no task_id provided
                task = WorkspaceTask.create(
                    workspace_id=workspace_uuid,
                    title=task_title,
                    description=task_description,
                    project_id=project_id_uuid,
                    status=data.get('status', 'todo'),
                    priority=data.get('priority', 'medium'),
                    due_date=datetime.strptime(data['due_date'], '%Y-%m-%d') if data.get('due_date') else None,
                    assigned_to=assigned_to_uuid,
                    created_by=current_user.user_id,
                    estimated_hours=data.get('estimated_hours'),
                    tags=data.get('tags', ['user_lead_draft', 'forwarded']),
                    parent_task_id=None
                )
            

            
            # Try to find or create a lead for this draft
            from models.lead_model import Lead
            lead = None
            
            # First try to find existing lead by company name
            if draft_data.get('company'):
                lead = Lead.query.filter_by(
                    company=draft_data.get('company'),
                    deleted=False
                ).first()
            
            # If no lead found, create a new one from draft data
            if not lead:
                # Generate search_keyword for the new lead
                search_keyword = {
                    'company': draft_data.get('company', 'Unknown Company'),
                    'location': f"{draft_data.get('city', '')}, {draft_data.get('state', '')}".strip(', '),
                    'industry': draft_data.get('industry', ''),
                    'source': 'user_lead_draft'
                }
                
                # Create new lead
                lead = Lead(
                    company_id=draft_data.get('company_id', 'user_draft'),
                    search_keyword=search_keyword,
                    draft_data=draft_data,
                    company=draft_data.get('company', 'Unknown Company'),
                    owner_first_name=draft_data.get('owner_first_name', ''),
                    owner_last_name=draft_data.get('owner_last_name', ''),
                    owner_email=draft_data.get('owner_email', ''),
                    owner_phone_number=draft_data.get('owner_phone_number', ''),
                    owner_title=draft_data.get('owner_title', ''),
                    city=draft_data.get('city', ''),
                    state=draft_data.get('state', ''),
                    company_phone=draft_data.get('company_phone', ''),
                    website=draft_data.get('website', ''),
                    industry=draft_data.get('industry', ''),
                    revenue=float(draft_data.get('revenue')) if draft_data.get('revenue') and str(draft_data.get('revenue')).replace('.', '').isdigit() else None,
                    employees=int(draft_data.get('employee_count')) if draft_data.get('employee_count') and str(draft_data.get('employee_count')).isdigit() else None,
                    source='user_lead_draft',
                    status='new'
                )
                
                db.session.add(lead)
                db.session.commit()
            
            # Add lead to task
            from models.task_lead_model import TaskLead
            task_lead = TaskLead.create(
                task_id=task.task_id,
                lead_id=lead.lead_id,
                added_by=current_user.user_id,
                notes=f"Forwarded from user lead draft: {draft.notes if draft.notes else 'No notes'}",
                status='active'
            )
            
            # Log the forwarding activity
            WorkspaceActivityLog.create(
                workspace_id=workspace_uuid,
                action='user_lead_draft_forwarded_to_task',
                user_id=current_user.user_id,
                entity_type='task',
                entity_id=task.task_id,
                changes={
                    'draft_id': data['draft_id'],
                    'draft_data': draft_data,
                    'draft_notes': draft.notes,
                    'is_favorite': draft.is_favorite,
                    'lead_id': lead.lead_id,
                    'lead_company': lead.company
                }
            )
            
            return {
                "message": "User lead draft forwarded to task successfully",
                "task": task.to_dict(),
                "task_id": str(task.task_id),
                "draft_id": data['draft_id'],
                "draft_company": draft_data.get('company', 'N/A'),
                "lead": lead.to_dict(),
                "task_lead": task_lead.to_dict()
            }, 201
            
        except Exception as e:
            return {"error": f"Failed to forward user lead draft to task: {str(e)}"}, 500 
        
    @staticmethod
    def mark_task_as_seen(task_id):
        """
        Updates the 'seen' flag of a specific task to True.
        This action can only be performed by the user the task is assigned to.
        """
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID format"}, 400

            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                return {"error": "Task not found"}, 404

            # Ensure the person marking the task as seen
            # is the person the task is assigned to.
            if task.assigned_to != current_user.user_id:
                return {"error": "Access denied: You are not assigned to this task."}, 403
            
            if not task.seen:
                task.seen = True
                db.session.commit()
            
            return {
                "message": "Task marked as seen successfully.", 
                "task_id": str(task.task_id), 
                "seen": task.seen
            }, 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error marking task {task_id} as seen: {e}", exc_info=True)
            return {"error": "An internal server error occurred while marking the task as seen."}, 500