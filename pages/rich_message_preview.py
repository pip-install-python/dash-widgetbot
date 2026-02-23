"""Visual Builder for Discord Components V2 messages.

Two-panel layout: builder controls on the left, live Discord-styled preview
on the right. Uses dcc.Store for all state and a Drawer for editing.
"""

import json
import os

import dash
from dash import dcc, html, callback, ctx, Input, Output, State, no_update
import dash_mantine_components as dmc

from dash_widgetbot.webhook import send_webhook_message
from dash_widgetbot.components import (
    action_row,
    button,
    components_v2_message,
    container,
    file as file_component,
    media_gallery,
    section,
    select_option,
    separator,
    string_select as ss_builder,
    text_display,
    thumbnail,
    unfurl_media,
)

dash.register_page(
    __name__,
    path="/rich-message-preview",
    title="Message Builder",
    name="Message Builder",
)

WEBHOOK_URL_DEFAULT = os.getenv("DISCORD_WEBHOOK_URL", "")

# Discord dark-theme colors
DC_BG = "#313338"
DC_EMBED_BG = "#2b2d31"
DC_TEXT = "#dbdee1"
DC_DIVIDER = "#3f4147"
DC_MUTED = "#949ba4"

MAX_ITEMS = 10
MAX_GALLERY = 4
MAX_BUTTONS = 5
MAX_OPTIONS = 4

# ---------------------------------------------------------------------------
# Type metadata
# ---------------------------------------------------------------------------

TYPE_LABELS = {
    "text_display": "Text",
    "separator": "Separator",
    "section": "Section",
    "media_gallery": "Gallery",
    "file": "File",
    "action_row": "Actions",
    "string_select": "Select",
}

TYPE_COLORS = {
    "text_display": "blue",
    "separator": "gray",
    "section": "violet",
    "media_gallery": "green",
    "file": "orange",
    "action_row": "red",
    "string_select": "cyan",
}


# Components that require an application-owned webhook (bot webhook) to handle
# interactions — standard webhook URLs cannot send these.
INTERACTIVE_NOTE_TYPES = {"string_select"}

# ---------------------------------------------------------------------------
# Default items
# ---------------------------------------------------------------------------


def make_default_item(item_type, counter):
    """Return a new item dict with sensible defaults."""
    cid = counter + 1
    base = {"id": f"{item_type[:3]}_{cid}", "type": item_type}
    if item_type == "text_display":
        base["content"] = "Hello, world!"
    elif item_type == "separator":
        base["divider"] = True
        base["spacing"] = "small"
    elif item_type == "section":
        base["text_content"] = "Section body text"
        base["accessory_type"] = "none"
        base["accessory_url"] = ""
        base["accessory_description"] = ""
        base["accessory_label"] = ""
        base["accessory_style"] = "link"
        base["accessory_url_link"] = ""
    elif item_type == "media_gallery":
        base["media_items"] = [
            {"url": "https://picsum.photos/seed/demo/400/300", "description": ""}
        ]
    elif item_type == "file":
        base["url"] = "https://example.com/file.txt"
        base["spoiler"] = False
    elif item_type == "action_row":
        base["buttons"] = [
            {"label": "Click Me", "url": "https://example.com", "style": "link"}
        ]
    elif item_type == "string_select":
        base["placeholder"] = "Choose an option..."
        base["options"] = [
            {"label": "Option 1", "value": "opt1"},
            {"label": "Option 2", "value": "opt2"},
        ]
    return base


def get_item_summary(item):
    """Short display text for the component list."""
    t = item["type"]
    if t == "text_display":
        return item.get("content", "")[:40] or "Empty text"
    if t == "separator":
        sp = item.get("spacing", "small")
        return f"Divider ({sp})" if item.get("divider") else f"Spacer ({sp})"
    if t == "section":
        return item.get("text_content", "")[:30] or "Empty section"
    if t == "media_gallery":
        n = len(item.get("media_items", []))
        return f"{n} image{'s' if n != 1 else ''}"
    if t == "file":
        return item.get("url", "")[:30] or "No URL"
    if t == "action_row":
        n = len(item.get("buttons", []))
        return f"{n} button{'s' if n != 1 else ''}"
    if t == "string_select":
        n = len(item.get("options", []))
        return f"{n} option{'s' if n != 1 else ''}"
    return t


# ---------------------------------------------------------------------------
# Store -> Discord payload
# ---------------------------------------------------------------------------


def store_to_payload(data):
    """Convert builder store data to a Discord Components V2 payload."""
    items = data.get("items", [])
    color_hex = data.get("container_color", "#5865F2")
    try:
        accent = int(color_hex.lstrip("#"), 16)
    except (ValueError, AttributeError):
        accent = 0x5865F2

    children = []

    for item in items:
        t = item["type"]
        if t == "text_display":
            children.append(text_display(item.get("content", "")))
        elif t == "separator":
            sp = item.get("spacing")
            children.append(separator(divider=item.get("divider", True), spacing=sp))
        elif t == "section":
            acc_type = item.get("accessory_type", "none")
            if acc_type == "thumbnail":
                acc = thumbnail(
                    unfurl_media(item.get("accessory_url", "")),
                    description=item.get("accessory_description") or None,
                )
            elif acc_type == "button":
                acc = button(
                    item.get("accessory_label", "Button"),
                    url=item.get("accessory_url_link") or None,
                    style=item.get("accessory_style", "link"),
                )
            else:
                acc = None
            td = text_display(item.get("text_content", ""))
            if acc:
                children.append(section(acc, td))
            else:
                children.append(text_display(item.get("text_content", "")))
        elif t == "media_gallery":
            mg_items = []
            for mi in item.get("media_items", []):
                entry = {"media": unfurl_media(mi.get("url", ""))}
                if mi.get("description"):
                    entry["description"] = mi["description"]
                mg_items.append(entry)
            if mg_items:
                children.append(media_gallery(*mg_items))
        elif t == "file":
            children.append(
                file_component(item.get("url", ""), spoiler=item.get("spoiler", False))
            )
        elif t == "action_row":
            btns = []
            for b in item.get("buttons", []):
                btns.append(
                    button(
                        b.get("label", ""),
                        url=b.get("url", ""),
                        style=b.get("style", "link"),
                    )
                )
            if btns:
                children.append(action_row(*btns))
        elif t == "string_select":
            opts = [
                select_option(o["label"], o["value"])
                for o in item.get("options", [])
                if o.get("label") and o.get("value")
            ]
            if opts:
                children.append(
                    action_row(
                        ss_builder(
                            "custom_select",
                            opts,
                            placeholder=item.get("placeholder", ""),
                        )
                    )
                )
        # Modal-only types (file_upload, radio_group, checkbox_group) are
        # intentionally skipped — they cannot appear in webhook messages.
        # Use modal_response() in bot interaction handlers instead.

    if not children:
        children.append(text_display("Empty message"))

    return {"message": components_v2_message(container(*children, color=accent))}


# ---------------------------------------------------------------------------
# Preview rendering (Discord dark-theme DMC)
# ---------------------------------------------------------------------------


def render_preview_component(item):
    """Map a single store item to DMC components styled like Discord."""
    t = item["type"]

    if t == "text_display":
        return dcc.Markdown(
            item.get("content", ""),
            style={"color": DC_TEXT, "margin": 0, "fontSize": 14},
        )

    if t == "separator":
        if item.get("divider", True):
            margin = "16px 0" if item.get("spacing") == "large" else "8px 0"
            return html.Hr(
                style={
                    "borderColor": DC_DIVIDER,
                    "margin": margin,
                    "borderWidth": "1px",
                    "borderStyle": "solid",
                }
            )
        spacing = 16 if item.get("spacing") == "large" else 8
        return html.Div(style={"height": spacing})

    if t == "section":
        text_part = dcc.Markdown(
            item.get("text_content", ""),
            style={"color": DC_TEXT, "fontSize": 14, "flex": "1"},
        )
        acc_type = item.get("accessory_type", "none")
        if acc_type == "thumbnail" and item.get("accessory_url"):
            accessory = dmc.Image(
                src=item["accessory_url"], w=80, h=80, radius="sm",
                style={"flexShrink": 0},
            )
        elif acc_type == "button":
            accessory = dmc.Button(
                item.get("accessory_label", "Button"),
                variant="light", color="gray", size="xs", style={"flexShrink": 0},
            )
        else:
            accessory = None
        children = [text_part]
        if accessory:
            children.append(accessory)
        return html.Div(
            children,
            style={
                "display": "flex", "alignItems": "center",
                "justifyContent": "space-between", "gap": 12,
            },
        )

    if t == "media_gallery":
        images = [
            dmc.Image(src=mi["url"], radius="sm", style={"maxHeight": 200})
            for mi in item.get("media_items", []) if mi.get("url")
        ]
        if not images:
            return html.Div("No images", style={"color": DC_MUTED, "fontSize": 12})
        return dmc.SimpleGrid(images, cols=min(len(images), 2), spacing="xs")

    if t == "file":
        return dmc.Paper(
            dmc.Group(
                [
                    dmc.ThemeIcon(
                        dmc.Text("F", fw=700, size="xs"),
                        variant="light", color="gray", size="sm",
                    ),
                    dmc.Text(
                        item.get("url", "file")[:50], size="sm", c=DC_TEXT,
                        truncate="end",
                    ),
                ],
                gap="xs",
            ),
            bg="#232428", radius="sm", p="xs",
        )

    if t == "action_row":
        btns = [
            dmc.Button(
                b.get("label", "Button"),
                variant="light", color="gray", size="xs",
                leftSection=dmc.Text("\u2197", size="xs")
                if b.get("style") == "link" else None,
            )
            for b in item.get("buttons", [])
        ]
        return dmc.Group(btns, gap="xs")

    if t == "string_select":
        opts = item.get("options", [])
        return dmc.Select(
            data=[{"label": o["label"], "value": o["value"]} for o in opts],
            placeholder=item.get("placeholder", "Select..."),
            size="sm",
            styles={
                "input": {"backgroundColor": "#1e1f22", "color": DC_TEXT,
                          "borderColor": DC_DIVIDER},
                "dropdown": {"backgroundColor": "#2b2d31"},
            },
        )

    return html.Div(f"Unknown: {t}", style={"color": DC_MUTED})


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


def _palette_card(label, icon_text, color, btn_id):
    return dmc.Paper(
        dmc.UnstyledButton(
            dmc.Stack(
                [
                    dmc.ThemeIcon(
                        dmc.Text(icon_text, fw=700, size="xs"),
                        variant="light", color=color, size="lg",
                    ),
                    dmc.Text(label, size="xs", fw=500, ta="center"),
                ],
                align="center", gap=4,
            ),
            id=btn_id, style={"width": "100%", "padding": 8},
        ),
        withBorder=True, radius="sm", p=0,
    )


def _editor_section(section_id, title, children):
    return html.Div(
        [dmc.Text(title, fw=600, size="sm", mb="xs")] + children,
        id=section_id, style={"display": "none"},
    )


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

layout = dmc.Container(
    [
        dmc.Space(h="md"),
        dmc.Title("Components V2 Builder", order=2, mb="xs"),
        dmc.Text(
            "Visually compose Discord messages, preview them live, then send via webhook.",
            c="dimmed", mb="md", size="sm",
        ),
        # Stores
        dcc.Store(id="bld-tree", data={"container_color": "#5865F2", "items": []}),
        dcc.Store(id="bld-editing", data=None),
        dcc.Store(id="bld-counter", data=0),
        dmc.Grid(
            [
                # ============== LEFT: Builder ==============
                dmc.GridCol(
                    dmc.Stack(
                        [
                            # Container settings
                            dmc.Paper(
                                [
                                    dmc.Text("Container", fw=600, size="sm", mb="xs"),
                                    dmc.ColorInput(
                                        id="bld-container-color",
                                        label="Accent color", value="#5865F2", size="xs",
                                    ),
                                ],
                                withBorder=True, p="sm", radius="sm",
                            ),
                            # Component palette
                            dmc.Paper(
                                [
                                    dmc.Text("Add Component", fw=600, size="sm", mb="xs"),
                                    dmc.SimpleGrid(
                                        [
                                            _palette_card("Text", "T", "blue", "bld-add-text"),
                                            _palette_card("Separator", "\u2014", "gray", "bld-add-separator"),
                                            _palette_card("Section", "S", "violet", "bld-add-section"),
                                            _palette_card("Gallery", "G", "green", "bld-add-gallery"),
                                            _palette_card("File", "F", "orange", "bld-add-file"),
                                            _palette_card("Actions", "A", "red", "bld-add-action-row"),
                                            _palette_card("Select", "V", "cyan", "bld-add-select"),
                                        ],
                                        cols=4, spacing="xs",
                                    ),
                                    dmc.Text(
                                        "Modal components (Radio, Checkbox, Upload) can only be "
                                        "used in bot interaction modals via modal_response().",
                                        c="dimmed", size="xs", mt="xs",
                                    ),
                                    # Hidden placeholders for removed palette buttons
                                    # (Dash requires all callback Input IDs to exist)
                                    html.Div(
                                        [
                                            html.Div(id="bld-add-upload"),
                                            html.Div(id="bld-add-radio"),
                                            html.Div(id="bld-add-checkbox"),
                                        ],
                                        style={"display": "none"},
                                    ),
                                    html.Div(id="bld-palette-limit", style={"marginTop": 4}),
                                ],
                                withBorder=True, p="sm", radius="sm",
                            ),
                            # Component list
                            dmc.Paper(
                                [
                                    dmc.Text("Components", fw=600, size="sm", mb="xs"),
                                    dmc.Select(
                                        id="bld-item-select", label="Select to edit",
                                        data=[], value=None, size="xs", clearable=True,
                                        mb="xs",
                                    ),
                                    dmc.Group(
                                        [
                                            dmc.Button("\u2191", id="bld-move-up", size="xs", variant="light", color="gray"),
                                            dmc.Button("\u2193", id="bld-move-down", size="xs", variant="light", color="gray"),
                                            dmc.Button("Delete", id="bld-delete-btn", size="xs", variant="light", color="red"),
                                        ],
                                        gap="xs",
                                    ),
                                    html.Div(id="bld-component-list", style={"marginTop": 8}),
                                ],
                                withBorder=True, p="sm", radius="sm",
                            ),
                        ],
                        gap="sm",
                    ),
                    span=5,
                ),
                # ============== RIGHT: Preview ==============
                dmc.GridCol(
                    dmc.Stack(
                        [
                            dmc.Paper(
                                [
                                    dmc.Text("Discord Preview", fw=600, size="sm", mb="xs"),
                                    html.Div(
                                        id="bld-preview-area",
                                        style={
                                            "backgroundColor": DC_BG, "borderRadius": 8,
                                            "padding": 16, "minHeight": 100,
                                        },
                                    ),
                                ],
                                withBorder=True, p="sm", radius="sm",
                            ),
                            dmc.Paper(
                                [
                                    dmc.Text("JSON Payload", fw=600, size="sm", mb="xs"),
                                    dmc.Code(
                                        id="bld-json-output",
                                        children="Add components to see the payload.",
                                        block=True,
                                        style={"maxHeight": 300, "overflow": "auto"},
                                    ),
                                ],
                                withBorder=True, p="sm", radius="sm",
                            ),
                            dmc.Paper(
                                [
                                    dmc.Text("Send to Discord", fw=600, size="sm", mb="xs"),
                                    dmc.TextInput(
                                        id="bld-webhook-url", label="Webhook URL",
                                        placeholder="https://discord.com/api/webhooks/...",
                                        value=WEBHOOK_URL_DEFAULT, size="xs", mb="xs",
                                    ),
                                    dmc.Grid(
                                        [
                                            dmc.GridCol(dmc.TextInput(
                                                id="bld-username", label="Username",
                                                placeholder="Optional", size="xs",
                                            ), span=6),
                                            dmc.GridCol(dmc.TextInput(
                                                id="bld-avatar-url", label="Avatar URL",
                                                placeholder="Optional", size="xs",
                                            ), span=6),
                                        ],
                                        mb="xs",
                                    ),
                                    html.Div(id="bld-send-note"),
                                    dmc.Group(
                                        [
                                            dmc.Button("Send", id="bld-send-btn", size="xs", color="green"),
                                            html.Div(id="bld-send-result"),
                                        ],
                                        gap="xs",
                                    ),
                                ],
                                withBorder=True, p="sm", radius="sm",
                            ),
                        ],
                        gap="sm",
                    ),
                    span=7,
                ),
            ],
            gutter="md",
        ),
        # ============== EDITOR DRAWER ==============
        dmc.Drawer(
            id="bld-editor-drawer",
            title="Edit Component",
            position="right", size="md",
            children=[
                dmc.Stack(
                    [
                        _editor_section("bld-sec-text", "Text Display", [
                            dmc.Textarea(
                                id="bld-ed-content", label="Content (markdown)",
                                placeholder="# Heading\nBody text...",
                                minRows=4, autosize=True,
                            ),
                        ]),
                        _editor_section("bld-sec-separator", "Separator", [
                            dmc.Switch(id="bld-ed-divider", label="Show divider line", checked=True, mb="xs"),
                            dmc.SegmentedControl(
                                id="bld-ed-spacing", data=["small", "large"], value="small",
                            ),
                        ]),
                        _editor_section("bld-sec-section", "Section", [
                            dmc.Textarea(
                                id="bld-ed-section-text", label="Text content (markdown)",
                                placeholder="Body text...", minRows=3, autosize=True, mb="xs",
                            ),
                            dmc.Select(
                                id="bld-ed-accessory-type", label="Accessory",
                                data=[
                                    {"label": "None", "value": "none"},
                                    {"label": "Thumbnail", "value": "thumbnail"},
                                    {"label": "Button", "value": "button"},
                                ],
                                value="none", size="xs", mb="xs",
                            ),
                            dmc.TextInput(id="bld-ed-acc-url", label="Thumbnail URL", size="xs", mb="xs"),
                            dmc.TextInput(id="bld-ed-acc-desc", label="Thumbnail description", size="xs", mb="xs"),
                            dmc.TextInput(id="bld-ed-acc-label", label="Button label", size="xs", mb="xs"),
                            dmc.TextInput(id="bld-ed-acc-url-link", label="Button URL", size="xs", mb="xs"),
                        ]),
                        _editor_section("bld-sec-gallery", "Media Gallery", [
                            *[
                                html.Div(
                                    [
                                        dmc.TextInput(id=f"bld-ed-mg-url-{i}", label=f"Image {i+1} URL", size="xs", mb=4),
                                        dmc.TextInput(id=f"bld-ed-mg-desc-{i}", label="Description", size="xs", mb="xs"),
                                    ],
                                    id=f"bld-mg-slot-{i}",
                                    style={"display": "none"} if i > 0 else {},
                                )
                                for i in range(MAX_GALLERY)
                            ],
                            dmc.Group([
                                dmc.Button("+ Image", id="bld-add-mg-item", size="xs", variant="light"),
                                dmc.Button("- Image", id="bld-rm-mg-item", size="xs", variant="light", color="red"),
                            ], gap="xs", mt="xs"),
                            dcc.Store(id="bld-mg-count", data=1),
                        ]),
                        _editor_section("bld-sec-file", "File", [
                            dmc.TextInput(id="bld-ed-file-url", label="File URL", size="xs", mb="xs"),
                            dmc.Switch(id="bld-ed-file-spoiler", label="Spoiler", checked=False),
                        ]),
                        _editor_section("bld-sec-action", "Action Row", [
                            *[
                                html.Div(
                                    [
                                        dmc.TextInput(id=f"bld-ed-btn-label-{i}", label=f"Button {i+1} label", size="xs", mb=4),
                                        dmc.TextInput(id=f"bld-ed-btn-url-{i}", label="URL", size="xs", mb="xs"),
                                    ],
                                    id=f"bld-btn-slot-{i}",
                                    style={"display": "none"} if i > 0 else {},
                                )
                                for i in range(MAX_BUTTONS)
                            ],
                            dmc.Group([
                                dmc.Button("+ Button", id="bld-add-ar-btn", size="xs", variant="light"),
                                dmc.Button("- Button", id="bld-rm-ar-btn", size="xs", variant="light", color="red"),
                            ], gap="xs", mt="xs"),
                            dcc.Store(id="bld-ar-count", data=1),
                        ]),
                        _editor_section("bld-sec-select", "String Select", [
                            dmc.TextInput(
                                id="bld-ed-select-placeholder",
                                label="Placeholder text", size="xs", mb="xs",
                            ),
                        ]),
                        _editor_section("bld-sec-upload", "File Upload", [
                            dmc.TextInput(
                                id="bld-ed-upload-label",
                                label="Upload label", size="xs", mb="xs",
                            ),
                        ]),
                        # Shared options editor (for select, radio, checkbox)
                        _editor_section("bld-sec-options", "Options", [
                            *[
                                html.Div(
                                    [
                                        dmc.TextInput(id=f"bld-ed-opt-label-{i}", label=f"Option {i+1} label", size="xs", mb=4),
                                        dmc.TextInput(id=f"bld-ed-opt-value-{i}", label="Value", size="xs", mb="xs"),
                                    ],
                                    id=f"bld-opt-slot-{i}",
                                    style={"display": "none"} if i > 0 else {},
                                )
                                for i in range(MAX_OPTIONS)
                            ],
                            dmc.Group([
                                dmc.Button("+ Option", id="bld-add-opt-item", size="xs", variant="light"),
                                dmc.Button("- Option", id="bld-rm-opt-item", size="xs", variant="light", color="red"),
                            ], gap="xs", mt="xs"),
                            dcc.Store(id="bld-opt-count", data=1),
                        ]),
                        dmc.Button("Save", id="bld-save-btn", fullWidth=True, mt="md"),
                    ],
                    gap="sm",
                ),
            ],
        ),
        dmc.Space(h="xl"),
    ],
    size="xl",
    py="md",
)


# ---------------------------------------------------------------------------
# CB1: Add component
# ---------------------------------------------------------------------------

@callback(
    Output("bld-tree", "data", allow_duplicate=True),
    Output("bld-counter", "data", allow_duplicate=True),
    Input("bld-add-text", "n_clicks"),
    Input("bld-add-separator", "n_clicks"),
    Input("bld-add-section", "n_clicks"),
    Input("bld-add-gallery", "n_clicks"),
    Input("bld-add-file", "n_clicks"),
    Input("bld-add-action-row", "n_clicks"),
    Input("bld-add-select", "n_clicks"),
    Input("bld-add-upload", "n_clicks"),
    Input("bld-add-radio", "n_clicks"),
    Input("bld-add-checkbox", "n_clicks"),
    State("bld-tree", "data"),
    State("bld-counter", "data"),
    prevent_initial_call=True,
)
def add_component(*args):
    trigger = ctx.triggered_id
    if not trigger:
        return no_update, no_update

    type_map = {
        "bld-add-text": "text_display",
        "bld-add-separator": "separator",
        "bld-add-section": "section",
        "bld-add-gallery": "media_gallery",
        "bld-add-file": "file",
        "bld-add-action-row": "action_row",
        "bld-add-select": "string_select",
        "bld-add-upload": "file_upload",
        "bld-add-radio": "radio_group",
        "bld-add-checkbox": "checkbox_group",
    }
    item_type = type_map.get(trigger)
    if not item_type:
        return no_update, no_update

    tree = args[10] or {"container_color": "#5865F2", "items": []}
    counter = args[11] or 0

    if len(tree["items"]) >= MAX_ITEMS:
        return no_update, no_update

    new_item = make_default_item(item_type, counter)
    tree["items"].append(new_item)
    return tree, counter + 1


# ---------------------------------------------------------------------------
# CB2: Delete component
# ---------------------------------------------------------------------------

@callback(
    Output("bld-tree", "data", allow_duplicate=True),
    Output("bld-editing", "data", allow_duplicate=True),
    Output("bld-editor-drawer", "opened", allow_duplicate=True),
    Output("bld-item-select", "value", allow_duplicate=True),
    Input("bld-delete-btn", "n_clicks"),
    State("bld-tree", "data"),
    State("bld-item-select", "value"),
    prevent_initial_call=True,
)
def delete_component(_n, tree, selected_id):
    if not selected_id or not tree:
        return no_update, no_update, no_update, no_update
    tree["items"] = [it for it in tree["items"] if it["id"] != selected_id]
    return tree, None, False, None


# ---------------------------------------------------------------------------
# CB3: Move component
# ---------------------------------------------------------------------------

@callback(
    Output("bld-tree", "data", allow_duplicate=True),
    Input("bld-move-up", "n_clicks"),
    Input("bld-move-down", "n_clicks"),
    State("bld-tree", "data"),
    State("bld-item-select", "value"),
    prevent_initial_call=True,
)
def move_component(_up, _down, tree, selected_id):
    if not selected_id or not tree:
        return no_update
    trigger = ctx.triggered_id
    items = tree["items"]
    idx = next((i for i, it in enumerate(items) if it["id"] == selected_id), None)
    if idx is None:
        return no_update
    if trigger == "bld-move-up" and idx > 0:
        items[idx], items[idx - 1] = items[idx - 1], items[idx]
    elif trigger == "bld-move-down" and idx < len(items) - 1:
        items[idx], items[idx + 1] = items[idx + 1], items[idx]
    else:
        return no_update
    tree["items"] = items
    return tree


# ---------------------------------------------------------------------------
# CB4: Open editor  (66 outputs)
# ---------------------------------------------------------------------------

@callback(
    Output("bld-editing", "data", allow_duplicate=True),
    Output("bld-editor-drawer", "opened", allow_duplicate=True),
    # 9 section visibility outputs
    Output("bld-sec-text", "style"),
    Output("bld-sec-separator", "style"),
    Output("bld-sec-section", "style"),
    Output("bld-sec-gallery", "style"),
    Output("bld-sec-file", "style"),
    Output("bld-sec-action", "style"),
    Output("bld-sec-select", "style"),
    Output("bld-sec-upload", "style"),
    Output("bld-sec-options", "style"),
    # Text display
    Output("bld-ed-content", "value"),
    # Separator
    Output("bld-ed-divider", "checked"),
    Output("bld-ed-spacing", "value"),
    # Section
    Output("bld-ed-section-text", "value"),
    Output("bld-ed-accessory-type", "value"),
    Output("bld-ed-acc-url", "value"),
    Output("bld-ed-acc-desc", "value"),
    Output("bld-ed-acc-label", "value"),
    Output("bld-ed-acc-url-link", "value"),
    # File
    Output("bld-ed-file-url", "value"),
    Output("bld-ed-file-spoiler", "checked"),
    # Gallery
    *[Output(f"bld-ed-mg-url-{i}", "value") for i in range(MAX_GALLERY)],
    *[Output(f"bld-ed-mg-desc-{i}", "value") for i in range(MAX_GALLERY)],
    *[Output(f"bld-mg-slot-{i}", "style") for i in range(MAX_GALLERY)],
    Output("bld-mg-count", "data"),
    # Buttons
    *[Output(f"bld-ed-btn-label-{i}", "value") for i in range(MAX_BUTTONS)],
    *[Output(f"bld-ed-btn-url-{i}", "value") for i in range(MAX_BUTTONS)],
    *[Output(f"bld-btn-slot-{i}", "style") for i in range(MAX_BUTTONS)],
    Output("bld-ar-count", "data"),
    # Select
    Output("bld-ed-select-placeholder", "value"),
    # Upload
    Output("bld-ed-upload-label", "value"),
    # Shared options
    *[Output(f"bld-ed-opt-label-{i}", "value") for i in range(MAX_OPTIONS)],
    *[Output(f"bld-ed-opt-value-{i}", "value") for i in range(MAX_OPTIONS)],
    *[Output(f"bld-opt-slot-{i}", "style") for i in range(MAX_OPTIONS)],
    Output("bld-opt-count", "data"),
    Input("bld-item-select", "value"),
    State("bld-tree", "data"),
    prevent_initial_call=True,
)
def open_editor(selected_id, tree):
    hide = {"display": "none"}
    show = {"display": "block"}
    # 2 core + 9 sections + 1+2+6+2 + 13(mg) + 16(btn) + 1+1 + 13(opt) = 66
    n_outputs = 66

    if not selected_id or not tree:
        return (None, False) + tuple([hide] * 9) + tuple([no_update] * (n_outputs - 11))

    item = next((it for it in tree["items"] if it["id"] == selected_id), None)
    if not item:
        return (None, False) + tuple([hide] * 9) + tuple([no_update] * (n_outputs - 11))

    t = item["type"]
    editing = {"id": item["id"], "type": t}

    # Section visibility: all hidden except the relevant one(s)
    section_keys = [
        "text_display", "separator", "section", "media_gallery",
        "file", "action_row", "string_select", "file_upload", "options",
    ]
    sec_styles = []
    for sk in section_keys:
        if sk == "options" and t in ("string_select", "radio_group", "checkbox_group"):
            sec_styles.append(show)
        elif sk == "string_select" and t == "string_select":
            sec_styles.append(show)
        elif sk == "file_upload" and t == "file_upload":
            sec_styles.append(show)
        elif sk == t:
            sec_styles.append(show)
        else:
            sec_styles.append(hide)

    # Text display
    content = item.get("content", "") if t == "text_display" else ""
    # Separator
    divider = item.get("divider", True) if t == "separator" else True
    spacing = item.get("spacing", "small") if t == "separator" else "small"
    # Section
    sec_text = item.get("text_content", "") if t == "section" else ""
    acc_type = item.get("accessory_type", "none") if t == "section" else "none"
    acc_url = item.get("accessory_url", "") if t == "section" else ""
    acc_desc = item.get("accessory_description", "") if t == "section" else ""
    acc_label = item.get("accessory_label", "") if t == "section" else ""
    acc_url_link = item.get("accessory_url_link", "") if t == "section" else ""
    # File
    file_url = item.get("url", "") if t == "file" else ""
    file_spoiler = item.get("spoiler", False) if t == "file" else False

    # Gallery
    mg_items = item.get("media_items", []) if t == "media_gallery" else []
    mg_count = max(len(mg_items), 1)
    mg_urls = [mg_items[i]["url"] if i < len(mg_items) else "" for i in range(MAX_GALLERY)]
    mg_descs = [mg_items[i].get("description", "") if i < len(mg_items) else "" for i in range(MAX_GALLERY)]
    mg_slot_styles = [show if i < mg_count else hide for i in range(MAX_GALLERY)]

    # Buttons
    btns = item.get("buttons", []) if t == "action_row" else []
    ar_count = max(len(btns), 1)
    btn_labels = [btns[i]["label"] if i < len(btns) else "" for i in range(MAX_BUTTONS)]
    btn_urls = [btns[i].get("url", "") if i < len(btns) else "" for i in range(MAX_BUTTONS)]
    btn_slot_styles = [show if i < ar_count else hide for i in range(MAX_BUTTONS)]

    # Select
    select_placeholder = item.get("placeholder", "") if t == "string_select" else ""
    # Upload
    upload_label = item.get("upload_label", "") if t == "file_upload" else ""

    # Shared options (for select, radio, checkbox)
    opts = item.get("options", []) if t in ("string_select", "radio_group", "checkbox_group") else []
    opt_count = max(len(opts), 1)
    opt_labels = [opts[i]["label"] if i < len(opts) else "" for i in range(MAX_OPTIONS)]
    opt_values = [opts[i]["value"] if i < len(opts) else "" for i in range(MAX_OPTIONS)]
    opt_slot_styles = [show if i < opt_count else hide for i in range(MAX_OPTIONS)]

    return (
        editing, True,
        *sec_styles,
        content,
        divider, spacing,
        sec_text, acc_type, acc_url, acc_desc, acc_label, acc_url_link,
        file_url, file_spoiler,
        *mg_urls, *mg_descs, *mg_slot_styles, mg_count,
        *btn_labels, *btn_urls, *btn_slot_styles, ar_count,
        select_placeholder,
        upload_label,
        *opt_labels, *opt_values, *opt_slot_styles, opt_count,
    )


# ---------------------------------------------------------------------------
# CB5: Save editor
# ---------------------------------------------------------------------------

@callback(
    Output("bld-tree", "data", allow_duplicate=True),
    Output("bld-editor-drawer", "opened", allow_duplicate=True),
    Input("bld-save-btn", "n_clicks"),
    State("bld-tree", "data"),
    State("bld-editing", "data"),
    # Text display
    State("bld-ed-content", "value"),
    # Separator
    State("bld-ed-divider", "checked"),
    State("bld-ed-spacing", "value"),
    # Section
    State("bld-ed-section-text", "value"),
    State("bld-ed-accessory-type", "value"),
    State("bld-ed-acc-url", "value"),
    State("bld-ed-acc-desc", "value"),
    State("bld-ed-acc-label", "value"),
    State("bld-ed-acc-url-link", "value"),
    # File
    State("bld-ed-file-url", "value"),
    State("bld-ed-file-spoiler", "checked"),
    # Gallery
    *[State(f"bld-ed-mg-url-{i}", "value") for i in range(MAX_GALLERY)],
    *[State(f"bld-ed-mg-desc-{i}", "value") for i in range(MAX_GALLERY)],
    State("bld-mg-count", "data"),
    # Buttons
    *[State(f"bld-ed-btn-label-{i}", "value") for i in range(MAX_BUTTONS)],
    *[State(f"bld-ed-btn-url-{i}", "value") for i in range(MAX_BUTTONS)],
    State("bld-ar-count", "data"),
    # Select
    State("bld-ed-select-placeholder", "value"),
    # Upload
    State("bld-ed-upload-label", "value"),
    # Options
    *[State(f"bld-ed-opt-label-{i}", "value") for i in range(MAX_OPTIONS)],
    *[State(f"bld-ed-opt-value-{i}", "value") for i in range(MAX_OPTIONS)],
    State("bld-opt-count", "data"),
    prevent_initial_call=True,
)
def save_editor(
    _n, tree, editing, content, divider, spacing,
    sec_text, acc_type, acc_url, acc_desc, acc_label, acc_url_link,
    file_url, file_spoiler,
    mg_url_0, mg_url_1, mg_url_2, mg_url_3,
    mg_desc_0, mg_desc_1, mg_desc_2, mg_desc_3,
    mg_count,
    btn_label_0, btn_label_1, btn_label_2, btn_label_3, btn_label_4,
    btn_url_0, btn_url_1, btn_url_2, btn_url_3, btn_url_4,
    ar_count,
    select_placeholder, upload_label,
    opt_label_0, opt_label_1, opt_label_2, opt_label_3,
    opt_value_0, opt_value_1, opt_value_2, opt_value_3,
    opt_count,
):
    if not editing or not tree:
        return no_update, no_update

    item_id = editing["id"]
    item_type = editing["type"]

    for item in tree["items"]:
        if item["id"] != item_id:
            continue

        if item_type == "text_display":
            item["content"] = content or ""
        elif item_type == "separator":
            item["divider"] = divider
            item["spacing"] = spacing
        elif item_type == "section":
            item["text_content"] = sec_text or ""
            item["accessory_type"] = acc_type or "none"
            item["accessory_url"] = acc_url or ""
            item["accessory_description"] = acc_desc or ""
            item["accessory_label"] = acc_label or ""
            item["accessory_url_link"] = acc_url_link or ""
        elif item_type == "media_gallery":
            mg_urls = [mg_url_0, mg_url_1, mg_url_2, mg_url_3]
            mg_descs = [mg_desc_0, mg_desc_1, mg_desc_2, mg_desc_3]
            count = min(mg_count or 1, MAX_GALLERY)
            item["media_items"] = [
                {"url": mg_urls[i] or "", "description": mg_descs[i] or ""}
                for i in range(count) if mg_urls[i]
            ]
            if not item["media_items"]:
                item["media_items"] = [{"url": "", "description": ""}]
        elif item_type == "file":
            item["url"] = file_url or ""
            item["spoiler"] = file_spoiler or False
        elif item_type == "action_row":
            btn_labels = [btn_label_0, btn_label_1, btn_label_2, btn_label_3, btn_label_4]
            btn_urls_list = [btn_url_0, btn_url_1, btn_url_2, btn_url_3, btn_url_4]
            count = min(ar_count or 1, MAX_BUTTONS)
            item["buttons"] = [
                {"label": btn_labels[i] or "", "url": btn_urls_list[i] or "", "style": "link"}
                for i in range(count)
            ]
        elif item_type == "string_select":
            item["placeholder"] = select_placeholder or ""
            _save_options(item)
        elif item_type == "file_upload":
            item["upload_label"] = upload_label or ""
        elif item_type in ("radio_group", "checkbox_group"):
            _save_options(item)
        break

    # helper closure captures opt fields
    def _do_save_options(target):
        ol = [opt_label_0, opt_label_1, opt_label_2, opt_label_3]
        ov = [opt_value_0, opt_value_1, opt_value_2, opt_value_3]
        count = min(opt_count or 1, MAX_OPTIONS)
        target["options"] = [
            {"label": ol[i] or "", "value": ov[i] or ""}
            for i in range(count) if ol[i] or ov[i]
        ]
        if not target["options"]:
            target["options"] = [{"label": "", "value": ""}]

    # Re-find and save options for types that need it
    for item in tree["items"]:
        if item["id"] == item_id and item_type in ("string_select", "radio_group", "checkbox_group"):
            _do_save_options(item)
            break

    return tree, False


def _save_options(item):
    """Placeholder -- actual saving done via closure in save_editor."""
    pass


# ---------------------------------------------------------------------------
# CB6: Update container color
# ---------------------------------------------------------------------------

@callback(
    Output("bld-tree", "data", allow_duplicate=True),
    Input("bld-container-color", "value"),
    State("bld-tree", "data"),
    prevent_initial_call=True,
)
def update_container_color(color, tree):
    if not tree:
        return no_update
    tree["container_color"] = color or "#5865F2"
    return tree


# ---------------------------------------------------------------------------
# CB7: Render all (preview + component list + JSON)
# ---------------------------------------------------------------------------

@callback(
    Output("bld-component-list", "children"),
    Output("bld-item-select", "data"),
    Output("bld-preview-area", "children"),
    Output("bld-json-output", "children"),
    Output("bld-palette-limit", "children"),
    Output("bld-send-note", "children"),
    Input("bld-tree", "data"),
)
def render_all(tree):
    if not tree or not tree.get("items"):
        empty_msg = dmc.Text(
            "Add components using the palette above.", c="dimmed", size="sm",
        )
        return (
            empty_msg, [],
            html.Div(
                dmc.Text(
                    "Your message preview will appear here.",
                    c=DC_MUTED, size="sm", fs="italic",
                ),
                style={"textAlign": "center", "padding": 40},
            ),
            "Add components to see the payload.",
            None,
            None,
        )

    items = tree["items"]
    color = tree.get("container_color", "#5865F2")

    # Component list badges
    comp_list = dmc.Stack(
        [
            dmc.Badge(
                f"{TYPE_LABELS.get(it['type'], it['type'])}: {get_item_summary(it)}",
                color=TYPE_COLORS.get(it["type"], "gray"),
                variant="light", size="sm",
                style={"maxWidth": "100%", "overflow": "hidden",
                       "textOverflow": "ellipsis"},
            )
            for it in items
        ],
        gap=4,
    )

    # Select data
    select_data = [
        {
            "label": f"{TYPE_LABELS.get(it['type'], it['type'])}: {get_item_summary(it)[:25]}",
            "value": it["id"],
        }
        for it in items
    ]

    # Discord preview
    preview_children = [
        html.Div(render_preview_component(item), style={"marginBottom": 8})
        for item in items
    ]
    preview = html.Div(
        preview_children,
        style={
            "backgroundColor": DC_EMBED_BG,
            "borderLeft": f"4px solid {color}",
            "borderRadius": 4, "padding": 12,
        },
    ) if preview_children else html.Div(
        dmc.Text("No renderable components.", c=DC_MUTED, size="sm"),
        style={"textAlign": "center", "padding": 40},
    )

    # JSON output
    try:
        payload = store_to_payload(tree)
        msg = payload.get("message")
        json_str = json.dumps(msg, indent=2) if msg else "{}"
    except Exception as exc:
        json_str = f"Error: {exc}"

    # Palette limit
    limit_msg = None
    if len(items) >= MAX_ITEMS:
        limit_msg = dmc.Text(f"Max {MAX_ITEMS} components reached.", c="red", size="xs")

    # Send note for interactive components
    send_note = None
    has_interactive = any(it["type"] in INTERACTIVE_NOTE_TYPES for it in items)
    if has_interactive:
        send_note = dmc.Text(
            "Note: Select menus require an application-owned webhook (bot) "
            "to handle user interactions.",
            size="xs", c="dimmed",
        )

    return comp_list, select_data, preview, json_str, limit_msg, send_note


# ---------------------------------------------------------------------------
# CB8: Send webhook
# ---------------------------------------------------------------------------

@callback(
    Output("bld-send-result", "children"),
    Input("bld-send-btn", "n_clicks"),
    State("bld-tree", "data"),
    State("bld-webhook-url", "value"),
    State("bld-username", "value"),
    State("bld-avatar-url", "value"),
    prevent_initial_call=True,
)
def send_webhook(_n, tree, webhook_url, username, avatar_url):
    if not tree or not tree.get("items"):
        return dmc.Badge("No components to send", color="yellow", size="sm")

    try:
        payload = store_to_payload(tree)
        msg = payload.get("message")
        if not msg:
            return dmc.Badge("Build error: no payload generated", color="red", size="sm")
    except Exception as exc:
        return dmc.Badge(f"Build error: {exc}", color="red", size="sm")

    result = send_webhook_message(
        components=msg["components"],
        flags=msg.get("flags"),
        webhook_url=webhook_url or None,
        username=username or None,
        avatar_url=avatar_url or None,
    )

    if result["success"]:
        return dmc.Badge(f"Sent! ID: {result['message_id']}", color="green", size="sm")
    return dmc.Badge(f"Error: {result['error'][:60]}", color="red", size="sm")


# ---------------------------------------------------------------------------
# CB9: Manage sub-item slot visibility
# ---------------------------------------------------------------------------

@callback(
    *[Output(f"bld-mg-slot-{i}", "style", allow_duplicate=True) for i in range(MAX_GALLERY)],
    Output("bld-mg-count", "data", allow_duplicate=True),
    Input("bld-add-mg-item", "n_clicks"),
    Input("bld-rm-mg-item", "n_clicks"),
    State("bld-mg-count", "data"),
    prevent_initial_call=True,
)
def manage_gallery_slots(_add, _rm, count):
    count = count or 1
    if ctx.triggered_id == "bld-add-mg-item":
        count = min(count + 1, MAX_GALLERY)
    elif ctx.triggered_id == "bld-rm-mg-item":
        count = max(count - 1, 1)
    styles = [{"display": "block"} if i < count else {"display": "none"} for i in range(MAX_GALLERY)]
    return *styles, count


@callback(
    *[Output(f"bld-btn-slot-{i}", "style", allow_duplicate=True) for i in range(MAX_BUTTONS)],
    Output("bld-ar-count", "data", allow_duplicate=True),
    Input("bld-add-ar-btn", "n_clicks"),
    Input("bld-rm-ar-btn", "n_clicks"),
    State("bld-ar-count", "data"),
    prevent_initial_call=True,
)
def manage_button_slots(_add, _rm, count):
    count = count or 1
    if ctx.triggered_id == "bld-add-ar-btn":
        count = min(count + 1, MAX_BUTTONS)
    elif ctx.triggered_id == "bld-rm-ar-btn":
        count = max(count - 1, 1)
    styles = [{"display": "block"} if i < count else {"display": "none"} for i in range(MAX_BUTTONS)]
    return *styles, count


@callback(
    *[Output(f"bld-opt-slot-{i}", "style", allow_duplicate=True) for i in range(MAX_OPTIONS)],
    Output("bld-opt-count", "data", allow_duplicate=True),
    Input("bld-add-opt-item", "n_clicks"),
    Input("bld-rm-opt-item", "n_clicks"),
    State("bld-opt-count", "data"),
    prevent_initial_call=True,
)
def manage_option_slots(_add, _rm, count):
    count = count or 1
    if ctx.triggered_id == "bld-add-opt-item":
        count = min(count + 1, MAX_OPTIONS)
    elif ctx.triggered_id == "bld-rm-opt-item":
        count = max(count - 1, 1)
    styles = [{"display": "block"} if i < count else {"display": "none"} for i in range(MAX_OPTIONS)]
    return *styles, count
