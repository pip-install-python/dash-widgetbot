"""dash-widgetbot example application.

Demonstrates DiscordCrate and DiscordWidget across 10 pages,
including Phase 2 Discord bot integration examples.
"""

import os

from dotenv import load_dotenv

load_dotenv()

from dash_widgetbot import add_discord_crate, add_discord_widget, add_discord_interactions, register_command, sync_discord_endpoint

# Register the global Crate BEFORE creating the Dash app
SERVER = os.getenv("WIDGETBOT_SERVER", "299881420891881473")
CHANNEL = os.getenv("WIDGETBOT_CHANNEL", "355719584830980096")
COLOR = os.getenv("WIDGETBOT_COLOR", "#5865f2")
SHARD = os.getenv("WIDGETBOT_SHARD", "")

add_discord_crate(
    server=SERVER,
    channel=CHANNEL,
    color=COLOR,
    shard=SHARD,
    defer=True,
)

# Multi-instance demo: register additional Crate instances BEFORE Dash()
CHANNEL_2 = os.getenv("WIDGETBOT_CHANNEL_2", "355719584830980096")

SUPPORT_IDS = add_discord_crate(
    server=SERVER,
    channel=CHANNEL,
    prefix="support",
    color="#e74c3c",
    shard=SHARD,
    location=["top", "right"],
    defer=False,
    pages=["/multi-instance"],
)

COMMUNITY_IDS = add_discord_crate(
    server=SERVER,
    channel=CHANNEL_2,
    prefix="community",
    color="#2ecc71",
    shard=SHARD,
    location=["top", "left"],
    defer=False,
    pages=["/multi-instance"],
)

# Widget embed -- must be registered before Dash() like the Crates above
WIDGET_IDS = add_discord_widget(
    server=SERVER,
    channel=CHANNEL,
    shard=SHARD,
    width="100%",
    height="500px",
    container_id="wgt-embed-container",
)

# Register Discord interactions endpoint (only if configured)
if os.getenv("DISCORD_PUBLIC_KEY"):
    add_discord_interactions()

    # Helper: post a classic embed to the channel so WidgetBot can render it
    def _post_channel_message(interaction, embed, *, image_bytes=None, image_mime="image/png", image_filename="ai_image.png"):
        """POST a type-0 channel message with a classic embed.

        Interaction responses (type 4/5) are a different message type that
        WidgetBot doesn't update in real-time.  Posting a regular channel
        message here ensures it shows up in both the Crate and Inline Widget.

        When *image_bytes* is provided the message is sent as multipart
        form-data with the image attached and the embed's ``image`` field
        pointing to ``attachment://<image_filename>``.
        """
        import requests as _req
        import json as _json
        channel_id = interaction.get("channel_id", "")
        bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
        if not channel_id or not bot_token:
            return
        try:
            if image_bytes:
                embed["image"] = {"url": f"attachment://{image_filename}"}
                _req.post(
                    f"https://discord.com/api/v10/channels/{channel_id}/messages",
                    headers={"Authorization": f"Bot {bot_token}"},
                    data={"payload_json": _json.dumps({"embeds": [embed]})},
                    files={"files[0]": (image_filename, image_bytes, image_mime)},
                    timeout=30,
                )
            else:
                _req.post(
                    f"https://discord.com/api/v10/channels/{channel_id}/messages",
                    headers={
                        "Authorization": f"Bot {bot_token}",
                        "Content-Type": "application/json",
                    },
                    json={"embeds": [embed]},
                    timeout=10,
                )
        except Exception as exc:
            print(f"[dash-widgetbot] _post_channel_message failed: {exc}")

    _COLOR_MAP = {
        "primary": 0x5865F2,
        "success": 0x57F287,
        "warning": 0xFEE75C,
        "danger": 0xED4245,
        "neutral": 0x99AAB5,
    }

    # Demo command handlers
    def _handle_ask(interaction):
        """Handle /ask -- structured Components V2 response with optional image."""
        from dash_widgetbot.ai_responder import generate_structured_response
        from dash_widgetbot.ai_builder import build_components_v2
        from dash_widgetbot.ai_image import generate_image
        from dash_widgetbot.components import container, text_display, separator

        tracker = interaction.get("_progress_tracker")

        options = interaction.get("data", {}).get("options", [])
        question = next((o["value"] for o in options if o["name"] == "question"), "")
        if not question:
            return "Please provide a question."

        # 1. Generate structured response
        if tracker:
            tracker.update("analyzing")
        on_progress = tracker.stream_callback() if tracker else None
        result = generate_structured_response(question, on_progress=on_progress)
        if tracker:
            tracker.update("parsing")

        if result["error"] or result["response"] is None:
            # Return a danger-colored error container
            error_msg = result["error"] or "Unknown error"
            err_container = container(
                text_display(f"# ❌ Error"),
                separator(),
                text_display(f"Could not generate a response.\n\n`{error_msg[:500]}`"),
                separator(),
                text_display("-# Powered by 2plot.ai"),
                color=0xED4245,
            )
            return {"components": [err_container]}

        ai_response = result["response"]

        # 2. Check for image generation
        image_url = None
        files = None
        if ai_response.image_prompt:
            if tracker:
                tracker.update("creating_image")
            img_result = generate_image(ai_response.image_prompt)
            if img_result["image_bytes"]:
                ext = "png" if "png" in img_result["mime_type"] else "jpg"
                filename = f"generated.{ext}"
                image_url = f"attachment://{filename}"
                files = [(filename, img_result["image_bytes"], img_result["mime_type"])]
            else:
                print(f"[dash-widgetbot] Image gen failed: {img_result['error']}")

        # 3. Build Components V2 payload
        payload = build_components_v2(ai_response, image_url=image_url)

        # 4. Attach files if generated
        if files:
            payload["_files"] = files

        # 5. Post a classic embed so WidgetBot Crate/Widget can render it
        if tracker:
            tracker.update("posting")
        desc = next(
            (b.text.content[:500] for b in ai_response.components if b.text),
            ai_response.title,
        )
        _post_channel_message(interaction, {
            "title": ai_response.title,
            "description": desc,
            "color": _COLOR_MAP.get(ai_response.color, 0x5865F2),
            "footer": {"text": "Powered by 2plot.ai"},
        })

        if tracker:
            tracker.update("complete")
        return payload

    def _handle_navigate(interaction):
        """Handle /navigate -- returns an action tag."""
        options = interaction.get("data", {}).get("options", [])
        path = next((o["value"] for o in options if o["name"] == "path"), "/")
        return f"Navigating to {path} [ACTION:navigate:{path}]"

    def _handle_status(interaction):
        """Handle /status -- returns app info."""
        return (
            "**dash-widgetbot** v0.1.0\n"
            f"Server: `{SERVER}`\n"
            f"Channel: `{CHANNEL}`\n"
            "Pages: Home, Commands, Events, Styling, Widget, "
            "Multi-Instance, Bot Bridge, Slash Commands, AI Chat, Webhook"
        )

    def _handle_gen(interaction):
        """Handle /gen -- generate a rich Dash UI component and push to gen_store."""
        from dash_widgetbot.gen_responder import generate_gen_response
        from dash_widgetbot.gen_store import gen_store, GenEntry
        from dash_widgetbot.ai_image import generate_image
        from dash_widgetbot.components import container, text_display, action_row, button

        tracker = interaction.get("_progress_tracker")

        options = interaction.get("data", {}).get("options", [])
        prompt = next((o["value"] for o in options if o["name"] == "prompt"), "")
        if not prompt:
            return "Please provide a prompt."

        # Extract discord user
        member = interaction.get("member", {})
        user = member.get("user", {})
        discord_user = user.get("username", "unknown")

        # Generate structured response
        if tracker:
            tracker.update("analyzing")
        on_progress = tracker.stream_callback() if tracker else None
        result = generate_gen_response(prompt, on_progress=on_progress)
        if tracker:
            tracker.update("parsing")

        if result["error"] or result["response"] is None:
            error_msg = result["error"] or "Unknown error"
            entry = GenEntry(
                prompt=prompt,
                discord_user=discord_user,
                error=error_msg,
            )
            gen_store.add(entry)
            err_container = container(
                text_display("# \u274c Generation Failed"),
                text_display(f"Could not generate content.\n\n`{error_msg[:500]}`"),
                text_display("-# Powered by 2plot.ai"),
                color=0xED4245,
            )
            return {"components": [err_container]}

        gen_resp = result["response"]

        # Handle image generation
        image_bytes = None
        image_mime = ""
        if gen_resp.format == "image" and gen_resp.image:
            if tracker:
                tracker.update("creating_image")
            img_result = generate_image(gen_resp.image.prompt)
            if img_result["image_bytes"]:
                image_bytes = img_result["image_bytes"]
                image_mime = img_result["mime_type"]

        if tracker:
            tracker.update("posting")
        entry = GenEntry(
            prompt=prompt,
            response=gen_resp,
            image_bytes=image_bytes,
            image_mime=image_mime,
            discord_user=discord_user,
        )
        gen_store.add(entry)

        # Build brief Discord ack with link to Dash page
        from dash_widgetbot.interactions import _detect_ngrok_url
        _base = (
            os.getenv("INTERACTIONS_URL", "").split("/api/")[0]
            or _detect_ngrok_url()
            or "http://127.0.0.1:8150"
        )
        dash_url = f"{_base.rstrip('/')}/discord-to-dash"

        # Post a classic embed so WidgetBot Crate/Widget can render it
        _post_channel_message(interaction, {
            "title": f"\u2728 {gen_resp.title}",
            "description": (
                f"Generated **{gen_resp.format.replace('_', ' ')}** for: *{prompt[:100]}*\n\n"
                f"[View in Dash]({dash_url})"
            ),
            "url": dash_url,
            "color": 0x5865F2,
            "footer": {"text": "Powered by 2plot.ai"},
        })

        if tracker:
            tracker.update("complete")
        ack_container = container(
            text_display(f"# \u2728 {gen_resp.title}"),
            text_display(f"Generated **{gen_resp.format.replace('_', ' ')}** for: *{prompt[:100]}*"),
            action_row(
                button(label="View in Dash", url=dash_url, style="link", emoji={"name": "\U0001f517"}),
            ),
            text_display("-# Powered by 2plot.ai"),
            color=0x5865F2,
        )
        return {"components": [ack_container]}

    def _build_gen_embed(gen_resp, *, dash_url=""):
        """Convert a GenResponse to a classic Discord embed dict."""
        color_hex = gen_resp.color.lstrip("#")
        color_int = int(color_hex, 16) if color_hex else 0x5865F2

        CALLOUT_ICONS = {"info": "ℹ️", "warning": "⚠️", "tip": "💡", "success": "✅", "danger": "❌"}

        if gen_resp.format == "article" and gen_resp.article:
            desc = gen_resp.article.body[:2000]
        elif gen_resp.format == "code" and gen_resp.code:
            lang = gen_resp.code.language
            code = gen_resp.code.code[:1400]
            desc = f"```{lang}\n{code}\n```"
            if gen_resp.code.explanation:
                desc += f"\n\n{gen_resp.code.explanation[:300]}"
        elif gen_resp.format == "data_table" and gen_resp.data_table:
            dt = gen_resp.data_table
            header = " | ".join(dt.columns)
            sep = " | ".join(["---"] * len(dt.columns))
            rows = "\n".join(" | ".join(str(c) for c in row) for row in dt.rows[:20])
            desc = f"{header}\n{sep}\n{rows}"
            if dt.caption:
                desc = f"*{dt.caption}*\n\n" + desc
        elif gen_resp.format == "callout" and gen_resp.callout:
            c = gen_resp.callout
            icon = CALLOUT_ICONS.get(c.variant, "ℹ️")
            desc = f"{icon} **{c.title}**\n\n{c.body}"
        elif gen_resp.format == "image" and gen_resp.image:
            desc = gen_resp.image.caption or f"*{gen_resp.image.prompt[:200]}*"
        else:
            desc = f"Generated {gen_resp.format}"

        embed = {
            "title": gen_resp.title,
            "description": desc,
            "color": color_int,
            "footer": {"text": gen_resp.footer or "Powered by Gemini AI"},
        }
        if dash_url:
            embed["url"] = dash_url
        return embed

    def _handle_ai(interaction):
        """Handle /ai -- single clean channel message with optional image."""
        from dash_widgetbot.gen_responder import generate_gen_response
        from dash_widgetbot.gen_store import gen_store, GenEntry
        from dash_widgetbot.ai_image import generate_image
        from dash_widgetbot.interactions import _detect_ngrok_url
        from dash_widgetbot.ai_responder import reset_client as _reset_client
        import time as _time

        tracker = interaction.get("_progress_tracker")

        options = interaction.get("data", {}).get("options", [])
        prompt = next((o["value"] for o in options if o["name"] == "prompt"), "")
        if not prompt:
            return "Please provide a prompt."

        member = interaction.get("member", {})
        discord_user = member.get("user", {}).get("username", "unknown")

        if tracker:
            tracker.update("analyzing")
        on_progress = tracker.stream_callback() if tracker else None
        result = generate_gen_response(prompt, on_progress=on_progress)
        # Retry once on transient httpx / connection errors (stale HTTP/2 pool)
        if result["error"] and any(
            s in result["error"].lower()
            for s in ["disconnect", "connection", "server", "remote", "protocol"]
        ):
            print(f"[dash-widgetbot] /ai: transient error '{result['error'][:80]}', resetting client and retrying...")
            _reset_client()
            _time.sleep(1)
            result = generate_gen_response(prompt, on_progress=on_progress)

        if tracker:
            tracker.update("parsing")

        if result["error"] or result["response"] is None:
            error_msg = result["error"] or "Unknown error"
            _post_channel_message(interaction, {
                "title": "\u274c Generation Failed",
                "description": f"Could not generate a response.\n\n`{error_msg[:500]}`",
                "color": 0xED4245,
                "footer": {"text": "Powered by Gemini AI"},
            })
            return f"\u274c {error_msg[:200]}"

        gen_resp = result["response"]

        # Generate image if format is image
        image_bytes = None
        image_mime = "image/png"
        if gen_resp.format == "image" and gen_resp.image:
            if tracker:
                tracker.update("creating_image")
            img_result = generate_image(gen_resp.image.prompt)
            if img_result["image_bytes"]:
                image_bytes = img_result["image_bytes"]
                image_mime = img_result["mime_type"]

        # Push to gen_store so Dash page updates
        if tracker:
            tracker.update("posting")
        gen_store.add(GenEntry(
            prompt=prompt,
            response=gen_resp,
            image_bytes=image_bytes,
            image_mime=image_mime,
            discord_user=discord_user,
        ))

        # Build Dash URL
        _base = (
            os.getenv("INTERACTIONS_URL", "").split("/api/")[0]
            or _detect_ngrok_url()
            or "http://127.0.0.1:8150"
        )
        dash_url = f"{_base.rstrip('/')}/discord-to-dash"

        # Post ONE channel message (WidgetBot renders this)
        ext = "png" if "png" in image_mime else "jpg"
        _post_channel_message(
            interaction,
            _build_gen_embed(gen_resp, dash_url=dash_url),
            image_bytes=image_bytes,
            image_mime=image_mime,
            image_filename=f"ai_image.{ext}",
        )

        if tracker:
            tracker.update("complete")
        # Ephemeral follow-up — private confirmation to the invoker only
        return f"\u2705 **{gen_resp.title}** posted to the channel. [View in Dash]({dash_url})"

    register_command("ask", _handle_ask, ephemeral=True)
    register_command("navigate", _handle_navigate)
    register_command("status", _handle_status)
    register_command("gen", _handle_gen, ephemeral=True)
    register_command("ai", _handle_ai, ephemeral=True)

    # Auto-sync the Discord Interactions Endpoint URL with ngrok / INTERACTIONS_URL
    sync_discord_endpoint()

    # Register all slash commands with the guild (instant availability)
    def _register_guild_commands():
        import requests as _req
        _app_id = os.getenv("DISCORD_APPLICATION_ID", "")
        _bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
        _guild_id = os.getenv("DISCORD_GUILD_ID", "1246197743307980940")
        if not _app_id or not _bot_token:
            return
        _cmds = [
            {
                "name": "ask",
                "description": "Ask the AI assistant a question",
                "type": 1,
                "options": [{"name": "question", "description": "Your question", "type": 3, "required": True}],
            },
            {
                "name": "navigate",
                "description": "Navigate to a page in the Dash app",
                "type": 1,
                "options": [{"name": "path", "description": "Page path (e.g. /crate-commands)", "type": 3, "required": True}],
            },
            {
                "name": "status",
                "description": "Show app status info",
                "type": 1,
            },
            {
                "name": "gen",
                "description": "Generate a rich Dash UI component from a prompt",
                "type": 1,
                "options": [{"name": "prompt", "description": "What to generate (article, code, table, image, or tip)", "type": 3, "required": True}],
            },
            {
                "name": "ai",
                "description": "Generate AI content and post it to the channel",
                "type": 1,
                "options": [{"name": "prompt", "description": "What to generate (article, code, image, table, or tip)", "type": 3, "required": True}],
            },
        ]
        try:
            resp = _req.put(
                f"https://discord.com/api/v10/applications/{_app_id}/guilds/{_guild_id}/commands",
                headers={"Authorization": f"Bot {_bot_token}"},
                json=_cmds,
                timeout=15,
            )
            if resp.ok:
                print(f"[dash-widgetbot] Registered {len(_cmds)} guild commands successfully.")
            else:
                print(f"[dash-widgetbot] Guild command registration failed ({resp.status_code}): {resp.text[:200]}")
        except Exception as exc:
            print(f"[dash-widgetbot] Guild command registration exception: {exc}")

    _register_guild_commands()

    # Debug endpoint: test /ask handler locally without Discord signature verification
    from dash import hooks
    @hooks.route("api/test-ask", methods=("GET",))
    def test_ask_route():
        from flask import Response, request as flask_request
        import json as _json

        q = flask_request.args.get("q", "Hello")
        fake_interaction = {
            "data": {"name": "ask", "options": [{"name": "question", "value": q}]},
        }
        try:
            result = _handle_ask(fake_interaction)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return Response(
                _json.dumps({"error": str(exc)}),
                status=500,
                content_type="application/json",
            )

        if isinstance(result, str):
            body = {"content": result}
        elif isinstance(result, dict):
            # Strip internal sentinels (_files, _modal) for display
            body = {k: v for k, v in result.items() if not k.startswith("_")}
        else:
            body = {"content": str(result)}

        return Response(
            _json.dumps(body, indent=2, default=str),
            status=200,
            content_type="application/json",
        )

    @hooks.route("api/test-gen", methods=("GET",))
    def test_gen_route():
        from flask import Response, request as flask_request
        import json as _json

        q = flask_request.args.get("q", "Explain REST APIs")
        fake_interaction = {
            "data": {"name": "gen", "options": [{"name": "prompt", "value": q}]},
            "member": {"user": {"username": "test-user"}},
        }
        try:
            result = _handle_gen(fake_interaction)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return Response(
                _json.dumps({"error": str(exc)}),
                status=500,
                content_type="application/json",
            )

        if isinstance(result, str):
            body = {"content": result}
        elif isinstance(result, dict):
            body = {k: v for k, v in result.items() if not k.startswith("_")}
        else:
            body = {"content": str(result)}

        return Response(
            _json.dumps(body, indent=2, default=str),
            status=200,
            content_type="application/json",
        )

    @hooks.route("api/test-ai", methods=("GET",))
    def test_ai_route():
        """Test /ai handler locally without Discord signature verification.

        Usage: GET /api/test-ai?q=draw+a+cat
        """
        from flask import Response, request as flask_request
        import json as _json

        q = flask_request.args.get("q", "Draw a cat riding a skateboard")
        fake_interaction = {
            "data": {"name": "ai", "options": [{"name": "prompt", "value": q}]},
            "member": {"user": {"username": "test-user"}},
            "channel_id": "",  # No channel_id → _post_channel_message is a no-op
        }
        try:
            result = _handle_ai(fake_interaction)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return Response(
                _json.dumps({"error": str(exc)}),
                status=500,
                content_type="application/json",
            )

        body = {"content": result} if isinstance(result, str) else {"content": str(result)}
        return Response(
            _json.dumps(body, indent=2, default=str),
            status=200,
            content_type="application/json",
        )

    @hooks.route("api/purge-bot-messages", methods=("GET",))
    def purge_bot_messages_route():
        """Delete recent bot messages from a channel.

        Clears Components V2 interaction-response messages that break WidgetBot.

        Usage: GET /api/purge-bot-messages?channel_id=<id>&limit=50
        Returns JSON: {"deleted": N, "errors": [...]}
        """
        from flask import Response, request as flask_request
        import requests as _req
        import json as _json

        channel_id = flask_request.args.get("channel_id", "")
        limit = min(int(flask_request.args.get("limit", "50")), 100)
        bot_token = os.getenv("DISCORD_BOT_TOKEN", "")

        if not channel_id or not bot_token:
            return Response(
                _json.dumps({"error": "channel_id and DISCORD_BOT_TOKEN are required"}),
                status=400, content_type="application/json",
            )

        headers = {"Authorization": f"Bot {bot_token}"}

        # Fetch bot's own user ID
        try:
            me_resp = _req.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=10)
            bot_user_id = me_resp.json().get("id", "") if me_resp.ok else ""
        except Exception:
            bot_user_id = ""

        # Fetch recent messages
        try:
            msgs_resp = _req.get(
                f"https://discord.com/api/v10/channels/{channel_id}/messages?limit={limit}",
                headers=headers,
                timeout=10,
            )
            if not msgs_resp.ok:
                return Response(
                    _json.dumps({"error": f"Failed to fetch messages: {msgs_resp.status_code} {msgs_resp.text[:200]}"}),
                    status=msgs_resp.status_code, content_type="application/json",
                )
            messages = msgs_resp.json()
        except Exception as exc:
            return Response(
                _json.dumps({"error": str(exc)}),
                status=500, content_type="application/json",
            )

        # Find bot message IDs (by author.id OR by interaction type flag)
        import time as _time
        now_ms = int(_time.time() * 1000)
        cutoff_ms = now_ms - (14 * 24 * 60 * 60 * 1000)  # 14 days ago

        bulk_ids = []
        old_ids = []
        errors = []

        for msg in messages:
            is_bot_msg = (bot_user_id and msg.get("author", {}).get("id") == bot_user_id)
            # Also catch interaction responses regardless of author
            has_components_v2 = bool(msg.get("flags", 0) & 32768)
            if not (is_bot_msg or has_components_v2):
                continue

            msg_id = msg["id"]
            # Snowflake → approximate ms timestamp
            msg_ms = (int(msg_id) >> 22) + 1420070400000
            if msg_ms > cutoff_ms:
                bulk_ids.append(msg_id)
            else:
                old_ids.append(msg_id)

        deleted = 0

        # Bulk delete (< 14 days, 2+ messages)
        if len(bulk_ids) >= 2:
            try:
                del_resp = _req.post(
                    f"https://discord.com/api/v10/channels/{channel_id}/messages/bulk-delete",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"messages": bulk_ids[:100]},
                    timeout=15,
                )
                if del_resp.ok:
                    deleted += len(bulk_ids)
                else:
                    errors.append(f"Bulk delete failed: {del_resp.status_code} {del_resp.text[:100]}")
            except Exception as exc:
                errors.append(f"Bulk delete exception: {exc}")
        elif len(bulk_ids) == 1:
            old_ids.extend(bulk_ids)

        # Individual delete for old messages or single message
        for msg_id in old_ids:
            try:
                del_resp = _req.delete(
                    f"https://discord.com/api/v10/channels/{channel_id}/messages/{msg_id}",
                    headers=headers,
                    timeout=10,
                )
                if del_resp.ok or del_resp.status_code == 204:
                    deleted += 1
                else:
                    errors.append(f"Delete {msg_id} failed: {del_resp.status_code}")
                _time.sleep(0.5)  # Respect rate limits
            except Exception as exc:
                errors.append(f"Delete {msg_id} exception: {exc}")

        return Response(
            _json.dumps({"deleted": deleted, "scanned": len(messages), "errors": errors}),
            status=200,
            content_type="application/json",
        )

    # ------------------------------------------------------------------
    # Crate slash command bridge
    # ------------------------------------------------------------------
    # When a user types "/ai draw a cat" (or /ask /gen /navigate /status)
    # as a regular message in the WidgetBot Crate, the sentMessage event
    # fires.  We intercept it here, build a fake interaction, and dispatch
    # the command in a background thread exactly like a real Discord slash
    # command — the result posts to the channel and shows up in the Crate.
    # ------------------------------------------------------------------

    import time as _cmd_time
    from dash import callback as _dcallback, Input as _DInput, Output as _DOutput, no_update as _no_update

    # Maps command name → the single option name it accepts
    _CMD_OPTION_MAP = {
        "ask": "question",
        "ai": "prompt",
        "gen": "prompt",
        "navigate": "path",
        "status": None,   # no options
    }

    _CMD_NOTIFY = {
        "ask": "Asking the AI…",
        "ai": "Generating content…",
        "gen": "Generating content…",
        "navigate": "Navigating…",
        "status": "Getting status…",
    }

    _CRATE_LOADING_MSGS = {
        "ask": "⏳ Gemini is generating a response...",
        "ai":  "⏳ Generating AI content...",
        "gen": "⏳ Generating content...",
    }

    @_dcallback(
        _DOutput("_crate-slash-result", "data"),
        _DOutput("_widgetbot-crate-command", "data", allow_duplicate=True),
        _DInput("_widgetbot-crate-event", "data"),
        prevent_initial_call=True,
    )
    def _handle_crate_slash(event_data):
        """Bridge: intercept /command messages sent from the WidgetBot Crate.

        Usage (type in the Crate):
            /ai draw a cat riding a skateboard
            /ask what is a neural network?
            /gen create a Python quicksort
            /navigate /crate-commands
            /status
        """
        if not event_data or event_data.get("type") != "sentMessage":
            return _no_update, _no_update

        content = (event_data.get("content") or "").strip()
        if not content.startswith("/"):
            return _no_update, _no_update

        # Parse "/cmd rest of text" — strip leading slash, split on first space
        parts = content[1:].split(None, 1)
        cmd_name = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if cmd_name not in _CMD_OPTION_MAP:
            return _no_update, _no_update

        # Prefer channel ID from event; fall back to the configured channel
        channel_id = event_data.get("channel_id") or os.getenv("WIDGETBOT_CHANNEL", "")

        option_name = _CMD_OPTION_MAP[cmd_name]
        options = [{"name": option_name, "value": rest}] if (option_name and rest) else []

        from dash_widgetbot.interactions import _command_handlers
        handler = _command_handlers.get(cmd_name)
        if not handler:
            return _no_update, _no_update

        fake_interaction = {
            "channel_id": channel_id,
            "data": {"name": cmd_name, "options": options},
            "member": {"user": {"username": "crate-user"}},
        }

        # Commands that call _post_channel_message themselves don't need the
        # return value posted.  Commands like /status and /navigate only return
        # a plain string — that string IS the response that must go to the channel.
        _SELF_POSTING = frozenset({"ai", "gen", "ask"})

        def _run():
            from dash_widgetbot.interactions import _post_loading_channel_message, _delete_channel_message

            loading_msg_id = None
            loading_text = _CRATE_LOADING_MSGS.get(cmd_name)
            if loading_text and channel_id:
                loading_msg_id = _post_loading_channel_message(channel_id, loading_text)

            # Create progress tracker for AI commands
            tracker = None
            if cmd_name in {"ai", "gen", "ask"}:
                from dash_widgetbot.progress import (
                    ProgressTracker, ChannelMessageSink, SocketIOSink, CrateNotifySink,
                )
                sinks = [SocketIOSink()]
                if loading_msg_id and channel_id:
                    sinks.append(ChannelMessageSink(channel_id, loading_msg_id))
                sinks.append(CrateNotifySink())
                tracker = ProgressTracker(sinks=sinks)
                fake_interaction["_progress_tracker"] = tracker

            try:
                print(f"[dash-widgetbot] Crate slash /{cmd_name}: '{rest[:80]}'")
                result = handler(fake_interaction)
                # Post plain-string results for commands that don't self-post
                if isinstance(result, str) and result and cmd_name not in _SELF_POSTING:
                    from dash_widgetbot.action_parser import strip_actions
                    _post_channel_message(fake_interaction, {
                        "description": strip_actions(result),
                        "color": 0x5865F2,
                        "footer": {"text": "dash-widgetbot"},
                    })
            except Exception as exc:
                import traceback
                print(f"[dash-widgetbot] Crate slash /{cmd_name} error: {exc}")
                traceback.print_exc()
            finally:
                if tracker:
                    tracker.close()
                if loading_msg_id:
                    _delete_channel_message(channel_id, loading_msg_id)

        import threading
        threading.Thread(target=_run, daemon=True).start()

        notify_cmd = {"action": "notify", "data": f"⏳ {_CMD_NOTIFY[cmd_name]}"}
        result = {"command": cmd_name, "args": rest[:120], "_ts": _cmd_time.time()}
        return result, notify_cmd

# ---------------------------------------------------------------------------
# Image endpoint: serve gen entry image bytes (omitted from socket payloads)
# ---------------------------------------------------------------------------
from dash import hooks as _hooks

@_hooks.route("api/gen/<entry_id>/image", methods=("GET",))
def gen_image_route(entry_id):
    from flask import Response
    from dash_widgetbot.gen_store import gen_store as _gen_store
    for entry in _gen_store.get_all():
        if entry.id == entry_id and entry.image_bytes:
            return Response(entry.image_bytes, content_type=entry.image_mime or "image/png")
    return Response("Not found", status=404)


# Now create the app ---------------------------------------------------------
import dash
from dash import html, dcc
import dash_mantine_components as dmc

app = dash.Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    external_stylesheets=dmc.styles.ALL,
)

# Guarded Socket.IO setup (requires [realtime] extras)
from dash_widgetbot._transport import has_socketio_packages as _has_sio_pkgs
_socketio = None
if _has_sio_pkgs():
    from flask_socketio import SocketIO
    from dash_widgetbot import configure_socketio
    _socketio = SocketIO(
        app.server,
        async_mode='threading',
        cors_allowed_origins="*",
        logger=False,
        engineio_logger=False,
    )
    configure_socketio(_socketio)

NAV_LINKS = [
    {"label": "Home", "href": "/"},
    {"label": "Commands", "href": "/crate-commands"},
    {"label": "Events", "href": "/crate-events"},
    {"label": "Styling", "href": "/crate-styling"},
    {"label": "Widget", "href": "/widget-embed"},
    {"label": "Multi-Instance", "href": "/multi-instance"},
    {"label": "Bot Bridge", "href": "/bot-bridge"},
    {"label": "Slash Cmds", "href": "/slash-commands"},
    {"label": "AI Chat", "href": "/ai-chat"},
    {"label": "Webhook", "href": "/webhook-send"},
    {"label": "Rich Messages", "href": "/rich-messages"},
    {"label": "Builder", "href": "/rich-message-preview"},
    {"label": "Gen Gallery", "href": "/discord-to-dash"},
]

app.layout = dmc.MantineProvider(
    dmc.AppShell(
        [
            # Hidden stores for app-level callbacks
            html.Div(
                [dcc.Store(id="_crate-slash-result")],
                style={"display": "none"},
            ),
            dmc.AppShellHeader(
                dmc.Group(
                    [
                        dmc.Text("dash-widgetbot", fw=700, size="lg"),
                        dmc.Group(
                            [
                                dmc.Anchor(
                                    link["label"],
                                    href=link["href"],
                                    underline="never",
                                    c="dimmed",
                                    fw=500,
                                    size="sm",
                                )
                                for link in NAV_LINKS
                            ],
                            gap="md",
                        ),
                    ],
                    justify="space-between",
                    px="md",
                    h="100%",
                ),
            ),
            dmc.AppShellMain(
                dash.page_container,
            ),
        ],
        header={"height": 56},
        padding="md",
    ),
)

if __name__ == "__main__":
    if _socketio:
        _socketio.run(app.server, debug=True, port=8150)
    else:
        app.run(debug=True, port=8150)
