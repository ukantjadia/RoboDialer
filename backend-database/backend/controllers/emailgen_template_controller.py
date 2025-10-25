from models.emailgen_template_model import EmailGenTemplate, db
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from flask import current_app
from datetime import datetime
import os
import json
from config.config import Config
from models.user_model import User

class EmailGenTemplateController:
    MAX_TEMPLATES = 2
    PREDEFINED_COUNT = 1

    @staticmethod
    def get_templates():
        current_app.logger.info(f"User {current_user.user_id}: {getattr(current_user, 'username', None)} fetching templates.")
        templates = EmailGenTemplate.query.filter_by(user_id=current_user.user_id).order_by(EmailGenTemplate.created_at).all()
        return [t.to_dict() for t in templates]

    @staticmethod
    def create_template(data):
        user_id = current_user.user_id
        current_app.logger.info(f"User {user_id}: creating template '{data.get('template_name')}'")
        count = EmailGenTemplate.query.filter_by(user_id=user_id).count()
        if count >= EmailGenTemplateController.MAX_TEMPLATES:
            current_app.logger.warning(f"User {user_id}: template limit reached.")
            return False, 'Template limit reached.'
        if EmailGenTemplate.query.filter_by(user_id=user_id, template_name=data['template_name']).first():
            current_app.logger.warning(f"User {user_id}: duplicate template name '{data['template_name']}'")
            return False, 'Template name must be unique.'
        # Validate that template_content contains '{{context}}'
        if '{{context}}' not in data['template_content']:
            current_app.logger.warning(f"User {user_id}: template content missing '{{context}}' placeholder.")
            return False, "Template content must include '{{context}}' placeholder."
        template = EmailGenTemplate(
            user_id=user_id,
            template_name=data['template_name'],
            template_content=data['template_content'],
            cta_line=data.get('cta_line', ''),
            is_default=False,
            is_predefined=False
        )
        db.session.add(template)
        try:
            db.session.commit()
            current_app.logger.info(f"User {user_id}: template '{template.template_name}' created.")
            return True, template.to_dict()
        except IntegrityError:
            db.session.rollback()
            current_app.logger.error(f"User {user_id}: IntegrityError on create_template.")
            return False, 'Template name must be unique.'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"User {user_id}: Exception on create_template: {str(e)}")
            return False, str(e)

    @staticmethod
    def update_template(template_id, data):
        user_id = current_user.user_id
        current_app.logger.info(f"User {user_id}: updating template {template_id}")
        template = EmailGenTemplate.query.filter_by(template_id=template_id, user_id=current_user.user_id).first()
        if not template:
            current_app.logger.warning(f"User {user_id}: template {template_id} not found for update.")
            return False, 'Template not found.'
        if 'template_name' in data and data['template_name'] != template.template_name:
            if EmailGenTemplate.query.filter_by(user_id=current_user.user_id, template_name=data['template_name']).first():
                current_app.logger.warning(f"User {user_id}: duplicate template name '{data['template_name']}' on update.")
                return False, 'Template name must be unique.'
            template.template_name = data['template_name']
        if 'template_content' in data:
            # Validate that template_content contains '{{context}}'
            if '{{context}}' not in data['template_content']:
                current_app.logger.warning(f"User {user_id}: template content missing '{{context}}' placeholder on update.")
                return False, "Template content must include '{{context}}' placeholder."
            template.template_content = data['template_content']
        if 'cta_line' in data:
            template.cta_line = data['cta_line']
        template.updated_at = datetime.utcnow()
        try:
            db.session.commit()
            current_app.logger.info(f"User {user_id}: template {template_id} updated.")
            return True, template.to_dict()
        except IntegrityError:
            db.session.rollback()
            current_app.logger.error(f"User {user_id}: IntegrityError on update_template.")
            return False, 'Template name must be unique.'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"User {user_id}: Exception on update_template: {str(e)}")
            return False, str(e)

    @staticmethod
    def delete_template(template_id):
        user_id = current_user.user_id
        current_app.logger.info(f"User {user_id}: deleting template {template_id}")
        template = EmailGenTemplate.query.filter_by(template_id=template_id, user_id=current_user.user_id).first()
        if not template:
            current_app.logger.warning(f"User {user_id}: template {template_id} not found for delete.")
            return False, 'Template not found.'
        db.session.delete(template)
        try:
            db.session.commit()
            current_app.logger.info(f"User {user_id}: template {template_id} deleted.")
            return True, 'Template deleted.'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"User {user_id}: Exception on delete_template: {str(e)}")
            return False, str(e)

    @staticmethod
    def set_default(template_id):
        user_id = current_user.user_id
        current_app.logger.info(f"User {user_id}: setting default template {template_id}")
        template = EmailGenTemplate.query.filter_by(template_id=template_id, user_id=user_id).first()
        if not template:
            current_app.logger.warning(f"User {user_id}: template {template_id} not found for set_default.")
            return False, 'Template not found.'
        EmailGenTemplate.query.filter_by(user_id=user_id, is_default=True).update({'is_default': False})
        template.is_default = True
        template.updated_at = datetime.utcnow()
        try:
            db.session.commit()
            current_app.logger.info(f"User {user_id}: template {template_id} set as default.")
            return True, template.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"User {user_id}: Exception on set_default: {str(e)}")
            return False, str(e)

    @staticmethod
    def increment_usage(template_id):
        user_id = current_user.user_id
        current_app.logger.info(f"User {user_id}: incrementing usage for template {template_id}")
        template = EmailGenTemplate.query.filter_by(template_id=template_id, user_id=current_user.user_id).first()
        if not template:
            current_app.logger.warning(f"User {user_id}: template {template_id} not found for increment_usage.")
            return False, 'Template not found.'
        template.usage_count += 1
        try:
            db.session.commit()
            current_app.logger.info(f"User {user_id}: usage incremented for template {template_id}.")
            return True, template.usage_count
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"User {user_id}: Exception on increment_usage: {str(e)}")
            return False, str(e)

    @staticmethod
    def init_user_templates(user):
        try:
            if user.has_initialized_templates:
                current_app.logger.info(f"User {user.user_id}: {user.username} already initialized templates.")
                templates = EmailGenTemplate.query.filter_by(user_id=user.user_id).all()
                return True, [t.to_dict() for t in templates], 200
            template_dir = os.path.join(Config.PREDEFINED_TEMPLATE_DIR, Config.PREDEFINED_TEMPLATE_VERSION)
            current_app.logger.info(f"Initializing templates for user {user.user_id} from {template_dir}")
            if not os.path.isdir(template_dir):
                current_app.logger.error(f"Predefined template directory not found: {template_dir}")
                return False, {"error": "Predefined template directory not found."}, 500
            files = [f for f in os.listdir(template_dir) if f.endswith('.json')]
            if not files:
                current_app.logger.error(f"No predefined template files found in {template_dir}")
                return False, {"error": "No predefined template files found."}, 500
            created_templates = []
            for i, fname in enumerate(files):
                fpath = os.path.join(template_dir, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    tpl = json.load(f)
                template = EmailGenTemplate(
                    user_id=user.user_id,
                    template_name=tpl['template_name'],
                    template_content=tpl['template_content'],
                    cta_line=tpl.get('cta_line'),
                    is_predefined=True,
                    is_default=(i == 0)
                )
                db.session.add(template)
                created_templates.append(template)
                current_app.logger.info(f"Added predefined template '{template.template_name}' for user {user.user_id}")
            user.has_initialized_templates = True
            db.session.commit()
            current_app.logger.info(f"User {user.user_id} templates initialized successfully.")
            return True, [t.to_dict() for t in created_templates], 201
        except Exception as e:
            current_app.logger.error(f"Error initializing templates for user {user.user_id}: {str(e)}")
            db.session.rollback()
            return False, {"error": str(e)}, 500