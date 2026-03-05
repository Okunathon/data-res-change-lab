# Import necessary packages
import os
import requests
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

MAX_SCORE = 32
GOOD_SCORE_THRESHOLD = 20

# Load .env from project root
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

print(f"[Init] Computed env_path: {env_path}")
print(f"[Init] Absolute path: {env_path.absolute()}")
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

# Dialogue state per session
dialog_states = {}

# Flat checkpoint definitions — no node logic, just behaviours and points
CHECKPOINTS = {
    # Opening
    1: {"requirement": "Thank the donors for meeting with you.", "points": 1},
    2: {"requirement": "Reference your prior relationship or last conversation.", "points": 2},

    # Cluster A: Framing choice
    3: {
        "requirement": "Lead with climate change research as mission-critical.",
        "points": 5,
        "mutually_exclusive_with": [4]
    },
    4: {
        "requirement": "Lead with general updates such as attendance or attractions.",
        "points": 0,
        "mutually_exclusive_with": [3]
    },

    # Institutional positioning
    5: {
        "requirement": "Position the aquarium as a serious research institution beyond being a children's attraction.",
        "points": 4
    },
    6: {"requirement": "Share measurable progress such as increased attendance or growth.", "points": 1},

    # Cluster B: Delivery style choice
    7: {
        "requirement": "Offer a concise verbal executive summary out of respect for their time.",
        "points": 4,
        "mutually_exclusive_with": [8]
    },
    8: {
        "requirement": "Hand over printed materials instead of summarizing.",
        "points": -2,
        "mutually_exclusive_with": [7]
    },

    # Program depth
    9: {
        "requirement": "Connect climate change research to hatchery or toxicology lab impact.",
        "points": 5
    },

    # Cluster C: Funding transition choice
    10: {
        "requirement": "Describe the program without clearly transitioning to funding.",
        "points": 0,
        "mutually_exclusive_with": [11]
    },
    11: {
        "requirement": "Transition explicitly toward investment in the program.",
        "points": 2,
        "mutually_exclusive_with": [10]
    },

    # Ask structure
    12: {
        "requirement": "State the total project cost of $50,000 and request a leadership gift of $25,000.",
        "points": 5,
        "mutually_exclusive_with": [13]
    },
    13: {
        "requirement": "Use presumptive or overly aggressive language when making the ask.",
        "points": -3,
        "mutually_exclusive_with": [12]
    },

    # Reinforcement
    14: {
        "requirement": "Reinforce that the donors' leadership is vital to the success of the project.",
        "points": 3
    }
}


def get_mood(off_task: bool, new_hits: list, penalty: int) -> str:
    if penalty > 0 or off_task:
        return "sad"
    if new_hits:
        return "happy"
    return "neutral"


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


def assess_checkpoints(conversation: list, completed: set, blocked: set) -> list:
    """
    Evaluate the full conversation and return a list of checkpoint keys
    (integers) that have been satisfied and are not yet completed.
    """
    remaining = {
        key: val for key, val in CHECKPOINTS.items()
        if key not in completed and key not in blocked
    }
    if not remaining:
        return []

    transcript = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in conversation
        if msg['role'] != 'system'
    )

    requirements_text = "\n".join(
        f"{k}: {v['requirement']}" for k, v in remaining.items()
    )

    prompt = f"""You are evaluating a fundraising pitch conversation. Based on the FULL conversation below, determine which behaviours the user (USER role) has clearly and explicitly demonstrated.

Conversation:
{transcript}

Behaviours to check:
{requirements_text}

Rules:
- Only mark a behaviour satisfied if the user clearly and explicitly demonstrates it
- Partial mentions or vague implications do not count
- Return ONLY a comma-separated list of satisfied behaviour keys (integers), or NONE if none are satisfied

Response:"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=30,
    )
    result = completion.choices[0].message.content.strip()
    print(f"[Checkpoint] Raw assessor response: {result}")

    if result.upper() == "NONE":
        return []

    found = [x.strip() for x in result.split(",")]
    return [int(x) for x in found if x.isdigit() and int(x) in remaining]


def assess_off_task(conversation: list) -> bool:
    """
    Returns True if the user's recent messages are going off-task.
    Only looks at the last 6 messages (3 exchanges) to detect recent drift.
    """
    recent = conversation[-3:]
    transcript = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in recent
        if msg['role'] != 'system'
    )

    prompt = f"""You are evaluating whether a fundraising pitch conversation has gone off-task.

The user is supposed to be pitching a marine aquarium's climate change research program to a potential donor. Off-task means: casual small talk, personal chat, unrelated topics, stalling, or anything not meaningfully related to the aquarium pitch or the funding ask.

Recent conversation:
{transcript}

Has the user's most recent message gone off-task or wasted the donor's time?
Answer only YES or NO."""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=5,
    )
    result = completion.choices[0].message.content.strip().upper()
    print(f"[OffTask] Assessor response: {result}")
    return result == "YES"


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

    output_path = audio_out_dir / f"reply_{session_id}.mp3"

    if output_path.exists():
        os.remove(output_path)
        print(f"[TTS] Deleted old audio file: {output_path}")

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


def payout_boost(score: int) -> int:
    if score >= MAX_SCORE:
        return 50_000
    if score >= GOOD_SCORE_THRESHOLD:
        return 5_000
    return 0


def should_end_conversation(state: dict) -> bool:
    return bool(state.get("conversation_closed"))


def funding_guidance(state: dict, new_hits: list) -> str | None:
    if state.get("ask_handled"):
        return None

    if 12 not in new_hits:
        return None

    state["ask_handled"] = True

    offer = payout_boost(state["score"])
    state["gift_offer"] = offer

    # Always allow 2 wrap-up turns after the ask
    state["wrapup_turns_left"] = 2

    if offer > 0:
        state["funding_committed"] = True
        return (
            "The user has made the funding ask. You are willing to commit funding now. "
            f"State your intent to give ${offer:,}, then request next steps: "
            "a 1-page summary, budget breakdown, timeline, and reporting cadence. "
            "Suggest scheduling a follow-up."
        )

    else:
        state["funding_committed"] = False
        return (
            "The user has made the funding ask. You are not ready to commit money today. "
            "Respond professionally and keep it open-ended: request a written proposal, "
            "specific metrics, budget detail, and suggest a follow-up meeting."
        )


def get_system_prompt(case_study: str) -> str:
    """Get system prompt based on case study"""
    prompts = {
        "template1": (
            "You are Dr. Jennifer Walker, a 55-year-old African American Biology Professor at the University of Hawaii, Honolulu. "
            "You hold a PhD in Genetics and Genomics from CalTech, an MS in Molecular Biology from Harvard, and a BS in Biology from UT Austin. "
            "You previously worked in private industry and hold lucrative gene patents. You're married to Fabio, a surf instructor, "
            "and have an adopted daughter from Somalia named Margaret who's in her mid-20s with an interest in art. "
            "You're easily distracted because you manage many responsibilities. You're not open to casual chatter and will try to quickly end "
            "conversations that aren't interesting or important. You're often checking your phone. You appreciate professionalism and respect for your time. "
            "You have no patience for overly personal or casual approaches - maintain professional distance. "
            "You love animals (you have a Rottweiler), the outdoors, sailing, sea life, and surfing competitions. "
            "You dislike crowded places and soda. You've given to conservation and human rights causes in the past. "
            "Your Twitter likes show aquatic animals. "
            "Keep responses brief (1-2 sentences max) and business-like. Show mild impatience if the pitch lacks focus or wastes time. "
            "Ask direct, pointed questions about impact, budget, and outcomes. If someone tries to be overly casual or personal, become noticeably less engaged. "
            "Show interest when they mention conservation, marine life, human rights, or demonstrate clear metrics and professionalism. "
            "You want to see: (1) Clear, measurable impact (especially conservation or human rights related), "
            "(2) Respect for your time with concise communication, (3) Professional tone, (4) Specific budget and outcomes, "
            "(5) Regular updates and accountability. "
            "You'll disengage if they: waste time with small talk, are vague about impact, lack financial clarity, "
            "try to be too familiar or casual, or don't have a clear ask. "
            "Start by politely asking about their work and its purpose, while keeping it focused. "
            "If they're focused and professional, ask about measurable outcomes. "
            "Then probe on budget and sustainability. "
            "If they maintain professionalism and show clear impact, ask how you'd be kept informed. "
            "Show subtle interest if they mention marine conservation, animal welfare, or human rights."
            "If the conversation strays too far away from the task at hand for too long, reply \"[DONE] We are done here.\" and NOTHING ELSE"
            "If the user inputs \"Fabio\" or \"surfing\" at any point, immediately reply \"[DONE] We are done here.\" and NOTHING ELSE"
        ),
        # ── Template 2 & 3 ──────────────────────────────────────────────────
        # Placeholder templates for future case study scenarios.
        # Replace bracketed tokens (e.g. [ROLE], [KEY TOPICS]) with real content.
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

        if 'audio' not in request.files:
            print("[API] Error: No audio file in request")
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audio']
        session_id = request.form.get('session_id', 'default')
        case_study = request.form.get('case_study', 'template1')

        print(f"[API] Session: {session_id}, Case Study: {case_study}")
        print(
            f"[API] Audio file: {audio_file.filename}, Content-Type: {audio_file.content_type}")

        audio_bytes = audio_file.read()
        content_type = audio_file.content_type or "audio/webm"

        if 'webm' in content_type.lower():
            content_type = "audio/webm"
        elif 'mp4' in content_type.lower() or 'm4a' in content_type.lower():
            content_type = "audio/mp4"

        print(f"[API] Audio size: {len(audio_bytes)} bytes")
        print(f"[API] Content-Type being sent to Deepgram: {content_type}")

        # Initialise dialogue state (do NOT reset every request)
        if session_id not in dialog_states:
            dialog_states[session_id] = {
                "score": 0,
                "completed": set(),
                "blocked": set(),
                "off_task_streak": 0,
                "ask_handled": False,
                "gift_offer": 0,
                "funding_committed": False,
                "wrapup_turns_left": 0,
                "conversation_closed": False,
            }

        # Initialise conversation history
        if session_id not in conversations:
            print(f"[API] Creating new conversation for session {session_id}")
            conversations[session_id] = [
                {"role": "system", "content": get_system_prompt(case_study)}
            ]

        state = dialog_states[session_id]

        # Step 1: Transcribe audio
        print("[API] Step 1: Transcribing audio...")
        transcript = transcribe_with_deepgram(audio_bytes, content_type)
        if not transcript:
            print("[API] Error: Transcription failed or empty")
            return jsonify({"error": "Transcription failed - no speech detected"}), 500
        print(f"[API] Transcript: {transcript}")

        # Hard-stop if conversation already closed
        if should_end_conversation(state):
            return jsonify({
                "transcript": transcript,
                "reply": "We’ve wrapped up. Please coordinate next steps with my office and send the written materials.",
                "audio_url": None,
                "score": state["score"],
                "max_score": MAX_SCORE,
                "boost": payout_boost(state["score"]),
                "completed": sorted(list(state["completed"])),
                "off_task": False,
                "off_task_streak": state.get("off_task_streak", 0),
                "penalty": 0,
                "warning": None,
                "conversation_complete": True,
                "gift_offer": state.get("gift_offer", 0),
            })

        # Append user message once
        conversations[session_id].append(
            {"role": "user", "content": transcript})

        # Step 2: Run assessments
        new_hits = assess_checkpoints(
            conversations[session_id],
            state["completed"],
            state["blocked"]
        )

        for key in new_hits:
            if key in state["completed"] or key in state["blocked"]:
                continue

            mex = set(CHECKPOINTS[key].get("mutually_exclusive_with", []))
            if mex & state["completed"]:
                state["blocked"].add(key)
                continue

            state["completed"].add(key)
            state["score"] += CHECKPOINTS[key]["points"]
            state["blocked"].update(mex)

        off_task = assess_off_task(conversations[session_id])
        penalty = 0
        warning = None

        if off_task:
            state["off_task_streak"] += 1
            if state["off_task_streak"] >= 2:
                penalty = 2 * (state["off_task_streak"] - 1)
                state["score"] = max(0, state["score"] - penalty)
                warning = f"You've gone off-task. -{penalty} points."
        else:
            state["off_task_streak"] = 0

        boost = payout_boost(state["score"])
        print(f"[Checkpoint] New hits: {new_hits}")
        print(
            f"[Score] {state['score']} / {MAX_SCORE} | Boost: ${boost} | Off-task streak: {state['off_task_streak']}")

        # Step 3: Get LLM response (with funding hook + wrap-up)
        print("[API] Step 3: Getting LLM response...")
        note = funding_guidance(state, new_hits)

        messages_for_llm = conversations[session_id]
        if note:
            messages_for_llm = conversations[session_id] + \
                [{"role": "system", "content": note}]

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_for_llm,
            max_tokens=256,
        )
        reply = completion.choices[0].message.content
        conversations[session_id].append(
            {"role": "assistant", "content": reply})
        print(f"[API] Reply: {reply}")

        # Wrap-up turn countdown + hard close
        if state.get("wrapup_turns_left", 0) > 0:
            state["wrapup_turns_left"] -= 1
            if state["wrapup_turns_left"] <= 0:
                state["conversation_closed"] = True
        # Step 4: Convert to speech
        print("[API] Step 4: Converting to speech...")
        audio_id = f"{session_id}_{int(time.time() * 1000)}"
        audio_path = synthesize_with_elevenlabs(reply, audio_id)
        if not audio_path:
            print("[API] Error: TTS failed")
            return jsonify({"error": "TTS failed"}), 500

        print(f"[API] Success! Audio saved to {audio_path}")

        return jsonify({
            "transcript": transcript,
            "reply": reply,
            "audio_url": f"/api/audio/{audio_id}",
            "score": state["score"],
            "max_score": MAX_SCORE,
            "boost": boost,
            "completed": sorted(list(state["completed"])),
            "off_task": off_task,
            "off_task_streak": state["off_task_streak"],
            "penalty": penalty,
            "warning": warning,
            "conversation_complete": state.get("conversation_closed", False),
            "gift_offer": state.get("gift_offer", 0),
        })

    except Exception as e:
        print(f"[API] EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/text', methods=['POST'])
def text_chat():
    """Handle text message input and return LLM response"""
    try:
        print("\n[API] Received text chat request")

        data = request.get_json()
        if not data or 'message' not in data:
            print("[API] Error: No message in request")
            return jsonify({"error": "No message provided"}), 400

        user_text = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        case_study = data.get('case_study', 'template1')

        print(f"[API] Session: {session_id}, Case Study: {case_study}")
        print(f"[API] User message: {user_text}")

        # Initialise dialogue state (do NOT reset every request)
        if session_id not in dialog_states:
            dialog_states[session_id] = {
                "score": 0,
                "completed": set(),
                "blocked": set(),
                "off_task_streak": 0,
                "ask_handled": False,
                "gift_offer": 0,
                "funding_committed": False,
                "wrapup_turns_left": 0,
                "conversation_closed": False,
            }

        # Initialise conversation history
        if session_id not in conversations:
            print(f"[API] Creating new conversation for session {session_id}")
            conversations[session_id] = [
                {"role": "system", "content": get_system_prompt(case_study)}
            ]

        state = dialog_states[session_id]

        # Hard-stop if conversation already closed
        if should_end_conversation(state):
            return jsonify({
                "message": user_text,
                "reply": "[DONE] We’ve wrapped up. Please coordinate next steps with my office and send the written materials.",
                "score": state["score"],
                "max_score": MAX_SCORE,
                "mood": "neutral",
                "boost": payout_boost(state["score"]),
                "completed": sorted(list(state["completed"])),
                "off_task": False,
                "off_task_streak": state.get("off_task_streak", 0),
                "penalty": 0,
                "warning": None,
                "conversation_complete": True,
                "gift_offer": state.get("gift_offer", 0),
            })

        # Append user message once
        conversations[session_id].append(
            {"role": "user", "content": user_text})

        # Run assessments
        new_hits = assess_checkpoints(
            conversations[session_id],
            state["completed"],
            state["blocked"]
        )

        for key in new_hits:
            if key in state["completed"] or key in state["blocked"]:
                continue

            mex = set(CHECKPOINTS[key].get("mutually_exclusive_with", []))
            if mex & state["completed"]:
                state["blocked"].add(key)
                continue

            state["completed"].add(key)
            state["score"] += CHECKPOINTS[key]["points"]
            state["blocked"].update(mex)

        off_task = assess_off_task(conversations[session_id])
        penalty = 0
        warning = None

        if off_task:
            state["off_task_streak"] += 1
            if state["off_task_streak"] >= 2:
                penalty = 2 * (state["off_task_streak"] - 1)
                state["score"] = max(0, state["score"] - penalty)
                warning = f"You've gone off-task. -{penalty} points."
        else:
            state["off_task_streak"] = 0

        boost = payout_boost(state["score"])
        print(f"[Checkpoint] New hits: {new_hits}")
        print(
            f"[Score] {state['score']} / {MAX_SCORE} | Boost: ${boost} | Off-task streak: {state['off_task_streak']}")

        # Generate reply (with funding hook + wrap-up)
        note = funding_guidance(state, new_hits)

        messages_for_llm = conversations[session_id]
        if note:
            messages_for_llm = conversations[session_id] + \
                [{"role": "system", "content": note}]

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_for_llm,
            max_tokens=256,
        )
        reply = completion.choices[0].message.content
        conversations[session_id].append(
            {"role": "assistant", "content": reply})

        # Wrap-up turn countdown + hard close
        if state.get("wrapup_turns_left", 0) > 0:
            state["wrapup_turns_left"] -= 1
            if state["wrapup_turns_left"] <= 0:
                state["conversation_closed"] = True

        mood = get_mood(off_task, new_hits, penalty)

        return jsonify({
            "message": user_text,
            "reply": reply,
            "score": state["score"],
            "max_score": MAX_SCORE,
            "mood": mood,
            "boost": boost,
            "completed": sorted(list(state["completed"])),
            "off_task": off_task,
            "off_task_streak": state["off_task_streak"],
            "penalty": penalty,
            "warning": warning,
            "conversation_complete": state.get("conversation_closed", False),
            "gift_offer": state.get("gift_offer", 0),
        })

    except Exception as e:
        print(f"[API] EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/audio/<session_id>', methods=['GET'])
def get_audio(session_id):
    """Serve the generated audio file"""
    audio_path = audio_out_dir / f"reply_{session_id}.mp3"

    print(f"[Audio] Request for session: {session_id}")
    print(f"[Audio] Looking for file: {audio_path}")
    print(f"[Audio] File exists: {audio_path.exists()}")

    if audio_path.exists():
        print(f"[Audio] Serving file: {audio_path}")
        print(f"[Audio] File size: {os.path.getsize(audio_path)} bytes")
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
    if audio_out_dir.exists():
        files = os.listdir(audio_out_dir)
        print(f"[Audio] Files in audio_out: {files}")
    return jsonify({"error": "Audio file not found"}), 404


@app.route('/api/reset/<session_id>', methods=['POST'])
def reset_conversation(session_id):
    """Reset conversation history and state for a session"""
    if session_id in conversations:
        del conversations[session_id]
    if session_id in dialog_states:
        del dialog_states[session_id]
    return jsonify({"message": "Conversation reset"})


@app.route('/api/final_review/<session_id>', methods=['GET'])
def final_review(session_id):

    if session_id not in conversations or session_id not in dialog_states:
        return jsonify({"error": "Session not found"}), 404

    conversation = conversations[session_id]
    state = dialog_states[session_id]

    transcript = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in conversation
        if m["role"] != "system"
    )

    checkpoints_hit = sorted(list(state["completed"]))
    score = state["score"]
# Coaching prompt — instructs the LLM to act as a pitch coach and
# provide specific, actionable feedback based on what actually happened
    prompt = f"""

You are a fundraising pitch coach.

The player attempted a donor pitch simulation.

Conversation transcript:
{transcript}

Checkpoints achieved:
{checkpoints_hit}

Score:
{score}

The checkpoints represent key fundraising behaviors like thanking the donor,
framing the mission, explaining impact, and making a funding ask.

Write a coaching assessment that includes:

1. Overall performance summary
2. What the user did well
3. What checkpoints they missed and why that matters
4. How to improve the pitch next time

Be concise but specific.
"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400
    )

    feedback = completion.choices[0].message.content

    return jsonify({
        "score": score,
        "checkpoints": checkpoints_hit,
        "feedback": feedback
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
 # ── Template 2 & 3 ──────────────────────────────────────────────────
    # Placeholder templates for future case study scenarios.
    # Replace bracketed tokens (e.g. [ROLE], [KEY TOPICS]) with real content.
