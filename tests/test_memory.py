"""Automated validation suite for the example Flask memory API."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:5000"
DEFAULT_LOG_FILE = Path(__file__).with_name("test_log.txt")


def configure_logger(log_path: Path) -> logging.Logger:
    """Return a logger that writes timestamped entries to ``log_path``."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("memory_api_test")
    logger.setLevel(logging.INFO)

    # Remove any pre-existing handlers so repeated runs do not duplicate output.
    logger.handlers.clear()

    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def log_response(logger: logging.Logger, label: str, response: requests.Response) -> None:
    """Write a detailed log entry for an HTTP response."""
    try:
        payload = response.json()
        payload_repr: Any = payload
    except requests.JSONDecodeError:
        payload_repr = response.text
    logger.info("%s | %s %s", label, response.status_code, json.dumps(payload_repr, ensure_ascii=False))


class MemoryApiValidator:
    """Wrapper around requests to validate the Flask memory API."""

    def __init__(self, base_url: str, logger: logging.Logger) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.logger = logger

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(self, label: str, method: str, path: str, **kwargs: Any) -> requests.Response:
        response = self.session.request(method, self._url(path), timeout=5, **kwargs)
        log_response(self.logger, label, response)
        return response

    def ping(self) -> Dict[str, Any]:
        response = self._request("health", "GET", "/health")
        response.raise_for_status()
        payload = response.json()
        assert payload.get("status") == "ok", "Health endpoint must report status 'ok'"
        return payload

    def create_entry(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        response = self._request(
            "create",
            "POST",
            "/memory",
            json={"key": key, "value": value},
        )
        response.raise_for_status()
        payload = response.json()
        assert payload.get("key") == key, "Created entry must echo the key"
        assert payload.get("entry", {}).get("value") == value, "Created entry must echo the value"
        return payload

    def read_entry(self, key: str) -> Dict[str, Any]:
        response = self._request("read", "GET", f"/memory/{key}")
        response.raise_for_status()
        payload = response.json()
        assert payload.get("key") == key, "Read entry must include the key"
        return payload

    def update_entry(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        response = self._request("update", "PUT", f"/memory/{key}", json={"value": value})
        response.raise_for_status()
        payload = response.json()
        assert payload.get("entry", {}).get("value") == value, "Updated value must match payload"
        return payload

    def list_entries(self) -> Dict[str, Any]:
        response = self._request("list", "GET", "/memory")
        response.raise_for_status()
        payload = response.json()
        assert isinstance(payload.get("items"), dict), "Listing must include an 'items' dictionary"
        return payload

    def delete_entry(self, key: str) -> Dict[str, Any]:
        response = self._request("delete", "DELETE", f"/memory/{key}")
        response.raise_for_status()
        payload = response.json()
        assert payload.get("key") == key, "Delete response must include key"
        return payload

    def reset(self) -> Dict[str, Any]:
        response = self._request("reset", "POST", "/memory/reset")
        response.raise_for_status()
        payload = response.json()
        assert payload.get("status") == "cleared", "Reset response must report 'cleared'"
        return payload


def run_suite(base_url: str, log_path: Path) -> None:
    logger = configure_logger(log_path)
    validator = MemoryApiValidator(base_url, logger)

    validator.ping()
    validator.reset()

    key = f"test-{uuid4()}"
    initial_value = {"message": "hello", "count": 1}
    updated_value = {"message": "updated", "count": 2}

    validator.create_entry(key, initial_value)
    read_payload = validator.read_entry(key)
    assert read_payload.get("entry", {}).get("value") == initial_value, "Read payload must match created value"

    validator.update_entry(key, updated_value)
    list_payload = validator.list_entries()
    assert list_payload["items"].get(key, {}).get("value") == updated_value, "Listing must show updated value"

    validator.delete_entry(key)

    missing_response = validator._request("confirm-missing", "GET", f"/memory/{key}")
    assert missing_response.status_code == 404, "Deleted entry should return HTTP 404"
    validator.reset()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the Flask memory API")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL of the running Flask server")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE), help="Path to log file for test results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_path = Path(args.log_file)
    run_suite(args.base_url, log_path)
    print(f"Validation completed successfully. Logs written to {log_path}")


if __name__ == "__main__":
    main()
