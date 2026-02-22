"""Generate AI responses with embedded [ACTION:type:data] tags using Gemini."""

import os

from .action_parser import parse_actions

_model = None

SYSTEM_PROMPT = """\
You are a helpful Discord bot assistant embedded in a Dash web application.

When your response should trigger an action in the Dash app, include action tags
using this exact format: [ACTION:type:data]

Available actions:
- [ACTION:navigate:/page-path] -- navigate to a page in the Dash app
- [ACTION:notify:message text] -- show a notification in the Crate widget
- [ACTION:toggle:true] or [ACTION:toggle:false] -- open or close the chat widget
- [ACTION:hide:] -- hide the chat widget entirely
- [ACTION:show:] -- show a hidden chat widget
- [ACTION:open_url:https://example.com] -- open a URL in a new tab

Rules:
- Place action tags at the END of your message, after the human-readable text.
- You can include multiple actions in one response.
- Only use actions when they are relevant to the user's request.
- Always provide a helpful text response alongside any actions.
"""


def _get_model():
    """Lazy-load the Gemini model on first call."""
    global _model
    if _model is not None:
        return _model
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai is required for AI responses. "
            "Install it with: pip install google-generativeai>=0.8.0"
        )
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    genai.configure(api_key=api_key)
    _model = genai.GenerativeModel("gemini-2.0-flash")
    return _model


def generate_response(user_message, *, context=None, system_override=None):
    """Generate an AI response with optional action tags.

    Parameters
    ----------
    user_message : str
        The user's message.
    context : str, optional
        Extra context appended to the system prompt (e.g. available pages).
    system_override : str, optional
        Completely replace the default system prompt.

    Returns
    -------
    dict
        ``{text, actions, error}`` where actions is a list of parsed action dicts.
    """
    try:
        model = _get_model()
    except (ImportError, ValueError) as exc:
        return {"text": "", "actions": [], "error": str(exc)}

    system = system_override or SYSTEM_PROMPT
    if context:
        system += f"\n\nAdditional context:\n{context}"

    try:
        response = model.generate_content(
            [{"role": "user", "parts": [{"text": f"{system}\n\nUser: {user_message}"}]}]
        )
        text = response.text or ""
        return {
            "text": text,
            "actions": parse_actions(text),
            "error": None,
        }
    except Exception as exc:
        return {"text": "", "actions": [], "error": str(exc)}
