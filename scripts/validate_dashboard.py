"""Validate the generated public dashboard snapshot."""

from __future__ import annotations

import json
import sys
from pathlib import Path


DASHBOARD_PATH = Path("data/dashboard.json")


def fail(message: str) -> None:
    print(f"Dashboard validation failed: {message}")
    raise SystemExit(1)


def main() -> int:
    if not DASHBOARD_PATH.exists():
        fail(f"file does not exist: {DASHBOARD_PATH}")

    try:
        payload = json.loads(
            DASHBOARD_PATH.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        fail(f"invalid JSON: {error}")

    if not isinstance(payload, dict):
        fail("root value must be an object")

    required_fields = {
        "generated_at",
        "health",
        "market",
        "watchlist",
        "news",
        "disclaimer",
    }

    missing_fields = required_fields - payload.keys()

    if missing_fields:
        fail(f"missing fields: {sorted(missing_fields)}")

    health = payload["health"]

    if not isinstance(health, dict):
        fail("health must be an object")

    if health.get("status") not in {"ok", "partial", "error"}:
        fail("health.status must be ok, partial, or error")

    if not isinstance(health.get("is_stale"), bool):
        fail("health.is_stale must be boolean")

    market = payload["market"]
    watchlist = payload["watchlist"]
    news = payload["news"]

    if not isinstance(market, dict):
        fail("market must be an object")

    if not isinstance(watchlist, dict):
        fail("watchlist must be an object")

    if not isinstance(news, dict):
        fail("news must be an object")

    alerts = watchlist.get("alerts", [])

    if not isinstance(alerts, list):
        fail("watchlist.alerts must be a list")

    private_fields = {
        "telegram_sent",
        "telegram_reason",
    }

    for index, alert in enumerate(alerts):
        if not isinstance(alert, dict):
            fail(f"alert {index} must be an object")

        leaked_fields = private_fields.intersection(alert.keys())

        if leaked_fields:
            fail(
                f"private fields exposed in alert {index}: "
                f"{sorted(leaked_fields)}"
            )

    print(
        "Dashboard validation passed: "
        f"{len(alerts)} alerts, "
        f"health={health.get('status')}, "
        f"stale={health.get('is_stale')}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
