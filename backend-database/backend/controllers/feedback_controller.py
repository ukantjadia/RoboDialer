import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.exc import SQLAlchemyError
from models.feedback_model import MessageFeedback, db
from utils.prompt_builder import PromptController
from utils.llm_message_generator import GenerateController
from config.config import Config
from flask import current_app

logger = logging.getLogger(__name__)

class FeedbackController:
    """
    Handles all feedback-related operations: upvote, downvote, regeneration, analytics, history, and deletion.
    All methods are static as this controller is stateless.
    """

    @staticmethod
    def capture_feedback(feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Capture user feedback (upvote/downvote/generation/regeneration) and store in the database.
        Returns a dict with success status and message.
        """
        current_app.logger.info(f"Capturing feedback: {feedback_data}")
        required_fields = [
            'message_id', 'feedback_type', 'company_name',
            'industry', 'tone', 'focus', 'context', 'model_used',
            'prompt_template', 'prompt_text', 'generated_message'
        ]
        missing_fields = [f for f in required_fields if f not in feedback_data]
        if missing_fields:
            current_app.logger.error(f"Missing required fields: {missing_fields}")
            return {
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }

        # Accept 'generation' as a feedback_type for initial logging
        valid_types = ['upvote', 'downvote', 'generation', 'regeneration']
        if feedback_data['feedback_type'] not in valid_types:
            current_app.logger.error(f"Invalid feedback type: {feedback_data['feedback_type']}")
            return {
                'success': False,
                'error': f'Invalid feedback type. Must be one of {valid_types}'
            }

        # Handle user_id defaulting
        user_id = feedback_data.get('user_id')
        if not user_id:
            user_id = 'test_user'

        try:
            feedback_record = MessageFeedback(
                entry_id=str(uuid.uuid4()),
                message_id=feedback_data['message_id'],
                parent_message_id=feedback_data.get('parent_message_id'),
                user_id=user_id,
                company_name=feedback_data['company_name'],
                industry=feedback_data['industry'],
                tone=feedback_data['tone'],
                focus=feedback_data['focus'],
                context=feedback_data['context'],
                model_used=feedback_data['model_used'],
                prompt_template=feedback_data['prompt_template'],
                prompt_text=feedback_data['prompt_text'],
                generated_message=feedback_data['generated_message'],
                feedback_type=feedback_data['feedback_type'],
                timestamp=datetime.utcnow()
            )
            db.session.add(feedback_record)
            db.session.commit()
            current_app.logger.info(f"Feedback ({feedback_data['feedback_type']}) captured for message_id: {feedback_data['message_id']}")
            return {
                'success': True,
                'message': f'Feedback ({feedback_data["feedback_type"]}) captured successfully',
                'feedback_id': feedback_record.entry_id
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error while capturing feedback: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Database error occurred while saving feedback'
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error while capturing feedback: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'An unexpected error occurred while processing feedback'
            }

    @staticmethod
    def handle_regeneration(regeneration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle regeneration request: generate new content and log as regeneration feedback.
        Returns a dict with the new content and status.
        """
        current_app.logger.info(f"Handling regeneration: {regeneration_data}")
        required_fields = ['company_name', 'industry', 'tone', 'focus', 'context', 'model_choice']
        missing_fields = [f for f in required_fields if f not in regeneration_data]
        if missing_fields:
            current_app.logger.error(f"Missing required fields for regeneration: {missing_fields}")
            return {
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }
        # Handle user_id defaulting for regeneration
        user_id = regeneration_data.get('user_id')
        if not user_id:
            user_id = 'test_user'
        original_data = regeneration_data.get('original_data', {})
        parent_message_id = regeneration_data.get('parent_message_id')
        try:
            prompt = PromptController.build_prompt(
                regeneration_data['tone'],
                regeneration_data['focus'],
                regeneration_data['company_name'],
                regeneration_data['industry'],
                regeneration_data['context']
            )
        except FileNotFoundError as fnf:
            current_app.logger.error(f"Prompt not found: {fnf}")
            return {'success': False, 'error': str(fnf)}
        except Exception as e:
            current_app.logger.error(f"Prompt build error: {e}")
            return {'success': False, 'error': str(e)}
        try:
            generated_message = GenerateController.generate_with_model(
                prompt,
                regeneration_data['model_choice']
            )
        except Exception as e:
            current_app.logger.error(f"LLM generation failed: {e}")
            return {'success': False, 'error': f'LLM generation failed: {str(e)}'}
        try:
            new_message_id = str(uuid.uuid4())
            feedback_record = MessageFeedback(
                entry_id=str(uuid.uuid4()),
                message_id=new_message_id,
                parent_message_id=parent_message_id,
                user_id=user_id,
                company_name=original_data.get('company_name', regeneration_data['company_name']),
                industry=original_data.get('industry', regeneration_data['industry']),
                tone=original_data.get('tone', regeneration_data['tone']),
                focus=original_data.get('focus', regeneration_data['focus']),
                context=original_data.get('context', regeneration_data['context']),
                model_used=regeneration_data['model_choice'],
                prompt_template=f"{regeneration_data['tone']}_{regeneration_data['focus']}_{Config.PROMPT_TEMPLATE_VERSION}",
                prompt_text=prompt,
                generated_message={
                    'message': generated_message,
                    'generated_at': datetime.utcnow().isoformat()
                },
                feedback_type='regeneration',
                timestamp=datetime.utcnow()
            )
            db.session.add(feedback_record)
            db.session.commit()
            current_app.logger.info(f"Regeneration feedback logged for user: {user_id}")
            return {
                'success': True,
                'message': generated_message,
                'generated_content': generated_message,
                'model_used': regeneration_data['model_choice'],
                'prompt_template': f"{regeneration_data['tone']}_{regeneration_data['focus']}_{Config.PROMPT_TEMPLATE_VERSION}",
                'prompt_text': prompt,
                'message_id': new_message_id,
                'parent_message_id': parent_message_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error during regeneration: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Database error occurred during regeneration'
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error during regeneration: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'An unexpected error occurred during regeneration'
            }

    @staticmethod
    def handle_template_regeneration(regeneration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle template regeneration request: generate new content and log as regeneration feedback.
        Returns a dict with the new content and status.
        """
        current_app.logger.info(f"Handling template regeneration: {regeneration_data}")
        required_fields = ['company_name', 'industry', 'person_name', 'tone', 'model_choice', 'template_id', 'context_point_index', 'additional_context', 'original_message_id']
        missing_fields = [f for f in required_fields if f not in regeneration_data]
        if missing_fields:
            current_app.logger.error(f"Missing required fields for template regeneration: {missing_fields}")
            return {
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }

        # Handle user_id defaulting for regeneration
        user_id = regeneration_data.get('user_id')
        if not user_id:
            user_id = 'test_user'

        original_message_id = regeneration_data.get('original_message_id')  # The original message being regenerated
        template_id = regeneration_data.get('template_id')
        context_point_index = regeneration_data.get('context_point_index')
        context_points = regeneration_data.get('additional_context', [])

        # Validate context_point_index
        if context_point_index < 0 or context_point_index >= len(context_points):
            current_app.logger.error(f"Invalid context_point_index: {context_point_index}")
            return {'success': False, 'error': 'Invalid context_point_index'}

        context_point = context_points[context_point_index]

        try:
            # Import here to avoid circular imports
            from models.emailgen_template_model import EmailGenTemplate
            from utils.prompt_builder import PromptController
            from utils.llm_message_generator import GenerateController
            from config.config import Config
            import os

            # Fetch the specific template
            template = EmailGenTemplate.query.filter(
                EmailGenTemplate.template_id == template_id,
                EmailGenTemplate.user_id == user_id
            ).first()

            if not template:
                current_app.logger.error(f"Template {template_id} not found for user {user_id}")
                return {'success': False, 'error': 'Template not found'}

            # Use a default system prompt file
            system_prompt_file = os.path.join(Config.PROMPT_DIR, f"casual_sales_{Config.PROMPT_TEMPLATE_VERSION}.txt")

            # Build prompt using context rewriting (same as generate_template_variants)
            prompt = PromptController.build_context_rewrite_prompt(
                tone=regeneration_data['tone'],
                template_content=template.template_content,
                company_name=regeneration_data['company_name'],
                person_name=regeneration_data['person_name'],
                industry=regeneration_data['industry'],
                context_point=context_point
            )

        except FileNotFoundError as fnf:
            current_app.logger.error(f"Prompt not found: {fnf}")
            return {'success': False, 'error': str(fnf)}
        except Exception as e:
            current_app.logger.error(f"Prompt build error: {e}")
            return {'success': False, 'error': str(e)}

        try:
            rewritten_context = GenerateController.generate_with_model(
                prompt,
                regeneration_data['model_choice']
            ).strip()

            # Parse subject from rewritten_context
            subject = None
            context_body = rewritten_context
            if rewritten_context.lower().startswith('subject:'):
                lines = rewritten_context.split('\n', 1)
                subject = lines[0].strip()
                context_body = lines[1].strip() if len(lines) > 1 else ''

            # Replace the context placeholder in the template
            final_email = template.template_content.replace('{{context}}', context_body)
            final_email = final_email.replace('{{company_name}}', regeneration_data['company_name'])
            final_email = final_email.replace('{{person_name}}', regeneration_data['person_name'])
            final_email = final_email.replace('{{industry}}', regeneration_data['industry'])

            # If template does not already have a subject line, add the generated subject at the top
            if subject and 'subject:' not in template.template_content.lower():
                final_email = f"{subject}\n" + final_email

        except Exception as e:
            current_app.logger.error(f"LLM generation failed: {e}")
            return {'success': False, 'error': f'LLM generation failed: {str(e)}'}

        try:
            new_message_id = str(uuid.uuid4())
            feedback_record = MessageFeedback(
                entry_id=str(uuid.uuid4()),
                message_id=new_message_id,
                parent_message_id=original_message_id,  # Set the original message as parent
                user_id=user_id,
                company_name=regeneration_data['company_name'],
                industry=regeneration_data['industry'],
                tone=regeneration_data['tone'],
                focus=template.template_name,  # Using template name as focus
                context=context_point,
                model_used=regeneration_data['model_choice'],
                prompt_template=template.template_content,  # Template content
                prompt_text=prompt,  # Actual prompt sent to LLM
                generated_message={
                    'message': final_email,
                    'template_id': str(template.template_id),
                    'template_name': template.template_name,
                    'variant': context_point_index + 1,
                    'generated_at': datetime.utcnow().isoformat()
                },
                feedback_type='regeneration',
                timestamp=datetime.utcnow()
            )
            db.session.add(feedback_record)
            db.session.commit()
            current_app.logger.info(f"Template regeneration feedback logged for user: {user_id}")
            return {
                'success': True,
                'message': final_email,
                'generated_content': final_email,
                'model_used': regeneration_data['model_choice'],
                'prompt_template': template.template_content,
                'prompt_text': prompt,
                'message_id': new_message_id,
                'parent_message_id': original_message_id,
                'template_id': template_id,
                'context_point_index': context_point_index,
                'template_name': template.template_name,
                'variant': context_point_index + 1,
                'timestamp': datetime.utcnow().isoformat()
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error during template regeneration: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Database error occurred during template regeneration'
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error during template regeneration: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'An unexpected error occurred during template regeneration'
            }

    @staticmethod
    def get_feedback_analytics(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Retrieve feedback analytics and statistics.
        Returns a dict containing analytics data.
        """
        current_app.logger.info(f"Retrieving feedback analytics with filters: {filters}")
        try:
            query = MessageFeedback.query
            if filters:
                if 'user_id' in filters:
                    query = query.filter(MessageFeedback.user_id == filters['user_id'])
                if 'model_used' in filters:
                    query = query.filter(MessageFeedback.model_used == filters['model_used'])
                if 'tone' in filters:
                    query = query.filter(MessageFeedback.tone == filters['tone'])
                if 'focus' in filters:
                    query = query.filter(MessageFeedback.focus == filters['focus'])
                if 'start_date' in filters and 'end_date' in filters:
                    query = query.filter(
                        MessageFeedback.timestamp >= filters['start_date'],
                        MessageFeedback.timestamp <= filters['end_date']
                    )
            feedback_records = query.all()
            total_feedback = len(feedback_records)
            upvotes = sum(1 for record in feedback_records if record.feedback_type == 'upvote')
            downvotes = sum(1 for record in feedback_records if record.feedback_type == 'downvote')
            generations = sum(1 for record in feedback_records if record.feedback_type == 'generation')
            regenerations = sum(1 for record in feedback_records if record.feedback_type == 'regeneration')
            model_stats = {}
            for record in feedback_records:
                model = record.model_used
                if model not in model_stats:
                    model_stats[model] = {'upvotes': 0, 'downvotes': 0, 'generations': 0, 'regenerations': 0}
                if record.feedback_type == 'upvote':
                    model_stats[model]['upvotes'] += 1
                elif record.feedback_type == 'downvote':
                    model_stats[model]['downvotes'] += 1
                elif record.feedback_type == 'generation':
                    model_stats[model]['generations'] += 1
                elif record.feedback_type == 'regeneration':
                    model_stats[model]['regenerations'] += 1
            tone_stats = {}
            focus_stats = {}
            for record in feedback_records:
                tone = record.tone
                if tone not in tone_stats:
                    tone_stats[tone] = {'upvotes': 0, 'downvotes': 0}
                if record.feedback_type == 'upvote':
                    tone_stats[tone]['upvotes'] += 1
                elif record.feedback_type == 'downvote':
                    tone_stats[tone]['downvotes'] += 1
                focus = record.focus
                if focus not in focus_stats:
                    focus_stats[focus] = {'upvotes': 0, 'downvotes': 0}
                if record.feedback_type == 'upvote':
                    focus_stats[focus]['upvotes'] += 1
                elif record.feedback_type == 'downvote':
                    focus_stats[focus]['downvotes'] += 1
            current_app.logger.info(f"Successfully retrieved analytics with {total_feedback} total feedback records")
            return {
                'success': True,
                'analytics': {
                    'total_feedback': total_feedback,
                    'upvotes': upvotes,
                    'downvotes': downvotes,
                    'generations': generations,
                    'regenerations': regenerations,
                    'satisfaction_rate': (upvotes / (upvotes + downvotes)) * 100 if (upvotes + downvotes) > 0 else 0,
                    'model_performance': model_stats,
                    'tone_performance': tone_stats,
                    'focus_performance': focus_stats
                }
            }
        except Exception as e:
            current_app.logger.error(f"Error retrieving feedback analytics: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to retrieve feedback analytics'
            }

    @staticmethod
    def get_user_feedback_history(user_id: str, limit: int = 50) -> Dict[str, Any]:
        """
        Get feedback history for a specific user.
        Returns a dict containing the user's feedback history.
        """
        current_app.logger.info(f"Retrieving feedback history for user_id: {user_id}")
        try:
            feedback_records = MessageFeedback.query.filter(
                MessageFeedback.user_id == user_id
            ).order_by(MessageFeedback.timestamp.desc()).limit(limit).all()
            history = []
            for record in feedback_records:
                history.append({
                    'entry_id': record.entry_id,
                    'message_id': record.message_id,
                    'company_name': record.company_name,
                    'industry': record.industry,
                    'tone': record.tone,
                    'focus': record.focus,
                    'model_used': record.model_used,
                    'prompt_template': record.prompt_template,
                    'feedback_type': record.feedback_type,
                    'timestamp': record.timestamp.isoformat(),
                    'generated_message': record.generated_message
                })
            current_app.logger.info(f"Successfully retrieved {len(history)} feedback records for user {user_id}")
            return {
                'success': True,
                'history': history,
                'total_records': len(history)
            }
        except Exception as e:
            current_app.logger.error(f"Error retrieving user feedback history: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to retrieve feedback history'
            }

    @staticmethod
    def delete_feedback(feedback_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete a specific feedback record (if user has permission).
        Returns a dict with success status.
        """
        current_app.logger.info(f"Deleting feedback record: {feedback_id} for user: {user_id}")
        try:
            feedback_record = MessageFeedback.query.filter(
                MessageFeedback.entry_id == feedback_id,
                MessageFeedback.user_id == user_id
            ).first()
            if not feedback_record:
                current_app.logger.error(f"Feedback record not found or access denied: {feedback_id}")
                return {
                    'success': False,
                    'error': 'Feedback record not found or access denied'
                }
            db.session.delete(feedback_record)
            db.session.commit()
            current_app.logger.info(f"Feedback record {feedback_id} deleted successfully")
            return {
                'success': True,
                'message': 'Feedback record deleted successfully'
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error while deleting feedback: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Database error occurred while deleting feedback'
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error while deleting feedback: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'An unexpected error occurred while deleting feedback'
            }
