# Onboarding (Dev Setup)

This repo runs **two servers**:
- Node/Express static server on `http://localhost:3000`
- Python/Flask API on `http://localhost:8080`

## Prereqs (macOS)
- Node.js (>= 14)
- Python (>= 3.8)
- (Optional) MySQL + MySQL Workbench (only if working on DB/migrations)

## 10-minute local setup
From the repo root:

1) Install Node deps
```bash
npm install
```

2) Create + activate a Python venv
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3) Install Python deps
```bash
pip install -r requirements.txt
```

4) Create `.env`
```bash
cp .env.example .env
# then edit .env and add real API keys
```

5) Start the Flask API (Terminal A)
```bash
source .venv/bin/activate
python python/api.py
```

6) Start the Node server (Terminal B)
```bash
npm run dev
```

7) Open the app
- `http://localhost:3000`

## Quick sanity checks
- If the UI loads at `:3000`, Node is good.
- If voice/chat requests succeed, Flask + keys are good.

## Optional: database setup (only if needed)
Follow the more detailed guide in DATABASE_SETUP.md. At a high level:
- Create the MySQL database `pitch_simulator`
- Set `DATABASE_URL` in `.env`
- Run migrations:
```bash
source .venv/bin/activate
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Common macOS issues

### `source venv/bin/activate` fails
Use `.venv` (this repo’s `.gitignore` expects `.venv/`):
```bash
source .venv/bin/activate
```

### `pip install pyaudio` fails
`pyaudio` often needs PortAudio on macOS:
```bash
brew install portaudio
pip install pyaudio
```
If you don’t have Homebrew installed, install it first or ask a teammate to help.

### Ports already in use
- Node default: 3000
- Flask default: 8080
Stop the conflicting process or change the port in the relevant server.

### Microphone permissions
Make sure Chrome has mic access (System Settings → Privacy & Security → Microphone).

## Where to look in code
- Flask API pipeline: python/api.py
- Static server: server.js
- Frontend logic (recording + API calls): public/js/main.js
- Pages: public/html/*.html
