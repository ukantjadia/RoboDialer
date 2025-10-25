from flask import jsonify, request, current_app
from flask_login import current_user
from models.task_lead_model import TaskLead
from models.workspace_task_model import WorkspaceTask
from models.lead_model import Lead
from models.workspace_model import Workspace
from models.workspace_member_model import WorkspaceMember
from models.workspace_activity_log_model import WorkspaceActivityLog
from datetime import datetime, timezone
import uuid
from models.lead_model import db

class TaskLeadController:
    """Controller for task-lead operations"""
    
    @staticmethod
    def add_lead_to_task(task_id, data):
        """Add a lead to a task"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID"}, 400
            
            # Get task and check access
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                return {"error": "Task not found"}, 404
            
            # Check if user is member of the workspace
            workspace = Workspace.query.get(task.workspace_id)
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Check if user has member role (minimum required to add leads)
            member = workspace.get_member_by_user_id(current_user.user_id)
            if not member or member.role not in ['admin', 'manager', 'member']:
                return {"error": "Only members can add leads to tasks"}, 403
            
            # Validate lead_id
            lead_id = data.get('lead_id')
            if not lead_id:
                return {"error": "Lead ID is required"}, 400
            
            # Check if lead exists
            lead = Lead.query.filter_by(lead_id=lead_id, deleted=False).first()
            if not lead:
                return {"error": "Lead not found"}, 404
            
            # Check if lead is already added to this task
            existing_task_lead = TaskLead.query.filter_by(task_id=task_uuid, lead_id=lead_id).first()
            if existing_task_lead:
                return {"error": "Lead is already added to this task"}, 409
            
            # Create task-lead relationship
            task_lead = TaskLead.create(
                task_id=task_uuid,
                lead_id=lead_id,
                added_by=current_user.user_id,
                notes=data.get('notes'),
                status=data.get('status', 'active')
            )
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=task.workspace_id,
                action='lead_added_to_task',
                user_id=current_user.user_id,
                entity_type='task_lead',
                entity_id=task_lead.id,
                changes={
                    'task_id': str(task_uuid),
                    'lead_id': lead_id,
                    'lead_company': lead.company
                }
            )
            
            return task_lead.to_dict(), 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to add lead to task: {str(e)}"}, 500
    
    @staticmethod
    def get_task_leads(task_id):
        """Get all leads for a task"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID"}, 400
            
            # Get task and check access
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                # Return empty result instead of error for non-existent tasks
                return {
                    "task_leads": [],
                    "total_count": 0,
                    "message": "Task not found, returning empty leads list"
                }, 200
            
            # Check if user is member of the workspace
            workspace = Workspace.query.get(task.workspace_id)
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get task leads
            task_leads = TaskLead.get_task_leads(task_uuid)
            
            return {
                "task_leads": [task_lead.to_dict() for task_lead in task_leads],
                "total_count": len(task_leads)
            }, 200
            
        except Exception as e:
            print(f"Error in get_task_leads: {str(e)}")
            return {"error": f"Failed to get task leads: {str(e)}"}, 500

    @staticmethod
    def get_project_task_leads(project_id):
        """Get all task leads from all tasks in a project (for managers and admins)"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate project_id
            try:
                project_uuid = uuid.UUID(project_id)
            except ValueError:
                return {"error": "Invalid project ID"}, 400
            
            # Import Project model
            from models.project_model import Project
            project = Project.query.get(project_uuid)
            if not project:
                return {"error": "Project not found"}, 404
            
            # Check if user is admin or manager of the workspace
            workspace = project.get_workspace()
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member:
                return {"error": "You are not a member of this workspace"}, 403
            
            # Get all task leads from the project
            task_leads = TaskLead.get_project_task_leads(project_uuid)
            
            # Safely convert to dict
            task_leads_data = []
            for task_lead in task_leads:
                try:
                    task_leads_data.append(task_lead.to_dict())
                except Exception as e:
                    print(f"Error converting task_lead to dict: {e}")
                    # Skip this task_lead or add minimal data
                    continue
            
            return {
                "project": project.to_dict(),
                "task_leads": task_leads_data,
                "count": len(task_leads_data)
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get project task leads: {str(e)}"}, 500

    @staticmethod
    def get_workspace_task_leads(workspace_id):
        """Get all task leads from all tasks in a workspace (for admins and managers)"""
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
            
            # Check if user is admin or manager of the workspace
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member:
                return {"error": "You are not a member of this workspace"}, 403
            
            # Get all task leads from the workspace
            task_leads = TaskLead.get_workspace_task_leads(workspace_uuid)
            
            return {
                "workspace": workspace.to_dict(),
                "task_leads": [task_lead.to_dict() for task_lead in task_leads],
                "count": len(task_leads)
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get workspace task leads: {str(e)}"}, 500
    
    @staticmethod
    def remove_lead_from_task(task_id, lead_id):
        """Remove a lead from a task"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID"}, 400
            
            # Get task and check access
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                return {"error": "Task not found"}, 404
            
            # Check if user is member of the workspace
            workspace = Workspace.query.get(task.workspace_id)
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Check if user has permission to remove leads
            member = workspace.get_member_by_user_id(current_user.user_id)
            if not member or member.role not in ['admin', 'manager', 'member']:
                return {"error": "Only members can remove leads from tasks"}, 403
            
            # Remove lead from task
            success = TaskLead.remove_lead_from_task(task_uuid, lead_id)
            if not success:
                return {"error": "Lead not found in task"}, 404
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=task.workspace_id,
                action='lead_removed_from_task',
                user_id=current_user.user_id,
                entity_type='task_lead',
                entity_id=None,
                changes={
                    'task_id': str(task_uuid),
                    'lead_id': lead_id
                }
            )
            
            return {"message": "Lead removed from task successfully"}, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to remove lead from task: {str(e)}"}, 500
    
    @staticmethod
    def update_task_lead_and_lead(task_id, lead_id, data):
        """
        Updates the Lead object with new data and the TaskLead object with
        status/notes from a single payload.
        """
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401

            task = WorkspaceTask.query.get(uuid.UUID(task_id))
            if not task: return {"error": "Task not found"}, 404
            
            workspace = task.get_workspace()
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403

            task_lead = TaskLead.query.filter_by(task_id=task.task_id, lead_id=lead_id).first()
            if not task_lead:
                return {"error": "Lead is not associated with this task"}, 404
            
            lead = task_lead.lead
            if not lead:
                return {"error": "Lead record not found"}, 404

            
            updatable_lead_fields = [
                'company', 'owner_first_name', 'owner_last_name', 'owner_email', 
                'owner_title', 'owner_phone_number', 'phone', 'website', 'industry', 
                'city', 'state', 'country', 'year_founded', 'employees', 'source'
            ]
            
            for field in updatable_lead_fields:
                if field in data:
                    setattr(lead, field, data[field])
            
            if 'revenue' in data:
                lead.revenue = Lead.parse_revenue(data['revenue'])
            
            lead.is_edited = True
            lead.edited_at = datetime.utcnow()
            lead.edited_by = current_user.user_id

            # Update the TaskLead Object 
            if 'status' in data:
                task_lead.status = data['status']
            if 'notes' in data:
                task_lead.notes = data['notes']
            
            db.session.commit()

            return {"message": "Lead and task link updated successfully"}, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update task lead: {str(e)}"}, 500
        

    @staticmethod
    def update_task_lead_status(task_id, lead_id, data):
        """Update the status of a task-lead relationship"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID"}, 400
            
            # Get task and check access
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                return {"error": "Task not found"}, 404
            
            # Check if user is member of the workspace
            workspace = Workspace.query.get(task.workspace_id)
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get task-lead relationship
            task_lead = TaskLead.query.filter_by(task_id=task_uuid, lead_id=lead_id).first()
            if not task_lead:
                return {"error": "Lead not found in task"}, 404
            
            # Update status
            new_status = data.get('status')
            if new_status:
                task_lead.update_status(new_status)
            
            # Update notes if provided
            notes = data.get('notes')
            if notes is not None:
                task_lead.update_notes(notes)
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=task.workspace_id,
                action='task_lead_status_updated',
                user_id=current_user.user_id,
                entity_type='task_lead',
                entity_id=task_lead.id,
                changes={
                    'status': {'old': task_lead.status, 'new': new_status} if new_status else {},
                    'notes': {'old': task_lead.notes, 'new': notes} if notes is not None else {}
                }
            )
            
            return task_lead.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update task lead status: {str(e)}"}, 500

    @staticmethod
    def score_task_lead(task_id, lead_id, data):
        """Score a task-lead relationship"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID"}, 400
            
            # Get task and check access
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                return {"error": "Task not found"}, 404
            
            # Check if user is member of the workspace
            workspace = Workspace.query.get(task.workspace_id)
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get task-lead relationship
            task_lead = TaskLead.query.filter_by(task_id=task_uuid, lead_id=lead_id).first()
            if not task_lead:
                return {"error": "Lead not found in task"}, 404
            
            # Validate score
            score = data.get('score')
            if not score or score not in ['good', 'medium', 'bad']:
                return {"error": "Score must be 'good', 'medium', or 'bad'"}, 400
            
            # Update score
            score_notes = data.get('score_notes')
            task_lead.update_score(score, score_notes, current_user.user_id)
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=task.workspace_id,
                action='task_lead_scored',
                user_id=current_user.user_id,
                entity_type='task_lead',
                entity_id=task_lead.id,
                changes={
                    'score': {'old': task_lead.score, 'new': score},
                    'score_notes': {'old': task_lead.score_notes, 'new': score_notes}
                }
            )
            
            return task_lead.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to score task lead: {str(e)}"}, 500

    @staticmethod
    def get_task_lead_score(task_id, lead_id):
        """Get the score for a specific task-lead relationship"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID"}, 400
            
            # Get task and check access
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                return {"error": "Task not found"}, 404
            
            # Check if user is member of the workspace
            workspace = Workspace.query.get(task.workspace_id)
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get task-lead relationship
            task_lead = TaskLead.query.filter_by(task_id=task_uuid, lead_id=lead_id).first()
            if not task_lead:
                return {"error": "Lead not found in task"}, 404
            
            return {
                "score": task_lead.score,
                "score_notes": task_lead.score_notes,
                "scored_by": task_lead.scored_by,
                "scored_at": task_lead.scored_at.isoformat() if task_lead.scored_at else None
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get task lead score: {str(e)}"}, 500

    @staticmethod
    def update_task_lead_score(task_id, lead_id, data):
        """Update the score for a task-lead relationship"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return {"error": "Invalid task ID"}, 400
            
            # Get task and check access
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                return {"error": "Task not found"}, 404
            
            # Check if user is member of the workspace
            workspace = Workspace.query.get(task.workspace_id)
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get task-lead relationship
            task_lead = TaskLead.query.filter_by(task_id=task_uuid, lead_id=lead_id).first()
            if not task_lead:
                return {"error": "Lead not found in task"}, 404
            
            # Validate score
            score = data.get('score')
            if not score or score not in ['good', 'medium', 'bad']:
                return {"error": "Score must be 'good', 'medium', or 'bad'"}, 400
            
            # Store old values for logging
            old_score = task_lead.score
            old_notes = task_lead.score_notes
            
            # Update score
            score_notes = data.get('score_notes')
            task_lead.update_score(score, score_notes, current_user.user_id)
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=task.workspace_id,
                action='task_lead_score_updated',
                user_id=current_user.user_id,
                entity_type='task_lead',
                entity_id=task_lead.id,
                changes={
                    'score': {'old': old_score, 'new': score},
                    'score_notes': {'old': old_notes, 'new': score_notes}
                }
            )
            
            return task_lead.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update task lead score: {str(e)}"}, 500
    
    @staticmethod
    def create_lead_for_task(task_id, data):
        """Create a new lead and add it to a task"""
        try:
            print(f"Creating lead for task: {task_id}")
            print(f"Data received: {data}")

            if not data.get('company'):
                return {"error": "Company name is required"}, 400
            
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate task_id
            try:
                task_uuid = uuid.UUID(task_id)
                print(f"Task UUID: {task_uuid}")
            except ValueError:
                print(f"Invalid task ID: {task_id}")
                return {"error": "Invalid task ID"}, 400
            
            # Get task and check access
            task = WorkspaceTask.query.get(task_uuid)
            if not task:
                print(f"Task not found: {task_uuid}")
                return {"error": "Task not found"}, 404
            
            print(f"Task found: {task.title}")
            
            # Check if user is member of the workspace
            workspace = Workspace.query.get(task.workspace_id)
            if not workspace.is_user_member(current_user.user_id):
                print(f"User {current_user.user_id} is not a member of workspace {task.workspace_id}")
                return {"error": "Access denied"}, 403
            
            # Check if user has member role
            member = workspace.get_member_by_user_id(current_user.user_id)
            if not member or member.role not in ['admin', 'manager', 'member']:
                print(f"User role {member.role if member else 'None'} not sufficient")
                return {"error": "Only members can create leads for tasks"}, 403
            
            # Validate required fields
            required_fields = ['company', 'owner_first_name', 'owner_email']
            for field in required_fields:
                if not data.get(field):
                    print(f"Missing required field: {field}")
                    return {"error": f"{field.replace('_', ' ').title()} is required"}, 400
            
            # Optional fields that should be empty string if not provided
            optional_fields = ['owner_last_name', 'owner_title', 'owner_phone_number', 'phone', 'website', 'industry', 'city', 'state']
            
            # Create lead data
            lead_id = Lead.generate_lead_id(
                company=data.get('company'), 
                website=data.get('website'), 
                street=data.get('street'),
                city=data.get('city'), 
                state=data.get('state'), 
                company_phone=data.get('phone') # Use the general phone as a fallback
            )

            lead = Lead.query.get(lead_id)

            lead_data = {
                'search_keyword': {},
                'company': data['company'],
                'owner_first_name': data['owner_first_name'],
                'owner_last_name': data.get('owner_last_name', ''), # Make owner_last_name optional
                'owner_email': data['owner_email'],
                'owner_title': data.get('owner_title'),
                'owner_phone_number': data.get('owner_phone_number'),
                'phone': data.get('phone'),
                'website': data.get('website'),
                'industry': data.get('industry'),
                'city': data.get('city'),
                'state': data.get('state'),
                'year_founded': data.get('year_founded'),
                'revenue': Lead.parse_revenue(data.get('revenue')),        
                'employees': data.get('employees'),    
                'source': 'manual',
                'status': 'new'
            }
            
            # Create lead
            if lead:
                # If lead exists, update it with new information
                for key, value in lead_data.items():
                    if value is not None:
                        setattr(lead, key, value)
                lead.updated_at = datetime.now(timezone.utc)
                current_app.logger.info(f"Lead {lead_id} updated.")
            else:
                # If lead does not exist, create a new one
                lead_data['lead_id'] = lead_id 
                lead = Lead(**lead_data)
                db.session.add(lead)
                current_app.logger.info(f"New lead {lead_id} created.")
            

            existing_task_lead = TaskLead.query.filter_by(task_id=task.task_id, lead_id=lead.lead_id).first()
            if existing_task_lead:
                return {"error": "This lead is already in the task"}, 409
            
            # Add lead to task
            print(f"Creating task-lead relationship")
            task_lead = TaskLead(
                task_id=task_uuid,
                lead_id=lead.lead_id,
                added_by=current_user.user_id,
                notes=data.get('notes'),
                status='active'
            )
            db.session.add(task_lead)
            print(f"Task-lead relationship created with ID: {task_lead.id}")
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=task.workspace_id,
                action='lead_created_for_task',
                user_id=current_user.user_id,
                entity_type='task_lead',
                entity_id=task_lead.id,
                changes={
                    'task_id': str(task_uuid),
                    'lead_id': lead.lead_id,
                    'lead_company': lead.company
                }
            )

            db.session.commit()
            
            return task_lead.to_dict(), 201
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating lead for task: {str(e)}")
            return {"error": f"Failed to create lead for task: {str(e)}"}, 500 