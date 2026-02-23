"""Gen Gallery page -- infinite scroll feed of AI-generated Dash components.

Polls ``gen_store`` every 2 seconds for new entries and renders them
as styled DMC cards. Includes a local test panel for development
without Discord.
"""

import dash
from dash import callback, dcc, html, Input, Output, State, no_update
import dash_mantine_components as dmc

from dash_widgetbot.gen_store import gen_store, GenEntry
from dash_widgetbot.gen_renderer import render_gen_card

dash.register_page(
    __name__,
    path="/discord-to-dash",
    title="Gen Gallery",
    name="Gen Gallery",
)

layout = dmc.Container(
    [
        dcc.Store(id="gen-cursor", data=0),
        dcc.Interval(id="gen-poll", interval=2000),

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
    prevent_initial_call=False,
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
