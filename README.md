# Agentic Voice Assistant (MVP)

This repository contains a minimal voice assistant that accepts audio, transcribes it (OpenAI Whisper), sends the transcript to an LLM (OpenAI), runs small skills (todo), synthesizes voice (ElevenLabs), and returns audio for playback.

Quick start (local)
1. Copy `.env.example` to `.env` and fill in keys.
2. (Optional) create Python venv and install dependencies:
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
3. Initialize DB:
   python scripts/init_db.py
4. Run:
   uvicorn server.main:app --reload
   Open http://localhost:8000/static/index.html

Or run with Docker:
   docker-compose up --build

Environment variables
- OPENAI_API_KEY - your OpenAI API key
- OPENAI_MODEL - model to use for planning (default: gpt-4o)
- ELEVEN_API_KEY - ElevenLabs API key (optional; if not set browser TTS fallback used)
- ELEVEN_VOICE_ID - ElevenLabs voice id

Files overview
- server/main.py - FastAPI server and endpoints
- agent/agent.py - lightweight agent that asks LLM for JSON actions
- skills/todo.py - SQLite todo skill
- stt.py - Whisper transcription wrapper (OpenAI)
- tts.py - ElevenLabs TTS wrapper (returns base64 audio)
- static/index.html - simple frontend recording UI
- scripts/init_db.py - DB initializer
- Dockerfile, docker-compose.yml - containerization

Next steps / improvements
- Add more skills: calendar, email, web search, browser automation
- Add voice activity detection and streaming STT
- Add better prompt engineering and safety filters
- Add authentication for multiple users and persisting histories

If you want, I can:
- Add Google Calendar and Gmail integrations
- Replace cloud STT/LLM/TTS with local equivalents
- Push this into your repo and open a PR (grant repo access)
- Expand agent to plan multi-step tasks and run background tools
