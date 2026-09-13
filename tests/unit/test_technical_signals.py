from types import SimpleNamespace

import numpy as np
import pandas as pd

from trading_engine.indicators import Filtro_ATR, Filtro_EMA, Filtro_MACD, Filtro_RSI
from trading_engine.indicators import Filtro_Stochastic, Filtro_Volume


def test_ema_buy_signal_active_returns_true_and_reason(monkeypatch):
    strategy = SimpleNamespace(
        ema_cruce_signal=True,
        ema_fast_series=pd.Series([1.0, 2.0]),
        ema_slow_series=pd.Series([2.0, 1.0]),
        ema_slow_minimo=False,
        ema_slow_minimo_STATE=False,
        ema_slow_ascendente=False,
        ema_slow_ascendente_STATE=False,
    )
    monkeypatch.setattr(Filtro_EMA, "crossover", lambda fast, slow: True)

    result = Filtro_EMA.check_ema_buy_signal(strategy, False)

    assert result == (True, "EMA Cruce Rápida/Lenta")


def test_ema_buy_signal_without_active_signal_preserves_false(monkeypatch):
    strategy = SimpleNamespace(
        ema_cruce_signal=False,
        ema_fast_series=None,
        ema_slow_series=None,
        ema_slow_minimo=False,
        ema_slow_minimo_STATE=False,
        ema_slow_ascendente=False,
        ema_slow_ascendente_STATE=False,
    )
    monkeypatch.setattr(Filtro_EMA, "crossover", lambda fast, slow: False)

    assert Filtro_EMA.check_ema_buy_signal(strategy, False) == (False, None)


def test_ema_global_filter_can_block_true_signal():
    strategy = SimpleNamespace(
        ema_slow_minimo=False,
        ema_slow_maximo=True,
        ema_slow_maximo_STATE=True,
        ema_slow_ascendente=False,
        ema_cruce_signal=False,
        ema_slow_descendente=False,
    )

    assert Filtro_EMA.apply_ema_global_filter(strategy, True) is False


def test_ema_sell_signal_active_returns_true_and_reason():
    strategy = SimpleNamespace(
        ema_slow_descendente=True,
        ema_slow_descendente_STATE=True,
        ema_slow_maximo=False,
        ema_slow_maximo_STATE=False,
        ema_cruce_signal=False,
    )

    assert Filtro_EMA.check_ema_sell_signal(strategy) == (True, "EMA Lenta Descendente")


def test_rsi_buy_signal_active_returns_true_and_reason(monkeypatch):
    strategy = SimpleNamespace(
        rsi=True,
        rsi_ind=pd.Series([20.0, 35.0]),
        rsi_minimo=True,
        rsi_minimo_STATE=True,
        rsi_threshold_ind=30.0,
        rsi_low_level=30.0,
        rsi_ascendente=False,
        rsi_ascendente_STATE=False,
    )
    monkeypatch.setattr(Filtro_RSI, "crossover", lambda current, threshold: True)

    assert Filtro_RSI.check_rsi_buy_signal(strategy, False) == (
        True,
        "RSI Giro desde Sobreventa",
    )


def test_rsi_sell_signal_active_returns_true_and_reason():
    strategy = SimpleNamespace(
        rsi=True,
        rsi_ind=pd.Series([75.0, 65.0]),
        rsi_high_level=70.0,
        rsi_maximo=False,
        rsi_maximo_STATE=False,
        rsi_descendente=True,
        rsi_descendente_STATE=True,
    )

    assert Filtro_RSI.check_rsi_sell_signal(strategy) == (True, "RSI Descendente")


def test_rsi_global_filter_allows_sufficient_value():
    strategy = SimpleNamespace(
        rsi=True,
        rsi_ind=pd.Series([55.0]),
        rsi_strength_threshold=50.0,
    )

    assert Filtro_RSI.apply_rsi_global_filter(strategy) is True


def test_rsi_global_filter_blocks_value_below_threshold():
    strategy = SimpleNamespace(
        rsi=True,
        rsi_ind=pd.Series([49.9]),
        rsi_strength_threshold=50.0,
    )

    assert Filtro_RSI.apply_rsi_global_filter(strategy) is False


def test_macd_buy_signal_active_returns_true_and_reason(monkeypatch):
    strategy = SimpleNamespace(
        macd=True,
        macd_hist=pd.Series([0.1, 0.2]),
        macd_line=pd.Series([0.0, 1.0]),
        macd_signal_line=pd.Series([1.0, 0.0]),
        macd_ascendente=True,
        macd_ascendente_STATE=True,
    )
    monkeypatch.setattr(Filtro_MACD, "crossover", lambda line, signal: True)

    assert Filtro_MACD.check_macd_buy_signal(strategy, False) == (True, "MACD Fuerte")


def test_macd_sell_signal_active_returns_true_and_reason():
    strategy = SimpleNamespace(
        macd_maximo=True,
        macd_maximo_STATE=True,
        macd_descendente=False,
        macd_descendente_STATE=False,
    )

    assert Filtro_MACD.check_macd_sell_signal(strategy) == (
        True,
        "MACD Máximo/Descendente",
    )


def test_macd_buy_signal_without_active_conditions_returns_false(monkeypatch):
    strategy = SimpleNamespace(
        macd=False,
        macd_hist=None,
        macd_line=None,
        macd_signal_line=None,
        macd_ascendente=False,
        macd_ascendente_STATE=False,
    )
    monkeypatch.setattr(Filtro_MACD, "crossover", lambda line, signal: True)

    assert Filtro_MACD.check_macd_buy_signal(strategy, False) == (False, None)


def test_stochastic_buy_crossover_returns_true(monkeypatch):
    strategy = SimpleNamespace(stoch_fast_ascendente=False, stoch_fast_minimo=False)
    monkeypatch.setattr(Filtro_Stochastic, "crossover", lambda k, d: True)

    result = Filtro_Stochastic.check_oscillator_buy_signal(
        strategy, "stoch_fast", np.array([10.0]), np.array([15.0]), 20.0
    )

    assert result == (True, "Stoch Fast Cruce")


def test_stochastic_ascending_filter_blocks_when_state_is_false(monkeypatch):
    strategy = SimpleNamespace(
        stoch_fast_ascendente=True,
        stoch_fast_ascendente_STATE=False,
        stoch_fast_minimo=False,
    )
    monkeypatch.setattr(Filtro_Stochastic, "crossover", lambda k, d: True)

    result = Filtro_Stochastic.check_oscillator_buy_signal(
        strategy, "stoch_fast", np.array([10.0]), np.array([15.0]), 20.0
    )

    assert result == (False, None)


def test_stochastic_minimum_filter_blocks_when_state_is_false(monkeypatch):
    strategy = SimpleNamespace(
        stoch_fast_ascendente=False,
        stoch_fast_minimo=True,
        stoch_fast_minimo_STATE=False,
    )
    monkeypatch.setattr(Filtro_Stochastic, "crossover", lambda k, d: True)

    result = Filtro_Stochastic.check_oscillator_buy_signal(
        strategy, "stoch_fast", np.array([10.0]), np.array([15.0]), 20.0
    )

    assert result == (False, None)


def test_stochastic_sell_signal_by_maximum_returns_true():
    strategy = SimpleNamespace(
        stoch_fast_maximo=True,
        stoch_fast_maximo_STATE=True,
        stoch_fast_descendente=False,
        stoch_fast_descendente_STATE=False,
    )

    assert Filtro_Stochastic.check_oscillator_sell_signal(strategy, "stoch_fast") == (
        True,
        "Stoch Fast Máximo/Descendente",
    )


def test_stochastic_sell_signal_by_descending_returns_true():
    strategy = SimpleNamespace(
        stoch_fast_maximo=False,
        stoch_fast_maximo_STATE=False,
        stoch_fast_descendente=True,
        stoch_fast_descendente_STATE=True,
    )

    assert Filtro_Stochastic.check_oscillator_sell_signal(strategy, "stoch_fast") == (
        True,
        "Stoch Fast Máximo/Descendente",
    )


def test_stochastic_sell_signal_without_settings_returns_false():
    strategy = SimpleNamespace()

    assert Filtro_Stochastic.check_oscillator_sell_signal(strategy, "stoch_fast") == (
        False,
        None,
    )


def test_atr_filter_disabled_allows_entry():
    strategy = SimpleNamespace(atr_enabled=False)

    assert Filtro_ATR.apply_atr_range_filter(strategy) == (True, None)


def test_atr_filter_allows_value_inside_range(monkeypatch):
    strategy = SimpleNamespace(
        atr_enabled=True,
        atr_period=14,
        atr_min=2.0,
        atr_max=5.0,
        data=SimpleNamespace(df=pd.DataFrame({"Close": [100.0]})),
    )
    monkeypatch.setattr(Filtro_ATR, "calculate_atr", lambda data, period: pd.Series([3.0]))

    assert Filtro_ATR.apply_atr_range_filter(strategy) == (True, "ATR en rango [2.00-5.00]")


def test_atr_filter_blocks_value_outside_range(monkeypatch):
    strategy = SimpleNamespace(
        atr_enabled=True,
        atr_period=14,
        atr_min=2.0,
        atr_max=5.0,
        data=SimpleNamespace(df=pd.DataFrame({"Close": [100.0]})),
    )
    monkeypatch.setattr(Filtro_ATR, "calculate_atr", lambda data, period: pd.Series([6.0]))

    assert Filtro_ATR.apply_atr_range_filter(strategy) == (
        False,
        "ATR 6.00 > Máximo 5.00 (exceso volatilidad)",
    )


def test_volume_filter_disabled_allows_entry():
    strategy = SimpleNamespace(volume_active=False)

    assert Filtro_Volume.apply_volume_filter(strategy) == (True, None)


def test_volume_filter_allows_valid_volume():
    strategy = SimpleNamespace(
        volume_active=True,
        volume_series=np.array([100.0]),
        data=SimpleNamespace(Volume=np.array([150.0])),
        volume_avg_multiplier=1.2,
        volume_minimo=False,
        volume_maximo=False,
        volume_ascendente=False,
        volume_descendente=False,
    )

    assert Filtro_Volume.apply_volume_filter(strategy) == (True, "Volumen Ok (x1.5)")


def test_volume_filter_blocks_invalid_volume():
    strategy = SimpleNamespace(
        volume_active=True,
        volume_series=np.array([100.0]),
        data=SimpleNamespace(Volume=np.array([110.0])),
        volume_avg_multiplier=1.2,
        volume_minimo=False,
        volume_maximo=False,
        volume_ascendente=False,
        volume_descendente=False,
    )

    assert Filtro_Volume.apply_volume_filter(strategy) == (
        False,
        "Volumen Bajo (110 < 120)",
    )
