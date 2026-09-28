from backend.app.cron_scan import (
    get_alert_key,
    should_send_alert,
)


def test_alert_key_is_stable():
    alert = {
        "symbol": "SPY",
        "type": "risk",
        "reason": "價格低於 50 日均線",
    }

    assert get_alert_key(alert) == (
        "SPY|risk|價格低於 50 日均線"
    )


def test_same_alert_is_blocked_during_cooldown():
    alert = {
        "symbol": "SPY",
        "type": "risk",
        "reason": "價格低於 50 日均線",
    }

    state = {
        "SPY|risk|價格低於 50 日均線": {
            "last_sent_at": 1_000,
        }
    }

    result = should_send_alert(
        alert=alert,
        state=state,
        now_timestamp=1_000 + 60,
    )

    assert result is False


def test_same_alert_can_send_after_24_hours():
    alert = {
        "symbol": "SPY",
        "type": "risk",
        "reason": "價格低於 50 日均線",
    }

    state = {
        "SPY|risk|價格低於 50 日均線": {
            "last_sent_at": 1_000,
        }
    }

    result = should_send_alert(
        alert=alert,
        state=state,
        now_timestamp=1_000 + 24 * 60 * 60,
    )

    assert result is True


def test_new_alert_can_send():
    alert = {
        "symbol": "QQQ",
        "type": "attention",
        "reason": "RSI 低於或等於 35",
    }

    assert should_send_alert(
        alert=alert,
        state={},
        now_timestamp=1_000,
    ) is True
