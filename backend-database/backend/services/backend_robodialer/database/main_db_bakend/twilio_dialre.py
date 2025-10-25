import os
import time
from typing import Optional
from urllib.parse import quote
from flask import request, jsonify, abort, Blueprint, current_app, send_file
from flask_cors import CORS
from twilio.twiml.voice_response import VoiceResponse, Dial, Say
from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.base.exceptions import TwilioRestException
from datetime import datetime 
import requests
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(dotenv_path=env_path)



from .speech_to_text import SpeechToTextConverter 
from .phone_utils import validate_phone_number, format_phone_display 



# --- DIALER ENGINE CLASS (FIXED) ---

class DialerEngineDev:
    def __init__(self):
        # Twilio Credentials
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.api_key_sid = os.getenv("TWILIO_API_KEY_SID")
        self.api_key_secret = os.getenv("TWILIO_API_SECRET")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twiml_app_sid = os.getenv("TWILIO_TWIML_APP_SID")
        self.client = Client(self.account_sid, self.auth_token)
        self.caller_id = os.getenv("TWILIO_CALLER_ID")
        self.base_url = os.getenv("BASE_URL")
        self.private_key = os.getenv("PRIVATE_KEY")
        
        required_vars = [
            self.account_sid, self.api_key_sid, self.api_key_secret,
            self.auth_token, self.twiml_app_sid, self.caller_id, self.base_url
        ]
        if not all(required_vars):
            raise ValueError("Missing one or more required Twilio environment variables.")
        
        # Agent management setup
        self.agents = {}
        self.register_agent("agent_1", "agent_1_client_id")
        self.conferences = {}

    def register_agent(self, agent_id: str, client_identity: str):
        self.agents[agent_id] = {"identity": client_identity, "status": "available"}
        print(f"Agent {agent_id} registered with identity {client_identity}")
        return {"registered": agent_id, "identity": client_identity}

    def get_agent_status(self, agent_id: str):
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "unknown agent"}, 404
        return {"agent_id": agent_id, "status": agent["status"]}

    def _find_available_agent(self) -> Optional[tuple]:
        for aid, meta in self.agents.items():
            if meta.get("status") == "available":
                return aid, meta["identity"]
        return None

    def _mark_agent_busy(self, agent_id: str):
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "busy"

    def _mark_agent_available(self, agent_id: str):
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "available"

    def get_token(self, identity="web_user"):
        token = AccessToken(self.account_sid, self.api_key_sid, self.api_key_secret, identity=identity)
        voice_grant = VoiceGrant(
            outgoing_application_sid=self.twiml_app_sid,
            incoming_allow=True
        )
        token.add_grant(voice_grant)
        return jsonify(token=token.to_jwt())

    def make_call_from_agent(self, agent_id: str, customer_number: str):
        # Validate phone number format
        is_valid, result = validate_phone_number(customer_number)
        if not is_valid:
            return jsonify({"error": result}), 400
        
        # Use the cleaned phone number
        cleaned_number = result
        
        # A unique conference name for this agent-initiated call
        conference_name = f"conf_{agent_id}_{int(time.time())}"
        
        try:
            # Step 1: Initiate the PSTN call to the customer. 
            # FIX: Set record=False to avoid conflicts; we let the TwiML <Conference> verb handle recording.
            customer_call = self.client.calls.create(
                to=cleaned_number,
                from_=self.caller_id,
                # Pass a custom flag to the TwiML webhook to confirm conference recording.
                url=f"{self.base_url}/api/twilio/join?Room={quote(conference_name)}&RecordConf=1", 
                status_callback=f"{self.base_url}/api/twilio/call_status", 
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method="POST",
                record=False # FIX: Control recording via TwiML
            )
            # Step 2: Mark agent as busy and return the conference name.
            self._mark_agent_busy(agent_id)
            return jsonify({
                "message": f"Call initiated to {format_phone_display(cleaned_number)}. Agent must now dial the returned conference room.",
                "conference": conference_name, 
                "customer_call_sid": customer_call.sid,
                "formatted_number": format_phone_display(cleaned_number)
            })
        except TwilioRestException as e:
            error_msg = f"Twilio error: {e.msg}"
            if e.code == 21614:  # Invalid phone number
                error_msg = f"Invalid phone number: {customer_number}. Please check the number format and try again."
            elif e.code == 21610:  # Unverified phone number (trial account)
                error_msg = f"Phone number {format_phone_display(cleaned_number)} is not verified for your Twilio trial account. Please verify this number in your Twilio console."
            elif e.code == 21612:  # The 'To' phone number is not currently reachable
                error_msg = f"Phone number {format_phone_display(cleaned_number)} is not currently reachable. Please check the number and try again."
            elif e.code == 21217:  # Phone number does not appear to be valid
                error_msg = f"Phone number {format_phone_display(cleaned_number)} does not appear to be valid. Please check the number format."
            elif e.code == 13223:  # Insufficient account balance
                error_msg = "Insufficient account balance to make this call. Please add funds to your Twilio account."
            elif e.code == 20003:  # Authentication error
                error_msg = "Authentication error. Please check your Twilio credentials."
            return jsonify({"error": error_msg}), 400
        except Exception as e:
            return jsonify({"error": f"Failed to initiate call: {str(e)}"}), 500

    def get_transcript(self, call_sid):
        try:
            recordings = self.client.recordings.list(call_sid=call_sid)
            if not recordings:
                # Also check for conference recordings if no call recordings found
                # Get call details to find any associated conference
                try:
                    call = self.client.calls(call_sid).fetch()
                    # Check for conference recordings (recordings might be associated with the conference, not the call)
                    all_recordings = self.client.recordings.list(limit=50)
                    conference_recordings = []
                    for rec in all_recordings:
                        if rec.source == 'Conference' and rec.date_created:
                            # Check if recording was created around the time of this call
                            time_diff = abs((call.date_created - rec.date_created).total_seconds())
                            if time_diff < 300:  # Within 5 minutes
                                conference_recordings.append(rec)
                    recordings = conference_recordings
                except Exception as e:
                    print(f"Error fetching call details: {e}")
            
            if not recordings:
                return {
                    "error": "No recordings available yet. Recordings may take a few minutes to become available after the call ends.", 
                    "call_sid": call_sid,
                    "status": "recording_pending",
                    "message": "This is normal behavior. Twilio recordings are processed after the call completes."
                }, 404
            
            transcript_data = []
            for rec in recordings:
                transcript_data.append({
                    "recording_sid": rec.sid,
                    "url": f"https://api.twilio.com{rec.uri.replace('.json', '.mp3')}",
                    "duration": getattr(rec, 'duration', 0),
                    "date_created": str(rec.date_created),
                    "source": getattr(rec, 'source', 'Call')
                })
            return {"call_sid": call_sid, "recordings": transcript_data}
        except Exception as e:
            return {"error": f"Failed to fetch recordings: {str(e)}", "call_sid": call_sid}, 500
    
    def generate_voice_twiml(self, to: str):
        resp = VoiceResponse()
        if to and to.startswith("room:"):
            # This is the agent's softphone connecting - this is correctly handled.
            room_name = to.replace("room:", "")
            resp.dial().conference(
                room_name,
                start_conference_on_enter=True,
                end_conference_on_exit=True
            )
        else:
            # Fallback for initial softphone connection / unexpected direct call
            resp.say("Welcome to the Twilio softphone. Please place a call to get started.")
        return str(resp)

    def generate_join_twiml(self, room: str):
        # This function handles the customer side when they answer the phone.
        resp = VoiceResponse()
        
        # Check for the custom flag passed from make_call_from_agent.
        record_flag = request.values.get("RecordConf")
        
        # FIX: Explicitly set the conference recording option using a string, which Twilio prefers.
        record_option = 'record-from-start' if record_flag == '1' else 'do-not-record'

        resp.dial().conference(
            room, 
            start_conference_on_enter=True, 
            end_conference_on_exit=True, 
            record=record_option # FIX: Use explicit string option
        )
        return str(resp) 
    
    def send_voicemail(self, customer_number: str, script: str, voice_id: str = "a167e0f3-df7e-4d52-a9c3-f949145efdab", model_id: str = "sonic-2"):
        """
        Generate AI voice with Cartesia and send as voicemail through Twilio
        """
        # Validate phone number format
        is_valid, result = validate_phone_number(customer_number)
        if not is_valid:
            return {"error": result}, 400
        
        # Use the cleaned phone number
        cleaned_number = result
        
        try:
            # --- Step 1: Call Cartesia ---
            headers = {
                "Authorization": f"Bearer {os.getenv('CARTESIA_API_KEY')}",
                "Content-Type": "application/json",
                "Cartesia-Version": "2025-04-16"
            }

            payload = {
                "transcript": script,
                "model_id": model_id,
                "voice": {
                    "mode": "id",
                    "id": voice_id,
                    "speed": 1.0 
                },
                "output_format": {
                    "container": "wav",
                    "encoding": "pcm_s16le",
                    "sample_rate": 16000
                    }
            }
            
            resp = requests.post(os.getenv("CARTESIA_URL"), headers=headers, json=payload)
            if resp.status_code != 200:
                return {"error": "Cartesia TTS failed", "details": resp.text}, 500

            # --- Step 2: Save audio ---
            os.makedirs("voicemails", exist_ok=True)
            file_hash = hash((script, voice_id, model_id))
            file_name = f"voicemail_{file_hash}.wav" 
            file_path = os.path.join("voicemails", file_name)
            with open(file_path, "wb") as f:
                f.write(resp.content)

            # --- Step 3: Generate public URL for Twilio ---
            audio_url = f"{self.base_url}/api/twilio/voicemails/{file_name}"

            # --- Step 4: Place Twilio call ---
            call = self.client.calls.create(
                to=cleaned_number,
                from_=self.caller_id,
                twiml=f'<Response><Play>{audio_url}</Play></Response>',
                status_callback=f"{self.base_url}/api/twilio/call_status",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method="POST"
            )

            return {
                "message": f"Voicemail sent to {format_phone_display(cleaned_number)}",
                "call_sid": call.sid,
                "audio_url": audio_url,
                "formatted_number": format_phone_display(cleaned_number)
            }

        except TwilioRestException as e:
            error_msg = f"Twilio error: {e.msg}"
            if e.code == 21614:  # Invalid phone number
                error_msg = f"Invalid phone number: {customer_number}. Please check the number format and try again."
            elif e.code == 21610:  # Unverified phone number (trial account)
                error_msg = f"Phone number {format_phone_display(cleaned_number)} is not verified for your Twilio trial account. Please verify this number in your Twilio console."
            elif e.code == 21612:  # The 'To' phone number is not currently reachable
                error_msg = f"Phone number {format_phone_display(cleaned_number)} is not currently reachable. Please check the number and try again."
            elif e.code == 21217:  # Phone number does not appear to be valid
                error_msg = f"Phone number {format_phone_display(cleaned_number)} does not appear to be valid. Please check the number format."
            elif e.code == 13223:  # Insufficient account balance
                error_msg = "Insufficient account balance to send voicemail. Please add funds to your Twilio account."
            elif e.code == 20003:  # Authentication error
                error_msg = "Authentication error. Please check your Twilio credentials."
            return {"error": error_msg}, 400
        except Exception as e:
            return {"error": f"Failed to send voicemail: {str(e)}"}, 500


