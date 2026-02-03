import os
import time
import json
import re
from typing import List, Optional
from groq import Groq

# =========================================================
# CONFIGURATION
# =========================================================
# Ensure you set this environment variable before running!

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    # Fallback for testing if env var not set (User provided key in prompt)
    import os
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ===================================GROQ_API_KEY======================
# PART 1: HONEYPOT AGENT LOGIC (From main.py)
# =========================================================
class Intelligence:
    def __init__(self):
        self.scamDetected = False
        self.upiIds: List[str] = []
        self.bankAccounts: List[str] = []
        self.phishingLinks: List[str] = []
        self.phoneNumbers: List[str] = []
        self.suspiciousKeywords: List[str] = []

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

# Honeypot Client
honeypot_client = Groq(api_key=GROQ_API_KEY)

HONEYPOT_SYSTEM_PROMPT = """
You are an advanced Agentic AI Honeypot designed for real-time scammer engagement.
Your role is to:
• Engage scammers naturally as a confused victim
• Extract scam intelligence (UPI, Bank, Links)
• Waste scammer resources
• NEVER reveal real personal info. Use fake placeholders.
• Speak comfortably but act slightly non-technical.
"""

def retry_api_call(func):
    def wrapper(*args, **kwargs):
        retries = 0
        while retries < 5:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate_limit" in error_str.lower():
                    wait_time = (2 ** retries) * 2  # 2, 4, 8, 16, 32 seconds
                    print(f"⚠️ Rate limit hit. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    return f"[Error]: {e}"
        return "[Error]: Max retries exceeded."
    return wrapper

@retry_api_call
def generate_honeypot_reply(user_text: str) -> str:
    completion = honeypot_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": HONEYPOT_SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        temperature=0.7,
        max_tokens=150
    )
    return completion.choices[0].message.content.strip()

# ...

# =========================================================
# PART 2: SPAMMER AGENT LOGIC (From auto_chat_runner.py)
# =========================================================
spammer_client = Groq(api_key=GROQ_API_KEY)

SCENARIOS = {
    "Level 1: Lottery Scam": {
        "system": "You are a persistent scammer. Convince the user they won $1M. Demand a $50 processing fee via UPI to 'scammer@upi'. Be pushy.",
        "first_message": "CONGRATULATIONS! You verify won $1,000,000! Reply now to claim!"
    },
    "Level 2: Tech Support Scam": {
        "system": "You are Microsoft Tech Support. The user has a virus. Tell them to download AnyDesk from 'http://bad-link.com' or call +91-9876543210. Be urgent.",
        "first_message": "ALERT: VIRUS DETECTED on your computer. Call Microsoft Support immediately."
    },
    "Level 3: KYC Update Scam": {
        "system": "You are a Bank Official. User account is blocked. Ask for OTP or PAN card update. Threaten account suspension.",
        "first_message": "Dear Customer, your Bank Account is blocked due to pending KYC. Update immediately."
    }
}
@retry_api_call
def generate_spammer_reply(history, system_prompt):
    messages = [{"role": "system", "content": system_prompt}] + history
    completion = spammer_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=150
    )
    return completion.choices[0].message.content


# =========================================================
# PART 3: INTERACTION LOOP
# =========================================================
def run_simulation():
    print("🚀 STARTING STANDALONE SIMULATION (NO SERVER REQUIRED)\n")
    
    for level_name, config in SCENARIOS.items():
        print(f"\n{'-'*60}")
        print(f"🎬 SCENARIO: {level_name}")
        print(f"{'-'*60}")
        
        # State
        spammer_history = []
        spammer_msg = config["first_message"]
        
        # Spammer speaks first
        print(f"🔴 SPAMMER: {spammer_msg}")
        spammer_history.append({"role": "assistant", "content": spammer_msg})

        # Track intelligence for this session
        intel = Intelligence()

        # Run 5 turns for demo (User asked for 10, but let's do 5 to keep it fast, or 10 if strict)
        # Let's do 7 turns for good measure.
        for i in range(1, 8):
            # 1. Honeypot processes Spammer's message
            extract_intelligence(spammer_msg, intel)
            honeypot_reply = generate_honeypot_reply(spammer_msg)
            
            print(f"🟢 HONEYPOINT: {honeypot_reply}")
            
            # Update Spammer's view of the world (Honeypot is the 'user' to the Spammer)
            spammer_history.append({"role": "user", "content": honeypot_reply})
            
            # 2. Spammer Replies
            spammer_msg = generate_spammer_reply(spammer_history, config["system"])
            print(f"🔴 SPAMMER: {spammer_msg}")
            spammer_history.append({"role": "assistant", "content": spammer_msg})
            
            time.sleep(3)

        # End of Level Report
        print(f"\n📊 EXTRACTED INTELLIGENCE ({level_name})")
        report = {
            "scamDetected": intel.scamDetected,
            "upiIds": intel.upiIds,
            "phoneNumbers": intel.phoneNumbers,
            "phishingLinks": intel.phishingLinks,
            "suspiciousKeywords": list(set(intel.suspiciousKeywords))
        }
        print(json.dumps(report, indent=4))
        print("="*60)

if __name__ == "__main__":
    run_simulation()
