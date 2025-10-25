from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from controllers.workspace_controller import WorkspaceController
from controllers.workspace_member_controller import WorkspaceMemberController
from controllers.project_controller import ProjectController
from controllers.workspace_task_controller import WorkspaceTaskController

from controllers.workspace_settings_controller import WorkspaceSettingsController
from controllers.team_controller import TeamController
from controllers.team_project_controller import TeamProjectController
from datetime import datetime
import json

# Create blueprint for web routes
workspace_web_bp = Blueprint('workspace_web', __name__, url_prefix='/workspace')

# Specific routes that need to be defined before general ones
@workspace_web_bp.route('/<workspace_id>/submissions')
@login_required
def workspace_submissions(workspace_id):
    """Render workspace submissions page"""
    try:
        # Get workspace details
        workspace_response, workspace_status = WorkspaceController.get_workspace(workspace_id)
        
        if workspace_status != 200:
            flash('Workspace not found', 'error')
            return redirect(url_for('workspace_web.workspace_list'))
        
        # Check if workspace_response is None or empty
        if not workspace_response:
            flash('Error: Unable to load workspace data', 'error')
            return redirect(url_for('workspace_web.workspace_list'))
        
        # workspace_response is the workspace data directly, not wrapped in 'workspace' key
        workspace = workspace_response
        
        # Check if user is admin or manager
        user_role = workspace.get('user_role')
        if user_role not in ['admin', 'manager']:
            flash('Only admins and managers can view submissions', 'error')
            return redirect(url_for('workspace_web.workspace_detail', workspace_id=workspace_id))
        
        return render_template('workspace/submissions.html', 
                             workspace=workspace)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Error loading submissions: {str(e)}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))

@workspace_web_bp.route('/')
@login_required
def workspace_list():
    """Render workspace list page"""
    try:
        # Get user workspaces
        workspaces_response, status_code = WorkspaceController.get_user_workspaces()
        
        if status_code == 200:
            workspaces = workspaces_response.get('workspaces', [])
        else:
            workspaces = []
            
        # Get join requests for user's workspaces where user is admin/manager
        join_requests = []
        total_pending_requests = 0
        
        for workspace in workspaces:
            if workspace.get('user_role') in ['admin', 'manager']:
                try:
                    from controllers.workspace_join_request_controller import WorkspaceJoinRequestController
                    requests_response, requests_status = WorkspaceJoinRequestController.get_workspace_join_requests(
                        workspace.get('workspace_id')
                    )
                    
                    if requests_status == 200:
                        workspace_requests = requests_response.get('requests', [])
                        total_pending_requests += len(workspace_requests)
                        
                        if workspace_requests:
                            join_requests.append({
                                'workspace': workspace,
                                'requests': workspace_requests,
                                'count': len(workspace_requests)
                            })
                except Exception as req_e:
                    print(f"Error getting join requests for workspace {workspace.get('workspace_id')}: {str(req_e)}")
        
        print(f"Found {total_pending_requests} total pending join requests across {len(join_requests)} workspaces")
            
        # If no workspaces found, create sample data for testing
        if not workspaces:
            print("No workspaces found")
            
    except Exception as e:
        print(f"Exception in workspace_list route: {str(e)}")
        import traceback
        traceback.print_exc()
        workspaces = []
        join_requests = []
        total_pending_requests = 0
        flash(f'Error loading workspaces: {str(e)}', 'error')
    
    return render_template('workspace/workspace_list.html', 
                         workspaces=workspaces,
                         join_requests=join_requests,
                         total_pending_requests=total_pending_requests)

@workspace_web_bp.route('/team-dashboard')
@login_required
def team_dashboard():
    """Redirect to team overview or show team list"""
    try:
        # Get user's teams
        teams_response, status_code = TeamController.get_teams()
        if status_code == 200:
            teams = teams_response.get('teams', [])
            if teams:
                # Redirect to first team's overview
                first_team = teams[0]
                return redirect(url_for('workspace_web.team_overview', team_id=first_team['id']))
            else:
                # No teams found, redirect to workspace list
                return redirect(url_for('workspace_web.workspace_list'))
        else:
            # Error loading teams, redirect to workspace list
            return redirect(url_for('workspace_web.workspace_list'))
    except Exception as e:
        # Exception occurred, redirect to workspace list
        return redirect(url_for('workspace_web.workspace_list'))

@workspace_web_bp.route('/team/<team_id>')
@login_required
def team_overview(team_id):
    """Render team overview page"""
    try:
        # For now, create a simple workspace object for testing
        workspace = {
            'workspace_id': team_id,
            'name': f'Workspace {team_id}',
            'description': 'Workspace description',
            'member_count': 5,
            'project_count': 3,
            'active_project_count': 2
        }
        
        # Initialize empty statistics and activity
        statistics = {}
        recent_activity = []
        
        # Initialize empty members list
        active_members = []
            
    except Exception as e:
        flash(f'Error loading workspace: {str(e)}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))
    
    return render_template('workspace/team_overview.html', team_id=team_id, workspace=workspace, statistics=statistics, recent_activity=recent_activity, active_members=active_members)

@workspace_web_bp.route('/team/<team_id>/members')
@login_required
def team_members(team_id):
    """Render team members management page"""
    try:
        # Handle 'current' team_id - redirect to team dashboard first
        if team_id == 'current':
            return redirect(url_for('workspace_web.team_dashboard'))
        
        # For now, create a simple workspace object for testing
        workspace = {
            'workspace_id': team_id,
            'name': f'Workspace {team_id}',
            'description': 'Workspace description'
        }
        
        # Initialize empty members list
        members = []
            
    except Exception as e:
        flash(f'Error loading members: {str(e)}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))
    
    # Get user role for permission checks
    workspace_response, workspace_status = WorkspaceController.get_workspace(team_id)
    if workspace_status == 200:
        user_role = workspace_response.get('user_role', 'member')
    else:
        user_role = 'member'
    
    return render_template('workspace/team_members.html', 
                         team_id=team_id, 
                         workspace=workspace, 
                         members=members,
                         user_role=user_role)

@workspace_web_bp.route('/team/<team_id>/projects')
@login_required
def team_projects(team_id):
    """Render team projects management page"""
    try:
        # Handle 'current' team_id - redirect to team dashboard first
        if team_id == 'current':
            return redirect(url_for('workspace_web.team_dashboard'))
        
        # Get workspace details and user role
        workspace_response, workspace_status = WorkspaceController.get_workspace(team_id)
        if workspace_status == 200:
            workspace = workspace_response
            user_role = workspace.get('user_role', 'member')
        else:
            # For now, just pass the team_id and create a simple workspace object
            workspace = {
                'workspace_id': team_id,
                'name': f'Workspace {team_id}',
                'description': 'Workspace description'
            }
            user_role = 'member'  # Default to member if can't get role
        
        # Create team object for template
        team = {
            'id': team_id,
            'name': workspace.get('name', f'Workspace {team_id}'),
            'description': workspace.get('description', 'Workspace description')
        }
        
        # Initialize empty projects list
        projects = []
            
    except Exception as e:
        flash(f'Error loading projects: {str(e)}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))
    
    return render_template('workspace/team_projects.html', 
                         team_id=team_id, 
                         team=team, 
                         workspace=workspace, 
                         projects=projects,
                         user_role=user_role)


@workspace_web_bp.route('/team/<team_id>/activity')
@login_required
def team_activity(team_id):
    """Render team activity logs page"""
    try:
        # Handle 'current' team_id - redirect to team dashboard first
        if team_id == 'current':
            return redirect(url_for('workspace_web.team_dashboard'))
        
        # For now, create a simple workspace object for testing
        workspace = {
            'workspace_id': team_id,
            'name': f'Workspace {team_id}',
            'description': 'Workspace description'
        }
        
        # Initialize empty activities list
        activities = []
            
    except Exception as e:
        flash(f'Error loading activity: {str(e)}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))
    
    return render_template('workspace/team_activity.html', team_id=team_id, workspace=workspace, activities=activities)

@workspace_web_bp.route('/team/<team_id>/settings')
@login_required
def team_settings(team_id):
    """Render team settings page"""
    try:
        # For now, create a simple workspace object for testing
        workspace = {
            'workspace_id': team_id,
            'name': f'Workspace {team_id}',
            'description': 'Workspace description',
            'industry': 'technology'
        }
            
    except Exception as e:
        flash(f'Error loading settings: {str(e)}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))
    
    # Get user role for permission checks
    workspace_response, workspace_status = WorkspaceController.get_workspace(team_id)
    if workspace_status == 200:
        user_role = workspace_response.get('user_role', 'member')
    else:
        user_role = 'member'
        
    return render_template('workspace/team_settings.html', 
                         team_id=team_id, 
                         workspace=workspace,
                         user_role=user_role)

@workspace_web_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_workspace():
    """Render create workspace page and handle form submission"""
    # Check subscription tier
    allowed_tiers = ['platinum', 'enterprise', 'platinum_annual']
    user_tier = current_user.tier.lower()
    
    if user_tier not in allowed_tiers:
        flash(f'❌ Workspace creation requires Platinum or Enterprise tier. Current tier: {current_user.tier}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            description = request.form.get('description')
            domain = request.form.get('domain')
            industry = request.form.get('industry')
            size = request.form.get('size', 'medium')
            
            # Validate required fields
            if not name:
                flash('Workspace name is required', 'error')
                return render_template('workspace/create_workspace.html')
            
            # Create workspace data
            workspace_data = {
                'name': name,
                'description': description,
                'domain': domain,
                'industry': industry,
                'size': size,
            }
            
            # Call the API to create workspace
            workspace_response, status_code = WorkspaceController.create_workspace(workspace_data)
            
            if status_code == 201:
                flash('Workspace created successfully!', 'success')
                print(f"Workspace created successfully: {workspace_response.get('name', 'Unknown')}")
                return redirect(url_for('workspace_web.workspace_list'))
            elif status_code == 400:
                # User already has a workspace
                error_msg = workspace_response.get("error", "You can only create one workspace")
                flash(f'❌ {error_msg}', 'error')
                print(f"Workspace limit error: {error_msg}")
            elif status_code == 403:
                # Subscription tier error
                error_msg = workspace_response.get("error", "Subscription tier not allowed")
                flash(f'❌ {error_msg}. Please upgrade to Platinum or Enterprise tier.', 'error')
                print(f"Subscription error: {error_msg}")
            else:
                error_msg = workspace_response.get("error", "Unknown error")
                flash(f'Error creating workspace: {error_msg}', 'error')
                print(f"Error creating workspace: {error_msg}")
                
        except Exception as e:
            flash(f'Error creating workspace: {str(e)}', 'error')
    
    return render_template('workspace/create_workspace.html')

@workspace_web_bp.route('/invitations')
@login_required
def invitation_sidebar():
    """Display invitation sidebar page"""
    return render_template('workspace/invitation_sidebar.html')

@workspace_web_bp.route('/<workspace_id>')
@login_required
def workspace_detail(workspace_id):
    """Render workspace overview with projects and statistics"""
    try:
        # Get workspace details
        workspace_response = WorkspaceController.get_workspace(workspace_id)
        if workspace_response.status_code != 200:
            flash('Workspace not found', 'error')
            return redirect(url_for('workspace_web.workspace_list'))
        workspace_data = workspace_response.get_json()
        workspace = workspace_data.get('workspace')

        # Get projects
        projects_response = ProjectController.get_workspace_projects(workspace_id)
        if projects_response.status_code == 200:
            projects_data = projects_response.get_json()
            projects = projects_data.get('projects', [])
        else:
            projects = []

        # Get workspace statistics
        stats_response = WorkspaceController.get_workspace_overview(workspace_id)
        if stats_response.status_code == 200:
            stats_data = stats_response.get_json()
            statistics = stats_data.get('statistics', {})
        else:
            statistics = {}
        # Get recent activity
        activity_response = WorkspaceSettingsController.get_workspace_activity_logs(workspace_id)
        if activity_response.status_code == 200:
            activity_data = activity_response.get_json()
            recent_activity = activity_data.get('activities', [])
        else:
            recent_activity = []
        # Get active members
        members_response = WorkspaceMemberController.get_workspace_members(workspace_id)
        if members_response.status_code == 200:
            members_data = members_response.get_json()
            active_members = members_data.get('members', [])
        else:
            active_members = []
    except Exception as e:
        flash(f'Error loading workspace: {str(e)}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))
    return render_template('workspace/workspace_detail.html', 
                         workspace=workspace,
                         statistics=statistics,
                         projects=projects,
                         recent_activity=recent_activity,
                         active_members=active_members)

@workspace_web_bp.route('/<workspace_id>/settings')
@login_required
def workspace_settings(workspace_id):
    """Render workspace settings page"""
    try:
        # Get workspace details
        workspace_response = WorkspaceController.get_workspace(workspace_id)
        if workspace_response.status_code != 200:
            flash('Workspace not found', 'error')
            return redirect(url_for('workspace_web.workspace_list'))
        
        workspace_data = workspace_response.get_json()
        workspace = workspace_data.get('workspace')
        
        # Get workspace members
        members_response = WorkspaceMemberController.get_workspace_members(workspace_id)
        if members_response.status_code == 200:
            members_data = members_response.get_json()
            members = members_data.get('members', [])
        else:
            members = []
        
    except Exception as e:
        flash(f'Error loading workspace settings: {str(e)}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))
    
    return render_template('workspace/workspace_settings.html', 
                         workspace=workspace,
                         members=members)

@workspace_web_bp.route('/<workspace_id>/analytics')
@login_required
def workspace_analytics(workspace_id):
    """Render workspace analytics page"""
    try:
        # Get workspace details
        workspace_response = WorkspaceController.get_workspace(workspace_id)
        if workspace_response.status_code != 200:
            flash('Workspace not found', 'error')
            return redirect(url_for('workspace_web.workspace_list'))
        
        workspace_data = workspace_response.get_json()
        workspace = workspace_data.get('workspace')
        
        # Get analytics data
        analytics_response = WorkspaceSettingsController.get_workspace_analytics(workspace_id)
        if analytics_response.status_code == 200:
            analytics_data = analytics_response.get_json()
            metrics = analytics_data.get('metrics', {})
            task_completion_data = analytics_data.get('task_completion_data', {})
            project_status_data = analytics_data.get('project_status_data', {})
            team_performance_data = analytics_data.get('team_performance_data', {})
            recent_activities = analytics_data.get('recent_activities', [])
        else:
            metrics = {}
            task_completion_data = {}
            project_status_data = {}
            team_performance_data = {}
            recent_activities = []
        
        # Get period from query params
        period = request.args.get('period', 'month')
        
    except Exception as e:
        flash(f'Error loading analytics: {str(e)}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))
    
    return render_template('workspace/workspace_analytics.html',
                         workspace=workspace,
                         metrics=metrics,
                         task_completion_data=task_completion_data,
                         project_status_data=project_status_data,
                         team_performance_data=team_performance_data,
                         recent_activities=recent_activities,
                         period=period)

@workspace_web_bp.route('/projects/<project_id>')
@login_required
def project_detail(project_id):
    """Render project detail page"""
    try:
        # Get project details
        project_response = ProjectController.get_project(project_id)
        if project_response.status_code != 200:
            flash('Project not found', 'error')
            return redirect(url_for('workspace_web.workspace_list'))
        
        project_data = project_response.get_json()
        project = project_data.get('project')
        workspace = project_data.get('workspace')
        
        # Get project statistics
        stats_response = ProjectController.get_project_statistics(project_id)
        if stats_response.status_code == 200:
            stats_data = stats_response.get_json()
            project_stats = stats_data.get('statistics', {})
        else:
            project_stats = {}
        

        
    except Exception as e:
        flash(f'Error loading project: {str(e)}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))
    
    return render_template('workspace/project_detail.html',
                         project=project,
                         workspace=workspace,
                         project_stats=project_stats)

@workspace_web_bp.route('/tasks/<task_id>', methods=['GET'])
@login_required
def task_detail(task_id):
    """Render task detail page"""
    try:
        # Get task details from API
        try:
            task_response, status_code = WorkspaceTaskController.get_task(task_id)
            if status_code != 200:
                print(f"Task not found for ID: {task_id}")
                flash('Task not found', 'error')
                return redirect(url_for('workspace_web.workspace_list'))
            else:
                task = task_response
     
        except Exception as e:
            print(f"Error getting task: {str(e)}")
            flash('Error loading task', 'error')
            return redirect(url_for('workspace_web.workspace_list'))
        
        # Get workspace details
        try:
            workspace_response, workspace_status = WorkspaceController.get_workspace(task['workspace_id'])
            if workspace_status == 200:
                workspace = workspace_response
            else:
                workspace = None
        except Exception as e:
            print(f"Error getting workspace: {str(e)}")
            workspace = None
        
        # Get current user's workspace membership
        current_member = None
        if workspace:
            try:
                from models.workspace_model import Workspace
                from models.workspace_member_model import WorkspaceMember
                workspace_obj = Workspace.query.get(task['workspace_id'])
                if workspace_obj:
                    member = workspace_obj.get_member_by_user_id(current_user.user_id)
                    if member:
                        current_member = member.to_dict()
        
            except Exception as e:
                print(f"Error getting current member: {str(e)}")
        
    except Exception as e:
        print(f"Error in task_detail route: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading task: {str(e)}', 'error')
        return redirect(url_for('workspace_web.workspace_list'))
    
    return render_template('workspace/task_detail.html',
                         task=task,
                         workspace=workspace,
                         current_member=current_member)


@workspace_web_bp.route('/invitation/<token>')
def invitation(token):
    """Render invitation page"""
    try:
        from models.workspace_invitation_model import WorkspaceInvitation
        from models.workspace_model import Workspace
        
        # Get invitation by token
        invitation = WorkspaceInvitation.query.filter_by(token=token).first()
        if not invitation:
            flash('Invalid or expired invitation', 'error')
            return redirect(url_for('main.index'))
        
        # Get workspace details
        workspace = Workspace.query.get(invitation.workspace_id)
        if not workspace:
            flash('Workspace not found', 'error')
            return redirect(url_for('main.index'))
        
        # Get inviter details
        from models.user_model import User
        inviter = User.query.filter_by(email=invitation.invited_by_email).first()
        
    except Exception as e:
        flash(f'Error loading invitation: {str(e)}', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('workspace/invitation.html',
                         invitation=invitation,
                         workspace=workspace,
                         inviter=inviter) 