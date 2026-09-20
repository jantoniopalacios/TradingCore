from types import SimpleNamespace

import numpy as np
import pandas as pd

from trading_engine.indicators import Filtro_ATR, Filtro_EMA, Filtro_MACD, Filtro_RSI
from trading_engine.indicators import Filtro_Stochastic, Filtro_Volume, Filtro_BollingerBands, Filtro_MoS
from trading_engine.core import Logica_Trading
from scenarios.BacktestWeb import estrategia_system


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


def test_macd_buy_cruce_up_returns_true_and_reason(monkeypatch):
    strategy = SimpleNamespace(
        macd=True,
        macd_buy_logic="macd_cruce_up",
        macd_line=pd.Series([0.0, 1.0]),
        macd_signal_line=pd.Series([1.0, 0.0]),
        macd_hist=pd.Series([-0.1, 0.2]),
    )
    monkeypatch.setattr(Filtro_MACD, "crossover", lambda line, signal: True)

    assert Filtro_MACD.check_macd_buy_signal(strategy, False) == (True, "MACD Cruce Up")


def test_macd_buy_histogram_crosses_from_negative_to_positive():
    strategy = SimpleNamespace(
        macd=True,
        macd_buy_logic="macd_histogram_buy",
        macd_hist=pd.Series([-0.2, 0.1]),
    )

    assert Filtro_MACD.check_macd_buy_signal(strategy, False) == (
        True,
        "MACD Histograma Buy",
    )


def test_macd_buy_histogram_requires_zero_crossing():
    strategy = SimpleNamespace(
        macd=True,
        macd_buy_logic="macd_histogram_buy",
        macd_hist=np.array([0.1, 0.2]),
    )

    assert Filtro_MACD.check_macd_buy_signal(strategy, False) == (False, None)


def test_macd_buy_none_disables_signal_even_if_crossover(monkeypatch):
    strategy = SimpleNamespace(
        macd=True,
        macd_buy_logic="None",
        macd_line=pd.Series([0.0, 1.0]),
        macd_signal_line=pd.Series([1.0, 0.0]),
        macd_hist=np.array([-0.2, 0.1]),
    )
    monkeypatch.setattr(Filtro_MACD, "crossover", lambda line, signal: True)

    assert Filtro_MACD.check_macd_buy_signal(strategy, False) == (False, None)


def test_macd_buy_none_preserves_existing_true_condition():
    strategy = SimpleNamespace(macd=True, macd_buy_logic="None")

    assert Filtro_MACD.check_macd_buy_signal(strategy, True) == (True, None)


def test_macd_sell_cruce_down_returns_true_and_reason(monkeypatch):
    strategy = SimpleNamespace(
        macd=True,
        macd_sell_logic="macd_cruce_down",
        macd_line=pd.Series([1.0, 0.0]),
        macd_signal_line=pd.Series([0.0, 1.0]),
    )
    monkeypatch.setattr(Filtro_MACD, "crossover", lambda signal, line: True)

    assert Filtro_MACD.check_macd_sell_signal(strategy) == (True, "MACD Cruce Down")


def test_macd_sell_histogram_crosses_from_positive_to_negative():
    strategy = SimpleNamespace(
        macd=True,
        macd_sell_logic="macd_histogram_sell",
        macd_hist=np.array([0.2, -0.1]),
    )

    assert Filtro_MACD.check_macd_sell_signal(strategy) == (
        True,
        "MACD Histograma Sell",
    )


def test_macd_sell_histogram_requires_zero_crossing():
    strategy = SimpleNamespace(
        macd=True,
        macd_sell_logic="macd_histogram_sell",
        macd_hist=np.array([-0.1, -0.2]),
    )

    assert Filtro_MACD.check_macd_sell_signal(strategy) == (False, None)


def test_macd_sell_none_disables_signal():
    strategy = SimpleNamespace(
        macd=True,
        macd_sell_logic="None",
        macd_hist=np.array([0.2, -0.1]),
    )

    assert Filtro_MACD.check_macd_sell_signal(strategy) == (False, None)


def test_macd_inactive_does_not_generate_buy_or_sell(monkeypatch):
    strategy = SimpleNamespace(
        macd=False,
        macd_buy_logic="macd_cruce_up",
        macd_sell_logic="macd_cruce_down",
        macd_line=pd.Series([0.0, 1.0]),
        macd_signal_line=pd.Series([1.0, 0.0]),
        macd_hist=np.array([-0.2, 0.1]),
    )
    monkeypatch.setattr(Filtro_MACD, "crossover", lambda a, b: True)

    assert Filtro_MACD.check_macd_buy_signal(strategy, False) == (False, None)
    assert Filtro_MACD.check_macd_sell_signal(strategy) == (False, None)


def test_macd_enabled_with_buy_none_keeps_buy_hold_fallback_available():
    strategy = SimpleNamespace(
        ema_cruce_signal=False,
        rsi=False,
        macd=True,
        macd_buy_logic="None",
        stoch_fast=False,
        stoch_mid=False,
        stoch_slow=False,
        bb_active=False,
    )

    assert Logica_Trading._has_technical_buy_signals_enabled(strategy) is False


def test_macd_window_kwargs_preserve_slow_fast_order():
    assert estrategia_system._macd_window_kwargs(12, 26) == {
        "window_slow": 26,
        "window_fast": 12,
    }


def test_stochastic_buy_minimum_logic_returns_true(monkeypatch):
    strategy = SimpleNamespace(
        stoch_fast_buy_logic="stoch_fast_minimo",
        stoch_fast_minimo_STATE=True,
        stoch_fast_ascendente_STATE=False,
    )

    monkeypatch.setattr(Filtro_Stochastic, "crossover", lambda k, d: True)

    result = Filtro_Stochastic.check_oscillator_buy_signal(
        strategy,
        "stoch_fast",
        np.array([10.0]),
        np.array([15.0]),
        20.0,
    )

    assert result == (True, "Stoch Fast Cruce & Mínimo")

def test_stochastic_buy_none_disables_signal(monkeypatch):
    strategy = SimpleNamespace(
        stoch_fast_buy_logic="None",
        stoch_fast_minimo_STATE=True,
        stoch_fast_ascendente_STATE=True,
    )

    monkeypatch.setattr(Filtro_Stochastic, "crossover", lambda k, d: True)

    result = Filtro_Stochastic.check_oscillator_buy_signal(
        strategy,
        "stoch_fast",
        np.array([10.0]),
        np.array([15.0]),
        20.0,
    )

    assert result == (False, None)

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

def test_stochastic_sell_none_disables_signal():
    strategy = SimpleNamespace(
        stoch_fast_sell_logic="None",
        stoch_fast_maximo_STATE=True,
        stoch_fast_descendente_STATE=True,
    )

    assert Filtro_Stochastic.check_oscillator_sell_signal(
        strategy,
        "stoch_fast",
    ) == (False, None)

def test_stochastic_sell_signal_by_maximum_returns_true():
    strategy = SimpleNamespace(
        stoch_fast_sell_logic="stoch_fast_maximo",
        stoch_fast_maximo_STATE=True,
        stoch_fast_descendente_STATE=False,
    )

    assert Filtro_Stochastic.check_oscillator_sell_signal(
        strategy,
        "stoch_fast",
    ) == (
        True,
        "Stoch Fast Máximo",
    )


def test_stochastic_sell_signal_by_descending_returns_true():
    strategy = SimpleNamespace(
        stoch_fast_sell_logic="stoch_fast_descendente",
        stoch_fast_maximo_STATE=False,
        stoch_fast_descendente_STATE=True,
    )

    assert Filtro_Stochastic.check_oscillator_sell_signal(
        strategy,
        "stoch_fast",
    ) == (
        True,
        "Stoch Fast Descendente",
    )

def test_stochastic_sell_signal_without_settings_returns_false():
    strategy = SimpleNamespace(
        stoch_fast_sell_logic="None",
        stoch_fast_maximo_STATE=True,
        stoch_fast_descendente_STATE=True,
    )

    assert Filtro_Stochastic.check_oscillator_sell_signal(
        strategy,
        "stoch_fast",
    ) == (False, None)

def test_stochastic_buy_none_is_not_technical_buy_signal():
    strategy = SimpleNamespace(
        stoch_fast=True,
        stoch_fast_buy_logic="None",
        stoch_mid=False,
        stoch_slow=False,
        ema_cruce_signal=False,
        rsi=False,
        macd=False,
        bb_active=False,
    )

    assert Logica_Trading._has_technical_buy_signals_enabled(strategy) is False

def test_stochastic_sell_helper_requires_enabled_variant():
    strategy = SimpleNamespace(
        stoch_fast=False,
        stoch_fast_sell_logic="stoch_fast_maximo",
    )

    assert (
        Logica_Trading._stoch_has_sell_signal_enabled(
            strategy,
            "stoch_fast",
        )
        is False
    )

def test_bollinger_without_buy_crossover_is_not_technical_buy_signal():
    strategy = SimpleNamespace(
        ema_cruce_signal=False,
        rsi=False,
        macd=False,
        stoch_fast=False,
        stoch_mid=False,
        stoch_slow=False,
        bb_active=True,
        bb_buy_crossover=False,
    )

    assert Logica_Trading._has_technical_buy_signals_enabled(strategy) is False

def test_bollinger_with_buy_crossover_is_technical_buy_signal():
    strategy = SimpleNamespace(
        ema_cruce_signal=False,
        rsi=False,
        macd=False,
        stoch_fast=False,
        stoch_mid=False,
        stoch_slow=False,
        bb_active=True,
        bb_buy_crossover=True,
    )

    assert Logica_Trading._has_technical_buy_signals_enabled(strategy) is True

def test_bollinger_buy_disabled_does_not_generate_signal(monkeypatch):
    strategy = SimpleNamespace(
        bb_active=True,
        bb_buy_crossover=False,
        data=SimpleNamespace(Close=np.array([90.0])),
        bb_lower_band_series=np.array([100.0]),
    )

    monkeypatch.setattr(Filtro_BollingerBands, "crossover", lambda a, b: True)

    assert Filtro_BollingerBands.check_bb_buy_signal(
        strategy,
        False,
    ) == (False, None)

def test_bollinger_buy_crossover_generates_signal(monkeypatch):
    strategy = SimpleNamespace(
        bb_active=True,
        bb_buy_crossover=True,
        data=SimpleNamespace(Close=np.array([90.0])),
        bb_lower_band_series=np.array([100.0]),
    )

    monkeypatch.setattr(Filtro_BollingerBands, "crossover", lambda a, b: True)

    assert Filtro_BollingerBands.check_bb_buy_signal(
        strategy,
        False,
    ) == (True, "BB Reversión desde Banda Inferior")

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

def test_mos_filter_disabled_allows_entry():
    strategy = SimpleNamespace(margen_seguridad_active=False)

    assert Filtro_MoS.apply_mos_filter(strategy) == (True, None)


def test_mos_filter_requires_value_above_threshold():
    strategy = SimpleNamespace(
        margen_seguridad_active=True,
        margen_seguridad_ind=np.array([40.0]),
        margen_seguridad_threshold=50.0,
        margen_seguridad_minimo=False,
        margen_seguridad_ascendente=False,
    )

    assert Filtro_MoS.apply_mos_filter(strategy) == (False, None)


def test_mos_filter_minimum_setting_requires_minimum_state():
    strategy = SimpleNamespace(
        margen_seguridad_active=True,
        margen_seguridad_ind=np.array([60.0]),
        margen_seguridad_threshold=50.0,
        margen_seguridad_minimo=True,
        margen_seguridad_minimo_STATE=False,
        margen_seguridad_ascendente=False,
    )

    assert Filtro_MoS.apply_mos_filter(strategy) == (False, None)

    strategy.margen_seguridad_minimo_STATE = True

    assert Filtro_MoS.apply_mos_filter(strategy) == (True, "MOS:60.0 Mínimo")


def test_mos_filter_combines_minimum_and_ascending_with_and():
    strategy = SimpleNamespace(
        margen_seguridad_active=True,
        margen_seguridad_ind=np.array([60.0]),
        margen_seguridad_threshold=50.0,
        margen_seguridad_minimo=True,
        margen_seguridad_minimo_STATE=True,
        margen_seguridad_ascendente=True,
        margen_seguridad_ascendente_STATE=False,
    )

    assert Filtro_MoS.apply_mos_filter(strategy) == (False, None)

    strategy.margen_seguridad_ascendente_STATE = True

    assert Filtro_MoS.apply_mos_filter(strategy) == (
        True,
        "MOS:60.0 Mínimo Ascendente",
    )


def test_mos_filter_active_without_data_blocks_entry():
    strategy = SimpleNamespace(
        margen_seguridad_active=True,
        margen_seguridad_ind=None,
    )

    assert Filtro_MoS.apply_mos_filter(strategy) == (False, "MOS Faltan Datos")

def test_volume_ma_uses_simple_moving_average():
    result = Filtro_Volume.calculate_volume_ma(pd.Series([1.0, 2.0, 3.0, 4.0]), 3)

    assert np.isnan(result.iloc[0])
    assert np.isnan(result.iloc[1])
    assert result.iloc[2] == 2.0
    assert result.iloc[3] == 3.0


def test_volume_state_ascending_uses_vma_trend_not_overshoot_count():
    strategy = SimpleNamespace(
        volume_active=True,
        volume_period=3,
        volume_series=np.array([100.0, 101.0, 102.0, 103.0]),
        volume_avg_multiplier=1.0,
        data=SimpleNamespace(Volume=np.array([10.0, 10.0, 10.0, 200.0])),
        volume_umbral_s=np.array([np.nan, np.nan, np.nan, np.nan]),
    )

    def fake_state(_series):
        return {"ascendente": True, "descendente": False}

    Filtro_Volume.update_volume_state(strategy, fake_state)

    assert strategy.volume_ascendente_STATE is True
    assert strategy.volume_descendente_STATE is False
    assert strategy.volume_minimo_STATE is False
    assert strategy.volume_maximo_STATE is True


def test_volume_filter_requires_selected_ascending_state():
    strategy = SimpleNamespace(
        volume_active=True,
        volume_series=np.array([100.0]),
        data=SimpleNamespace(Volume=np.array([150.0])),
        volume_avg_multiplier=1.2,
        volume_minimo=False,
        volume_maximo=False,
        volume_ascendente=True,
        volume_ascendente_STATE=False,
        volume_descendente=False,
    )

    assert Filtro_Volume.apply_volume_filter(strategy) == (
        False,
        "Volumen No Cumple Estado",
    )

    strategy.volume_ascendente_STATE = True
    assert Filtro_Volume.apply_volume_filter(strategy) == (True, "Volumen Ok (x1.5)")


def test_volume_filter_accepts_pandas_series_last_value():
    strategy = SimpleNamespace(
        volume_active=True,
        volume_series=pd.Series([100.0]),
        data=SimpleNamespace(Volume=pd.Series([150.0])),
        volume_avg_multiplier=1.2,
        volume_minimo=False,
        volume_maximo=False,
        volume_ascendente=False,
        volume_descendente=False,
    )

    assert Filtro_Volume.apply_volume_filter(strategy) == (True, "Volumen Ok (x1.5)")
