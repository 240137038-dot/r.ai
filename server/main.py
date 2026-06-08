from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import uuid
import tempfile
import base64
from agent.agent import Agent
from stt import transcribe_audio
from tts import synthesize_text

app = FastAPI(title="Agentic Voice Assistant")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize agent (uses environment variables for API keys)
agent = Agent()

@app.post("/api/audio")
async def handle_audio(file: UploadFile = File(...)):
    # Save incoming file
    suffix = os.path.splitext(file.filename)[1] or ".webm"
    tmp_path = os.path.join(tempfile.gettempdir(), f"upload-{uuid.uuid4().hex}{suffix}")
    with open(tmp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        # Transcribe
        text = transcribe_audio(tmp_path)
        if not text:
            raise HTTPException(status_code=400, detail="Empty transcription")

        # Agent handles text -> action/result
        result = agent.handle_text(text)

        # If the result requests device confirmation, include pending id/message
        if isinstance(result, dict) and result.get("device_pending"):
            return JSONResponse({"transcript": text, "response_text": result.get("message"), "device_pending": True, "pending_id": result.get("pending_id")})

        # If agent returns text_to_speak, synthesize audio and return base64
        if "text" in result:
            audio_b64 = synthesize_text(result["text"])
            return JSONResponse({"transcript": text, "response_text": result["text"], "audio_base64": audio_b64})
        else:
            return JSONResponse({"transcript": text, "result": result})
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

@app.post("/api/device/confirm")
def confirm_device(payload: dict):
    pending_id = payload.get("pending_id")
    confirm = payload.get("confirm", False)
    if not pending_id:
        raise HTTPException(status_code=400, detail="pending_id required")
    if not confirm:
        return {"ok": False, "message": "Cancelled by user."}
    res = agent.device.confirm_and_execute(int(pending_id))
    return res

@app.get("/api/device/pending")
def list_pending():
    return agent.device.list_pending()

@app.get("/api/todos")
def list_todos():
    return agent.todo.list_todos()

@app.post("/api/todos")
def add_todo(payload: dict):
    title = payload.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="missing title")
    return agent.todo.add_todo(title)

@app.post("/api/todos/{todo_id}/complete")
def complete_todo(todo_id: int):
    return agent.todo.complete_todo(todo_id)
