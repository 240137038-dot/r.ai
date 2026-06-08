import os
import requests
import base64

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
ELEVEN_VOICE = os.getenv("ELEVEN_VOICE_ID", "alloy")  # example default voice id
ELEVEN_URL = os.getenv("ELEVEN_URL", "https://api.elevenlabs.io/v1/text-to-speech")

def synthesize_text(text: str) -> str:
    """
    Call ElevenLabs to synthesize text. Returns base64 encoded WAV/MP3 bytes.
    """
    if not ELEVEN_API_KEY:
        # fallback simple: return empty string and rely on frontend TTS
        return ""
    url = f"{ELEVEN_URL}/{ELEVEN_VOICE}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"text": text, "voice_settings": {"stability": 0.3, "similarity_boost": 0.75}}
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        print("TTS error", resp.status_code, resp.text)
        return ""
    audio_bytes = resp.content
    return base64.b64encode(audio_bytes).decode("utf-8")
