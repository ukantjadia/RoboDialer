from models.lead_model import db
from datetime import datetime, timezone
import uuid
import json
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum, UniqueConstraint

class ProjectMember(db.Model):
    """
    Model to link WorkspaceMembers to Projects.
    This table defines which members are part of which project.
    """
    __tablename__ = 'project_members'

    project_member_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.project_id', ondelete='CASCADE'), nullable=False, index=True)
    workspace_member_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspace_members.workspace_member_id', ondelete='CASCADE'), nullable=False, index=True)
    added_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    added_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)

    # This ensures a workspace member can only be added to a project once.
    __table_args__ = (
        UniqueConstraint('project_id', 'workspace_member_id', name='uq_project_member'),
    )

    def to_dict(self):
        return {
            "project_member_id": str(self.project_member_id),
            "project_id": str(self.project_id),
            "workspace_member_id": str(self.workspace_member_id),
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "added_by": str(self.added_by),
        }