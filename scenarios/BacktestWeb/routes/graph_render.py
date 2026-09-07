import json

from bokeh.embed import file_html
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure
from bokeh.resources import CDN

from .helpers import _parse_iso_datetimes


GRAPH_SNAPSHOT_PREFIX = "__GRAPH_SNAPSHOT_JSON__:"


def _extract_graph_snapshot_payload_from_db(resultado):
    raw_blob = (resultado.grafico_html or '').strip()
    if not raw_blob:
        return None
    if raw_blob.startswith(GRAPH_SNAPSHOT_PREFIX):
        raw_blob = raw_blob[len(GRAPH_SNAPSHOT_PREFIX):]
    else:
        # Si no tiene prefijo, asumimos legacy HTML y no snapshot JSON.
        return None
    try:
        payload = json.loads(raw_blob)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _render_bokeh_html_from_snapshot(snapshot_payload, resultado):
    ohlcv = snapshot_payload.get('ohlcv') or {}
    x = _parse_iso_datetimes(ohlcv.get('index'))
    o = ohlcv.get('open') or []
    h = ohlcv.get('high') or []
    l = ohlcv.get('low') or []
    c = ohlcv.get('close') or []

    n = min(len(x), len(o), len(h), len(l), len(c))
    if n <= 0:
        return None

    x = x[:n]
    o = o[:n]
    h = h[:n]
    l = l[:n]
    c = c[:n]

    valid_diffs = []
    prev = None
    for ts in x:
        if ts is not None and prev is not None:
            valid_diffs.append(max((ts - prev).total_seconds() * 1000.0, 1.0))
        if ts is not None:
            prev = ts
    candle_width = (valid_diffs[0] if valid_diffs else 24 * 60 * 60 * 1000) * 0.7

    up_idx, down_idx = [], []
    top, bottom = [], []
    for i in range(n):
        oi = o[i]
        ci = c[i]
        if oi is None or ci is None:
            top.append(oi if oi is not None else ci)
            bottom.append(ci if oi is not None else oi)
            down_idx.append(i)
            continue
        top.append(max(oi, ci))
        bottom.append(min(oi, ci))
        if ci >= oi:
            up_idx.append(i)
        else:
            down_idx.append(i)

    p_price = figure(
        x_axis_type='datetime',
        title=f"{resultado.symbol} | Precio",
        height=360,
        tools='pan,wheel_zoom,box_zoom,reset,save',
        sizing_mode='stretch_width',
    )
    p_price.segment(x, h, x, l, color='#6b7280')

    if up_idx:
        p_price.vbar(
            x=[x[i] for i in up_idx],
            width=candle_width,
            top=[top[i] for i in up_idx],
            bottom=[bottom[i] for i in up_idx],
            fill_color='#16a34a',
            line_color='#15803d',
        )
    if down_idx:
        p_price.vbar(
            x=[x[i] for i in down_idx],
            width=candle_width,
            top=[top[i] for i in down_idx],
            bottom=[bottom[i] for i in down_idx],
            fill_color='#dc2626',
            line_color='#b91c1c',
        )

    source = ColumnDataSource(data={'x': x, 'open': o, 'high': h, 'low': l, 'close': c})
    p_price.add_tools(HoverTool(
        tooltips=[('Fecha', '@x{%F %T}'), ('Open', '@open{0.00}'), ('High', '@high{0.00}'), ('Low', '@low{0.00}'), ('Close', '@close{0.00}')],
        formatters={'@x': 'datetime'},
        mode='vline',
    ))

    trades = snapshot_payload.get('trades') or {}
    entry_x = _parse_iso_datetimes(trades.get('entry_time'))
    entry_y = trades.get('entry_price') or []
    m = min(len(entry_x), len(entry_y))
    entries = [(entry_x[i], entry_y[i]) for i in range(m) if entry_x[i] is not None and entry_y[i] is not None]
    if entries:
        p_price.scatter(x=[p[0] for p in entries], y=[p[1] for p in entries], marker='triangle', size=8, color='#2563eb')

    eq = snapshot_payload.get('equity') or {}
    eq_x = _parse_iso_datetimes(eq.get('index'))
    eq_y = eq.get('equity') or []
    k = min(len(eq_x), len(eq_y))
    eq_points = [(eq_x[i], eq_y[i]) for i in range(k) if eq_x[i] is not None and eq_y[i] is not None]

    p_equity = figure(
        x_axis_type='datetime',
        title='Equity Curve',
        height=220,
        tools='pan,wheel_zoom,box_zoom,reset,save',
        sizing_mode='stretch_width',
        x_range=p_price.x_range,
    )
    if eq_points:
        p_equity.line([p[0] for p in eq_points], [p[1] for p in eq_points], line_width=2, color='#0ea5e9')

    dd_y = eq.get('drawdown_pct') or []
    d = min(len(eq_x), len(dd_y))
    dd_points = [(eq_x[i], dd_y[i]) for i in range(d) if eq_x[i] is not None and dd_y[i] is not None]
    p_dd = figure(
        x_axis_type='datetime',
        title='Drawdown %',
        height=180,
        tools='pan,wheel_zoom,box_zoom,reset,save',
        sizing_mode='stretch_width',
        x_range=p_price.x_range,
    )
    if dd_points:
        p_dd.line([p[0] for p in dd_points], [p[1] for p in dd_points], line_width=2, color='#f97316')

    return file_html(column(p_price, p_equity, p_dd, sizing_mode='stretch_width'), CDN, f"Backtest {resultado.symbol}")


def _read_graph_html_with_cache(resultado):
    # Modo sin cache de disco: reconstruir en cada visualizacion desde snapshot en BD.
    snapshot_payload = _extract_graph_snapshot_payload_from_db(resultado)
    if snapshot_payload:
        return _render_bokeh_html_from_snapshot(snapshot_payload, resultado)

    # Fallback legacy para registros historicos antiguos con HTML persistido.
    db_html = (resultado.grafico_html or '').strip()
    if db_html and not db_html.startswith(GRAPH_SNAPSHOT_PREFIX):
        return db_html

    return None
