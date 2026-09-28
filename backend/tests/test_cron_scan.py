import json

from backend.app.cron_scan import save_alerts


def test_save_alerts(tmp_path, monkeypatch):
    import backend.app.cron_scan as cron_scan

    output_path = tmp_path / "alerts.json"
    monkeypatch.setattr(cron_scan, "OUTPUT_PATH", output_path)

    save_alerts(
        [
            {
                "symbol": "TEST",
                "type": "information",
                "message": "Test alert",
            }
        ]
    )

    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert "generated_at" in payload
    assert len(payload["alerts"]) == 1
    assert payload["alerts"][0]["symbol"] == "TEST"
