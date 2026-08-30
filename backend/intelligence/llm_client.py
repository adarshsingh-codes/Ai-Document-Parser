"""
Thin wrapper around the OpenAI client so intelligence modules never
import `openai` directly. This is the ONLY seam we need for mocking in
unit tests: pass a fake client into get_topics_and_subtopics(), or let
it default to a real OpenAI() client (reads OPENAI_API_KEY from env).
"""
import json
import os

from backend.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"  # cheap + fast; swap to gpt-4o for higher-quality topics later


class LLMError(Exception):
    """Raised when the LLM call fails or returns something we can't parse."""
    pass


def get_client():
    """Build a real OpenAI client. Kept as its own function so tests can
    monkeypatch/skip this entirely by injecting their own client instead."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMError(
            "OPENAI_API_KEY is not set. Add it to your .env file "
            "(see .env.example)."
        )
    return OpenAI(api_key=api_key)


def call_json_completion(
    client,
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
) -> dict:
    """Call the chat completion API and parse the response as JSON.

    `client` is injected (not constructed here) specifically so unit
    tests can pass a mock with a `.chat.completions.create(...)` method
    instead of hitting the real API.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as e:
        raise LLMError(f"OpenAI API call failed: {e}") from e

    try:
        raw_content = response.choices[0].message.content
    except (AttributeError, IndexError) as e:
        raise LLMError(f"Unexpected response shape from OpenAI: {e}") from e

    try:
        return json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error("LLM returned non-JSON content: %s", raw_content[:500])
        raise LLMError(f"LLM response was not valid JSON: {e}") from e
