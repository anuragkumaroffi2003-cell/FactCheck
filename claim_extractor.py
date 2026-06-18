import json
import google.generativeai as genai
from config import GOOGLE_API_KEY
from models import Claim

genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

def extract_claims(pdf_text: str):
    if not pdf_text:
        return []

    prompt = f"""
Extract factual claims as JSON list.

Return format:
[
  {{"text": "...", "context": "..."}}
]

TEXT:
{pdf_text[:8000]}
"""

    try:
        response = model.generate_content(prompt)

        raw = response.text.strip()

        print("\nRAW OUTPUT:\n", raw)

        raw = raw.replace("```json", "").replace("```", "")

        start = raw.find("[")
        end = raw.rfind("]") + 1

        if start == -1 or end == -1:
            return []

        data = json.loads(raw[start:end])

        return [
            Claim(
                id=i + 1,
                text=item["text"],
                context=item.get("context", "")
            )
            for i, item in enumerate(data)
        ]

    except Exception as e:
        print("ERROR:", e)
        return []