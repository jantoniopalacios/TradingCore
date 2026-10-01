from datetime import datetime, timedelta
import os

import pandas as pd

from trading_engine.utils import Data_download


def _ohlcv_frame(dates, symbol="AAPL"):
    return pd.DataFrame(
        {
            "Open": [10.0] * len(dates),
            "High": [11.0] * len(dates),
            "Low": [9.0] * len(dates),
            "Close": [10.5] * len(dates),
            "Adj Close": [10.5] * len(dates),
            "Volume": [1000] * len(dates),
            "Symbol": [symbol] * len(dates),
        },
        index=pd.DatetimeIndex(dates, name="Date"),
    )


def test_full_ohlcv_reuses_fresh_max_cache_without_cutting_history(tmp_path, monkeypatch):
    dates = pd.date_range("2000-01-03", periods=4, freq="D")
    cache_path = tmp_path / "AAPL_1d_MAX.csv"
    _ohlcv_frame(dates).to_csv(cache_path)

    def fail_download(*args, **kwargs):
        raise AssertionError("La caché MAX fresca debe reutilizarse")

    monkeypatch.setattr(Data_download.yf, "download", fail_download)

    result = Data_download.load_or_download_full_ohlcv(
        ["AAPL"], intervalo="1d", data_files_path=tmp_path
    )

    assert len(result) == 4
    assert result.index.min() == dates.min()
    assert result.index.max() == dates.max()
    assert result["Symbol"].unique().tolist() == ["AAPL"]


def test_full_ohlcv_requests_max_and_keeps_cache_on_degraded_download(
    tmp_path,
    monkeypatch,
):
    dates = pd.date_range("2000-01-03", periods=60, freq="D")
    cache_path = tmp_path / "AAPL_1d_MAX.csv"
    _ohlcv_frame(dates).to_csv(cache_path)
    yesterday = (datetime.now() - timedelta(days=1)).timestamp()
    os.utime(cache_path, (yesterday, yesterday))
    download_calls = []

    def degraded_download(symbol, **kwargs):
        download_calls.append((symbol, kwargs))
        short_dates = pd.date_range("2024-01-01", periods=5, freq="D")
        return _ohlcv_frame(short_dates).drop(columns="Symbol")

    monkeypatch.setattr(Data_download.yf, "download", degraded_download)

    result = Data_download.load_or_download_full_ohlcv(
        ["AAPL"], intervalo="1d", data_files_path=tmp_path
    )

    assert download_calls[0][0] == "AAPL"
    assert download_calls[0][1]["period"] == "max"
    assert download_calls[0][1]["interval"] == "1d"
    assert len(result) == 60
    assert result.index.min() == dates.min()
    assert result.index.max() == dates.max()