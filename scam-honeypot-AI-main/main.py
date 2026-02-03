from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import PlainTextResponse
from typing import Optional, List
import time
import re
import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from prompts import SYSTEM_PROMPT

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

    # UPI ID
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

    if intel.upiIds or intel.phishingLinks or intel.phoneNumbers or len(intel.suspiciousKeywords) > 0:
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
            stream=False,
            stop=None,
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
# HEALTH CHECK (IMPORTANT FOR GUVI)
# =========================================================
@app.get("/")
def health():
    return {
        "status": "alive",
        "service": "Agentic Honeypot",
        "message": "API is reachable"
    }


# =========================================================
# GUVI API ENTRY POINT (CRITICAL FIX)
# =========================================================
@app.post("/honey-pot-entry")
async def honey_pot_entry(
    request: Request,
    x_api_key: Optional[str] = Header(None)
):
    try:
        start_time = time.time()

        # --- API KEY VALIDATION ---
        if x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API Key")

        # --- SAFE BODY PARSING (GUVI sends NO body) ---
        try:
            body = await request.json()
        except Exception:
            body = {}

        # Handle case where body might be None (invalid JSON e.g. 'null')
        if body is None:
            body = {}

        user_text = body.get("message", "Hello, I received a call regarding my account.")
        session_id = body.get("sessionId", "guvi-session")

        intel = Intelligence()
        if user_text:
             extract_intelligence(str(user_text), intel) # Ensure string

        reply = generate_ai_reply(str(user_text) if user_text else "")

        latency = round(time.time() - start_time, 3)

        return {
            "status": "success",
            "sessionId": session_id,
            "scamDetected": intel.scamDetected,
            "reply": reply,
            "extractedIntelligence": {
                "upiIds": intel.upiIds,
                "phoneNumbers": intel.phoneNumbers,
                "phishingLinks": intel.phishingLinks,
                "keywords": intel.suspiciousKeywords
            },
            "latencySeconds": latency
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return {
            "status": "error",
            "message": str(e),
            "scamDetected": False,
            "reply": "System Error",
            "extractedIntelligence": {},
            "latencySeconds": 0
        }
