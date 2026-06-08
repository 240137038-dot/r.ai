# Agentic Voice Assistant (MVP)

This repository contains a minimal voice assistant that accepts audio, transcribes it (OpenAI Whisper), sends the transcript to an LLM (OpenAI), runs small skills (todo), synthesizes voice (ElevenLabs), and returns audio for playback.

## Quick start (local)

1. Copy `.env.example` to `.env` and fill in your API keys and other variables:

   ```bash
   cp .env.example .env
   # then edit .env
   ```

2. (Optional) Create a Python virtual environment and install dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Initialize the database:

   ```bash
   python scripts/init_db.py
   ```

4. Run the server locally:

   ```bash
   uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Open: http://localhost:8000/static/index.html

### Or run with Docker

```bash
docker-compose up --build
```

## Environment variables

Set these variables in your `.env` file or in your environment:

- OPENAI_API_KEY - your OpenAI API key
- OPENAI_MODEL - model to use for planning (default: gpt-4o)
- ELEVEN_API_KEY - ElevenLabs API key (optional; if not set browser TTS fallback used)
- ELEVEN_VOICE_ID - ElevenLabs voice id
- DB_PATH - path to sqlite DB file (default: data/assistant.db)
- ENABLE_DEVICE_CONTROL - set to `true` to enable device control features
- DEVICE_ALLOWLIST_PATH - path to the device allowlist JSON (default: config/device_allowlist.json)

## Files overview

- `server/main.py` - FastAPI server and endpoints
- `agent/agent.py` - lightweight agent that asks LLM for JSON actions
- `skills/todo.py` - SQLite todo skill
- `skills/device.py` - Device control skill (Windows + Android via ADB)
- `stt.py` - Whisper transcription wrapper (OpenAI)
- `tts.py` - ElevenLabs TTS wrapper (returns base64 audio)
- `static/index.html` - simple frontend recording UI
- `scripts/init_db.py` - DB initializer
- `Dockerfile`, `docker-compose.yml` - containerization
- `config/device_allowlist.json` - example allowlist for device control

## Device Control (Windows + Android via ADB)

WARNING: Device control can perform destructive or disruptive operations. Use the allowlist and confirmation flow carefully.

1. Enable device control by setting `ENABLE_DEVICE_CONTROL=true` and configuring the allowlist at `config/device_allowlist.json`.
2. Put safe scripts in `scripts/safe/` and add allowed apps or scripts to the allowlist. Example allowlist:

```json
{
  "allowed_scripts": [
    "scripts/safe/example.sh"
  ],
  "allowed_apps": [
    "C:\\Program Files\\SomeApp\\app.exe",
    "com.example.myapp"
  ]
}
```

3. Android support requires `adb` (Android Platform Tools) in your PATH and USB debugging enabled on the device.
4. Risky actions (reboot, shutdown, delete, format, factory_reset) require explicit confirmation before execution. The assistant will persist a pending action and you must confirm via `/api/device/confirm` or the UI.

### Device control API endpoints

- `GET /api/device/pending` — list pending/unexecuted device actions
- `POST /api/device/confirm` — confirm and execute a pending action

Example confirm request (JSON):

```json
{ "pending_id": 5, "confirm": true }
```

## Common commands / examples

- List pending device actions:

```bash
curl http://localhost:8000/api/device/pending
```

- Confirm and execute pending ID 5:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"pending_id":5,"confirm":true}' http://localhost:8000/api/device/confirm
```

## Next steps / improvements

- Add more skills: calendar, email, web search, browser automation
- Add voice activity detection and streaming STT
- Add better prompt engineering and safety filters
- Add authentication for multiple users and persisting histories

If you want, I can:

- Add Google Calendar and Gmail integrations
- Replace cloud STT/LLM/TTS with local equivalents
- Open a pull request to merge the `agentic-device-control` branch into `main` and add CI tests
- Expand agent to plan multi-step tasks and run background tools

## Troubleshooting

- If transcription fails, check the `OPENAI_API_KEY` and OpenAI SDK version. The SDK may require different method names depending on version.
- If ElevenLabs returns errors, verify `ELEVEN_API_KEY` and the `ELEVEN_VOICE_ID` configuration.
- For Windows device control, some actions require elevated privileges (run assistant as Administrator).

---

If you want me to apply additional fixes or improve wording, tell me what to change and I will update the README and open a PR.