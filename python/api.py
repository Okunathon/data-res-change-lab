import os
try:
    import requests
except ModuleNotFoundError:
    raise SystemExit("Missing dependency: run 'python -m pip install requests' in your project's virtualenv")
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

# Load .env from project root
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

print(f"[Init] Loading .env from: {env_path}")
print(f"[Init] .env exists: {env_path.exists()}")

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# API Keys
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print(f"[Init] ELEVEN_API_KEY loaded: {bool(ELEVEN_API_KEY)}")
print(f"[Init] DEEPGRAM_API_KEY loaded: {bool(DEEPGRAM_API_KEY)}")
print(f"[Init] OPENAI_API_KEY loaded: {bool(OPENAI_API_KEY)}")

if not all([ELEVEN_API_KEY, DEEPGRAM_API_KEY, OPENAI_API_KEY]):
    raise RuntimeError("Missing API keys in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)

# Voice ID for ElevenLabs
CHATBOT_VOICE_ID = "Xb7hH8MSUJpSbSDYk0k2"  # Alice

# Create audio output directory in project root
audio_out_dir = project_root / "audio_out"
audio_out_dir.mkdir(exist_ok=True)
print(f"[Init] Audio output directory: {audio_out_dir}")

# Store conversation history per session (in-memory, simple approach)
conversations = {}


def transcribe_with_deepgram(audio_bytes: bytes, content_type: str) -> str:
    """Transcribe audio using Deepgram API"""
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": content_type,
    }
    
    params = {
        "model": "nova-2",
        "smart_format": "true",
        "punctuate": "true",
    }
    
    print("[STT] Sending audio to Deepgram...")
    resp = requests.post(
        "https://api.deepgram.com/v1/listen",
        headers=headers,
        params=params,
        data=audio_bytes,
    )
    
    if resp.status_code != 200:
        print("[STT] Error:", resp.text)
        return ""
    
    try:
        data = resp.json()
        transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"]
        print("[STT] Transcript:", transcript)
        return transcript.strip()
    except (KeyError, IndexError) as e:
        print("[STT] Error parsing response:", e)
        return ""


def get_chatbot_reply(conversation: list, user_text: str, case_study: str) -> str:
    """Get reply from OpenAI"""
    conversation.append({"role": "user", "content": user_text})
    
    print("[OpenAI] Generating reply...")
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation,
        max_tokens=256,
    )
    
    reply = completion.choices[0].message.content
    conversation.append({"role": "assistant", "content": reply})
    
    print("[OpenAI] Reply:", reply)
    return reply


def synthesize_with_elevenlabs(text: str, session_id: str) -> str:
    """Convert text to speech using ElevenLabs"""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{CHATBOT_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.85,
        },
    }
    
    print("[TTS] Requesting audio from ElevenLabs...")
    print(f"[TTS] Text to convert: {text[:100]}...")
    
    resp = requests.post(url, headers=headers, json=payload, stream=True)
    
    if resp.status_code != 200:
        print("[TTS] Error:", resp.text)
        return ""
    
    print(f"[TTS] Received audio response")
    print(f"[TTS] Content-Type: {resp.headers.get('content-type')}")
    
    # Use absolute path to project root's audio_out directory
    output_path = audio_out_dir / f"reply_{session_id}.mp3"
    
    # Delete old audio file if it exists
    if output_path.exists():
        os.remove(output_path)
        print(f"[TTS] Deleted old audio file: {output_path}")
    
    # Write the audio file in chunks to ensure complete write
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    
    file_size = os.path.getsize(output_path)
    print(f"[TTS] Saved audio to {output_path}")
    print(f"[TTS] File size on disk: {file_size} bytes")
    
    if file_size == 0:
        print("[TTS] ERROR: File is empty!")
        return ""
    
    return output_path


def get_system_prompt(case_study: str) -> str:
    """Get system prompt based on case study"""
    prompts = {
        "template1": (
            # ROLE & BACKGROUND
            "You are Dr. Jennifer Walker, a 55-year-old African American Biology Professor at the University of Hawaii, Honolulu. "
            "You hold a PhD in Genetics and Genomics from CalTech, an MS in Molecular Biology from Harvard, and a BS in Biology from UT Austin. "
            "You previously worked in private industry and hold lucrative gene patents. You're married to Fabio, a surf instructor, "
            "and have an adopted daughter from Somalia named Margaret who's in her mid-20s with an interest in art. "
            
            # PERSONALITY & BEHAVIOR
            "You're easily distracted because you manage many responsibilities. You're not open to casual chatter and will try to quickly end "
            "conversations that aren't interesting or important. You're often checking your phone. You appreciate professionalism and respect for your time. "
            "You have no patience for overly personal or casual approaches - maintain professional distance. "
            
            # INTERESTS & VALUES
            "You love animals (you have a Rottweiler), the outdoors, sailing, sea life, and surfing competitions. "
            "You dislike crowded places and soda. You've given to conservation and human rights causes in the past. "
            "Your Twitter likes show aquatic animals. "
            
            # CONVERSATION STYLE
            "Keep responses brief (1-2 sentences max) and business-like. Show mild impatience if the pitch lacks focus or wastes time. "
            "Ask direct, pointed questions about impact, budget, and outcomes. If someone tries to be overly casual or personal, become noticeably less engaged. "
            "Show interest when they mention conservation, marine life, human rights, or demonstrate clear metrics and professionalism. "
            
            # EVALUATION CRITERIA
            "You want to see: (1) Clear, measurable impact (especially conservation or human rights related), "
            "(2) Respect for your time with concise communication, (3) Professional tone, (4) Specific budget and outcomes, "
            "(5) Regular updates and accountability. "
            
            # RED FLAGS
            "You'll disengage if they: waste time with small talk, are vague about impact, lack financial clarity, "
            "try to be too familiar or casual, or don't have a clear ask. "
            
            # CONVERSATION PROGRESSION
            "Start by politely asking about their work and its purpose, while keeping it focused. "
            "If they're focused and professional, ask about measurable outcomes. "
            "Then probe on budget and sustainability. "
            "If they maintain professionalism and show clear impact, ask how you'd be kept informed. "
            "Show subtle interest if they mention marine conservation, animal welfare, or human rights."
        ),
        "template2": (
            "You are a [ROLE] interviewing a [SUBJECT]. "
            "Focus on [KEY TOPICS]. "
            "Be [TONE]. Keep responses [LENGTH]."
        ),
        "template3": (
            "You are a [ROLE] interviewing a [SUBJECT]. "
            "Ask about [KEY TOPICS]. "
            "Balance [ASPECT 1] with [ASPECT 2]. Keep responses [LENGTH]."
        ),
    }
    return prompts.get(case_study, prompts["template1"])


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle audio upload, transcription, LLM response, and TTS"""
    try:
        print("\n[API] Received chat request")
        
        # Get audio file and metadata
        if 'audio' not in request.files:
            print("[API] Error: No audio file in request")
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        session_id = request.form.get('session_id', 'default')
        case_study = request.form.get('case_study', 'saas')
        
        print(f"[API] Session: {session_id}, Case Study: {case_study}")
        print(f"[API] Audio file: {audio_file.filename}, Content-Type: {audio_file.content_type}")
        
        # Read audio bytes
        audio_bytes = audio_file.read()
        content_type = audio_file.content_type or "audio/webm"
        
        # If it's WebM, try to detect if it has codecs specified
        if 'webm' in content_type.lower():
            content_type = "audio/webm"
        elif 'mp4' in content_type.lower() or 'm4a' in content_type.lower():
            content_type = "audio/mp4"
        
        print(f"[API] Audio size: {len(audio_bytes)} bytes")
        print(f"[API] Content-Type being sent to Deepgram: {content_type}")
        
        # Initialize conversation if new session
        if session_id not in conversations:
            print(f"[API] Creating new conversation for session {session_id}")
            conversations[session_id] = [
                {"role": "system", "content": get_system_prompt(case_study)}
            ]
        
        # Step 1: Transcribe audio
        print("[API] Step 1: Transcribing audio...")
        transcript = transcribe_with_deepgram(audio_bytes, content_type)
        if not transcript:
            print("[API] Error: Transcription failed or empty")
            return jsonify({"error": "Transcription failed - no speech detected"}), 500
        
        print(f"[API] Transcript: {transcript}")
        
        # Step 2: Get LLM response
        print("[API] Step 2: Getting LLM response...")
        reply = get_chatbot_reply(conversations[session_id], transcript, case_study)
        print(f"[API] Reply: {reply}")
        
        # Step 3: Convert to speech
        print("[API] Step 3: Converting to speech...")
        # Create unique audio ID using timestamp to avoid caching issues
        audio_id = f"{session_id}_{int(time.time() * 1000)}"
        audio_path = synthesize_with_elevenlabs(reply, audio_id)
        if not audio_path:
            print("[API] Error: TTS failed")
            return jsonify({"error": "TTS failed"}), 500
        
        print(f"[API] Success! Audio saved to {audio_path}")
        
        # Return response
        return jsonify({
            "transcript": transcript,
            "reply": reply,
            "audio_url": f"/api/audio/{audio_id}"
        })
    
    except Exception as e:
        print(f"[API] EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat-text', methods=['POST'])
def chat_text():
    """Handle text input, LLM response, and optional TTS"""
    try:
        print("\n[API] Received text chat request")
        
        data = request.get_json()
        if not data or 'message' not in data:
            print("[API] Error: No message in request")
            return jsonify({"error": "No message provided"}), 400
        
        user_message = data['message'].strip()
        session_id = data.get('session_id', 'default')
        case_study = data.get('case_study', 'template1')
        with_audio = data.get('with_audio', True)  # Generate audio by default for text-to-text
        
        print(f"[API] Session: {session_id}, Case Study: {case_study}")
        print(f"[API] User message: {user_message[:100]}...")
        
        # Initialize conversation if new session
        if session_id not in conversations:
            print(f"[API] Creating new conversation for session {session_id}")
            conversations[session_id] = [
                {"role": "system", "content": get_system_prompt(case_study)}
            ]
        
        # Get LLM response
        print("[API] Getting LLM response...")
        reply = get_chatbot_reply(conversations[session_id], user_message, case_study)
        print(f"[API] Reply: {reply}")
        
        response_data = {
            "message": user_message,
            "reply": reply
        }
        
        # Generate audio if requested
        if with_audio:
            print("[API] Converting to speech...")
            audio_id = f"{session_id}_{int(time.time() * 1000)}"
            audio_path = synthesize_with_elevenlabs(reply, audio_id)
            if audio_path:
                response_data["audio_url"] = f"/api/audio/{audio_id}"
                print(f"[API] Audio generated: {audio_path}")
            else:
                print("[API] Warning: TTS failed, continuing without audio")
        
        print("[API] Text chat success!")
        return jsonify(response_data)
    
    except Exception as e:
        print(f"[API] EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/audio/<session_id>', methods=['GET'])
def get_audio(session_id):
    """Serve the generated audio file"""
    # Use absolute path to project root's audio_out directory
    audio_path = audio_out_dir / f"reply_{session_id}.mp3"
    print(f"[Audio] Request for session: {session_id}")
    print(f"[Audio] Looking for file: {audio_path}")
    print(f"[Audio] File exists: {audio_path.exists()}")
    
    if audio_path.exists():
        print(f"[Audio] Serving file: {audio_path}")
        print(f"[Audio] File size: {os.path.getsize(audio_path)} bytes")
        
        # Send file with proper headers
        response = send_file(
            str(audio_path), 
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name=f'reply_{session_id}.mp3'
        )
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'no-cache'
        return response
    
    print(f"[Audio] ERROR: File not found")
    # List files in audio_out directory for debugging
    if audio_out_dir.exists():
        files = os.listdir(audio_out_dir)
        print(f"[Audio] Files in audio_out: {files}")
    
    return jsonify({"error": "Audio file not found"}), 404


@app.route('/api/reset/<session_id>', methods=['POST'])
def reset_conversation(session_id):
    """Reset conversation history for a session"""
    if session_id in conversations:
        del conversations[session_id]
    return jsonify({"message": "Conversation reset"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
