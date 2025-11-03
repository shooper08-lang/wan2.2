"""Simple Flask-based in-memory key value API.

This module exposes a small REST API that can be used to exercise
integration-style validation for examples and tutorials.  The API is not
intended for production use; it keeps data only in process memory.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from flask import Flask, abort, jsonify, request

app = Flask(__name__)

# A trivial in-memory data store.  Keys are user provided strings, values are
# dictionaries that include a timestamp and arbitrary payload supplied by the
# client.
STORE: Dict[str, Dict[str, Any]] = {}


def _utcnow() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


@app.route("/health", methods=["GET"])
def health_check():
    """Return a simple health check payload."""
    return jsonify({"status": "ok", "timestamp": _utcnow()})


@app.route("/memory", methods=["GET"])
def list_memory():
    """Return the entire in-memory store."""
    return jsonify({"items": STORE, "count": len(STORE), "timestamp": _utcnow()})


@app.route("/memory", methods=["POST"])
def create_memory():
    """Create a new memory entry.

    The JSON payload must include a ``value`` field.  A ``key`` field is
    optional; when omitted a random UUID string is used.  The response includes
    the resolved key together with the stored value and timestamp.
    """
    payload = request.get_json(silent=True) or {}
    if "value" not in payload:
        abort(400, description="JSON body must include a 'value' field")

    key = payload.get("key") or str(uuid4())
    value = payload["value"]
    entry = {"value": value, "timestamp": _utcnow()}
    STORE[key] = entry
    return jsonify({"key": key, "entry": entry})


@app.route("/memory/<string:key>", methods=["GET"])
def read_memory(key: str):
    """Return a single memory entry by key."""
    if key not in STORE:
        abort(404, description=f"No entry stored for key '{key}'")
    return jsonify({"key": key, "entry": STORE[key], "timestamp": _utcnow()})


@app.route("/memory/<string:key>", methods=["PUT"])
def update_memory(key: str):
    """Update an existing memory entry."""
    if key not in STORE:
        abort(404, description=f"No entry stored for key '{key}'")

    payload = request.get_json(silent=True) or {}
    if "value" not in payload:
        abort(400, description="JSON body must include a 'value' field")

    STORE[key] = {"value": payload["value"], "timestamp": _utcnow()}
    return jsonify({"key": key, "entry": STORE[key]})


@app.route("/memory/<string:key>", methods=["DELETE"])
def delete_memory(key: str):
    """Delete an existing memory entry."""
    if key not in STORE:
        abort(404, description=f"No entry stored for key '{key}'")
    removed = STORE.pop(key)
    return jsonify({"key": key, "entry": removed, "timestamp": _utcnow()})


@app.route("/memory/reset", methods=["POST"])
def reset_memory():
    """Clear the in-memory store."""
    STORE.clear()
    return jsonify({"status": "cleared", "timestamp": _utcnow(), "count": 0})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
