import json
import google.generativeai as genai
from config import GOOGLE_API_KEY
from models import Verdict, Evidence

genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

def verify_claim(claim, search_results):

    evidence_text = "\n".join(r.get("snippet", "") for r in search_results)

    prompt = f"""
You are a fact checker.

Claim: {claim.text}

Evidence:
{evidence_text}

Return JSON:
{{
  "status": "Verified|False|Inaccurate|Unverifiable",
  "confidence": 0.0
}}
"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.replace("```json", "").replace("```", "")

        data = json.loads(raw)

        return Verdict(
            claim=claim,
            status=data.get("status", "Unverifiable"),
            corrected_fact=None,
            explanation="",
            evidence_used=[],
            confidence=float(data.get("confidence", 0.0)),
            source_agreement="N/A"
        )

    except Exception as e:
        print("VERIFY ERROR:", e)

        return Verdict(
            claim=claim,
            status="Unverifiable",
            corrected_fact=None,
            explanation="error",
            evidence_used=[],
            confidence=0.0,
            source_agreement="0/0"
        )