from fastapi import FastAPI, Request, Header, HTTPException, Response
from fastapi.responses import PlainTextResponse
from typing import Optional, List
import time
import requests 
import re
import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from prompts import SYSTEM_PROMPT

# =========================================================
# APP INIT
# =========================================================
app = FastAPI(title="Agentic Scam Honeypot API")

# =========================================================
# CONFIG
# =========================================================
API_KEY = "team_top_250_secret"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq Client
if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY not found in environment variables. AI responses will fail.")
    groq_client = None
else:
    groq_client = Groq(api_key=GROQ_API_KEY)

# =========================================================
# INTELLIGENCE STRUCTURE
# =========================================================
class Intelligence:
    def __init__(self):
        self.scamDetected = False
        self.upiIds: List[str] = []
        self.bankAccounts: List[str] = []
        self.phishingLinks: List[str] = []
        self.phoneNumbers: List[str] = []
        self.suspiciousKeywords: List[str] = []
        self.callback_sent = False

# =========================================================
# SIMPLE DETECTION & EXTRACTION
# =========================================================
def extract_intelligence(text: str, intel: Intelligence):
    if not text:
        return

    # UPI IDs
    intel.upiIds += re.findall(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}", text)

    # Phone numbers
    intel.phoneNumbers += re.findall(r"\b\d{10}\b", text)

    # URLs
    intel.phishingLinks += re.findall(r"https?://[^\s]+", text)

    # Keywords
    keywords = ["urgent", "verify", "blocked", "otp", "account", "refund", "pay", "money"]
    for k in keywords:
        if k in text.lower():
            intel.suspiciousKeywords.append(k)

    if intel.upiIds or intel.phishingLinks or intel.phoneNumbers or intel.suspiciousKeywords:
        intel.scamDetected = True

# =========================================================
# AI RESPONSE GENERATOR (GROQ)
# =========================================================
def generate_ai_reply(user_text: str) -> str:
    if not groq_client:
        return "System Error: AI backend not configured."

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7,
            max_tokens=150,
            top_p=1,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating AI reply: {e}")
        return "I'm having some network trouble, can you repeat that?"

# =========================================================
# SOURCE CODE ACCESS
# =========================================================
@app.get("/source_code", response_class=PlainTextResponse)
def get_source_code():
    with open(__file__, "r") as f:
        return f.read()

# =========================================================
# HEALTH CHECK
# =========================================================
@app.get("/")
def health():
    return {
        "status": "alive",
        "service": "Agentic Honeypot",
        "message": "API is reachable"
    }

# =========================================================
# HEAD FIX (REMOVES 405 ERROR)
# =========================================================
@app.head("/")
def head_root():
    return Response(status_code=200)

# =========================================================
# GUVI CALLBACK
# =========================================================

def send_guvi_callback(session_id: str, intel: Intelligence, msg_count: int):
    """
    Sends the mandatory final result callback to GUVI evaluation endpoint.
    """
    url = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    
    agent_notes = "Scam detected."
    if intel.suspiciousKeywords:
        agent_notes += f" Keywords found: {', '.join(intel.suspiciousKeywords)}."
    
    payload = {
        "sessionId": session_id,
        "scamDetected": intel.scamDetected,
        "totalMessagesExchanged": msg_count,
        "extractedIntelligence": {
            "bankAccounts": intel.bankAccounts,
            "upiIds": intel.upiIds,
            "phishingLinks": intel.phishingLinks,
            "phoneNumbers": intel.phoneNumbers,
            "suspiciousKeywords": intel.suspiciousKeywords
        },
        "agentNotes": agent_notes
    }

    try:
        # Using a short timeout to prevent hanging the main request
        # In a production app, use asyncio or a background task
        print(f"📡 Sending Callback for {session_id}...")
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print("✅ Callback Success")
        else:
            print(f"⚠️ Callback Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Callback Error: {e}")

# =========================================================
# GUVI API ENTRY POINT
# =========================================================
@app.post("/honey-pot-entry")
async def honey_pot_entry(
    request: Request,
    x_api_key: Optional[str] = Header(None)
):
    start_time = time.time()

    # --- API KEY VALIDATION ---
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # --- SAFE BODY PARSING ---
    try:
        raw_body = await request.body()
        body = json.loads(raw_body) if raw_body else {}
    except Exception as e:
        print(f"Body parsing error: {e}")
        body = {}

    if not isinstance(body, dict):
        body = {}

    # Parse Message
    message_data = body.get("message", {})
    if isinstance(message_data, dict):
        user_text = message_data.get("text", "")
    else:
        user_text = str(message_data) # Fallback if message is just a string
    
    if not user_text:
        user_text = "Hello" # Default fallback

    session_id = body.get("sessionId", "guvi-session")
    
    # Parse History for Count
    history = body.get("conversationHistory", [])
    total_messages = len(history) + 1 # +1 for the current message

    intel = Intelligence()
    extract_intelligence(str(user_text), intel)

    reply = generate_ai_reply(str(user_text))

    # --- SEND MANDATORY CALLBACK IF SCAM DETECTED ---
    if intel.scamDetected:
        # We assume the engagement is sufficient if we detected a scam.
        # Running synchronously here for simplicity as per requirements.
        send_guvi_callback(session_id, intel, total_messages)

    latency = round(time.time() - start_time, 3)

    # Simplified response as per Section 8 of the prompt
    return {
        "status": "success",
        "reply": reply
    }
