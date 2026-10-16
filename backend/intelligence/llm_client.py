"""
Thin wrapper around the Gemini client so intelligence modules never
import `google.genai` directly. This is the ONLY seam we need for mocking
in unit tests: pass a fake client into intelligence functions, or let it
default to a real Gemini client.
"""

import json
import os

from dotenv import load_dotenv

load_dotenv()

from backend.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "gemini-3.8-flash"


class LLMError(Exception):
    """Raised when the LLM call fails or returns something we can't parse."""
    pass


def get_client():
    """Build a real Gemini client."""
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise LLMError(
            "GEMINI_API_KEY is not set. Add it to your .env file "
            "(see .env.example)."
        )

    return genai.Client(api_key=api_key)


def call_json_completion(
    client,
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
) -> dict:
    """Call Gemini and parse the response as JSON.

    `client` is injected specifically so unit tests can pass a mock
    instead of making a real API call.
    """

    try:
        prompt = f"{system_prompt}\n\n{user_prompt}"

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "temperature": temperature,
                "response_mime_type": "application/json",
            },
        )
    except Exception as e:
        raise LLMError(f"Gemini API call failed: {e}") from e

    try:
        raw_content = response.text
    except AttributeError as e:
        raise LLMError(f"Unexpected response shape from Gemini: {e}") from e

    if isinstance(raw_content, dict):
        return raw_content

    if not isinstance(raw_content, str):
        raise LLMError(
            f"Unexpected response content type from Gemini: "
            f"{type(raw_content).__name__}"
        )

    try:
        return json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error(
            "LLM returned non-JSON content: %s",
            raw_content[:500]
        )
        raise LLMError(f"LLM response was not valid JSON: {e}") from e