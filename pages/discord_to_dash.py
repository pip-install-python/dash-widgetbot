"""Gen Gallery page -- infinite scroll feed of AI-generated Dash components.

Polls ``gen_store`` every 2 seconds for new entries and renders them
as styled DMC cards. Includes a local test panel for development
without Discord.

Socket.IO path (additive, when [realtime] installed):
  gen_store.add() emits gen_result on /widgetbot-gen → DashSocketIO
  → _on_gen_result_sio callback → card prepended instantly (<100ms).
  dcc.Interval stays active as the zero-dependency fallback.
"""

import dash
from dash import callback, dcc, html, Input, Output, State, no_update
import dash_mantine_components as dmc

from dash_widgetbot.gen_store import gen_store, GenEntry
from dash_widgetbot.gen_renderer import render_gen_card
from dash_widgetbot._transport import has_socketio_packages

dash.register_page(
    __name__,
    path="/discord-to-dash",
    title="Gen Gallery",
    name="Gen Gallery",
)

# Conditionally include DashSocketIO for real-time push
_sio_layout_extra = []
if has_socketio_packages():
    from dash_socketio import DashSocketIO
    from dash_widgetbot._constants import SIO_NAMESPACE_GEN, SIO_EVENT_GEN_RESULT, SIO_EVENT_GEN_PROGRESS
    _sio_layout_extra = [
        DashSocketIO(
            id="_widgetbot-gen-sio",
            eventNames=[SIO_EVENT_GEN_RESULT, SIO_EVENT_GEN_PROGRESS],
            url=SIO_NAMESPACE_GEN,
        )
    ]

layout = dmc.Container(
    [
        dcc.Store(id="gen-cursor", data=0),
        dcc.Interval(id="gen-poll", interval=2000),
        *_sio_layout_extra,

        dmc.Space(h="xl"),
        dmc.Group(
            [
                dmc.Title("Gen Gallery", order=2),
                dmc.Badge(id="gen-count-badge", children="0 entries", variant="light", size="lg"),
                dmc.Badge(id="gen-poll-status", children="polling", color="teal", variant="dot", size="sm"),
            ],
            gap="md",
            mb="md",
        ),
        dmc.Text(
            "AI-generated Dash components from Discord /gen commands. "
            "Cards appear here in real-time as prompts are processed.",
            c="dimmed",
            mb="xl",
        ),

        # Local test panel
        dmc.Accordion(
            dmc.AccordionItem(
                [
                    dmc.AccordionControl("Test /gen locally"),
                    dmc.AccordionPanel(
                        dmc.Stack(
                            [
                                dmc.Text(
                                    "Generate content without Discord. Pick a prompt or type your own.",
                                    size="sm",
                                    c="dimmed",
                                ),
                                dmc.Group(
                                    [
                                        dmc.TextInput(
                                            id="gen-test-input",
                                            placeholder='e.g. "Explain Python decorators"',
                                            style={"flex": 1},
                                        ),
                                        dmc.Button(
                                            "Generate",
                                            id="gen-test-btn",
                                            color="indigo",
                                            loading=False,
                                        ),
                                    ],
                                ),
                                html.Div(id="gen-test-status"),
                            ],
                            gap="sm",
                        ),
                    ),
                ],
                value="test-gen",
            ),
            mb="xl",
        ),

        # Progress container -- animated cards for in-flight generations
        html.Div(id="gen-progress-container", children=[]),

        # Feed container -- cards accumulate here
        html.Div(id="gen-feed", children=[]),
    ],
    size="lg",
    py="xl",
)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@callback(
    Output("gen-feed", "children"),
    Output("gen-cursor", "data"),
    Output("gen-count-badge", "children"),
    Input("gen-poll", "n_intervals"),
    State("gen-cursor", "data"),
    State("gen-feed", "children"),
    prevent_initial_call=True,
)
def poll_gen_store(_n, cursor, existing_children):
    """Poll for new gen entries and prepend them to the feed."""
    cursor = cursor or 0
    new_entries = gen_store.get_since(cursor)
    total = gen_store.count()

    if not new_entries:
        return no_update, no_update, f"{total} entries"

    # Render new cards (newest first)
    new_cards = [render_gen_card(entry) for entry in reversed(new_entries)]

    # Prepend to existing children
    current = existing_children or []
    updated = new_cards + current

    return updated, total, f"{total} entries"


# Socket.IO real-time callback (additive — only registered when packages present)
if has_socketio_packages():
    @callback(
        Output("gen-feed", "children", allow_duplicate=True),
        Input("_widgetbot-gen-sio", "data"),
        State("gen-feed", "children"),
        prevent_initial_call=True,
    )
    def _on_gen_result_sio(data, current):
        """Prepend a card instantly when gen_store emits via Socket.IO."""
        if not data or data.get("event") != "gen_result":
            return no_update
        entry_data = data.get("data", {})

        # Reconstruct GenEntry from socket payload (image_bytes omitted;
        # use /api/gen/<id>/image URL if the rendered card needs the image)
        from dash_widgetbot.gen_schemas import GenResponse
        resp = None
        if entry_data.get("response"):
            try:
                resp = GenResponse(**entry_data["response"])
            except Exception:
                pass

        entry = GenEntry(
            id=entry_data.get("id", ""),
            prompt=entry_data.get("prompt", ""),
            discord_user=entry_data.get("discord_user", ""),
            timestamp=entry_data.get("timestamp", 0) or 0,
            error=entry_data.get("error"),
            response=resp,
        )
        card = render_gen_card(entry)
        return [card] + (current or [])

    @callback(
        Output("gen-progress-container", "children"),
        Input("_widgetbot-gen-sio", "data"),
        State("gen-progress-container", "children"),
        prevent_initial_call=True,
    )
    def _on_gen_progress_sio(data, current):
        """Show/update animated progress cards during AI generation."""
        if not data:
            return no_update

        event_name = data.get("event", "")
        event_data = data.get("data", {})

        # Handle gen_progress events
        if event_name == "gen_progress":
            task_id = event_data.get("task_id", "")
            phase = event_data.get("phase", "")
            percent = event_data.get("percent", 0)
            detail = event_data.get("detail", "")

            if not task_id:
                return no_update

            # Remove card on complete or error
            if phase in ("complete", "error"):
                cards = current or []
                return [c for c in cards if not _is_progress_card(c, task_id)]

            # Build/update progress card
            from dash_widgetbot.progress import _PHASE_LABELS
            label = _PHASE_LABELS.get(phase, phase)
            detail_text = f" ({detail})" if detail else ""

            card = dmc.Card(
                [
                    dmc.Group(
                        [
                            dmc.Loader(size="xs", type="dots"),
                            dmc.Text(f"{label}{detail_text}", size="sm", fw=500),
                            dmc.Badge(phase.replace("_", " "), variant="light", color="indigo", size="sm"),
                        ],
                        gap="sm",
                    ),
                    dmc.Space(h="xs"),
                    dmc.Progress(
                        value=percent,
                        animated=True,
                        color="indigo",
                        size="lg",
                    ),
                ],
                withBorder=True,
                shadow="sm",
                p="md",
                mb="md",
                id={"type": "gen-progress-card", "task_id": task_id},
                style={"borderLeft": "4px solid var(--mantine-color-indigo-6)"},
            )

            # Replace existing card for same task_id or prepend new one
            cards = current or []
            updated = False
            new_cards = []
            for c in cards:
                if _is_progress_card(c, task_id):
                    new_cards.append(card)
                    updated = True
                else:
                    new_cards.append(c)
            if not updated:
                new_cards.insert(0, card)
            return new_cards

        # Handle gen_result — clear any progress card for that task
        if event_name == "gen_result":
            cards = current or []
            # gen_result doesn't carry task_id, so clear all progress cards
            remaining = [c for c in cards if not _is_any_progress_card(c)]
            if remaining != cards:
                return remaining

        return no_update


def _is_progress_card(component, task_id):
    """Check if a Dash component is a progress card for a specific task_id."""
    try:
        cid = getattr(component, "id", None) or (component.get("props", {}).get("id") if isinstance(component, dict) else None)
        if isinstance(cid, dict):
            return cid.get("type") == "gen-progress-card" and cid.get("task_id") == task_id
    except Exception:
        pass
    return False


def _is_any_progress_card(component):
    """Check if a Dash component is any progress card."""
    try:
        cid = getattr(component, "id", None) or (component.get("props", {}).get("id") if isinstance(component, dict) else None)
        if isinstance(cid, dict):
            return cid.get("type") == "gen-progress-card"
    except Exception:
        pass
    return False


@callback(
    Output("gen-test-status", "children"),
    Input("gen-test-btn", "n_clicks"),
    State("gen-test-input", "value"),
    running=[(Output("gen-test-btn", "loading"), True, False)],
    prevent_initial_call=True,
)
def local_gen_test(_n, prompt):
    """Run /gen locally and push the result to gen_store."""
    if not prompt:
        return dmc.Badge("Enter a prompt first", color="yellow", variant="light", size="sm")

    from dash_widgetbot.gen_responder import generate_gen_response
    from dash_widgetbot.ai_image import generate_image

    result = generate_gen_response(prompt)

    if result["error"] or result["response"] is None:
        error_msg = result["error"] or "Unknown error"
        entry = GenEntry(
            prompt=prompt,
            discord_user="local",
            error=error_msg,
        )
        gen_store.add(entry)
        return dmc.Badge(f"Error: {error_msg[:60]}", color="red", variant="light", size="sm")

    gen_resp = result["response"]

    # Handle image generation
    image_bytes = None
    image_mime = ""
    if gen_resp.format == "image" and gen_resp.image:
        img_result = generate_image(gen_resp.image.prompt)
        if img_result["image_bytes"]:
            image_bytes = img_result["image_bytes"]
            image_mime = img_result["mime_type"]

    entry = GenEntry(
        prompt=prompt,
        response=gen_resp,
        image_bytes=image_bytes,
        image_mime=image_mime,
        discord_user="local",
    )
    gen_store.add(entry)

    return dmc.Badge(
        f"Generated: {gen_resp.format}",
        color="teal", variant="light", size="sm",
    )
