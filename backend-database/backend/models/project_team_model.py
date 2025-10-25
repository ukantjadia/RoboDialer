from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

class ProjectTeam(db.Model):
    """Model for multi-team projects (optional)"""
    __tablename__ = 'project_teams'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.project_id', ondelete='CASCADE'), nullable=False)
    team_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(50), default='contributor')  # lead, contributor, reviewer, etc.
    responsibility = db.Column(db.Text, nullable=True)  # What this team is responsible for
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<ProjectTeam {self.project_id} - {self.team_id}>'

    def to_dict(self):
        """Convert ProjectTeam object to a dictionary."""
        project_data = None
        if self.project_id:
            from models.project_model import Project
            project = Project.query.get(self.project_id)
            if project:
                project_data = {
                    'project_id': str(project.project_id),
                    'name': project.name,
                    'description': project.description
                }

        team_data = None
        if self.team_id:
            from models.workspace_model import Workspace
            team = Workspace.query.get(self.team_id)
            if team:
                team_data = {
                    'workspace_id': str(team.workspace_id),
                    'name': team.name,
                    'description': team.description
                }

        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'team_id': str(self.team_id),
            'role': self.role,
            'responsibility': self.responsibility,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'project': project_data,
            'team': team_data
        }

    @staticmethod
    def create(project_id, team_id, role='contributor', responsibility=None):
        """Create a new project team association"""
        project_team = ProjectTeam(
            project_id=project_id,
            team_id=team_id,
            role=role,
            responsibility=responsibility
        )
        db.session.add(project_team)
        db.session.commit()
        return project_team

    def update(self, **kwargs):
        """Update project team information"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    def get_project(self):
        """Get the project this team is associated with"""
        from models.project_model import Project
        return Project.query.get(self.project_id)

    def get_team(self):
        """Get the team associated with this project"""
        from models.workspace_model import Workspace
        return Workspace.query.get(self.team_id)

    def get_team_members(self):
        """Get all members of the team working on this project"""
        from models.workspace_member_model import WorkspaceMember
        return WorkspaceMember.query.filter_by(
            workspace_id=self.team_id,
            is_active=True
        ).all()

    def get_team_tasks(self):
        """Get all tasks assigned to this team for this project"""
        from models.workspace_task_model import WorkspaceTask
        from models.workspace_member_model import WorkspaceMember
        return WorkspaceTask.query.filter_by(
            project_id=self.project_id
        ).join(
            WorkspaceMember, 
            WorkspaceMember.user_id == WorkspaceTask.assigned_to
        ).filter(
            WorkspaceMember.workspace_id == self.team_id,
            WorkspaceMember.is_active == True
        ).all()

    @staticmethod
    def get_project_teams(project_id, active_only=True):
        """Get all teams associated with a project"""
        query = ProjectTeam.query.filter_by(project_id=project_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(ProjectTeam.created_at).all()

    @staticmethod
    def get_team_projects(team_id, active_only=True):
        """Get all projects associated with a team"""
        query = ProjectTeam.query.filter_by(team_id=team_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(ProjectTeam.created_at).all()

    @staticmethod
    def get_project_team(project_id, team_id):
        """Get specific project-team association"""
        return ProjectTeam.query.filter_by(
            project_id=project_id,
            team_id=team_id
        ).first()

    def deactivate(self):
        """Deactivate this project-team association"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    @staticmethod
    def get_project_team_summary(project_id):
        """Get summary of teams working on a project"""
        teams = ProjectTeam.get_project_teams(project_id)
        summary = {
            'total_teams': len(teams),
            'teams': [],
            'roles': {}
        }
        
        for team_assoc in teams:
            team_data = team_assoc.to_dict()
            summary['teams'].append(team_data)
            
            # Count roles
            role = team_assoc.role
            if role not in summary['roles']:
                summary['roles'][role] = 0
            summary['roles'][role] += 1
        
        return summary

    @staticmethod
    def get_team_project_summary(team_id):
        """Get summary of projects a team is working on"""
        projects = ProjectTeam.get_team_projects(team_id)
        summary = {
            'total_projects': len(projects),
            'projects': [],
            'roles': {}
        }
        
        for project_assoc in projects:
            project_data = project_assoc.to_dict()
            summary['projects'].append(project_data)
            
            # Count roles
            role = project_assoc.role
            if role not in summary['roles']:
                summary['roles'][role] = 0
            summary['roles'][role] += 1
        
        return summary 