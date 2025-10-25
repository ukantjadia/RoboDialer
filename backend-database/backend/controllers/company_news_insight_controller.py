from models.company_news_insight_model import CompanyNewsInsight, db
from models.user_lead_drafts_model import UserLeadDraft
from flask_login import current_user
from sqlalchemy import and_
from datetime import datetime

class CompanyNewsInsightController:
    @staticmethod
    def create_insight(data):
        insight = CompanyNewsInsight(
            user_id=current_user.user_id,
            lead_id=data['lead_id'],
            company_name=data['company_name'],
            headline=data['headline'],
            insights=data['insights'],
            source=data.get('source'),
            tags=data.get('tags'),
            published_at=data.get('published_at'),
            saved_at=datetime.utcnow()
        )
        db.session.add(insight)
        db.session.commit()
        return insight

    @staticmethod
    def create_standalone_insight(data):
        insight = CompanyNewsInsight(
            user_id=current_user.user_id,
            lead_id=None,
            company_name=data['company_name'],
            headline=data['headline'],
            insights=data['insights'],
            source=data.get('source'),
            tags=data.get('tags'),
            published_at=data.get('published_at'),
            saved_at=datetime.utcnow()
        )
        db.session.add(insight)
        db.session.commit()
        return insight

    @staticmethod
    def get_insight(insight_id):
        return CompanyNewsInsight.query.get(insight_id)

    @staticmethod
    def update_insight(insight_id, data):
        insight = CompanyNewsInsight.query.get(insight_id)
        if not insight:
            return None
        # Only allow update if user owns it
        if insight.user_id != current_user.user_id:
            return None
        for key in ['headline', 'insights', 'source', 'tags', 'published_at', 'company_name']:
            if key in data:
                setattr(insight, key, data[key])
        db.session.commit()
        return insight

    @staticmethod
    def delete_insight(insight_id):
        insight = CompanyNewsInsight.query.get(insight_id)
        if not insight:
            return False
        if insight.user_id != current_user.user_id:
            return False
        db.session.delete(insight)
        db.session.commit()
        return True

    @staticmethod
    def list_insights():
        # Only show insights for leads the user has in UserLeadDraft
        user_lead_ids = [d.lead_id for d in UserLeadDraft.query.filter_by(user_id=current_user.user_id, is_deleted=False).all()]
        return CompanyNewsInsight.query.filter(
            and_(
                CompanyNewsInsight.user_id == current_user.user_id,
                CompanyNewsInsight.lead_id.in_(user_lead_ids)
            )
        ).all()

    @staticmethod
    def list_standalone_insights():
        return CompanyNewsInsight.query.filter(
            CompanyNewsInsight.user_id == current_user.user_id,
            CompanyNewsInsight.lead_id.is_(None)
        ).all()