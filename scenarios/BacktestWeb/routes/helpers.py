import json
from datetime import datetime


def _is_enabled(value):
    """Normaliza flags bool que pueden venir como bool, numero o texto."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'on', 'yes', 'si', 'sí'}
    return bool(value)


def _build_strategy_short_title(result_row):
    """Genera un titulo corto y legible para el historial SQL a partir de params_tecnicos."""
    try:
        params = json.loads(result_row.params_tecnicos) if result_row.params_tecnicos else {}
    except Exception:
        params = {}

    indicators = []
    if _is_enabled(params.get('ema_cruce_signal')) or any(_is_enabled(params.get(k)) for k in ('ema_slow_minimo', 'ema_slow_maximo', 'ema_slow_ascendente', 'ema_slow_descendente')):
        indicators.append('EMA')
    if _is_enabled(params.get('rsi')):
        indicators.append('RSI')
    if _is_enabled(params.get('macd')):
        indicators.append('MACD')
    if any(_is_enabled(params.get(k)) for k in ('stoch_fast', 'stoch_mid', 'stoch_slow')):
        indicators.append('STOCH')
    if _is_enabled(params.get('bb_active')):
        indicators.append('BB')

    risk_flags = []
    if _is_enabled(params.get('breakeven_enabled')):
        risk_flags.append('BE')
    if _is_enabled(params.get('stoploss_swing_enabled')):
        risk_flags.append('SWING')
    if _is_enabled(params.get('rsi')) and params.get('rsi_trailing_limit') is not None and (
        params.get('trailing_pct_below') is not None or params.get('trailing_pct_above') is not None
    ):
        risk_flags.append('TSL-RSI')

    core = '+'.join(indicators) if indicators else 'BASE'
    risk = f" | {'/'.join(risk_flags)}" if risk_flags else ''
    interval_value = (
        params.get('INTERVAL')
        or params.get('interval')
        or params.get('intervalo')
        or getattr(result_row, 'intervalo', None)
    )
    interval = f" ({interval_value})" if interval_value else ''

    title = f"{core}{risk}{interval}"
    return title[:56] + '...' if len(title) > 59 else title


def _build_strategy_short_title_from_params(params):
    class _ResultProxy:
        params_tecnicos = json.dumps(params, ensure_ascii=False)
        intervalo = params.get('intervalo')

    return _build_strategy_short_title(_ResultProxy())


def _sanitize_filename_component(value):
    cleaned = ''.join(ch if ch.isalnum() or ch in ('-', '_', '+', '(', ')') else '-' for ch in str(value or '').strip())
    while '--' in cleaned:
        cleaned = cleaned.replace('--', '-')
    return cleaned.strip('-_') or 'config'


def _normalize_symbol_token(value):
    token = str(value or '').strip().upper()
    if not token:
        return ''
    allowed = ''.join(ch for ch in token if ch.isascii() and (ch.isalnum() or ch in ('.', '-', '_', '^', '=')))
    return allowed.strip()


def _parse_iso_datetimes(values):
    out = []
    for v in values or []:
        if not v:
            out.append(None)
            continue
        try:
            out.append(datetime.fromisoformat(str(v).replace('Z', '+00:00')))
        except Exception:
            out.append(None)
    return out


def _scheduler_trigger_label(intervalo: str) -> str:
    """Etiqueta legible de trigger para el dashboard sin depender del proceso scheduler."""
    v = str(intervalo or '').strip().lower()
    minute_map = {
        '1m': 1,
        '2m': 2,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '60m': 60,
        '1h': 60,
        '90m': 90,
    }
    if v in minute_map:
        mins = minute_map[v]
        hours = mins // 60
        rem = mins % 60
        if rem == 0:
            return f"interval[{hours}:00:00]"
        return f"interval[0:{rem:02d}:00]"
    if v == '1d':
        return "cron[mon-fri 22:00 Europe/Madrid]"
    if v == '1wk':
        return "cron[mon 09:00 Europe/Madrid]"
    if v == '1mo':
        return "cron[day=1 09:00 Europe/Madrid]"
    return "cron[mon-fri 22:00 Europe/Madrid]"