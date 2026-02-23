"""Generate images via the Gemini REST API.

Uses ``requests.post()`` directly instead of the ``google-generativeai`` SDK
so that a separate ``GEMINI_IMAGE_API_KEY`` / ``GEMINI_IMAGE_MODEL`` can be
used without conflicting with the global ``genai.configure()`` call used by
the text model.
"""

from __future__ import annotations

import base64
import os

import requests


def generate_image(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    timeout: int = 60,
) -> dict:
    """Generate an image from a text prompt using Gemini.

    Parameters
    ----------
    prompt : str
        Text description of the desired image.
    api_key : str, optional
        Gemini API key.  Falls back to ``GEMINI_IMAGE_API_KEY``,
        then ``GEMINI_API_KEY``.
    model : str, optional
        Model name.  Falls back to ``GEMINI_IMAGE_MODEL``,
        defaults to ``"gemini-2.0-flash-exp-image-generation"``.
    timeout : int
        Request timeout in seconds.

    Returns
    -------
    dict
        ``{"image_bytes": bytes | None, "mime_type": str, "error": str | None}``
    """
    key = (
        api_key
        or os.getenv("GEMINI_IMAGE_API_KEY")
        or os.getenv("GEMINI_API_KEY", "")
    )
    if not key:
        return {"image_bytes": None, "mime_type": "", "error": "No image API key configured"}

    model_name = model or os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-exp-image-generation")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={key}"
    )

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    try:
        resp = requests.post(url, json=body, timeout=timeout)
        if not resp.ok:
            return {
                "image_bytes": None,
                "mime_type": "",
                "error": f"API error {resp.status_code}: {resp.text[:300]}",
            }

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return {"image_bytes": None, "mime_type": "", "error": "No candidates returned"}

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            inline_data = part.get("inlineData") or part.get("inline_data")
            if inline_data:
                raw = base64.b64decode(inline_data["data"])
                mime = inline_data.get("mimeType") or inline_data.get("mime_type", "image/png")
                return {"image_bytes": raw, "mime_type": mime, "error": None}

        return {"image_bytes": None, "mime_type": "", "error": "No image data in response"}

    except requests.RequestException as exc:
        return {"image_bytes": None, "mime_type": "", "error": str(exc)}
