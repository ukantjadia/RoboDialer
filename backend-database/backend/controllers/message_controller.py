import asyncio
from models.message_model import db, Message
from models.user_model import User
from flask import current_app
from flask_login import current_user
from datetime import datetime
from models.emailgen_template_model import EmailGenTemplate
from utils.llm_message_generator import GenerateController
import logging
from utils.prompt_builder import PromptController
import os

class MessageController:
    @staticmethod
    def save_generated_message(message_data):
        """
        Saves the generated email and LinkedIn message to the database
        for the currently logged-in user in a structured JSON format.

        Args:
            message_data (dict): A dictionary containing the response from the external API.
                                 Expected keys: 'company', 'email', 'linkedin_message', 'subject'.

        Returns:
            tuple: (success, message)
        """
        try:
            user_id = current_user.user_id
            username = current_user.username
            current_app.logger.info(f"User '{username}' attempting to save a generated message.")

            # Extract data from the API response
            company_name = message_data.get('company')
            email_body = message_data.get('email')
            linkedin_body = message_data.get('linkedin_message')
            subject = message_data.get('subject')
            timestamp = datetime.utcnow().isoformat()

            # Construct the JSON for the email message
            email_json = None
            if email_body:
                email_json = {
                    'company_name': company_name,
                    'subject': subject,
                    'generated_message': email_body,
                    'timestamp': timestamp
                }

            # Construct the JSON for the LinkedIn message
            linkedin_json = None
            if linkedin_body:
                linkedin_json = {
                    'company_name': company_name,
                    'generated_message': linkedin_body,
                    'timestamp': timestamp
                }

            # Ensure there is something to save
            if not email_json and not linkedin_json:
                current_app.logger.info(f"No message content found in response to save for user '{username}' ({user_id})")
                return False, "No message content to save"

            # Create and save the new Message record
            new_message = Message(
                user_id=user_id,
                email_message=email_json,
                linkedin_message=linkedin_json
            )
            db.session.add(new_message)
            db.session.commit()

            current_app.logger.info(f"Successfully saved structured message {new_message.id} for user '{username}' ({user_id})")
            return True, new_message.to_dict()

        except Exception as e:
            db.session.rollback()
            username = current_user.username if current_user.is_authenticated else "anonymous"
            current_app.logger.error(f"Failed to save message for user '{username}': {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def save_user_message(data):
        """
        Saves a message from a user's save action on the frontend.

        Args:
            data (dict): The payload from the frontend. Expected keys:
                         'type' ('email' or 'linkedin'), 'message',
                         'company_name', and 'subject' (for email).

        Returns:
            tuple: (success, message)
        """
        try:
            user_id = current_user.user_id
            username = current_user.username

            message_type = data.get('type')
            if not message_type or message_type not in ['email', 'linkedin']:
                current_app.logger.warning(f"Invalid message type '{message_type}' from user '{username}'")
                return False, "Invalid or missing 'type' in payload"

            current_app.logger.info(f"User '{username}' attempting to save a '{message_type}' message.")

            timestamp = datetime.utcnow().isoformat()
            message_body = data.get('message')
            company_name = data.get('company_name')

            content = {}
            if message_type == 'email':
                content = {
                    'company_name': company_name,
                    'subject': data.get('subject'),
                    'generated_message': message_body,
                    'timestamp': timestamp
                }
            else: # linkedin
                content = {
                    'company_name': company_name,
                    'generated_message': message_body,
                    'timestamp': timestamp
                }

            new_message = Message(
                user_id=user_id,
                message_type=message_type,
                message_content=content
            )
            db.session.add(new_message)
            db.session.commit()

            current_app.logger.info(f"Successfully saved {message_type} message {new_message.message_id} for user '{username}'")
            return True, new_message.to_dict()

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in save_user_message for user '{current_user.username}': {e}", exc_info=True)
            return False, str(e)

    @staticmethod
    def get_user_messages(user_id, message_type=None):
        """
        Retrieves messages for a specific user, optionally filtered by type.

        Args:
            user_id (str): The ID of the user.
            message_type (str, optional): 'email' or 'linkedin'. Defaults to None (all messages).

        Returns:
            tuple: (success, data)
        """
        try:
            user = User.query.get(user_id)
            username = user.username if user else "Unknown"
            log_message_type = message_type if message_type else 'all'
            current_app.logger.info(f"Fetching '{log_message_type}' message history for user '{username}' ({user_id}).")

            query = Message.query.filter_by(user_id=user_id)

            if message_type:
                query = query.filter_by(message_type=message_type)

            messages = query.order_by(Message.created_at.desc()).all()

            current_app.logger.info(f"Successfully retrieved {len(messages)} messages for user '{username}'")
            return True, [message.to_dict() for message in messages]
        except Exception as e:
            current_app.logger.error(f"Error fetching messages for user {user_id}: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    async def _generate_variant(template, context_point, company_name, person_name, industry, tone, model_choice, variant_num, system_prompt_file, user_id=None):
        logger = logging.getLogger(__name__)
        # Validate template content
        if '{{context}}' not in template.template_content:
            current_app.logger.warning(f"Template {template.template_id} missing '{{context}}'. Skipping.")
            return None
        try:
            current_app.logger.info(f"Generating variant {variant_num} for template {template.template_id}")

            # Build prompt for context point rewriting
            prompt = PromptController.build_context_rewrite_prompt(
                tone=tone,
                template_content=template.template_content,
                company_name=company_name,
                person_name=person_name,
                industry=industry,
                context_point=context_point
            )

            # Call LLM to get rewritten context point
            rewritten_context = await asyncio.to_thread(
                GenerateController.generate_with_model,
                prompt, model_choice
            )
            current_app.logger.info(f"Rewritten context: -----------{context_point}----------------{rewritten_context}")
            # Clean up the response (remove any extra formatting, newlines, etc.)
            rewritten_context = rewritten_context.strip()

            # Parse subject from rewritten_context
            subject = None
            context_body = rewritten_context
            if rewritten_context.lower().startswith('subject:'):
                lines = rewritten_context.split('\n', 1)
                subject = lines[0].strip()
                context_body = lines[1].strip() if len(lines) > 1 else ''

            # Replace the context placeholder in the template
            final_email = template.template_content.replace('{{context}}', context_body)
            final_email = final_email.replace('{{company_name}}', company_name)
            final_email = final_email.replace('{{person_name}}', person_name)
            final_email = final_email.replace('{{industry}}', industry)

            # If template does not already have a subject line, add the generated subject at the top
            if subject and 'subject:' not in template.template_content.lower():
                final_email = f"{subject}\n" + final_email

            # Capture feedback with detailed information
            if user_id:
                from controllers.feedback_controller import FeedbackController
                import uuid
                from datetime import datetime

                message_id = str(uuid.uuid4())
                feedback_type = 'generation'  # Always generation for initial variants

                current_app.logger.info(f"Capturing feedback for variant {variant_num}, type: {feedback_type}")

                FeedbackController.capture_feedback({
                    'message_id': message_id,
                    'parent_message_id': None,  # No parent for initial generation
                    'feedback_type': feedback_type,
                    'user_id': user_id,
                    'company_name': company_name,
                    'industry': industry,
                    'tone': tone,
                    'focus': template.template_name,  # Using template name as focus
                    'context': context_point,
                    'model_used': model_choice,
                    'prompt_template': template.template_content,  # Template content
                    'prompt_text': prompt,  # Actual prompt sent to LLM
                    'generated_message': {
                        'message': final_email,
                        'template_id': str(template.template_id),
                        'template_name': template.template_name,
                        'variant': variant_num,
                        'rewritten_context': rewritten_context,
                        'generated_at': datetime.utcnow().isoformat()
                    }
                })

            current_app.logger.info(f"Successfully generated variant {variant_num} for template {template.template_id}")
            return {
                'template_id': str(template.template_id),
                'template_name': template.template_name,
                'variant': variant_num,
                'email': final_email,
                'message_id': message_id if user_id else None,
                'parent_message_id': None  # No parent for initial generation
            }
        except Exception as e:
            current_app.logger.error(f"LLM generation failed for template {template.template_id}, variant {variant_num}: {e}", exc_info=True)
            return None

    @staticmethod
    def generate_template_variants(user_id, company_name, industry, person_name, tone, model_choice, template_ids, context_points):
        current_app.logger.info(f"Generating template variants for user {user_id}, templates: {template_ids}, context_points: {len(context_points)}")

        try:
            # Fetch templates
            templates = EmailGenTemplate.query.filter(
                EmailGenTemplate.template_id.in_(template_ids),
                EmailGenTemplate.user_id == user_id
            ).all()
            template_map = {str(t.template_id): t for t in templates}

            if not templates:
                current_app.logger.error(f"No templates found for user {user_id} with template_ids: {template_ids}")
                return []

            current_app.logger.info(f"Found {len(templates)} templates for user {user_id}")

            tasks = []
            for template_id in template_ids:
                template = template_map.get(str(template_id))
                if not template:
                    current_app.logger.warning(f"Template {template_id} not found for user {user_id}")
                    continue
                for idx, context_point in enumerate(context_points):
                    tasks.append(MessageController._generate_variant(
                        template, context_point, company_name, person_name, industry, tone, model_choice, idx+1, None, user_id
                    ))

            current_app.logger.info(f"Starting generation of {len(tasks)} variants")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            all_results = loop.run_until_complete(asyncio.gather(*tasks))
            loop.close()
            results = [r for r in all_results if r]

            current_app.logger.info(f"Successfully generated {len(results)} variants out of {len(tasks)} tasks")
            return results

        except Exception as e:
            current_app.logger.error(f"Error in generate_template_variants for user {user_id}: {str(e)}", exc_info=True)
            return []