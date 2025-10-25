from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB

class AIAnalysis(db.Model):
    """Model for storing AI analysis data - one per lead (optionally per task) within a project"""
    __tablename__ = 'ai_analysis'

    # Primary key
    analysis_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    lead_id = db.Column(db.String(100), db.ForeignKey('leads.lead_id', ondelete='CASCADE'), nullable=False)
    task_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspace_tasks.task_id', ondelete='CASCADE'), nullable=True)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.project_id', ondelete='CASCADE'), nullable=False)
    workspace_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)

    # Company data snapshot from lead at creation time
    company_name = db.Column(db.String(1000), nullable=False)
    website = db.Column(db.String(1000), nullable=True)
    industry = db.Column(db.String(1000), nullable=True)
    location_state = db.Column(db.String(1000), nullable=True)
    employees = db.Column(db.String(100), nullable=True)
    revenue = db.Column(db.Float, nullable=True)

    # Scraped website content
    website_text = db.Column(JSONB, nullable=True)
    last_scraped = db.Column(db.DateTime, nullable=True)

    # AI Analysis Results (Stable)
    ai_analysis_stable = db.Column(JSONB, nullable=True)
    risk_score = db.Column(db.Float, nullable=True)
    growth_potential_score = db.Column(db.Float, nullable=True)
    investment_recommendation = db.Column(db.String(100), nullable=True)
    overall_score = db.Column(db.Float, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AIAnalysis {self.analysis_id}: {self.company_name}>'

    def to_dict(self):
        """Convert AIAnalysis object to a dictionary."""
        return {
            'analysis_id': str(self.analysis_id),
            'lead_id': self.lead_id,
            'task_id': str(self.task_id) if self.task_id else None,
            'project_id': str(self.project_id),
            'workspace_id': str(self.workspace_id),
            'user_id': str(self.user_id),
            'company_name': self.company_name,
            'website': self.website,
            'industry': self.industry,
            'location_state': self.location_state,
            'employees': self.employees,
            'revenue': self.revenue,
            'website_text': self.website_text,
            'last_scraped': self.last_scraped.isoformat() if self.last_scraped else None,
            'ai_analysis_stable': self.ai_analysis_stable,
            'risk_score': self.risk_score,
            'growth_potential_score': self.growth_potential_score,
            'investment_recommendation': self.investment_recommendation,
            'overall_score': self.overall_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def create_or_update_analysis(cls, lead_id, project_id, workspace_id, user_id,
                                 company_data, website_text=None, ai_analysis=None, task_id=None):
        """Create or update AI analysis for a lead within a project (optionally scoped by task)."""
        from flask import current_app
        current_app.logger.info(f'[AI Analysis Model] Starting create_or_update_analysis - Lead: {lead_id}, Project: {project_id}, Task: {task_id}, User: {user_id}')

        try:
            # Lookup existing by composite key
            query_kwargs = {'project_id': project_id, 'lead_id': lead_id}
            if task_id:
                query_kwargs['task_id'] = task_id
            else:
                query_kwargs['task_id'] = None

            existing_analysis = cls.query.filter_by(**query_kwargs).first()

            if existing_analysis:
                current_app.logger.info(f'[AI Analysis Model] Found existing analysis: {existing_analysis.analysis_id}, updating dynamic fields...')

                # Update dynamic fields only; keep company snapshot unchanged
                existing_analysis.user_id = user_id
                existing_analysis.website_text = website_text
                existing_analysis.ai_analysis_stable = ai_analysis
                existing_analysis.last_scraped = datetime.utcnow() if website_text else existing_analysis.last_scraped
                existing_analysis.updated_at = datetime.utcnow()

                if ai_analysis:
                    existing_analysis.risk_score = ai_analysis.get('risk_score')
                    existing_analysis.growth_potential_score = ai_analysis.get('growth_potential_score')
                    existing_analysis.investment_recommendation = ai_analysis.get('investment_recommendation')
                    existing_analysis.overall_score = ai_analysis.get('overall_score')

                db.session.commit()
                current_app.logger.info(f'[AI Analysis Model] Successfully updated analysis: {existing_analysis.analysis_id}')
                return existing_analysis
            else:
                current_app.logger.info(f'[AI Analysis Model] No existing analysis found, creating new one...')

                analysis = cls(
                    lead_id=lead_id,
                    task_id=task_id,
                    project_id=project_id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    company_name=company_data.get('company_name', ''),
                    website=company_data.get('website'),
                    industry=company_data.get('industry'),
                    location_state=company_data.get('state'),
                    employees=company_data.get('employees'),
                    revenue=company_data.get('revenue'),
                    website_text=website_text,
                    ai_analysis_stable=ai_analysis,
                    last_scraped=datetime.utcnow() if website_text else None
                )

                if ai_analysis:
                    analysis.risk_score = ai_analysis.get('risk_score')
                    analysis.growth_potential_score = ai_analysis.get('growth_potential_score')
                    analysis.investment_recommendation = ai_analysis.get('investment_recommendation')
                    analysis.overall_score = ai_analysis.get('overall_score')

                db.session.add(analysis)
                db.session.commit()
                current_app.logger.info(f'[AI Analysis Model] Successfully created new analysis: {analysis.analysis_id}')
                return analysis

        except Exception as e:
            current_app.logger.error(f'[AI Analysis Model] Error in create_or_update_analysis: {str(e)}')
            current_app.logger.error(f'[AI Analysis Model] Error details - Lead: {lead_id}, Project: {project_id}, Task: {task_id}, User: {user_id}')
            raise

    @classmethod
    def get_by_project(cls, project_id):
        """Deprecated: Get first analysis for a specific project (kept for backward compatibility where needed)."""
        return cls.query.filter_by(project_id=project_id).first()

    @classmethod
    def get_all_by_project(cls, project_id):
        """Get all analyses for a project, sorted by most recently updated."""
        return (
            cls.query
            .filter_by(project_id=project_id)
            .order_by(cls.updated_at.desc())
            .all()
        )

    @classmethod
    def get_all_by_project_and_task(cls, project_id, task_id):
        """Get all analyses for a given project and task, sorted by most recently updated."""
        return (
            cls.query
            .filter_by(project_id=project_id, task_id=task_id)
            .order_by(cls.updated_at.desc())
            .all()
        )