"""Transport layer: Socket.IO (if available) or dcc.Store fallback.

The store bridge is always active.  Socket.IO is purely additive —
call ``configure_socketio(socketio)`` from your app to enable it.
No flask_socketio import happens at module level.
"""

_socketio_instance = None
_transport_mode = "store"


def configure_socketio(socketio):
    """Register the consumer app's SocketIO instance with the hook."""
    global _socketio_instance, _transport_mode
    if socketio is None:
        return
    _socketio_instance = socketio
    _transport_mode = "socketio"


def get_socketio():
    return _socketio_instance


def is_socketio_available():
    return _transport_mode == "socketio" and _socketio_instance is not None


def has_socketio_packages():
    """Check if flask-socketio and dash-socketio are importable."""
    try:
        import flask_socketio  # noqa
        import dash_socketio   # noqa
        return True
    except ImportError:
        return False
