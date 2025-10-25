from flask import jsonify
from flask_login import current_user
from models.task_submission_model import TaskSubmission
from models.workspace_task_model import WorkspaceTask
from models.workspace_model import Workspace
from models.workspace_member_model import WorkspaceMember

from models.lead_model import db
import uuid

class TaskSubmissionController:
    
    @staticmethod
    def submit_task(task_id, data):
        """Submit a task for review/approval"""
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
            
            # Check if user can submit this task (assigned to them or they created it)
            if task.assigned_to != current_user.user_id and task.created_by != current_user.user_id:
                return {"error": "You can only submit tasks assigned to you or created by you"}, 403
            
            # Get submission data
            submission_type = data.get('submission_type', 'completion')
            message = data.get('message')
            auto_complete = data.get('auto_complete', False)  # For direct completion without review
            
            # Validate submission type
            valid_types = ['completion', 'review', 'approval', 'update']
            if submission_type not in valid_types:
                return {"error": f"Invalid submission type. Must be one of: {', '.join(valid_types)}"}, 400
            
            # Create submission
            submission = TaskSubmission.create(
                task_id=task.task_id,
                workspace_id=task.workspace_id,
                submitted_by=current_user.user_id,
                submission_type=submission_type,
                message=message
            )
            
            # For completion submissions, update task status to 'review' to indicate it's under review
            if submission_type == 'completion':
                task.update(status='review', updated_by=current_user.user_id)
            
            # If auto_complete is True and it's a completion submission, complete the task immediately
            # This is useful for simple tasks that don't require manager approval
            if auto_complete and submission_type == 'completion':
                actual_hours = data.get('actual_hours')
                task.complete_task(current_user.user_id, actual_hours)
                submission.approve(current_user.user_id, "Auto-completed on submission")
            
            return {
                "submission": submission.to_dict(),
                "task": task.to_dict(include_submissions=True, detailed_submissions=False),
                "message": "Task submitted successfully"
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to submit task: {str(e)}"}, 500
    
    @staticmethod
    def get_pending_submissions(workspace_id):
        """Get pending submissions for managers and admins"""
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
            
            # Check if user is member of workspace
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Check if user is member of workspace (allow all members to view)
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member:
                return {"error": "You are not a member of this workspace"}, 403
            
            # Get submissions that need review (pending and under_review)
            submissions = TaskSubmission.get_submissions_for_review(workspace_uuid)
            
            return {
                "submissions": [submission.to_dict() for submission in submissions],
                "count": len(submissions)
            }, 200
            
        except Exception as e:
            import traceback
            return {"error": f"Failed to get pending submissions: {str(e)}"}, 500
    
    @staticmethod
    def review_submission(submission_id, data):
        """Review a submission (approve/reject)"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate submission_id
            try:
                submission_uuid = uuid.UUID(submission_id)
            except ValueError:
                return {"error": "Invalid submission ID"}, 400
            
            submission = TaskSubmission.query.get(submission_uuid)
            if not submission:
                return {"error": "Submission not found"}, 404
            
            # Check if user is admin or manager of the workspace
            workspace = submission.workspace
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or current_member.role not in ['admin', 'manager']:
                return {"error": "Only admins and managers can review submissions"}, 403
            
            # Get review data
            action = data.get('action')  # 'approve', 'reject', 'under_review'
            notes = data.get('notes')
            actual_hours = data.get('actual_hours')  # Optional actual hours for completion
            
            # Validate action
            valid_actions = ['approve', 'reject', 'under_review']
            if action not in valid_actions:
                return {"error": f"Invalid action. Must be one of: {', '.join(valid_actions)}"}, 400
            
            # Get the task for status updates
            task = submission.task
            
            if action == 'approve':
                submission.approve(current_user.user_id, notes)
                
                # Handle different submission types when approved
                if submission.submission_type == 'completion':
                    # Mark the task as completed
                    if task.status != 'completed':
                        task.complete_task(submission.submitted_by, actual_hours)
                        # Refresh task object to get updated status
                        db.session.refresh(task)
                elif submission.submission_type == 'review':
                    # Update task status to in_progress for review submissions
                    task.update(status='in_progress', updated_by=current_user.user_id)
                    db.session.refresh(task)
                elif submission.submission_type == 'update':
                    # Keep current status but update timestamp
                    task.update(updated_by=current_user.user_id)
                    db.session.refresh(task)
                else:
                    # Default: mark task as completed for any approved submission
                    if task.status != 'completed':
                        task.complete_task(submission.submitted_by, actual_hours)
                        db.session.refresh(task)
                
            elif action == 'reject':
                submission.reject(current_user.user_id, notes)
                
                # When rejected, revert task status based on submission type
                if submission.submission_type == 'completion':
                    # Revert to in_progress for completion rejections
                    task.update(status='in_progress', updated_by=current_user.user_id)
                    db.session.refresh(task)
                elif submission.submission_type == 'review':
                    # Revert to todo for review rejections
                    task.update(status='todo', updated_by=current_user.user_id)
                    db.session.refresh(task)
                    
            elif action == 'under_review':
                submission.mark_under_review(current_user.user_id)
                # Task stays in 'review' status when marked under review
            
            return {
                "submission": submission.to_dict(),
                "task": task.to_dict(include_submissions=True, detailed_submissions=False),
                "message": f"Submission {action} successfully"
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to review submission: {str(e)}"}, 500
    

    
 