import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")
STT_MODEL = os.getenv("STT_MODEL", "whisper-1")

def transcribe_audio(path: str) -> str:
    """
    Use OpenAI Whisper API to transcribe local audio file.
    Returns transcribed text or empty string.
    """
    try:
        with open(path, "rb") as audio_file:
            # The exact SDK call may vary depending on openai package version
            resp = openai.Audio.transcribe(STT_MODEL, audio_file)
            return resp.get("text", "").strip()
    except AttributeError:
        # fallback older client style
        try:
            resp = openai.Transcription.create(model=STT_MODEL, file=open(path, "rb"))
            return resp.get("text", "").strip()
        except Exception as e:
            print("STT transcription error:", e)
            return ""
    except Exception as e:
        print("STT transcription error:", e)
        return ""
