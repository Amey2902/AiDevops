import os
import requests
from typing import Optional, Dict, Any

class GeminiClient:
    """
    Lightweight, resilient Google Gemini API client.
    Supports gemini-2.5-flash and gemini-1.5-flash with graceful fallback
    to deterministic SRE reasoning if billing or quota limits are encountered.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-2.5-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    def generate_text(self, prompt: str, system_instruction: str = "") -> Optional[str]:
        if not self.is_configured():
            return None

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
            else:
                # Log status for diagnostic purposes
                print(f"[GeminiClient] API returned status {resp.status_code}")
        except Exception as e:
            print(f"[GeminiClient] Error calling Gemini: {e}")

        return None

