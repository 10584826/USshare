import json

from backend.app.cron_scan import save_dashboard


def test_save_dashboard(tmp_path, monkeypatch):
    import backend.app.cron_scan as cron_scan

    output_path = tmp_path / "dashboard.json"
    monkeypatch.setattr(cron_scan, "OUTPUT_PATH", output_path)

    payload = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "market": {},
        "watchlist": {
            "alerts": [],
        },
        "news": {
            "top_stories": [],
        },
        "disclaimer": "For reference only",
    }

    save_dashboard(payload)

    assert output_path.exists()

    saved = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert saved["generated_at"] == payload["generated_at"]
    assert "market" in saved
    assert "watchlist" in saved
    assert "news" in saved
