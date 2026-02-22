"""Parse [ACTION:type:data] patterns from bot messages.

Zero dependencies -- this is the foundation for the action bridge.
"""

import re

_ACTION_RE = re.compile(r"\[ACTION:(\w+):([^\]]*)\]")

VALID_ACTIONS = frozenset({"navigate", "notify", "toggle", "hide", "show", "open_url"})


def parse_actions(text):
    """Extract action dicts from text containing [ACTION:type:data] patterns.

    Returns a list of ``{"type": ..., "data": ...}`` dicts for each valid match.
    """
    if not text:
        return []
    actions = []
    for m in _ACTION_RE.finditer(text):
        action_type, data = m.group(1), m.group(2)
        if action_type in VALID_ACTIONS:
            actions.append({"type": action_type, "data": data})
    return actions


def strip_actions(text):
    """Remove all [ACTION:...] tags, returning clean display text."""
    if not text:
        return text
    return _ACTION_RE.sub("", text).strip()


# JS equivalent for clientside callbacks
ACTION_PARSER_JS = """
(function() {
    const ACTION_RE = /\\[ACTION:(\\w+):([^\\]]*)\\]/g;
    const VALID = new Set(["navigate", "notify", "toggle", "hide", "show", "open_url"]);

    window._dashWidgetBot = window._dashWidgetBot || {};

    window._dashWidgetBot.parseActions = function(text) {
        if (!text) return [];
        const actions = [];
        let m;
        ACTION_RE.lastIndex = 0;
        while ((m = ACTION_RE.exec(text)) !== null) {
            if (VALID.has(m[1])) {
                actions.push({type: m[1], data: m[2]});
            }
        }
        return actions;
    };

    window._dashWidgetBot.stripActions = function(text) {
        if (!text) return text;
        return text.replace(/\\[ACTION:\\w+:[^\\]]*\\]/g, '').trim();
    };
})();
"""
