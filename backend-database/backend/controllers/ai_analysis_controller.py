from models.ai_analysis_model import AIAnalysis, db
from models.lead_model import Lead
from models.project_model import Project
from models.workspace_model import Workspace
from models.user_model import User
from flask import current_app
from datetime import datetime
import uuid
import logging

class AIAnalysisController:
    """Controller for AI Analysis operations"""

    @staticmethod
    def create_or_update_analysis(lead_id, project_id, user_id, website_text=None, ai_analysis=None, task_id=None):
        """
        Create new AI analysis or update existing one for a project/lead (optionally per task)
        """
        current_app.logger.info(f'[AI Analysis Controller] Starting create_or_update_analysis - Lead: {lead_id}, Project: {project_id}, Task: {task_id}, User: {user_id}')

        try:
            # Validate lead exists
            current_app.logger.info(f'[AI Analysis Controller] Validating lead: {lead_id}')
            lead = Lead.query.filter_by(lead_id=lead_id, deleted=False).first()
            if not lead:
                current_app.logger.warning(f'[AI Analysis Controller] Lead not found: {lead_id}')
                return False, "Lead not found", None, 404
            current_app.logger.info(f'[AI Analysis Controller] Lead validated: {lead.company}')

            # Validate project exists
            current_app.logger.info(f'[AI Analysis Controller] Validating project: {project_id}')
            project = Project.query.filter_by(project_id=project_id).first()
            if not project:
                current_app.logger.warning(f'[AI Analysis Controller] Project not found: {project_id}')
                return False, "Project not found", None, 404
            current_app.logger.info(f'[AI Analysis Controller] Project validated: {project.name}')

            # Validate workspace exists
            current_app.logger.info(f'[AI Analysis Controller] Validating workspace: {project.workspace_id}')
            workspace = Workspace.query.filter_by(workspace_id=project.workspace_id).first()
            if not workspace:
                current_app.logger.warning(f'[AI Analysis Controller] Workspace not found: {project.workspace_id}')
                return False, "Workspace not found", None, 404
            current_app.logger.info(f'[AI Analysis Controller] Workspace validated: {workspace.name}')

            # Validate task_id if provided
            if task_id:
                current_app.logger.info(f'[AI Analysis Controller] Validating task: {task_id}')
                try:
                    task_uuid = uuid.UUID(task_id)
                    from models.workspace_task_model import WorkspaceTask
                    task = WorkspaceTask.query.filter_by(task_id=task_uuid, project_id=project_id).first()
                    if not task:
                        current_app.logger.warning(f'[AI Analysis Controller] Task not found: {task_id}')
                        return False, "Task not found", None, 404
                    current_app.logger.info(f'[AI Analysis Controller] Task validated: {task.title}')
                except ValueError:
                    current_app.logger.warning(f'[AI Analysis Controller] Invalid task ID format: {task_id}')
                    return False, "Invalid task ID format", None, 400

            # Prepare company data from lead (snapshot at creation)
            current_app.logger.info(f'[AI Analysis Controller] Preparing company data from lead')
            company_data = {
                'company_name': lead.company,
                'website': lead.website,
                'industry': lead.industry,
                'state': lead.state,
                'employees': str(lead.employees) if lead.employees else None,
                'revenue': lead.revenue
            }

            # Create or update AI analysis record
            current_app.logger.info(f'[AI Analysis Controller] Creating/updating analysis record')
            analysis = AIAnalysis.create_or_update_analysis(
                lead_id=lead_id,
                project_id=project_id,
                workspace_id=project.workspace_id,
                user_id=user_id,
                company_data=company_data,
                website_text=website_text,
                ai_analysis=ai_analysis,
                task_id=task_id
            )

            current_app.logger.info(f'[AI Analysis Controller] Analysis record created/updated successfully: {analysis.analysis_id}')
            return True, "AI analysis saved successfully", analysis.to_dict(), 200

        except Exception as e:
            current_app.logger.error(f'[AI Analysis Controller] Error creating/updating AI analysis: {str(e)}')
            return False, "Internal server error", None, 500

    @staticmethod
    def get_project_analysis(project_id):
        """
        Get ALL AI analyses for a specific project as a list sorted by updated_at desc
        """
        current_app.logger.info(f'[AI Analysis Controller] Starting get_project_analysis - Project: {project_id}')

        try:
            # Validate project_id format
            current_app.logger.info(f'[AI Analysis Controller] Validating project ID format: {project_id}')
            try:
                project_uuid = uuid.UUID(project_id)
            except ValueError:
                current_app.logger.warning(f'[AI Analysis Controller] Invalid project ID format: {project_id}')
                return False, "Invalid project ID format", None, 400

            # Validate project exists
            current_app.logger.info(f'[AI Analysis Controller] Validating project exists: {project_uuid}')
            project = Project.query.filter_by(project_id=project_uuid).first()
            if not project:
                current_app.logger.warning(f'[AI Analysis Controller] Project not found: {project_uuid}')
                return False, "Project not found", None, 404

            # Get all analyses for project
            current_app.logger.info(f'[AI Analysis Controller] Retrieving analyses for project: {project_uuid}')
            analyses = AIAnalysis.get_all_by_project(project_uuid)
            data = [a.to_dict() for a in analyses]
            return True, "Analyses found", data, 200

        except Exception as e:
            current_app.logger.error(f'[AI Analysis Controller] Error getting project analyses: {str(e)}')
            return False, "Internal server error", None, 500

    @staticmethod
    def get_task_analysis(project_id, task_id):
        """
        Get ALL AI analyses for a specific project+task as a list sorted by updated_at desc
        """
        current_app.logger.info(f'[AI Analysis Controller] Starting get_task_analysis - Project: {project_id}, Task: {task_id}')

        try:
            # Validate UUIDs
            try:
                project_uuid = uuid.UUID(project_id)
            except ValueError:
                return False, "Invalid project ID format", None, 400
            try:
                task_uuid = uuid.UUID(task_id)
            except ValueError:
                return False, "Invalid task ID format", None, 400

            # Validate project exists
            project = Project.query.filter_by(project_id=project_uuid).first()
            if not project:
                return False, "Project not found", None, 404

            # Validate task belongs to project
            from models.workspace_task_model import WorkspaceTask
            task = WorkspaceTask.query.filter_by(task_id=task_uuid, project_id=project_uuid).first()
            if not task:
                return False, "Task not found", None, 404

            # Fetch analyses
            analyses = AIAnalysis.get_all_by_project_and_task(project_uuid, task_uuid)
            data = [a.to_dict() for a in analyses]
            return True, "Analyses found", data, 200

        except Exception as e:
            current_app.logger.error(f'[AI Analysis Controller] Error getting task analyses: {str(e)}')
            return False, "Internal server error", None, 500

    @staticmethod
    def validate_analysis_data(data):
        """
        Validate the incoming analysis data
        """
        current_app.logger.info(f'[AI Analysis Controller] Validating analysis data')

        required_fields = ['lead_id', 'project_id']

        for field in required_fields:
            if field not in data:
                current_app.logger.warning(f'[AI Analysis Controller] Missing required field: {field}')
                return False, f"Missing required field: {field}"

        # Validate project_id format
        current_app.logger.info(f'[AI Analysis Controller] Validating project ID format: {data["project_id"]}')
        try:
            uuid.UUID(data['project_id'])
            current_app.logger.info(f'[AI Analysis Controller] Project ID format validated')
        except ValueError:
            current_app.logger.warning(f'[AI Analysis Controller] Invalid project ID format: {data["project_id"]}')
            return False, "Invalid project ID format"

        return True, None

    @staticmethod
    def validate_user_access(user_id, project_id):
        """Validate if user has access to the project"""
        current_app.logger.info(f'[AI Analysis Controller] Validating user access - User: {user_id}, Project: {project_id}')

        try:
            project = Project.query.filter_by(project_id=project_id).first()
            if not project:
                return False, "Project not found"

            workspace = Workspace.query.filter_by(workspace_id=project.workspace_id).first()
            if not workspace:
                return False, "Workspace not found"

            return True, None
        except Exception:
            return False, "Error validating access"

    @staticmethod
    def format_analysis_response(analysis_data, exists):
        """
        Format the analysis response

        Args:
            analysis_data (dict): Analysis data
            exists (bool): Whether analysis exists

        Returns:
            dict: Formatted response
        """
        current_app.logger.info(f'[AI Analysis Controller] Formatting analysis response - Exists: {exists}')
        return {
            'success': True,
            'analysis': analysis_data,
            'exists': exists
        }

    @staticmethod
    def format_error_response(message, status_code):
        """
        Format error response

        Args:
            message (str): Error message
            status_code (int): HTTP status code

        Returns:
            dict: Formatted error response
        """
        current_app.logger.warning(f'[AI Analysis Controller] Formatting error response - Message: {message}, Status: {status_code}')
        return {
            'error': message
        }, status_code