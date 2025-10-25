import os
import requests
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

class SpeechToTextConverter:
    def __init__(self):
        # Twilio
        self.ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
        self.AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
        self.client = Client(self.ACCOUNT_SID, self.AUTH_TOKEN)

        # Deepgram
        self.DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
        self.deepgram_url = "https://api.deepgram.com/v1/listen"

        # Recording save path
        self.recordings_dir = os.path.join(os.path.dirname(__file__), "recordings")
        os.makedirs(self.recordings_dir, exist_ok=True)

    def download_recording(self, recording_sid):
        """Download a recording from Twilio by SID"""
        output_file = os.path.join(self.recordings_dir, f"{recording_sid}_recording.wav")

        recording = self.client.recordings(recording_sid).fetch()
        recording_url = f"https://api.twilio.com{recording.uri.replace('.json', '.wav')}"

        response = requests.get(recording_url, auth=(self.client.username, self.client.password))
        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            print(f"Recording saved as {output_file}")
            return output_file
        else:
            raise Exception(f"Failed to download recording: {response.text}")

    def transcribe_recording(self, file_path):
        """Send recording to Deepgram for transcription"""
        headers = {
            "Authorization": f"Token {self.DEEPGRAM_API_KEY}",
            "Content-Type": "audio/wav"
        }

        with open(file_path, "rb") as audio_file:
            audio_bytes = audio_file.read()

        # Send raw bytes directly in the request body
        response = requests.post(
            f"{self.deepgram_url}?punctuate=true&model=general",
            headers=headers,
            data=audio_bytes
        )

        if response.status_code == 200:
            result = response.json()
            transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
            return transcript if transcript.strip() else "No speech detected"
        else:
            raise Exception(f"Deepgram transcription failed: {response.text}")


    def convert(self, recording_sid):
        """Download + transcribe in one step"""
        file_path = self.download_recording(recording_sid)
        return self.transcribe_recording(file_path)
