import pandas as pd

from backend.app.services.indicators import (
    calculate_rsi,
    calculate_sma,
    calculate_volume_ratio,
    determine_market_status,
)


def test_calculate_sma():
    prices = pd.Series(range(1, 80))

    result = calculate_sma(prices, window=50)

    assert result == 54.5


def test_calculate_rsi_for_continuous_rise():
    prices = pd.Series(range(1, 80))

    result = calculate_rsi(prices, window=14)

    assert result == 100.0


def test_calculate_volume_ratio():
    volumes = pd.Series([100] * 20 + [200])

    result = calculate_volume_ratio(volumes, window=20)

    assert result == 2.0


def test_determine_market_status():
    status, status_text = determine_market_status(
        price=110,
        sma50=100,
        rsi14=55,
    )

    assert status == "bullish"
    assert status_text == "偏多"
