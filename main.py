import uvicorn
import httpx
import os
import base64
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

EDEN_AI_API_KEY = os.environ.get("EDEN_AI_API_KEY")
EDEN_API_URL = "https://api.edenai.run/v2/audio/speech_to_speech"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Server is updated and ready!"}

@app.post("/convert-voice-eden/")
async def convert_voice_eden(
    source_audio: UploadFile = File(...),
    reference_audio: UploadFile = File(...)
):
    if not EDEN_AI_API_KEY:
        return JSONResponse(
            status_code=500,
            content={"error": "EDEN_AI_API_KEY environment variable not found on the server."}
        )

    allowed_types = {"audio/mpeg", "audio/wav", "audio/mp3", "audio/x-wav", "audio/webm", "audio/ogg"}
    if source_audio.content_type not in allowed_types:
        return JSONResponse(status_code=400, content={"error": f"Unsupported file type for source_audio: {source_audio.content_type}"})
    if reference_audio.content_type not in allowed_types:
        return JSONResponse(status_code=400, content={"error": f"Unsupported file type for reference_audio: {reference_audio.content_type}"})

    source_bytes = await source_audio.read()
    reference_bytes = await reference_audio.read()

    headers = {"Authorization": f"Bearer {EDEN_AI_API_KEY}"}
    payload = {
        "providers": "elevenlabs",
        "fallback_providers": "coqui",
        "language": "he",
    }
    files = {
        'file': (source_audio.filename, source_bytes, source_audio.content_type),
        'reference_file': (reference_audio.filename, reference_bytes, reference_audio.content_type)
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        try:
            response = await client.post(
                EDEN_API_URL,
                headers=headers,
                data=payload,
                files=files
            )

            if response.status_code == 200:
                result_data = response.json()
                provider_result = result_data.get('elevenlabs') or result_data.get('coqui')

                if provider_result and provider_result.get('status') == 'success':
                    audio_base64 = provider_result.get('audio')
                    if not audio_base64:
                        return JSONResponse(status_code=500, content={"error": "No audio data returned by provider."})

                    audio_bytes = base64.b64decode(audio_base64)
                    return Response(content=audio_bytes, media_type="audio/mpeg")

                return JSONResponse(status_code=500, content={"error": "Eden AI provider failed", "details": result_data})

            return JSONResponse(status_code=response.status_code, content={"error": "Failed to call Eden AI", "details": response.text})

        except httpx.RequestError as e:
            return JSONResponse(status_code=500, content={"error": "Request to Eden AI failed", "details": str(e)})
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": "An internal server error occurred", "details": str(e)})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
