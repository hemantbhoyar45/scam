import os
import time
import json
import requests
from groq import Groq

# Configuration
API_URL = "http://127.0.0.1:8000/honey-pot-entry"
API_KEY = "team_top_250_secret"
# Use the same key we used for the server
import os
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("Error: GROQ_API_KEY not found.")
    exit(1)

spammer_client = Groq(api_key=GROQ_API_KEY)

# Scenarios
SCENARIOS = {
    "Level 1: Lottery Scam": {
        "system": "You are a persistent scammer trying to convince the user they won a $1M lottery. You need them to pay a small processing fee via UPI or Bank Transfer. Be pushy but realistic. Do not give up. Ask for payment details repeatedly.",
        "first_message": "CONGRATULATIONS! You have won $1,000,000 in the International Global Lottery! To claim your prize, reply immediately!"
    },
    "Level 2: Tech Support Scam": {
        "system": "You are a 'Microsoft Tech Support' agent. You detected a virus on the user's computer. You need them to download 'AnyDesk' or 'TeamViewer' so you can fix it. Be authoritative and urgent. Ask them to go to a specific URL to download it.",
        "first_message": "ALERT: Your Windows computer is infected with a critical virus. Microsoft has blocked your IP. Call us or reply immediately to unlock your device."
    },
    "Level 3: KYC Update Scam": {
        "system": "You are a bank official (SBI/HDFC). The user's account is blocked due to pending KYC. You need them to click a link or share OTP to unblock it. Threaten that the account will be frozen permanently if they don't act now.",
        "first_message": "Dear Customer, Your SBI account will be blocked today due to incomplete KYC. Please update your PAN immediately to avoid suspension."
    }
}

def generate_spammer_reply(history, system_prompt):
    messages = [{"role": "system", "content": system_prompt}] + history
    try:
        completion = spammer_client.chat.completions.create(
             model="llama-3.3-70b-versatile",
             messages=messages,
             temperature=0.7,
             max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"[Spammer AI Error]: {e}"

def run_level(level_name, config):
    print(f"\n{'='*60}")
    print(f"STARTING {level_name.upper()}")
    print(f"{'='*60}\n")
    
    chat_history = []
    session_id = f"sim-{int(time.time())}"
    
    # 1. Spammer sends first message
    spammer_msg = config["first_message"]
    print(f"🔴 SPAMMER: {spammer_msg}")
    chat_history.append({"role": "assistant", "content": spammer_msg}) # Spammer is assistant in its own context? No, let's keep it simple.
    
    # We maintain history for the Spammer (the AI we call directly).
    # Spammer Role = assistant
    # Honeypot Role = user (from Spammer's POV)
    spammer_history = [{"role": "assistant", "content": spammer_msg}]

    last_intel = {}

    for i in range(10): # 10 Turns
        # 2. Honeypot replies to Spammer's message
        try:
            payload = {
                "message": spammer_msg,
                "sessionId": session_id
            }
            headers = {"x-api-key": API_KEY}
            response = requests.post(API_URL, json=payload, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.text}")
                break
                
            data = response.json()
            honeypot_reply = data["reply"]
            last_intel = data["extractedIntelligence"]
            
            print(f"🟢 HONEYPOT: {honeypot_reply}")
            print("-" * 30)
            
            # Update Spammer's history with Honeypot's reply
            spammer_history.append({"role": "user", "content": honeypot_reply})
            
            # 3. Spammer generates next message based on Honeypot's reply
            spammer_msg = generate_spammer_reply(spammer_history, config["system"])
            print(f"🔴 SPAMMER: {spammer_msg}")
            
            # Update Spammer's history with its own new reply
            spammer_history.append({"role": "assistant", "content": spammer_msg})
            
            time.sleep(0.1) # Small delay for readability

        except Exception as e:
            print(f"❌ Error in loop: {e}")
            break

    print(f"\n{'-'*20} FINAL EXTRACTED INTELLIGENCE ({level_name}) {'-'*20}")
    print(json.dumps(last_intel, indent=4))
    print("="*60)

def main():
    print("🚀 Starting Auto-Chat Simulation...")
    
    for level, config in SCENARIOS.items():
        run_level(level, config)
        time.sleep(2)

    print("\n✅ Simulation Complete.")

if __name__ == "__main__":
    main()
