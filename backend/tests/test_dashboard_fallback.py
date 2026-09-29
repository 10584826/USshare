from backend.app.cron_scan import load_json_file


def test_load_json_file_returns_none_for_missing_file(tmp_path):
    result = load_json_file(tmp_path / "missing.json")

    assert result is None


def test_load_json_file_returns_payload(tmp_path):
    path = tmp_path / "dashboard.json"
    path.write_text(
        '{"health": {"status": "ok"}}',
        encoding="utf-8",
    )

    result = load_json_file(path)

    assert result == {"health": {"status": "ok"}}


def test_load_json_file_returns_none_for_invalid_json(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("{invalid", encoding="utf-8")

    result = load_json_file(path)

    assert result is None
