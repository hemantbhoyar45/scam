from groq import Groq
import os

# User provided key
key = os.getenv("GROQ_API_KEY")

print(f"Testing Groq API with key: {key[:5]}...{key[-5:]}")

try:
    client = Groq(api_key=key)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Hello"}],
    )
    print("Success! Reply:", completion.choices[0].message.content)
except Exception as e:
    print("Error:", e)
