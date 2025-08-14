# זהו תוכן הקובץ main.py
import uvicorn
import httpx
import os
import base64
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

EDEN_API_KEY = "YOUR_EDEN_AI_API_KEY" # <--- הדבק כאן את המפתח שלך!
EDEN_API_URL = "https://api.edenai.run/v2/audio/speech_to_speech"

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/convert-voice-eden/")
async def convert_voice_eden(source_audio: UploadFile = File(...), reference_audio: UploadFile = File(...)):
    headers = {"Authorization": f"Bearer {EDEN_API_KEY}"}
    payload = {"providers": "elevenlabs", "fallback_providers": "coqui", "language": "he"}
    files = {'file': (source_audio.filename, await source_audio.read(), source_audio.content_type), 'reference_file': (reference_audio.filename, await reference_audio.read(), reference_audio.content_type)}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(EDEN_API_URL, headers=headers, data=payload, files=files, timeout=60.0)
            if response.status_code == 200:
                result_data = response.json()
                provider_result = result_data.get('elevenlabs') or result_data.get('coqui')
                if provider_result and provider_result.get('status') == 'success':
                    audio_base64 = provider_result.get('audio')
                    audio_bytes = base64.b64decode(audio_base64)
                    return Response(content=audio_bytes, media_type="audio/mpeg")
                else: return JSONResponse(status_code=500, content={"error": "Eden AI provider failed", "details": result_data})
            else: return JSONResponse(status_code=response.status_code, content={"error": "Failed to call Eden AI", "details": response.text})
        except Exception as e: return JSONResponse(status_code=500, content={"error": "An internal error occurred", "details": str(e)})

@app.get("/")
def root():
    return {"status": "Backend is running!"}