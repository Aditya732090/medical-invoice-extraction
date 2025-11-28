"""
llm_engine.py

Sends a base64-encoded image to an OpenAI LLM (vision-capable) and requests structured JSON.

NOTE:
- This file uses the `openai` Python package and the ChatCompletion endpoint in a general manner.
- Set environment variable OPENAI_API_KEY before running.
- Set OPENAI_MODEL to a vision-capable model you have access to (e.g. "gpt-4o-mini" or a vision-capable name).
"""

import os
import json
import logging
import re

try:
    import openai
except Exception as e:
    openai = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # change to actual vision-capable model if available


if openai and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

def _extract_json_from_text(text: str):
    """
    Try to safely extract the first JSON object from a free-text response.
    """
    try:
        # try direct parse first
        return json.loads(text)
    except Exception:
        # fallback: find first {...} block
        m = re.search(r'\{.*\}', text, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                raise RuntimeError("LLM returned malformed JSON; cannot parse.")
        raise RuntimeError("LLM did not return JSON.")

def extract_from_image_b64(image_b64: str, schema: dict, filename: str = "document"):
    """
    Send the base64 image in the prompt and request JSON respecting the provided schema.

    Returns: parsed Python dict (JSON structure).
    Raises RuntimeError on failure.
    """
    if openai is None:
        raise RuntimeError("openai package is not installed. Install 'openai' Python package.")
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY environment variable not set.")

    # Build the system + user prompts
    system_msg = (
        "You are a precise invoice parsing assistant. "
        "Return EXACTLY valid JSON, matching the schema provided. Do not provide extra commentary."
    )

    user_prompt = (
        "Schema (JSON):\n" + json.dumps(schema, indent=2) + "\n\n"
        f"Image filename: {filename}\n\n"
        "Below is a base64-encoded JPEG/PNG of a page of an invoice. "
        "Extract line items (description, amount), subtotals, and final total. "
        "For any missing field, return null or empty array as appropriate.\n\n"
        "BEGIN IMAGE BASE64\n"
        + image_b64 +
        "\nEND IMAGE BASE64\n\n"
        "IMPORTANT:\n"
        "- The output must be a single JSON object parsable by a JSON parser.\n"
        "- For bounding boxes use either null or an object {\"x\":int,\"y\":int,\"w\":int,\"h\":int}.\n"
        "- Provide a 'confidence' for each line item between 0 and 1.\n\n"
        "Return the JSON now."
    )

    try:
        # ChatCompletion call - depending on the installed package version you might use different call patterns.
        # We use openai.ChatCompletion.create for compatibility; adapt if your SDK is different.
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=1500
        )
        text = response['choices'][0]['message']['content']
        parsed = _extract_json_from_text(text)
        return parsed
    except Exception as e:
        logger.error("LLM call failed: %s", str(e))
        raise RuntimeError(f"LLM request failed: {e}")
