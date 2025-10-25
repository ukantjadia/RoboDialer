from flask import Blueprint, jsonify, request, render_template, current_app
from flask_login import login_required, current_user
from controllers.feedback_controller import FeedbackController
from utils.prompt_builder import PromptController
from utils.llm_message_generator import GenerateController
import uuid
from controllers.message_controller import MessageController
import logging
import re
from datetime import datetime

import asyncio
from config.config import Config
from models.feedback_model import MessageFeedback, db

logger = logging.getLogger(__name__)
message_bp = Blueprint('message_bp', __name__)

@message_bp.route('/save_message', methods=['POST'])
@login_required
def save_message():
    """
    Saves a generated message (email or linkedin) from a user action.
    """
    current_app.logger.info(f'Route hit: /api/save_message by user_id={current_user.user_id}, username={current_user.username}')

    try:
        data = request.get_json()
        if not data:
            current_app.logger.warning(f'Invalid JSON payload from user {current_user.username}')
            return jsonify({"error": "Invalid JSON payload"}), 400

        success, result = MessageController.save_user_message(data)

        if not success:
            current_app.logger.error(f'Failed to save message for user {current_user.username}: {result}')
            # Provide a more specific error code if it's a validation issue
            if result == "Invalid or missing 'type' in payload":
                return jsonify({"error": result}), 400
            return jsonify({"error": result}), 500

        current_app.logger.info(f'Successfully saved message for user {current_user.username}')
        return jsonify(result), 201

    except Exception as e:
        current_app.logger.error(f'Unexpected error in save_message for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@message_bp.route('/generated_history/email', methods=['GET'])
@login_required
def get_email_message_history():
    """
    Get email message history for the currently logged-in user.
    """
    current_app.logger.info(f'Route hit: /api/generated_history/email by user_id={current_user.user_id}, username={current_user.username}')

    try:
        success, result = MessageController.get_user_messages(current_user.user_id, message_type='email')

        if not success:
            current_app.logger.error(f'Failed to get email history for user {current_user.username}: {result}')
            return jsonify({"error": result}), 500

        current_app.logger.info(f'Successfully retrieved email history for user {current_user.username}')
        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f'Unexpected error in get_email_message_history for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@message_bp.route('/generated_history/linkedin', methods=['GET'])
@login_required
def get_linkedin_message_history():
    """
    Get LinkedIn message history for the currently logged-in user.
    """
    current_app.logger.info(f'Route hit: /api/generated_history/linkedin by user_id={current_user.user_id}, username={current_user.username}')

    try:
        success, result = MessageController.get_user_messages(current_user.user_id, message_type='linkedin')

        if not success:
            current_app.logger.error(f'Failed to get LinkedIn history for user {current_user.username}: {result}')
            return jsonify({"error": result}), 500

        current_app.logger.info(f'Successfully retrieved LinkedIn history for user {current_user.username}')
        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f'Unexpected error in get_linkedin_message_history for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@message_bp.route("/email-generator", methods=["GET"])
def show_email_form():
    current_app.logger.info(f'Route hit: /email-generator')
    return render_template("emailgen/email_generator.html")

@message_bp.route("/api/generate-email-all-tones", methods=["POST"])
def generate_email_all_tones():
    current_app.logger.info(f'Route hit: /api/generate-email-all-tones')

    try:
        data     = request.get_json(force=True)
        company  = data.get("company_name", "").strip()
        industry = data.get("industry", "").strip()
        focus    = data.get("focus", "")
        model    = data.get("model_choice", "")
        contexts = data.get("additional_context", [])

        # Filter out empty context points from the end
        while contexts and not contexts[-1].strip():
            current_app.logger.info(f'Removing empty context point from end: "{contexts[-1]}"')
            contexts.pop()

        if not (company and industry and focus and model and contexts):
            current_app.logger.warning(f'Missing required fields in generate-email-all-tones request')
            return jsonify({"error": "Missing required fields"}), 400

        for i, pt in enumerate(contexts[:3]):
            if len(pt.split()) < 20:
                current_app.logger.warning(f'Context point {i+1} too short in generate-email-all-tones request')
                return jsonify({"error": f"Context point {i+1} must be ≥20 words."}), 400

        context = " ".join(contexts)
        DEFAULT_TONES = ["direct", "professional", "friendly", "casual"]
        tones = data.get("tones") or DEFAULT_TONES

        async def build_and_call(tone):
            prompt = PromptController.build_prompt(tone, focus, company, industry, context)
            message = await asyncio.to_thread(
                GenerateController.generate_with_model,
                prompt, model
            )
            return {"tone": tone, "prompt": prompt, "message": message}

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tasks = [build_and_call(t) for t in tones]
            results = loop.run_until_complete(asyncio.gather(*tasks))
        except Exception as e:
            current_app.logger.error(f"Parallel generation error: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
        finally:
            loop.close()

        output = []
        for r in results:
            msg_id = str(uuid.uuid4())
            print(r["message"])
            r["message"] = re.sub(r'\*\*', '', r["message"])
            FeedbackController.capture_feedback({
                "message_id":        msg_id,
                "parent_message_id": None,  # No parent for initial generation
                "feedback_type":     "generation",
                "user_id":           data.get("user_id","anonymous"),
                "company_name":      company,
                "industry":          industry,
                "tone":              r["tone"],
                "focus":             focus,
                "context":           context,
                "model_used":        model,
                "prompt_template":   f"{r['tone']}_{focus}_{Config.PROMPT_TEMPLATE_VERSION}",
                "prompt_text":       r["prompt"],
                "generated_message": {
                    "message":      r["message"],
                    "generated_at": datetime.utcnow().isoformat()
                }
            })
            output.append({
                "tone":       r["tone"],
                "message_id": msg_id,
                "message":    r["message"]
            })

        current_app.logger.info(f'Successfully generated {len(output)} email variants')
        return jsonify(output), 200

    except Exception as e:
        current_app.logger.error(f'Unexpected error in generate_email_all_tones: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@message_bp.route("/api/generate-email", methods=["POST"])
def generate_email():
    current_app.logger.info(f'Route hit: /api/generate-email')

    try:
        data         = request.get_json(force=True)
        tone         = data["tone"]
        focus        = data["focus"]
        company      = data["company_name"]
        industry     = data["industry"]
        model_choice = data["model_choice"]
        user_id      = data.get("user_id", "anonymous")

        # Validate 3 required context points
        context_points = data["additional_context"]

        # Filter out empty context points from the end
        while context_points and not context_points[-1].strip():
            current_app.logger.info(f'Removing empty context point from end: "{context_points[-1]}"')
            context_points.pop()

        for i, pt in enumerate(context_points[:3]):
            if len(pt.strip().split()) < 20:
                current_app.logger.warning(f'Context point {i+1} too short in generate-email request')
                return jsonify({
                    "error": f"Point {i+1} must be at least 20 words."
                }), 400
        context = " ".join(context_points)

        current_app.logger.info(f"Generate request: {data}")

        # Build prompt
        prompt = PromptController.build_prompt(
            tone, focus, company, industry, context
        )

        # Call LLM
        generated_message = GenerateController.generate_with_model(
            prompt, model_choice
        )

        # Log "generation" action
        message_id          = str(uuid.uuid4())
        feedback_type       = "generation"  # Always generation for this endpoint

        FeedbackController.capture_feedback({
            "message_id":       message_id,
            "parent_message_id": None,  # No parent for initial generation
            "feedback_type":    feedback_type,
            "user_id":          user_id,
            "company_name":     company,
            "industry":         industry,
            "tone":             tone,
            "focus":            focus,
            "context":          context,
            "model_used":       model_choice,
            "prompt_template":  f"{tone}_{focus}_{Config.PROMPT_TEMPLATE_VERSION}",
            "prompt_text":      prompt,
            "generated_message":{
                "message":     generated_message,
                "generated_at": datetime.utcnow().isoformat()
            }
        })

        current_app.logger.info(f'Successfully generated email with message_id: {message_id}')
        return jsonify({
            "message_id":     message_id,
            "parent_message_id": None,
            "message":        generated_message,
            "prompt_version": f"{tone}_{focus}_{Config.PROMPT_TEMPLATE_VERSION}",
            "model_used":     model_choice,
            "prompt_text":    prompt
        }), 200

    except Exception as e:
        current_app.logger.error("Error in generate_email", exc_info=True)
        return jsonify({"error": str(e)}), 500

@message_bp.route("/api/feedback", methods=["POST"])
def submit_feedback():
    current_app.logger.info(f'Route hit: /api/feedback')

    try:
        data = request.get_json(force=True)
        current_app.logger.info("Feedback request: %s", data)

        result = FeedbackController.capture_feedback(data)
        status = 200 if result.get("success") else 400

        if result.get("success"):
            current_app.logger.info(f'Successfully captured feedback')
        else:
            current_app.logger.error(f'Failed to capture feedback: {result.get("error")}')

        return jsonify(result), status

    except Exception as e:
        current_app.logger.error(f'Unexpected error in submit_feedback: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@message_bp.route("/feedback-view", methods=["GET"])
def feedback_view():
    current_app.logger.info(f'Route hit: /feedback-view')

    try:
        all_rows = MessageFeedback.query.order_by(
            MessageFeedback.timestamp.desc()
        ).all()

        dashboard = {}
        for row in all_rows:
            key = row.parent_message_id or row.message_id
            if key not in dashboard:
                # capture one snippet of the generated email
                gen = ""
                gm = row.generated_message
                if isinstance(gm, dict):
                    gen = gm.get("message", "")
                elif gm:
                    gen = gm
                dashboard[key] = {
                    "message_id": key,
                    "generated": gen,
                    "upvote_count": 0,
                    "downvote_count": 0,
                    "regeneration_count": 0,
                    "entries": []
                }
            if row.feedback_type == "upvote":
                dashboard[key]["upvote_count"] += 1
            elif row.feedback_type == "downvote":
                dashboard[key]["downvote_count"] += 1
            elif row.feedback_type == "regeneration":
                dashboard[key]["regeneration_count"] += 1
            dashboard[key]["entries"].append(row.to_dict())
        messages = sorted(
            dashboard.values(),
            key=lambda m: m["entries"][0]["timestamp"],
            reverse=True
        )
        current_app.logger.info(f'Successfully loaded feedback view with {len(messages)} messages')
        return render_template("emailgen/feedback_view.html", messages=messages)

    except Exception as e:
        current_app.logger.error(f'Unexpected error in feedback_view: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@message_bp.route('/api/generate_template_variants', methods=['POST'])
@login_required
def generate_template_variants():
    current_app.logger.info(f'Route hit: /api/generate_template_variants by user_id={current_user.user_id}, username={current_user.username}')

    try:
        data = request.get_json(force=True)
        company_name = data.get('company_name', '').strip()
        industry = data.get('industry', '').strip()
        person_name = data.get('person_name', '').strip()
        tone = data.get('tone', '').strip()
        model_choice = data.get('model_choice', '').strip()
        template_ids = data.get('template_ids', [])
        context_points = data.get('additional_context', [])

        # Filter out empty context points from the end
        while context_points and not context_points[-1].strip():
            current_app.logger.info(f'Removing empty context point from end: "{context_points[-1]}"')
            context_points.pop()

        # Validate required fields
        if not (company_name and industry and person_name and tone and model_choice and template_ids and context_points):
            current_app.logger.warning(f'Missing required fields in generate_template_variants request from user {current_user.username}')
            return jsonify({'error': 'Missing required fields'}), 400
        if len(context_points) < 3:
            current_app.logger.warning(f'Insufficient context points in generate_template_variants request from user {current_user.username}')
            return jsonify({'error': 'At least 3 context points required'}), 400
        for i, pt in enumerate(context_points[:3]):
            if len(pt.strip().split()) < 20:
                current_app.logger.warning(f'Context point {i+1} too short in generate_template_variants request from user {current_user.username}')
                return jsonify({'error': f'Context point {i+1} must be at least 20 words.'}), 400

        # Call controller logic (no parent_message_id needed for initial generation)
        results = MessageController.generate_template_variants(
            current_user.user_id,
            company_name,
            industry,
            person_name,
            tone,
            model_choice,
            template_ids,
            context_points
        )

        current_app.logger.info(f'Successfully generated {len(results)} template variants for user {current_user.username}')
        return jsonify(results), 200

    except Exception as e:
        current_app.logger.error(f'Unexpected error in generate_template_variants for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@message_bp.route('/api/regenerate_template_variant', methods=['POST'])
@login_required
def regenerate_template_variant():
    current_app.logger.info(f'Route hit: /api/regenerate_template_variant by user_id={current_user.user_id}, username={current_user.username}')

    try:
        data = request.get_json(force=True)

        # Validate that original_message_id is provided for regeneration
        original_message_id = data.get('original_message_id')
        if not original_message_id:
            current_app.logger.warning(f'Missing original_message_id in regenerate_template_variant request from user {current_user.username}')
            return jsonify({'error': 'Missing original_message_id for regeneration'}), 400

        # Filter out empty context points from the end
        context_points = data.get('additional_context', [])
        while context_points and not context_points[-1].strip():
            current_app.logger.info(f'Removing empty context point from end: "{context_points[-1]}"')
            context_points.pop()
        data['additional_context'] = context_points

        # Add user_id to the data for the feedback controller
        data['user_id'] = current_user.user_id

        # Call the feedback controller for template regeneration
        result = FeedbackController.handle_template_regeneration(data)

        if not result.get('success'):
            current_app.logger.error(f'Failed to regenerate template variant for user {current_user.username}: {result.get("error")}')
            return jsonify(result), 400

        current_app.logger.info(f'Successfully regenerated template variant for user {current_user.username}')
        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f'Unexpected error in regenerate_template_variant for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
