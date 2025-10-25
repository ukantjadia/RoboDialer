from flask import jsonify, request
from flask_login import current_user
from models.workspace_model import Workspace
from models.project_model import Project
from models.project_metrics_model import ProjectMetrics
from models.project_team_model import ProjectTeam
from models.workspace_activity_log_model import WorkspaceActivityLog
from models.lead_model import db
import uuid

class TeamProjectController:
    """Controller for team project management operations"""
    
    @staticmethod
    def get_team_projects(team_id):
        """Get all projects in a team"""
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
            
            # Get all projects in this workspace
            projects = workspace.get_projects()
            
            projects_data = []
            for project in projects:
                project_data = project.to_dict()
                
                # Get project metrics
                metrics = ProjectMetrics.get_project_metrics(project.project_id)
                project_data['metrics'] = [metric.to_dict() for metric in metrics]
                
                # Get project teams (if multi-team project)
                project_teams = ProjectTeam.get_project_teams(project.project_id)
                project_data['teams'] = [pt.to_dict() for pt in project_teams]
                
                projects_data.append(project_data)
            
            return {"projects": projects_data}, 200
            
        except Exception as e:
            return {"error": f"Failed to get team projects: {str(e)}"}, 500
    
    @staticmethod
    def get_team_project(team_id, project_id):
        """Get a specific project in a team"""
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
            
            # Validate project_id
            try:
                project_uuid = uuid.UUID(project_id)
            except ValueError:
                return {"error": "Invalid project ID"}, 400
            
            project = Project.query.get(project_uuid)
            if not project or project.workspace_id != team_uuid:
                return {"error": "Project not found"}, 404
            
            project_data = project.to_dict()
            
            # Get project metrics
            metrics = ProjectMetrics.get_project_metrics(project.project_id)
            project_data['metrics'] = [metric.to_dict() for metric in metrics]
            
            return {"project": project_data}, 200
            
        except Exception as e:
            return {"error": f"Failed to get team project: {str(e)}"}, 500
    
    @staticmethod
    def create_team_project(team_id, data):
        """Create a new project in team"""
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
            
            # Check if user can create projects (admin or manager only)
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or current_member.role not in ['admin', 'manager']:
                return {"error": "Only admins and managers can create projects"}, 403
            
            # Validate required fields
            if not data.get('name'):
                return {"error": "Project name is required"}, 400
            
            # Create project
            project = Project.create(
                workspace_id=team_uuid,
                name=data['name'],
                description=data.get('description'),
                priority=data.get('priority', 'medium'),
                created_by=current_user.user_id,
                revenue=data.get('revenue'),
                location=data.get('location'),
                employees=data.get('employees'),
                progress=data.get('progress', 0)
            )
            
            # Add metrics if provided
            if 'metrics' in data:
                for metric_data in data['metrics']:
                    ProjectMetrics.create(
                        project_id=project.project_id,
                        name=metric_data['name'],
                        value=metric_data['value'],
                        created_by=current_user.user_id
                    )
            
            # Add team members if provided
            if 'team' in data:
                for member_id in data['team']:
                    # Check if member is part of the team
                    member = workspace.get_member_by_user_id(member_id)
                    if member:
                        ProjectTeam.create(
                            project_id=project.project_id,
                            team_id=team_uuid,
                            role='contributor'
                        )
            
            # Log activity
            WorkspaceActivityLog.create(
                workspace_id=team_uuid,
                action='project_created',
                user_id=current_user.user_id,
                entity_type='project',
                entity_id=project.project_id,
                changes={'project_name': project.name}
            )
            
            project_data = project.to_dict()
            
            # Get project metrics
            metrics = ProjectMetrics.get_project_metrics(project.project_id)
            project_data['metrics'] = [metric.to_dict() for metric in metrics]
            
            return project_data, 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to create project: {str(e)}"}, 500
    
    @staticmethod
    def update_team_project(team_id, project_id, data):
        """Update project in team"""
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
                return {"error": "Only admins and managers can update projects"}, 403
            
            # Validate project_id
            try:
                project_uuid = uuid.UUID(project_id)
            except ValueError:
                return {"error": "Invalid project ID"}, 400
            
            project = Project.query.get(project_uuid)
            if not project or project.workspace_id != team_uuid:
                return {"error": "Project not found"}, 404
            
            # Track changes
            changes = {}
            allowed_fields = ['name', 'description', 'priority', 'status', 'revenue', 'location', 'employees', 'progress']
            
            for field in allowed_fields:
                if field in data:
                    old_value = getattr(project, field)
                    if old_value != data[field]:
                        changes[field] = {'old': old_value, 'new': data[field]}
                        setattr(project, field, data[field])
            
            if changes:
                project.update()
                
                # Log activity
                WorkspaceActivityLog.create(
                    workspace_id=team_uuid,
                    action='project_updated',
                    user_id=current_user.user_id,
                    entity_type='project',
                    entity_id=project.project_id,
                    changes=changes
                )
            
            # Update metrics if provided
            if 'metrics' in data:
                for metric_data in data['metrics']:
                    ProjectMetrics.update_or_create(
                        project_id=project.project_id,
                        name=metric_data['name'],
                        value=metric_data['value'],
                        created_by=current_user.user_id
                    )
            
            project_data = project.to_dict()
            
            # Get project metrics
            metrics = ProjectMetrics.get_project_metrics(project.project_id)
            project_data['metrics'] = [metric.to_dict() for metric in metrics]
            
            return project_data, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update project: {str(e)}"}, 500
    
    @staticmethod
    def delete_team_project(team_id, project_id):
        """Delete project from team"""
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
                return {"error": "Only admins and managers can delete projects"}, 403
            
            # Validate project_id
            try:
                project_uuid = uuid.UUID(project_id)
            except ValueError:
                return {"error": "Invalid project ID"}, 400
            
            project = Project.query.get(project_uuid)
            if not project or project.workspace_id != team_uuid:
                return {"error": "Project not found"}, 404
            
            # Log activity before deletion
            WorkspaceActivityLog.create(
                workspace_id=team_uuid,
                action='project_deleted',
                user_id=current_user.user_id,
                entity_type='project',
                entity_id=project.project_id,
                changes={'project_name': project.name}
            )
            
            # Delete project (cascade will handle related data)
            db.session.delete(project)
            db.session.commit()
            
            return {"message": "Project deleted successfully"}, 204
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to delete project: {str(e)}"}, 500 