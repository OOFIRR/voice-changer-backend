import os
import httpx
import base64
from flask import Flask, request, jsonify, Response
from flask_cors import CORS # Import the CORS library

# Create the Flask app instance
app = Flask(__name__)

# Apply CORS to your app to allow requests from any origin
# This will solve the CORS policy error
CORS(app)

# Load the API key from environment variables
EDEN_AI_API_KEY = os.environ.get("EDEN_AI_API_KEY")
EDEN_API_URL = "https://api.edenai.run/v2/audio/speech_to_speech"

# A simple route to check if the server is running
@app.route("/")
def read_root():
    return jsonify(message="Flask server with CORS is updated and ready!")

# The main voice conversion route
@app.route("/convert-voice-eden/", methods=["POST"])
def convert_voice_eden():
    # 1. Check for the API key
    if not EDEN_AI_API_KEY:
        return jsonify(error="EDEN_AI_API_KEY environment variable not found."), 500

    # 2. Check if files were sent
    if 'source_audio' not in request.files or 'reference_audio' not in request.files:
        return jsonify(error="Both source_audio and reference_audio files are required."), 400

    source_audio_file = request.files['source_audio']
    reference_audio_file = request.files['reference_audio']

    # 3. Set up the request to Eden AI
    headers = {"Authorization": f"Bearer {EDEN_AI_API_KEY}"}
    payload = {
        "providers": "elevenlabs",
        "fallback_providers": "coqui",
        "language": "he",
    }
    files = {
        'file': (source_audio_file.filename, source_audio_file.read(), source_audio_file.content_type),
        'reference_file': (reference_audio_file.filename, reference_audio_file.read(), reference_audio_file.content_type)
    }

    # 4. Make the request to Eden AI
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(EDEN_API_URL, headers=headers, data=payload, files=files)

            if response.status_code == 200:
                result_data = response.json()
                provider_result = result_data.get('elevenlabs') or result_data.get('coqui')

                if provider_result and provider_result.get('status') == 'success':
                    audio_base64 = provider_result.get('audio')
                    audio_bytes = base64.b64decode(audio_base64)
                    return Response(audio_bytes, mimetype="audio/mpeg")

                return jsonify(error="Eden AI provider failed", details=result_data), 500
            
            return jsonify(error="Failed to call Eden AI", details=response.text), response.status_code

    except Exception as e:
        return jsonify(error="An internal server error occurred", details=str(e)), 500
