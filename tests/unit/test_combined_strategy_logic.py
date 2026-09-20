from types import SimpleNamespace

import numpy as np
import pandas as pd

from trading_engine.core import Logica_Trading


class FakePosition:
    def __init__(self, active=False):
        self.active = active
        self.close_calls = 0

    def __bool__(self):
        return self.active

    def close(self):
        self.close_calls += 1
        self.active = False


def _base_strategy(*, position_active=False):
    strategy = SimpleNamespace(
        position=FakePosition(position_active),
        ticker="TEST",
        data=SimpleNamespace(
            Close=np.array([100.0]),
            High=np.array([101.0]),
            Low=np.array([99.0]),
            index=pd.DatetimeIndex(["2026-01-01"]),
        ),
        trades=[],
        trades_list=[],
        max_price=100.0,
        my_stop_loss=90.0,
        stoploss_percentage_below_close=0.10,
        stoploss_swing_enabled=False,
        breakeven_enabled=False,
        ema_cruce_signal=False,
        ema_slow_minimo=False,
        ema_slow_maximo=False,
        ema_slow_ascendente=False,
        ema_slow_descendente=False,
        ema_slow_minimo_STATE=False,
        ema_slow_maximo_STATE=False,
        ema_slow_ascendente_STATE=False,
        ema_slow_descendente_STATE=False,
        rsi=False,
        rsi_ind=None,
        rsi_minimo=False,
        rsi_ascendente=False,
        macd=False,
        macd_buy_logic="None",
        macd_sell_logic="None",
        stoch_fast=False,
        stoch_fast_buy_logic="None",
        stoch_fast_sell_logic="None",
        stoch_k_fast=np.array([10.0]),
        stoch_d_fast=np.array([15.0]),
        stoch_fast_low_level=20.0,
        stoch_mid=False,
        stoch_mid_buy_logic="None",
        stoch_mid_sell_logic="None",
        stoch_k_mid=np.array([10.0]),
        stoch_d_mid=np.array([15.0]),
        stoch_mid_low_level=20.0,
        stoch_slow=False,
        stoch_slow_buy_logic="None",
        stoch_slow_sell_logic="None",
        stoch_k_slow=np.array([10.0]),
        stoch_d_slow=np.array([15.0]),
        stoch_slow_low_level=20.0,
        bb_active=False,
        bb_buy_crossover=False,
        atr_enabled=False,
        volume_active=False,
        margen_seguridad_active=False,
    )
    strategy.buy_calls = 0

    def buy():
        strategy.buy_calls += 1

    strategy.buy = buy
    return strategy


def _patch_buy_pipeline(
    monkeypatch,
    *,
    ema_signal=False,
    rsi_signal=False,
    macd_signal=False,
    stoch_signal=False,
    bb_signal=False,
    ema_filter=True,
    rsi_filter=True,
    atr_filter=True,
    volume_filter=True,
    mos_filter=True,
):
    monkeypatch.setattr(Logica_Trading, "_actualizar_estados_indicadores", lambda strategy: None)
    monkeypatch.setattr(Logica_Trading, "_build_signal_context", lambda *args, **kwargs: "{}")
    monkeypatch.setattr(
        Logica_Trading,
        "check_ema_buy_signal",
        lambda strategy, current: (current or ema_signal, "EMA test" if ema_signal else None),
    )
    monkeypatch.setattr(
        Logica_Trading,
        "check_rsi_buy_signal",
        lambda strategy, current: (current or rsi_signal, "RSI test" if rsi_signal else None),
    )
    monkeypatch.setattr(
        Logica_Trading,
        "check_macd_buy_signal",
        lambda strategy, current: (current or macd_signal, "MACD test" if macd_signal else None),
    )
    monkeypatch.setattr(
        Logica_Trading,
        "check_oscillator_buy_signal",
        lambda strategy, prefix, k, d, level: (stoch_signal, "Stoch test" if stoch_signal else None),
    )
    monkeypatch.setattr(
        Logica_Trading,
        "check_bb_buy_signal",
        lambda strategy, current: (current or bb_signal, "BB test" if bb_signal else None),
    )
    monkeypatch.setattr(
        Logica_Trading,
        "apply_ema_global_filter",
        lambda strategy, current: current if ema_filter else False,
    )
    monkeypatch.setattr(Logica_Trading, "apply_rsi_global_filter", lambda strategy: rsi_filter)
    monkeypatch.setattr(
        Logica_Trading,
        "apply_atr_range_filter",
        lambda strategy: (atr_filter, "ATR test" if atr_filter else None),
    )
    monkeypatch.setattr(
        Logica_Trading,
        "apply_volume_filter",
        lambda strategy: (volume_filter, "Volume test" if volume_filter else None),
    )
    monkeypatch.setattr(
        Logica_Trading,
        "apply_mos_filter",
        lambda strategy: (mos_filter, "MOS test" if mos_filter else None),
    )


def test_combined_buy_signals_use_or(monkeypatch):
    strategy = _base_strategy()
    strategy.rsi = True
    strategy.rsi_minimo = True
    strategy.rsi_ind = np.array([55.0])

    _patch_buy_pipeline(monkeypatch, ema_signal=False, rsi_signal=True, macd_signal=False)

    Logica_Trading.check_buy_signal(strategy)

    assert strategy.buy_calls == 1


def test_combined_atr_filter_blocks_valid_technical_signal(monkeypatch):
    strategy = _base_strategy()
    strategy.ema_cruce_signal = True

    _patch_buy_pipeline(monkeypatch, ema_signal=True, atr_filter=False)

    Logica_Trading.check_buy_signal(strategy)

    assert strategy.buy_calls == 0


def test_combined_volume_filter_blocks_valid_technical_signal(monkeypatch):
    strategy = _base_strategy()
    strategy.ema_cruce_signal = True

    _patch_buy_pipeline(monkeypatch, ema_signal=True, volume_filter=False)

    Logica_Trading.check_buy_signal(strategy)

    assert strategy.buy_calls == 0


def test_combined_mos_filter_blocks_valid_technical_signal(monkeypatch):
    strategy = _base_strategy()
    strategy.ema_cruce_signal = True
    strategy.margen_seguridad_active = True

    _patch_buy_pipeline(monkeypatch, ema_signal=True, mos_filter=False)

    Logica_Trading.check_buy_signal(strategy)

    assert strategy.buy_calls == 0


def test_combined_all_active_filters_must_allow_entry(monkeypatch):
    strategy = _base_strategy()
    strategy.ema_cruce_signal = True
    strategy.rsi = True
    strategy.rsi_ind = np.array([55.0])
    strategy.volume_active = True
    strategy.margen_seguridad_active = True
    strategy.atr_enabled = True

    _patch_buy_pipeline(
        monkeypatch,
        ema_signal=True,
        ema_filter=True,
        rsi_filter=True,
        atr_filter=True,
        volume_filter=True,
        mos_filter=True,
    )

    Logica_Trading.check_buy_signal(strategy)

    assert strategy.buy_calls == 1


def test_combined_buy_hold_survives_indicators_with_buy_none(monkeypatch):
    strategy = _base_strategy()
    strategy.ema_slow_ascendente_STATE = True

    strategy.macd = True
    strategy.macd_buy_logic = "None"

    strategy.stoch_fast = True
    strategy.stoch_fast_buy_logic = "None"

    strategy.bb_active = True
    strategy.bb_buy_crossover = False

    _patch_buy_pipeline(monkeypatch)

    Logica_Trading.check_buy_signal(strategy)

    assert Logica_Trading._has_technical_buy_signals_enabled(strategy) is False
    assert strategy.buy_calls == 1


def test_combined_rsi_global_filter_blocks_buy_hold(monkeypatch):
    strategy = _base_strategy()
    strategy.ema_slow_minimo_STATE = True
    strategy.rsi = True
    strategy.rsi_ind = np.array([40.0])
    strategy.rsi_minimo = False
    strategy.rsi_ascendente = False

    _patch_buy_pipeline(monkeypatch, rsi_signal=False, rsi_filter=False)

    Logica_Trading.check_buy_signal(strategy)

    assert Logica_Trading._has_technical_buy_signals_enabled(strategy) is False
    assert strategy.buy_calls == 0


def test_combined_sell_signals_use_or_and_close_on_macd(monkeypatch):
    strategy = _base_strategy(position_active=True)
    strategy.macd = True
    strategy.macd_sell_logic = "macd_cruce_down"

    monkeypatch.setattr(Logica_Trading, "_actualizar_estados_indicadores", lambda strategy: None)
    monkeypatch.setattr(Logica_Trading, "_build_signal_context", lambda *args, **kwargs: "{}")
    monkeypatch.setattr(Logica_Trading, "check_ema_sell_signal", lambda strategy: (False, None))
    monkeypatch.setattr(Logica_Trading, "check_rsi_sell_signal", lambda strategy: (False, None))
    monkeypatch.setattr(
        Logica_Trading,
        "check_macd_sell_signal",
        lambda strategy: (True, "MACD test sell"),
    )
    monkeypatch.setattr(
        Logica_Trading,
        "check_oscillator_sell_signal",
        lambda strategy, prefix: (False, None),
    )
    monkeypatch.setattr(Logica_Trading, "check_bb_sell_signal", lambda strategy: (False, None))

    Logica_Trading.manage_existing_position(strategy)

    assert strategy.position.close_calls == 1
    assert strategy.trades_list[-1]["Tipo"] == "VENTA"
    assert strategy.trades_list[-1]["Descripcion"] == "MACD test sell"
# ---------------------------------------------------------------------------
# Stop management regression tests
# ---------------------------------------------------------------------------

def _patch_position_management(monkeypatch):
    monkeypatch.setattr(
        Logica_Trading,
        "_actualizar_estados_indicadores",
        lambda strategy: None,
    )
    monkeypatch.setattr(
        Logica_Trading,
        "_build_signal_context",
        lambda *args, **kwargs: "{}",
    )


def test_combined_trailing_base_raises_stop(monkeypatch):
    strategy = _base_strategy(position_active=True)
    strategy.data.Close = np.array([110.0])
    strategy.data.High = np.array([111.0])
    strategy.max_price = 100.0
    strategy.my_stop_loss = 90.0
    strategy.stoploss_percentage_below_close = 0.10

    _patch_position_management(monkeypatch)

    Logica_Trading.manage_existing_position(strategy)

    assert strategy.max_price == 110.0
    assert strategy.my_stop_loss == 99.0
    assert strategy.position.close_calls == 0


def test_combined_breakeven_can_dominate_trailing_base(monkeypatch):
    strategy = _base_strategy(position_active=True)
    strategy.max_price = 100.0
    strategy.my_stop_loss = 80.0
    strategy.stoploss_percentage_below_close = 0.10
    strategy.breakeven_enabled = True
    strategy.breakeven_trigger_pct = 0.02
    strategy.trades = [SimpleNamespace(entry_price=100.0)]

    _patch_position_management(monkeypatch)

    Logica_Trading.manage_existing_position(strategy)

    assert strategy.my_stop_loss == 98.0
    assert strategy.position.close_calls == 0


def test_combined_swing_can_dominate_trailing_and_breakeven(monkeypatch):
    strategy = _base_strategy(position_active=True)
    strategy.data.Low = np.array([100.0, 100.0])
    strategy.max_price = 100.0
    strategy.my_stop_loss = 80.0
    strategy.stoploss_percentage_below_close = 0.10
    strategy.breakeven_enabled = True
    strategy.breakeven_trigger_pct = 0.02
    strategy.trades = [SimpleNamespace(entry_price=100.0)]
    strategy.stoploss_swing_enabled = True
    strategy.stoploss_swing_lookback = 2
    strategy.stoploss_swing_buffer = 1.0

    _patch_position_management(monkeypatch)

    Logica_Trading.manage_existing_position(strategy)

    # Trailing = 90, break-even = 98 y swing = 99.
    assert strategy.my_stop_loss == 99.0
    assert strategy.position.close_calls == 0


def test_combined_stop_never_moves_down(monkeypatch):
    strategy = _base_strategy(position_active=True)
    strategy.max_price = 100.0
    strategy.my_stop_loss = 95.0
    strategy.stoploss_percentage_below_close = 0.10

    _patch_position_management(monkeypatch)

    Logica_Trading.manage_existing_position(strategy)

    # El candidato trailing seria 90, pero un stop ya situado en 95 no debe bajar.
    assert strategy.my_stop_loss == 95.0
    assert strategy.position.close_calls == 0
