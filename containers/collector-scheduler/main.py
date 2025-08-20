"""Minimal scheduler used in tests.

Exposes build_collect_payload, post_collect, write_run_manifest, and run_once.
The functions are intentionally small so unit tests can monkeypatch side-effects.
"""
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import httpx

COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://content-collector:8000/collect")


def build_collect_payload() -> Dict[str, Any]:
    return {
        "sources": [
            {
                "type": "reddit",
                "subreddits": os.environ.get(
                    "SCHED_SUBREDDITS", "technology,programming"
                ).split(","),
                "limit": int(os.environ.get("SCHED_LIMIT", "5")),
            }
        ],
        "options": {
            "deduplicate": True,
            "max_total_items": int(os.environ.get("SCHED_MAX_ITEMS", "100")),
        },
        "run_id": str(uuid.uuid4()),
    }


def post_collect(payload: Dict[str, Any]) -> httpx.Response:
    headers = {"Content-Type": "application/json"}
    timeout = httpx.Timeout(30.0, connect=10.0)
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(COLLECTOR_URL, json=payload, headers=headers)
        return resp


def write_run_manifest(run_manifest: Dict[str, Any]) -> str:
    # In production this would persist to blob storage; tests monkeypatch it.
    now = datetime.now(timezone.utc)
    return f"http://blob/run-manifests/run_{run_manifest['run_id']}.json"


def main_loop_once() -> int:
    payload = build_collect_payload()
    resp = post_collect(payload)
    status_code = resp.status_code if resp is not None else 0

    run_manifest = {
        "run_id": payload["run_id"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
        "trigger": {"type": "scheduler", "service": "collector-scheduler"},
        "collector_response": {"status_code": status_code},
    }

    try:
        write_run_manifest(run_manifest)
    except Exception:
        pass

    return 0 if status_code == 200 else 2


def run_once():
    return main_loop_once()
