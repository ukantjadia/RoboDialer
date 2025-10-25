from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

class ProjectMetrics(db.Model):
    """Model for project metrics"""
    __tablename__ = 'project_metrics'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.project_id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(200), nullable=False)  # Metric name (e.g. Revenue, Tasks Completed)
    value = db.Column(db.String(500), nullable=False)  # Metric value
    metric_type = db.Column(db.String(50), nullable=True)  # Type of metric (numeric, percentage, text, etc.)
    unit = db.Column(db.String(50), nullable=True)  # Unit of measurement (%, $, hours, etc.)
    target_value = db.Column(db.String(500), nullable=True)  # Target value for this metric
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<ProjectMetrics {self.name}: {self.value}>'

    def to_dict(self):
        """Convert ProjectMetrics object to a dictionary."""
        creator_data = None
        if self.created_by:
            from models.user_model import User
            user = User.query.get(self.created_by)
            if user:
                creator_data = {
                    'user_id': str(user.user_id),
                    'username': user.username,
                    'email': user.email
                }

        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'name': self.name,
            'value': self.value,
            'metric_type': self.metric_type,
            'unit': self.unit,
            'target_value': self.target_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': str(self.created_by) if self.created_by else None,
            'is_active': self.is_active,
            'creator': creator_data
        }

    @staticmethod
    def create(project_id, name, value, metric_type=None, unit=None, target_value=None, created_by=None):
        """Create a new project metric"""
        metric = ProjectMetrics(
            project_id=project_id,
            name=name,
            value=value,
            metric_type=metric_type,
            unit=unit,
            target_value=target_value,
            created_by=created_by
        )
        db.session.add(metric)
        db.session.commit()
        return metric

    def update(self, **kwargs):
        """Update project metric information"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    def get_project(self):
        """Get the project this metric belongs to"""
        from models.project_model import Project
        return Project.query.get(self.project_id)

    def get_creator(self):
        """Get the user who created this metric"""
        if self.created_by:
            from models.user_model import User
            return User.query.get(self.created_by)
        return None

    def is_on_target(self):
        """Check if metric is on target"""
        if not self.target_value or not self.value:
            return None
        
        try:
            current_value = float(self.value)
            target_value = float(self.target_value)
            return current_value >= target_value
        except (ValueError, TypeError):
            return None

    def get_progress_percentage(self):
        """Get progress percentage towards target"""
        if not self.target_value or not self.value:
            return None
        
        try:
            current_value = float(self.value)
            target_value = float(self.target_value)
            if target_value == 0:
                return 0
            return min(100, (current_value / target_value) * 100)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def get_project_metrics(project_id, active_only=True):
        """Get all metrics for a project"""
        query = ProjectMetrics.query.filter_by(project_id=project_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(ProjectMetrics.created_at.desc()).all()

    @staticmethod
    def get_metric_by_name(project_id, name, active_only=True):
        """Get a specific metric by name"""
        query = ProjectMetrics.query.filter_by(project_id=project_id, name=name)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.first()

    @staticmethod
    def update_or_create(project_id, name, value, metric_type=None, unit=None, target_value=None, created_by=None):
        """Update existing metric or create new one"""
        existing = ProjectMetrics.get_metric_by_name(project_id, name, active_only=False)
        if existing:
            existing.update(
                value=value,
                metric_type=metric_type,
                unit=unit,
                target_value=target_value,
                is_active=True
            )
            return existing
        else:
            return ProjectMetrics.create(
                project_id=project_id,
                name=name,
                value=value,
                metric_type=metric_type,
                unit=unit,
                target_value=target_value,
                created_by=created_by
            )

    def deactivate(self):
        """Deactivate this metric"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    @staticmethod
    def get_common_metrics():
        """Get list of common metric names"""
        return [
            'Target Industry',
            'Target Location',
            'Min Revenue',
            'Target Revenue',
            'Max Revenue',
            'Min Employee',
            'Target Employee',
            'Max Employee',
            'Matching Keyword - Positive',
            'Matching Keyword - Negative'
        ] 