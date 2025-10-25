from flask import Blueprint, jsonify, request, current_app,abort
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import logging
import requests
from flask_login import login_required, current_user

from models.lead_model import db  # Import the shared db
from models import Lead, Agent, CallLog
from models.user_lead_drafts_model import UserLeadDraft
from .main_db_bakend.twilio_routes import bp as twilio_bp
from .main_db_bakend.email_backend import EmailService



# --- Blueprint Setup ---
robo_dailer_bp = Blueprint("robo_dailer_api", __name__, url_prefix="")
robo_dailer_bp.register_blueprint(twilio_bp)


# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='db_logs.log',
    filemode='a'
)

# --- Custom Exceptions ---
class APIError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

# --- Error Handlers ---
@robo_dailer_bp.errorhandler(APIError)
def handle_api_error(error: APIError):
    current_app.logger.error(f"API Error ({error.status_code}): {error.message}")
    return jsonify({"status": "error", "message": error.message}), error.status_code

@robo_dailer_bp.errorhandler(404)
def resource_not_found(_):
    return jsonify({"status": "error", "message": "Resource not found (404)"}), 404

@robo_dailer_bp.errorhandler(500)
def internal_server_error(error):
    current_app.logger.exception("Internal server error.")
    return jsonify({"status": "error", "message": "Internal Server Error (500)."}), 500

# --- Helper Functions ---
def validate_fields(data: dict, required: list):
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise APIError(f"Missing required fields: {', '.join(missing)}", 400)

def parse_iso8601(dt_str: str):
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00')).replace(microsecond=0)
    except Exception:
        raise APIError(f"Invalid ISO 8601 timestamp: {dt_str}", 400)

# --- Lead Endpoints ---
@robo_dailer_bp.route('/api/v1/leads', methods=['GET'])
def get_all_leads():
    # status = request.args.get('status')
    limit = int(request.args.get('limit', 100))  # default to 100 if not provided

    query = Lead.query
    # if status:
    #     query = query.filter_by(status=status)

    leads = [lead.to_dict() for lead in query.limit(limit).all()]

    return jsonify({
        "status": "success",
        "total": len(leads),
        "leads": leads
    }), 200


@robo_dailer_bp.route('/api/v1/leads/<string:lead_id>', methods=['GET'])
def get_lead(lead_id):
    lead = Lead.query.filter_by(lead_id=lead_id).first()
    if not lead:
        raise APIError("Lead not found.", 404)
    return jsonify({"status": "success", "lead": lead.to_dict()}), 200

# @robo_dailer_bp.route('/api/v1/add_leads', methods=['POST'])
# def add_leads():
#     data = request.get_json() or {}
#     required = ["company_id", "search_keyword", "company", "source", "owner_email"]
#     validate_fields(data, required)
#     try:
#         new_lead = Lead(
#             lead_id=data.get("lead_id"),
#             company_id=data["company_id"],
#             search_keyword=data["search_keyword"],
#             draft_data=data.get("draft_data"),
#             company=data["company"],
#             website=data.get("website"),
#             industry=data.get("industry"),
#             product_category=data.get("product_category"),
#             business_type=data.get("business_type"),
#             employees=data.get("employees"),
#             revenue=data.get("revenue"),
#             year_founded=data.get("year_founded"),
#             bbb_rating=data.get("bbb_rating"),
#             street=data.get("street"),
#             city=data.get("city"),
#             state=data.get("state"),
#             country=data.get("country"),
#             company_phone=data.get("company_phone"),
#             company_linkedin=data.get("company_linkedin"),
#             owner_first_name=data.get("owner_first_name"),
#             owner_last_name=data.get("owner_last_name"),
#             owner_title=data.get("owner_title"),
#             owner_linkedin=data.get("owner_linkedin"),
#             owner_phone_number=data.get("owner_phone_number"),
#             owner_email=data["owner_email"],
#             phone=data.get("phone"),
#             source=data["source"],
#             status=data.get("status", "new"),
#             is_edited=data.get("is_edited", False),
#             edited_by=data.get("edited_by")
#         )
#         db.session.add(new_lead)
#         db.session.commit()
#         return jsonify({"status": "success", "message": "Lead added.", "lead": new_lead.to_dict()}), 201
#     except IntegrityError:
#         db.session.rollback()
#         raise APIError(f"Lead with company ID '{data['company_id']}' already exists.", 409)
#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Error adding lead: {e}", exc_info=True)
#         raise APIError("Failed to add lead.", 500)

# --- Agent Endpoints ---
@robo_dailer_bp.route('/api/v1/agents', methods=['POST'])
def add_agent():
    data = request.get_json() or {}
    required = ['name', 'email', 'phone']
    validate_fields(data, required)
    try:
        new_agent = Agent(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            status=data.get('status', 'active'),
            is_available=data.get('is_available', True),
            total_calls=data.get('total_calls', 0),
        )
        db.session.add(new_agent)
        db.session.commit()
        return jsonify({"status": "success", "message": "Agent added.", "agent_id": new_agent.id}), 201
    except IntegrityError:
        db.session.rollback()
        raise APIError(f"Agent with email '{data['email']}' already exists.", 409)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding agent: {e}", exc_info=True)
        raise APIError("Failed to add agent.", 500)

@robo_dailer_bp.route('/api/v1/agents', methods=['GET'])
def get_all_agents():
    try:
        agents = [agent.to_dict() for agent in Agent.query.all()]
        return jsonify({"status": "success", "total": len(agents), "agents": agents}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching agents: {e}", exc_info=True)
        raise APIError("Failed to retrieve agents.", 500)

# --- Call Log Endpoints ---
@robo_dailer_bp.route('/api/v1/call_logs', methods=['POST'])
def add_call_log():
    data = request.get_json() or {}
    required = ['agent_id', 'phone_number']
    validate_fields(data, required)

    # --- Agent validation ---
    try:
        agent_id = int(data['agent_id'])
    except ValueError:
        raise APIError("agent_id must be an integer.", 400)

    agent = Agent.query.filter_by(id=agent_id).first()
    if not agent:
        raise APIError(f"Agent with ID '{agent_id}' not found.", 404)

    # --- Timestamps and duration ---
    started_at = parse_iso8601(data.get('started_at')) if data.get('started_at') else None
    ended_at = parse_iso8601(data.get('ended_at')) if data.get('ended_at') else None
    duration = data.get('duration')
    if started_at and ended_at and not duration:
        duration = int((ended_at - started_at).total_seconds())

    # --- Notes and summary ---
    notes = data.get('notes', '')
    summary = data.get('summary')
    final_notes = f"SUMMARY: {summary}\n---\nNOTES: {notes}" if summary else notes

    # --- Idempotency: agent + phone + time window ---
    if started_at:
        window_start = started_at - timedelta(seconds=10)
        window_end = started_at + timedelta(seconds=10)
        existing = CallLog.query.filter(
            CallLog.agent_id == agent_id,
            CallLog.phone_number == data['phone_number'],
            CallLog.started_at.between(window_start, window_end)
        ).first()
        if existing:
            return jsonify({
                "status": "success",
                "message": "Call log already exists.",
                "call_log": existing.to_dict()
            }), 200

    # --- Create CallLog ---
    call_log = CallLog(
        agent_id=agent_id,
        lead_id=data.get('lead_id'),  # Optional lead reference
        phone_number=data['phone_number'],
        direction=data.get('direction', 'outgoing'),
        status=data.get('status', 'completed'),
        action_taken=data.get('action_taken', 'call'),
        contact_name=data.get('contact_name'),
        started_at=started_at,
        ended_at=ended_at,
        duration=duration,
        notes=final_notes,
        follow_up_required=data.get('follow_up_required', False),
        call_attempt_number=data.get('call_attempt_number', 1)
    )

    # --- Persist ---
    try:
        db.session.add(call_log)
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": "Call log added.",
            "call_log": call_log.to_dict()
        }), 201
    except IntegrityError:
        db.session.rollback()
        existing = CallLog.query.filter_by(
            agent_id=agent_id,
            phone_number=data['phone_number'],
            started_at=started_at
        ).first()
        return jsonify({
            "status": "success",
            "message": "Call log already exists.",
            "call_log": existing
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ DETAILED ERROR adding call log: {type(e).__name__}: {str(e)}", exc_info=True)
        print(f"❌ DETAILED ERROR adding call log: {type(e).__name__}: {str(e)}")
        print(f"❌ Request data was: {request.get_json()}")
        raise APIError(f"Failed to add call log. Details: {str(e)}", 500)


@robo_dailer_bp.route('/api/v1/get_call_logs', methods=['GET'])
def get_call_logs():
    agent_id = request.args.get('agent_id')
    query = CallLog.query

    # --- Agent filter ---
    if agent_id:
        try:
            query = query.filter_by(agent_id=int(agent_id))
        except ValueError:
            raise APIError("agent_id must be an integer.", 400)

    # --- ORDER BY most recent first (by created_at which is when record was added) ---
    query = query.order_by(CallLog.created_at.desc())

    logs = [log.to_dict() for log in query.all()]
    print(f"🔍 GET call_logs: Found {len(logs)} total call logs, ordered by created_at DESC")
    if logs:
        print(f"🔍 First few call IDs: {[log['id'] for log in logs[:5]]}")
        print(f"🔍 First few created_at: {[log.get('created_at', 'None') for log in logs[:5]]}")
    
    return jsonify({
        "status": "success",
        "count": len(logs),
        "call_logs": logs
    }), 200


@robo_dailer_bp.route('/api/v1/call_logs/<int:call_log_id>', methods=['PUT', 'PATCH'])
def update_call_log(call_log_id):
    """Update an existing call log (for notes, summary, etc.)"""
    data = request.get_json() or {}
    
    # Find the existing call log
    call_log = CallLog.query.filter_by(id=call_log_id).first()
    if not call_log:
        raise APIError(f"Call log with ID '{call_log_id}' not found.", 404)
    
    try:
        # Update only the fields that are provided
        if 'notes' in data:
            call_log.notes = data['notes']
        if 'summary' in data:
            # Handle summary with notes formatting
            summary = data.get('summary')
            notes = data.get('notes', call_log.notes or '')
            if summary:
                call_log.notes = f"SUMMARY: {summary}\n---\nNOTES: {notes}"
            else:
                call_log.notes = notes
        if 'status' in data:
            call_log.status = data['status']
        if 'action_taken' in data:
            call_log.action_taken = data['action_taken']
        if 'contact_name' in data:
            call_log.contact_name = data['contact_name']
        if 'follow_up_required' in data:
            call_log.follow_up_required = data['follow_up_required']
        if 'follow_up_date' in data:
            call_log.follow_up_date = parse_iso8601(data['follow_up_date']) if data['follow_up_date'] else None
        
        # Update the updated_at timestamp
        call_log.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Call log updated.",
            "call_log": call_log.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating call log: {e}", exc_info=True)
        raise APIError("Failed to update call log.", 500)


@robo_dailer_bp.route("/api/v1/send_email", methods=["POST"])
def send_email_route():
    data = request.get_json(force=True)

    # Extract fields
    lead_name = data.get("name")
    lead_email = data.get("email")

    if not lead_name or not lead_email:
        abort(400, description="Missing required fields: 'name' and 'email'")

    email_service = EmailService()
    try:
        # Send the missed call email
        email_service.send_missed_call_email(lead_name, lead_email)

        return jsonify({
            "status": "success",
            "message": f"Missed call email sent to {lead_email}"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@robo_dailer_bp.route('/api/v1/agents/<int:agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    try:
        agent = Agent.query.get(agent_id)
        if not agent:
            raise APIError(f"Agent with ID {agent_id} not found.", 404)

        db.session.delete(agent)
        db.session.commit()
        return jsonify({"status": "success", "message": f"Agent with ID {agent_id} deleted."}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting agent {agent_id}: {e}", exc_info=True)
        raise APIError("Failed to delete agent.", 500)
    
@robo_dailer_bp.route('/api/v1/grade_agents/<int:agent_id>', methods=['POST'])
def grade_agent(agent_id):
    """
    Updates the score_given field for a specific agent based on request data.
    
    Expected JSON payload: {"score": 4.5}
    """
    try:
        data = request.get_json()
    except Exception:
        current_app.logger.warning("Agent grading request failed: Missing or invalid JSON body.")
        return jsonify({"status": "error", "message": "Invalid JSON body provided"}), 400
    
    # 1. Extract and validate score
    score = data.get('score')
    if score is None:
        current_app.logger.warning("Agent grading failed for ID %d: Missing 'score' field.", agent_id)
        return jsonify({"status": "error", "message": "The 'score' field is required in the JSON body"}), 400

    try:
        # Attempt to convert score to a float for validation/storage
        score_float = float(score)
        
        # Optional: Add validation logic for score range (e.g., 0.0 to 5.0)
        # if not (0.0 <= score_float <= 5.0):
        #     return jsonify({"status": "error", "message": "Score must be between 0.0 and 5.0"}), 400

    except ValueError:
        current_app.logger.warning("Agent grading failed for ID %d: Invalid score value: %s.", agent_id, score)
        return jsonify({"status": "error", "message": "Score must be a valid number"}), 400

    # 2. Find the agent
    agent = Agent.query.get(agent_id)
    if not agent:
        current_app.logger.error("Agent grading failed: Agent ID %d not found.", agent_id)
        return jsonify({"status": "error", "message": f"Agent with ID {agent_id} not found"}), 404

    # 3. Update the score
    try:
        agent.score_given = score_float
        db.session.commit()
        
        current_app.logger.info("Agent %d graded successfully with score: %.2f", agent_id, score_float)
        
        return jsonify({
            "status": "success",
            "message": f"Agent {agent_id} score updated successfully.",
            "agent_id": agent_id,
            "new_score": agent.score_given
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Database error while grading Agent ID %d: %s", agent_id, str(e))
        return jsonify({"status": "error", "message": f"Database error updating score: {str(e)}"}), 500


# --- Enriched Leads Endpoints ---
@robo_dailer_bp.route("/api/v1/enriched_leads", methods=["GET"])
def get_enriched_leads():
    """Get all enriched leads from user_lead_drafts for calling - handles both standalone and integrated modes"""
    try:
        # Check if we have an authenticated user (integrated mode)
        user_id = None
        try:
            if current_user.is_authenticated:
                user_id = current_user.user_id
                current_app.logger.info(f"Fetching enriched leads for authenticated user: {user_id}")
        except:
            current_app.logger.info("Running in standalone mode - no authentication required")
        
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status', 'pending')  # Default to pending
        phase = request.args.get('phase', 'approved')   # Default to approved
        
        # Build base query
        query = UserLeadDraft.query.filter(
            UserLeadDraft.is_deleted == False,
            UserLeadDraft.status == status,
            UserLeadDraft.phase == phase
        )
        
        # Add user filter only if authenticated (integrated mode)
        if user_id:
            query = query.filter(UserLeadDraft.user_id == user_id)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        enriched_leads = query.offset(offset).limit(limit).all()
        
        # Convert to dict and extract phone numbers from draft_data
        leads_data = []
        for draft in enriched_leads:
            try:
                # Extract phone from draft_data
                phone_number = None
                if draft.draft_data and isinstance(draft.draft_data, dict):
                    phone_number = (
                        draft.draft_data.get('companyPhone') or 
                        draft.draft_data.get('phone') or 
                        draft.draft_data.get('phone_number')
                    )
                
                # Format for calling interface
                lead_data = {
                    'lead_id': draft.lead_id,
                    'draft_id': draft.draft_id,
                    'company': draft.draft_data.get('company', 'Unknown Company'),
                    'phone_number': phone_number,
                    'website': draft.draft_data.get('website'),
                    'industry': draft.draft_data.get('industry'),
                    'employees': draft.draft_data.get('employees'),
                    'revenue': draft.draft_data.get('revenue'),
                    'city': draft.draft_data.get('city'),
                    'state': draft.draft_data.get('state'),
                    'contact_name': draft.draft_data.get('contact_name', draft.draft_data.get('contactPerson', draft.draft_data.get('company'))),
                    'created_at': draft.created_at.isoformat() if draft.created_at else None,
                    'version': draft.version,
                    'status': draft.status,
                    'phase': draft.phase,
                    'source': 'enriched_data'
                }
                
                # Only include leads with phone numbers
                if phone_number:
                    leads_data.append(lead_data)
                    
            except Exception as e:
                current_app.logger.error(f"Error processing draft {draft.id}: {e}")
                continue
        
        return jsonify({
            "status": "success",
            "data": leads_data,
            "total_count": total_count,
            "count": len(leads_data),
            "has_more": (offset + len(leads_data)) < total_count,
            "user_id": str(user_id) if user_id else "standalone_mode",
            "mode": "integrated" if user_id else "standalone"
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching enriched leads: {e}", exc_info=True)
        raise APIError("Failed to fetch enriched leads.", 500)


@robo_dailer_bp.route("/api/v1/enriched_leads/<draft_id>", methods=["GET"])
def get_enriched_lead_by_id(draft_id):
    """Get specific enriched lead by draft_id - handles both standalone and integrated modes"""
    try:
        # Check if we have an authenticated user (integrated mode)
        user_id = None
        try:
            if current_user.is_authenticated:
                user_id = current_user.user_id
        except:
            pass  # Running in standalone mode
        
        # Build query based on mode
        if user_id:
            # Integrated mode: filter by current user
            draft = UserLeadDraft.query.filter_by(
                draft_id=draft_id,
                user_id=user_id,
                is_deleted=False
            ).first()
        else:
            # Standalone mode: any draft for demo
            draft = UserLeadDraft.query.filter_by(
                draft_id=draft_id,
                is_deleted=False
            ).first()
        
        if not draft:
            raise APIError("Enriched lead not found" + (" or access denied" if user_id else ""), 404)
        
        # Extract phone from draft_data
        phone_number = None
        if draft.draft_data and isinstance(draft.draft_data, dict):
            phone_number = (
                draft.draft_data.get('companyPhone') or 
                draft.draft_data.get('phone') or 
                draft.draft_data.get('phone_number')
            )
        
        lead_data = {
            'lead_id': draft.lead_id,
            'draft_id': draft.draft_id,
            'company': draft.draft_data.get('company', 'Unknown Company'),
            'phone_number': phone_number,
            'website': draft.draft_data.get('website'),
            'industry': draft.draft_data.get('industry'),
            'employees': draft.draft_data.get('employees'),
            'revenue': draft.draft_data.get('revenue'),
            'city': draft.draft_data.get('city'),
            'state': draft.draft_data.get('state'),
            'contact_name': draft.draft_data.get('contact_name', draft.draft_data.get('contactPerson', draft.draft_data.get('company'))),
            'created_at': draft.created_at.isoformat() if draft.created_at else None,
            'version': draft.version,
            'status': draft.status,
            'phase': draft.phase,
            'source': 'enriched_data',
            'full_data': draft.draft_data,  # Include full data for detailed view
            'user_id': str(user_id) if user_id else "standalone_mode",
            'mode': "integrated" if user_id else "standalone"
        }
        
        return jsonify({
            "status": "success",
            "data": lead_data
        }), 200
        
    except APIError:
        raise
    except Exception as e:
        current_app.logger.error(f"Error fetching enriched lead {draft_id}: {e}", exc_info=True)
        raise APIError("Failed to fetch enriched lead.", 500)



