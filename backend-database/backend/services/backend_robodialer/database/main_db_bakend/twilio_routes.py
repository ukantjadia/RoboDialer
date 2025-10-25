import os
from urllib.parse import quote
from flask import request, jsonify, abort, Blueprint, current_app, send_file,Response
from flask_cors import CORS
from twilio.twiml.voice_response import VoiceResponse
from datetime import datetime 

# --- ACTUAL EXTERNAL IMPORTS ---
# Assuming these classes are available and functional in your production environment
from .twilio_dialre import DialerEngineDev
from .speech_to_text import SpeechToTextConverter

# Import database models for call logs
from models.lead_model import db
from models import CallLog, Agent 

# --- LAZY INITIALIZATION FUNCTION ---
dialer_engine = None

def get_dialer_engine():
    """
    Lazy initialization of the dialer engine.
    Uses the real DialerEngineDev class.
    """
    global dialer_engine

    if dialer_engine is None:
        try:
            # Direct instantiation of the actual DialerEngine
            dialer_engine = DialerEngineDev()
        except Exception as e:
            # Fatal error if the real engine cannot be instantiated
            current_app.logger.critical(f"FATAL: Could not initialize DialerEngineDev: {e}", exc_info=True)
            # Re-raise as a critical runtime error to prevent the app from starting up incorrectly
            raise RuntimeError("Dialer service failed to initialize.") from e

    return dialer_engine

# --- BLUEPRINT SETUP ---
bp = Blueprint("twilio_logic", __name__, url_prefix="/api/twilio")
CORS(bp)

# Middleware to handle ngrok warning page bypassing
@bp.before_request
def bypass_ngrok_warning():
    """
    Bypass ngrok warning page for Twilio webhooks
    """
    # Check if request is coming from Twilio
    user_agent = request.headers.get('User-Agent', '')
    if 'TwilioProxy' in user_agent or 'twilio' in user_agent.lower():
        # This is a Twilio webhook request
        pass
    
    # Log the request for debugging
    current_app.logger.info(f"Received request to {request.path} from {request.remote_addr} with User-Agent: {user_agent[:100]}")

# --- ROUTES ---
@bp.route("/token", methods=["GET"])
def get_token_route():
    identity = "agent_1_client_id" # This should likely come from a session/auth system
    engine = get_dialer_engine()
    # The DialerEngineDev.get_token returns a Flask Response object
    return engine.get_token(identity=identity)

@bp.route("/make_call", methods=["POST"])
def make_call_route():
    data = request.get_json(force=True)

    agent_id = data.get("agent_id")
    customer_number = data.get("to")
    print("CUSTOMER NUMBER IS ",customer_number)
    dialer_type = data.get("dialer_type")  # "manual" or "auto"
    lead_id = data.get("lead_id") if dialer_type == "auto" else None

    # Basic validation
    if not agent_id or not customer_number:
        abort(400, description="Missing 'agent_id' or 'to' in JSON body")

    if not dialer_type or dialer_type not in ["manual", "auto"]:
        abort(400, description="Missing or invalid 'dialer_type'. Must be 'manual' or 'auto'.")

    if dialer_type == "auto" and not lead_id:
        abort(400, description="Missing 'lead_id' for auto dial mode.")

    current_app.logger.info(
        f"Initiating {dialer_type} call from agent {agent_id} "
        f"to customer {customer_number} "
        f"{'(Lead ' + str(lead_id) + ')' if lead_id else ''}"
    )

    engine = get_dialer_engine()
    # Pass lead_id along if it's auto-dial, else None
    return engine.make_call_from_agent(agent_id, customer_number)

@bp.route("/voice", methods=["POST", "GET"])
def voice_webhook():
    try:
        to = request.values.get("To")
        engine = get_dialer_engine()
        resp = engine.generate_voice_twiml(to)
        return Response(resp, mimetype="application/xml")
    except Exception as e:
        current_app.logger.error(f"Error in voice webhook: {e}")
        # Return a simple fallback TwiML
        fallback_resp = VoiceResponse()
        fallback_resp.say("Unable to connect. Please try again later.")
        return Response(str(fallback_resp), mimetype="application/xml")


@bp.route("/join", methods=["POST", "GET"])
def join_webhook():
    """
    Twilio TwiML URL for connecting the customer leg of a call into a conference room.
    """
    try:
        room = request.values.get("Room")
        if not room:
            abort(400, description="Missing Room parameter")
        current_app.logger.info(f"Join Webhook received call for Room: {room}")
        engine = get_dialer_engine()
        twiml_response = engine.generate_join_twiml(room)
        return Response(twiml_response, mimetype="application/xml")
    except Exception as e:
        current_app.logger.error(f"Error in join webhook: {e}")
        # Return a simple fallback TwiML
        fallback_resp = VoiceResponse()
        fallback_resp.say("Unable to connect to conference. Please try again later.")
        return Response(str(fallback_resp), mimetype="application/xml")

@bp.route("/call_status", methods=["POST"])
def call_status_webhook():
    """
    Twilio callback for status updates (answered, completed, failed, etc.)
    Used to manage agent availability.
    """
    try:
        call_sid = request.values.get('CallSid')
        status = request.values.get('CallStatus')
        direction = request.values.get('Direction')
        
        current_app.logger.info(f"Call SID {call_sid} status changed to {status}. Direction: {direction}")
        
        # Example logic to update agent status (Assuming you map CallSid back to Agent ID)
        if status in ['completed', 'failed', 'no-answer']:
            # This is where you would call engine._mark_agent_available(agent_id)
            pass 
            
        return "", 200
    except Exception as e:
        current_app.logger.error(f"Error in call status webhook: {e}")
        return "", 200  # Always return 200 to prevent retries

@bp.route("/get_transcript/<call_sid>")
def get_recording_sid(call_sid):
    """
    Fetches recording SIDs for a call and sends them for transcription.
    """
    get_dialer_engine() # Ensure engine is initialized
    engine = get_dialer_engine()
    result = engine.get_transcript(call_sid)
    
    # Handle the new error response format
    if isinstance(result, tuple) and len(result) == 2:
        error_data, status_code = result
        return jsonify(error_data), status_code
    
    transcript_data = result
    if not transcript_data or not transcript_data.get("recordings"):
        return jsonify({"error": "No recordings found"}), 404

    # Direct use of the actual SpeechToTextConverter class
    try:
        converter = SpeechToTextConverter()
    except Exception as e:
        current_app.logger.error(f"FATAL: Could not instantiate SpeechToTextConverter: {e}", exc_info=True)
        return jsonify({"error": "Transcription service unavailable."}), 503

    results = []
    for rec in transcript_data["recordings"]:
        try:
            # Use the actual conversion method
            text = converter.convert(rec["recording_sid"])
        except Exception as e:
            current_app.logger.error(f"Error converting speech to text for {rec['recording_sid']}: {e}")
            text = "Transcription failed."
        results.append({
            "recording_sid": rec["recording_sid"],
            "url": rec["url"],
            "transcript": text
        })
    return jsonify({"call_sid": call_sid, "recordings": results})

@bp.route('/incoming_call', methods=['POST'])
def handle_incoming_call():
    """
    Twilio TwiML URL for inbound calls. It finds an agent and bridges the call.
    """
    engine = get_dialer_engine()
    agent = engine._find_available_agent()
    call_sid = request.values.get('CallSid')
    conference_name = f"incoming_conf_{call_sid}"
    response = VoiceResponse()
    
    # Put the incoming call into a conference
    dial = response.dial()
    dial.conference(
        conference_name,
        start_conference_on_enter=True,
        wait_url="http://twimlets.com/holdmusic?Bucket=com.twilio.music.classical",
    )
    
    if agent:
        agent_id, client_identity = agent
        try:
            # Call the agent's softphone (client identity) to join the same conference
            engine.client.calls.create(
                to=f"client:{client_identity}",
                from_=engine.caller_id,
                # The agent softphone's call will hit the /voice endpoint with To=room:conference_name
                url=f"{engine.base_url}/api/twilio/voice?To={quote(f'room:{conference_name}')}"),
            engine._mark_agent_busy(agent_id)
            current_app.logger.info(f"Incoming call {call_sid} routed to agent {agent_id}.")
        except Exception as e:
            current_app.logger.error(f"Error initiating call to agent {agent_id} for incoming call {call_sid}: {e}", exc_info=True)
            response.say("We are experiencing a technical difficulty. Please try again later.")
            return str(response)
    else:
        current_app.logger.warning(f"No agent available for incoming call {call_sid}. Sending to voicemail/IVR.")
        response.say("Thank you for calling. All agents are busy. Please leave a message.")
        # Alternatively, use <Record> or redirect to a voicemail flow

    return str(response)

@bp.route("/private/agent_status/<agent_id>", methods=["GET"])
def get_agent_status_route(agent_id):
    auth_header = request.headers.get('X-Private-Key')
    engine = get_dialer_engine()
    if auth_header != engine.private_key:
        abort(403, description="Unauthorized access")
    # DialerEngineDev provides this method
    return jsonify(engine.get_agent_status(agent_id))

@bp.route("/send_voicemail", methods=["POST"])
def send_voicemail():
    data = request.get_json() or {}
    if "script" not in data or "phone" not in data:
        return jsonify({"message": "Both 'phone' and 'script' fields are required"}), 400 
    
    phone_number = data.get('phone')
    script = data.get('script')
    agent_id = data.get('agent_id', 1)  # Default to agent 1 if not provided
    current_app.logger.info(f"Sending voicemail to {phone_number} with script: {script[:50]}...")
    engine = get_dialer_engine()
    
    # DialerEngineDev.send_voicemail returns a JSON response (or tuple)
    result = engine.send_voicemail(phone_number, script)
    
    # Handle the (response, status_code) tuple returned by DialerEngineDev for errors
    if isinstance(result, tuple) and len(result) == 2:
        return jsonify(result[0]), result[1]
    
    # If voicemail was sent successfully, create a call log entry
    if isinstance(result, dict) and result.get('call_sid'):
        try:
            # Import the database models
            from models.lead_model import db
            from models import CallLog, Agent
            from datetime import datetime
            
            # Find the agent
            agent = Agent.query.filter_by(id=agent_id).first()
            if agent:
                # Create call log entry directly
                call_log = CallLog(
                    agent_id=agent_id,
                    phone_number=phone_number,
                    direction='outgoing',
                    status='completed',
                    action_taken='voicemail',
                    contact_name=None,  # Could be enhanced to extract from lead info
                    started_at=datetime.now(),
                    ended_at=datetime.now(),
                    duration=0,
                    notes=f"Voicemail sent: {script}",
                    follow_up_required=False,
                    call_attempt_number=1
                )
                
                db.session.add(call_log)
                db.session.commit()
                
                # Add the call log to the result
                result['call_log'] = call_log.to_dict()
                current_app.logger.info(f"Created call log entry for voicemail to {phone_number}")
            else:
                current_app.logger.warning(f"Agent with ID {agent_id} not found, skipping call log creation")
        except Exception as e:
            current_app.logger.error(f"Error creating call log for voicemail: {e}")
            # Don't fail the voicemail if call log creation fails
            db.session.rollback()
    
    return jsonify(result)

@bp.route("/voicemails/<filename>")
def serve_voicemail(filename):
    """
    Serves the locally saved voicemail audio file to Twilio.
    """
    try:
        # Assuming the 'voicemails' directory is relative to the current working directory
        file_path = os.path.join("voicemails", filename)
        if not os.path.exists(file_path):
            current_app.logger.error(f"Voicemail file not found: {filename}")
            abort(404, description="Voicemail file not found")
        return send_file(file_path, mimetype="audio/wav")
    except FileNotFoundError:
        current_app.logger.error(f"Voicemail file not found: {filename}")
        abort(404, description="Voicemail file not found")
    except Exception as e:
        current_app.logger.error(f"Error serving voicemail file {filename}: {e}")
        abort(500, description="Internal server error")


# --- CALL LOGS ENDPOINTS ---
@bp.route("/call_logs", methods=["GET"])
def get_call_logs():
    """Get all call logs with optional filtering"""
    try:
        agent_id = request.args.get('agent_id')
        query = CallLog.query
        
        # Filter by agent if specified
        if agent_id:
            try:
                query = query.filter_by(agent_id=int(agent_id))
            except ValueError:
                return jsonify({"status": "error", "message": "agent_id must be an integer"}), 400
        
        # Order by most recent first (by created_at - when record was created)
        query = query.order_by(CallLog.created_at.desc())
        
        # Get all call logs
        call_logs = query.all()
        print(f"🔍 GET call_logs: Found {len(call_logs)} total call logs")
        if call_logs:
            print(f"🔍 First few call IDs: {[log.id for log in call_logs[:5]]}")
            print(f"🔍 First few created_at: {[log.created_at for log in call_logs[:5]]}")
        
        logs_data = []

        for log in call_logs:
            # Get agent information
            agent = Agent.query.get(log.agent_id) if log.agent_id else None
            
            # Format the call log data to match frontend expectations
            log_data = {
                'id': str(log.id),
                'leadId': log.lead_id,
                'agentId': log.agent_id,
                'agentName': agent.name if agent else 'Unknown',
                'from': log.phone_number if log.direction == 'incoming' else 'Agent',
                'to': 'Agent' if log.direction == 'incoming' else log.phone_number,
                'contactName': log.contact_name,
                'direction': log.direction,
                'status': log.status,
                'action_taken': log.action_taken,
                'startTime': int(log.started_at.timestamp() * 1000) if log.started_at else None,
                'endTime': int(log.ended_at.timestamp() * 1000) if log.ended_at else None,
                'duration': log.duration,
                'notes': log.notes,
                'call_attempt_number': log.call_attempt_number,
                'follow_up_required': log.follow_up_required
            }
            logs_data.append(log_data)
        
        return jsonify({
            "status": "success",
            "count": len(logs_data),
            "call_logs": logs_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching call logs: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to fetch call logs"}), 500


@bp.route("/call_logs", methods=["POST"])
def create_or_update_call_log():
    """Create or update a call log"""
    try:
        data = request.get_json() or {}
        current_app.logger.info(f"📨 Received call log request: {data}")
        
        # Required fields validation
        required_fields = ['agent_id', 'direction']
        missing = [f for f in required_fields if not data.get(f)]
        current_app.logger.info(f"🔍 Required field check - agent_id: {data.get('agent_id')}, direction: {data.get('direction')}")
        if missing:
            current_app.logger.error(f"❌ Missing required fields: {missing}")
            return jsonify({"status": "error", "message": f"Missing required fields: {', '.join(missing)}"}), 400
        
        # Check if this is an update (has an id) or create (no id)
        call_id = data.get('id')
        current_app.logger.info(f"🔍 Looking for call_id: {call_id} (type: {type(call_id)})")
        
        if call_id:
            # Convert to integer for database lookup
            try:
                call_id_int = int(call_id)
                call_log = CallLog.query.get(call_id_int)
                current_app.logger.info(f"🔍 Found existing call_log: {call_log}")
                if not call_log:
                    current_app.logger.error(f"❌ Call log with ID {call_id} not found")
                    # If not found, create new instead of error
                    current_app.logger.info(f"🆕 Creating new call log instead")
                    call_log = CallLog()
                else:
                    current_app.logger.info(f"✅ Updating existing call log {call_id}")
            except (ValueError, TypeError):
                current_app.logger.error(f"❌ Invalid call_id format: {call_id}")
                # If invalid ID, create new
                current_app.logger.info(f"🆕 Creating new call log due to invalid ID")
                call_log = CallLog()
        else:
            # Create new call log
            current_app.logger.info(f"🆕 Creating new call log")
            call_log = CallLog()
        
        # Update/set fields
        if 'agent_id' in data:
            call_log.agent_id = data['agent_id']
        if 'agentId' in data:  # Support both formats for backwards compatibility
            call_log.agent_id = data['agentId']
        if 'leadId' in data:
            call_log.lead_id = data['leadId']
        if 'lead_id' in data:
            call_log.lead_id = data['lead_id']
        if 'direction' in data:
            call_log.direction = data['direction']
        if 'status' in data:
            call_log.status = data['status']
        if 'action_taken' in data:
            call_log.action_taken = data['action_taken']
        if 'contactName' in data:
            call_log.contact_name = data['contactName']
        if 'notes' in data:
            call_log.notes = data['notes']
        if 'summary' in data:
            # Handle summary with notes formatting
            summary = data.get('summary')
            notes = data.get('notes', call_log.notes or '')
            if summary:
                call_log.notes = f"SUMMARY: {summary}\n---\nNOTES: {notes}"
        
        # Handle phone number based on direction
        if 'phone_number' in data and data['phone_number']:
            # Direct phone_number field (preferred)
            call_log.phone_number = data['phone_number']
        elif data['direction'] == 'outgoing':
            call_log.phone_number = data.get('to')
        else:
            call_log.phone_number = data.get('from')
        
        current_app.logger.info(f"📞 Phone number set to: {call_log.phone_number}")
        
        # Handle timestamps
        if 'startTime' in data and data['startTime']:
            call_log.started_at = datetime.fromtimestamp(data['startTime'] / 1000)
        elif not call_log.started_at:
            # Default for new calls without explicit startTime
            call_log.started_at = datetime.now()
            
        if 'endTime' in data and data['endTime']:
            call_log.ended_at = datetime.fromtimestamp(data['endTime'] / 1000)
        
        # Calculate duration if not provided
        if 'duration' in data:
            call_log.duration = data['duration']
        elif call_log.started_at and call_log.ended_at:
            call_log.duration = int((call_log.ended_at - call_log.started_at).total_seconds())
        
        # Set updated timestamp
        call_log.updated_at = datetime.now()
        
        # Save to database
        if call_log.id is None:  # New call log (no database ID yet)
            db.session.add(call_log)
        
        db.session.commit()
        current_app.logger.info(f"✅ Call log saved with ID: {call_log.id}")
        
        # Get agent information for response
        agent = Agent.query.get(call_log.agent_id) if call_log.agent_id else None
        
        # Format response to match frontend expectations
        response_data = {
            'id': str(call_log.id),
            'leadId': call_log.lead_id,
            'agentId': call_log.agent_id,
            'agentName': agent.name if agent else 'Unknown',
            'from': call_log.phone_number if call_log.direction == 'incoming' else 'Agent',
            'to': 'Agent' if call_log.direction == 'incoming' else call_log.phone_number,
            'contactName': call_log.contact_name,
            'direction': call_log.direction,
            'status': call_log.status,
            'action_taken': call_log.action_taken,
            'startTime': int(call_log.started_at.timestamp() * 1000) if call_log.started_at else None,
            'endTime': int(call_log.ended_at.timestamp() * 1000) if call_log.ended_at else None,
            'duration': call_log.duration,
            'notes': call_log.notes,
            'call_attempt_number': call_log.call_attempt_number,
            'follow_up_required': call_log.follow_up_required
        }
        
        return jsonify({
            "status": "success",
            "message": "Call log saved successfully",
            "call_log": response_data
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ DETAILED ERROR saving call log: {type(e).__name__}: {str(e)}", exc_info=True)
        print(f"❌ DETAILED ERROR saving call log: {type(e).__name__}: {str(e)}")
        print(f"❌ Request data was: {request.get_json()}")
        return jsonify({"status": "error", "message": "Failed to save call log", "error_details": str(e)}), 500


# --- AGENTS ENDPOINTS ---
@bp.route("/agents", methods=["GET"])
def get_agents():
    """Get all agents (excluding archived by default)"""
    try:
        include_archived = request.args.get('include_archived', 'false').lower() == 'true'
        
        if include_archived:
            agents = Agent.query.all()
        else:
            agents = Agent.query.filter_by(is_archived=False).all()
        
        agents_data = []
        
        for agent in agents:
            agent_data = {
                'id': agent.id,
                'name': agent.name,
                'email': agent.email,
                'phone': agent.phone,
                'status': agent.status,
                'is_available': agent.is_available,
                'is_archived': agent.is_archived,
                'total_calls': agent.total_calls,
                'score_given': agent.score_given
            }
            agents_data.append(agent_data)
        
        return jsonify({
            "status": "success",
            "count": len(agents_data),
            "agents": agents_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching agents: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to fetch agents"}), 500


@bp.route("/agents/<int:agent_id>", methods=["PUT", "PATCH"])
def update_agent(agent_id):
    """Update agent status or other fields"""
    try:
        data = request.get_json() or {}
        
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({"status": "error", "message": f"Agent with ID {agent_id} not found"}), 404
        
        # Update fields that are provided
        if 'status' in data:
            agent.status = data['status']
        if 'is_available' in data:
            agent.is_available = data['is_available']
        if 'name' in data:
            agent.name = data['name']
        if 'email' in data:
            agent.email = data['email']
        if 'phone' in data:
            agent.phone = data['phone']
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Agent updated successfully",
            "agent": {
                'id': agent.id,
                'name': agent.name,
                'email': agent.email,
                'phone': agent.phone,
                'status': agent.status,
                'is_available': agent.is_available,
                'total_calls': agent.total_calls,
                'score_given': agent.score_given
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating agent {agent_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to update agent"}), 500


# --- AGENT PREFERENCES ENDPOINTS ---
@bp.route("/agent_preferences/<int:agent_id>", methods=["GET"])
def get_agent_preferences(agent_id):
    """Get agent preferences"""
    try:
        from models.cold_call_agent_model import AgentPreferences
        
        preferences = AgentPreferences.query.filter_by(agent_id=agent_id).first()
        
        if not preferences:
            # Return default preferences if none exist
            return jsonify({
                "status": "success",
                "preferences": {
                    "agent_id": agent_id,
                    "voicemail_script": None,
                    "auto_voicemail_enabled": False
                }
            }), 200
        
        return jsonify({
            "status": "success",
            "preferences": preferences.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching agent preferences for {agent_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to fetch agent preferences"}), 500


@bp.route("/agent_preferences/<int:agent_id>", methods=["PUT", "POST"])
def update_agent_preferences(agent_id):
    """Update or create agent preferences"""
    try:
        from models.cold_call_agent_model import AgentPreferences, Agent
        
        data = request.get_json() or {}
        
        # Verify agent exists
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({"status": "error", "message": f"Agent with ID {agent_id} not found"}), 404
        
        # Get or create preferences
        preferences = AgentPreferences.query.filter_by(agent_id=agent_id).first()
        if not preferences:
            preferences = AgentPreferences(agent_id=agent_id)
            db.session.add(preferences)
        
        # Update fields that are provided
        if 'voicemail_script' in data:
            preferences.voicemail_script = data['voicemail_script']
        if 'auto_voicemail_enabled' in data:
            preferences.auto_voicemail_enabled = data['auto_voicemail_enabled']
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Agent preferences updated successfully",
            "preferences": preferences.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating agent preferences for {agent_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to update agent preferences"}), 500


# --- AGENT ARCHIVING ENDPOINTS ---
@bp.route("/agents/<int:agent_id>/archive", methods=["PUT"])
def archive_agent(agent_id):
    """Archive an agent instead of deleting"""
    try:
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({"status": "error", "message": f"Agent with ID {agent_id} not found"}), 404
        
        agent.is_archived = True
        agent.status = 'archived'
        agent.is_available = False
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Agent archived successfully",
            "agent": agent.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error archiving agent {agent_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to archive agent"}), 500


@bp.route("/agents/<int:agent_id>/unarchive", methods=["PUT"])
def unarchive_agent(agent_id):
    """Unarchive an agent"""
    try:
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({"status": "error", "message": f"Agent with ID {agent_id} not found"}), 404
        
        agent.is_archived = False
        agent.status = 'active'
        agent.is_available = True
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Agent unarchived successfully",
            "agent": agent.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error unarchiving agent {agent_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to unarchive agent"}), 500