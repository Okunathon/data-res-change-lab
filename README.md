# Donation Pitch Simulator

A web application that simulates donor pitch meetings using AI-powered voice conversations. Practice your fundraising pitches with realistic donor personas powered by OpenAI, Deepgram (speech-to-text), and ElevenLabs (text-to-speech).

## Project Structure

```
.
├── server.js                 # Node.js server for serving static files
├── python/
│   ├── api.py               # Flask API server (STT, LLM, TTS pipeline)
│   └── chatbot.py           # [Legacy/unused chatbot logic]
├── public/
│   └── html/                # HTML files, CSS, and JavaScript
│       ├── index.html       # Landing page
│       ├── simulation.html  # Pitch simulation interface
│       ├── case-studies.html    # Case study selection page
│       ├── preview.html     # Donor persona preview
│       ├── css/
│       │   └── style.css    # Styles
│       └── js/
│           ├── main.js          # Client-side logic (recording, API calls)
│           ├── index.js         # Landing page scripts
│           └── case-studies.js  # Case study page scripts
├── audio_out/               # Generated audio responses (gitignored)
├── package.json             # Node.js dependencies
├── requirements.txt         # Python dependencies
├── .env                     # API keys (gitignored)
└── README.md                # This file
```

## Architecture

### Frontend (HTML/CSS/JS)
- **Text Mode**: Type messages to the AI donor
- **Voice Mode**: Hold-to-record voice input, get audio responses
- Handles audio recording (WebM/MP4), playback, and session management

### Backend API (Python Flask)
The `python/api.py` server handles the full conversation pipeline:

1. **Speech-to-Text** (Deepgram): Transcribes user audio
2. **LLM Processing** (OpenAI GPT-4): Generates donor responses based on persona prompts
3. **Text-to-Speech** (ElevenLabs): Converts responses to natural speech
4. **Audio Management**: Saves/serves audio files, cleans up old recordings

### Donor Personas
Defined in `get_system_prompt()` in `api.py`:
- **template1**: Dr. Jennifer Walker - Biology professor, conservation-focused, time-conscious
- **template2-3**: Placeholder templates for additional personas

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:
- **Node.js** (v14 or higher) - [Download here](https://nodejs.org/)
- **Python** (v3.8 or higher) - [Download here](https://www.python.org/)
- **npm** (comes with Node.js)

API Keys (store in `.env` file in project root):
- `OPENAI_API_KEY` - OpenAI API key
- `DEEPGRAM_API_KEY` - Deepgram speech-to-text API key
- `ELEVEN_API_KEY` - ElevenLabs text-to-speech API key

To verify your installation, run:
```bash
node --version
python --version
npm --version
```

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/dhu27/data-res-change-lab.git
cd data-res-change-lab
```

2. **Install Node.js dependencies**:
```bash
npm install
```

3. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

4. **Create `.env` file** in the project root:
```bash
OPENAI_API_KEY=your_openai_key_here
DEEPGRAM_API_KEY=your_deepgram_key_here
ELEVEN_API_KEY=your_elevenlabs_key_here
```

### Running the Application

You need to run **both servers**:

#### 1. Start the Flask API Server (Python)
```bash
python python/api.py
```
This starts the API server on `http://localhost:8080`

#### 2. Start the Node.js Web Server
In a separate terminal:
```bash
npm start
# or for development with auto-reload:
npm run dev
```
This serves the frontend on `http://localhost:3000`

#### 3. Open the Application
Navigate to **`http://localhost:3000`** in your browser

#### Stopping the Servers
Press `Ctrl + C` in each terminal window

### Viewing Changes

- **Python API changes** (`python/api.py`): Restart the Flask server
- **Frontend changes** (HTML/CSS/JS): Refresh browser with `Cmd + Shift + R` (macOS) or `Ctrl + Shift + R` (Windows/Linux)
- **Node server changes** (`server.js`): Auto-restarts in dev mode (`npm run dev`)

## Features

- **Voice Conversation**: Hold-to-record voice input, receive AI-generated audio responses
- **Text Mode**: Type messages for text-based interaction
- **Multiple Personas**: Different donor profiles with unique personalities and preferences
- **Session Management**: Maintains conversation context throughout the pitch
- **Real-time Processing**: Integrated STT → LLM → TTS pipeline
- **Audio Cleanup**: Automatically manages audio file storage

## API Endpoints

### Flask API (`http://localhost:8080`)

- `POST /api/chat` - Main conversation endpoint
  - Accepts: `audio` (file), `session_id`, `case_study`
  - Returns: `transcript`, `reply` (text), `audio_url`
  
- `GET /api/audio/<session_id>` - Serve generated audio files

- `POST /api/reset/<session_id>` - Reset conversation history

### Node.js Routes (`http://localhost:3000`)

- `/` - Landing page
- `/case-studies.html` - Select donor persona
- `/preview.html` - View persona details
- `/simulation.html` - Interactive pitch simulation

## How It Works

1. **User records audio** by holding the record button
2. **Audio sent to Flask API** (`/api/chat`)
3. **Deepgram transcribes** the audio to text
4. **OpenAI generates response** based on donor persona and conversation history
5. **ElevenLabs synthesizes** the response into natural speech
6. **Audio returned to client** and played automatically
7. **Conversation context maintained** in server memory by session ID

## Troubleshooting

**Page not updating?**
- Hard refresh: `Cmd + Shift + R` (macOS) or `Ctrl + Shift + R` (Windows/Linux)
- Check that both servers are running
- Verify files are being served from correct directory

**"No audio file provided" error?**
- Check microphone permissions in browser
- Verify audio is being recorded (check browser console logs)
- Try a different browser (Chrome/Edge recommended)

**Audio not playing?**
- Check Flask server logs for TTS errors
- Verify `audio_out/` directory exists
- Check that audio file was created (look for file size in logs)
- Inspect browser console for audio loading errors

**API connection failed?**
- Verify Flask server is running on port 8080
- Check `.env` file has all three API keys
- Review Flask server terminal for error messages
- Ensure CORS is enabled (already configured in `api.py`)

**"Transcription failed" error?**
- Verify Deepgram API key is valid
- Check recording duration (must be > 500ms)
- Review audio format compatibility

**Server won't start?**
- **Node.js**: Check if port 3000 is in use
- **Flask**: Check if port 8080 is in use
- Verify all dependencies installed (`npm install` and `pip install -r requirements.txt`)
- Check for syntax errors in terminal output

## Future Enhancements

- [ ] Database integration (SQLite/PostgreSQL) for conversation history
- [ ] Additional donor personas (template2, template3)
- [ ] Analytics dashboard for pitch performance
- [ ] User accounts and session persistence
- [ ] Improve conversation flow
- [ ] Add decimal system for checkpoints

## License

ISC
