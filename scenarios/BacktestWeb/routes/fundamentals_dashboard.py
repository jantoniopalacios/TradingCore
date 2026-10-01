from __future__ import annotations

import logging
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from bokeh.embed import components
from bokeh.layouts import column, row
from bokeh.models import (
    CheckboxGroup,
    ColumnDataSource,
    CustomJS,
    Div,
    HoverTool,
    Legend,
    LegendItem,
    RadioButtonGroup,
)
from bokeh.palettes import Category10
from bokeh.plotting import figure
from bokeh.resources import CDN
from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for

from trading_engine.fundamentals.bootstrap import BootstrapStateStore
from trading_engine.fundamentals.legacy_adapter import build_legacy_eps_dataframe
from trading_engine.fundamentals.store import FundamentalStore, STORE_COLUMNS

from ..configuracion import (
    BACKTESTING_BASE_DIR,
    DATA_FILES_BASE_PATH,
    global_full_ratio_path,
)
from ..database import Simbolo, Usuario
from trading_engine.fundamentals.valuation_cache import (
    merge_valuation_rows,
    migrate_legacy_valuation_cache,
    persist_valuation_rows,
)


fundamentals_bp = Blueprint("fundamentals", __name__, url_prefix="/fundamentals")
logger = logging.getLogger(__name__)

VALUATION_COLUMNS = (
    "LTM EPS",
    "LTM EPS %",
    "PER",
    "PER M5Y",
    "% PER vs PER M5Y",
    "Margen de seguridad",
    "Full Ratio",
)


def _coverage_label(eps_periods):
    if eps_periods <= 0:
        return "Sin datos"
    if eps_periods < 4:
        return "Cobertura insuficiente"
    if eps_periods >= 20:
        return "Cobertura suficiente"
    return "Cobertura parcial"


def _current_user_and_symbols():
    if not session.get("logged_in"):
        return None, None, redirect(url_for("main.login"))

    username = str(session.get("user_mode") or "").strip().lower()
    user = Usuario.query.filter_by(username=username).first()
    if user is None:
        abort(403)

    configured_symbols = Simbolo.query.filter_by(usuario_id=user.id).order_by(
        Simbolo.symbol.asc()
    ).all()
    symbols = list(
        dict.fromkeys(
            str(item.symbol or "").strip().upper()
            for item in configured_symbols
            if str(item.symbol or "").strip()
        )
    )
    return user, symbols, None


def _selected_symbols_from_request():
    user, configured_symbols, response = _current_user_and_symbols()
    if response is not None:
        return None, None, (jsonify({"status": "error", "message": "No autenticado."}), 401)

    payload = request.get_json(silent=True)
    submitted = payload.get("symbols") if isinstance(payload, dict) else None
    if not isinstance(submitted, list) or any(not isinstance(symbol, str) for symbol in submitted):
        return None, None, (jsonify({"status": "error", "message": "Lista de símbolos inválida."}), 400)

    selected_symbols = list(dict.fromkeys(symbol.strip().upper() for symbol in submitted if symbol.strip()))
    if not selected_symbols:
        return None, None, (jsonify({"status": "error", "message": "No hay activos seleccionados."}), 400)

    unconfigured = sorted(set(selected_symbols) - set(configured_symbols))
    if unconfigured:
        return None, None, (
            jsonify({"status": "error", "message": "La selección contiene símbolos no configurados."}),
            403,
        )
    return user, selected_symbols, None


def _merge_selected_valuation_rows(existing, recalculated, selected_symbols):
    return merge_valuation_rows(existing, recalculated, selected_symbols)

def _persist_selected_valuation(full_ratio_path, recalculated, selected_symbols):
    return persist_valuation_rows(full_ratio_path, recalculated, selected_symbols)


def _load_saved_valuation(full_ratio_path, symbol):
    path = Path(full_ratio_path) / "FR_diario.csv"
    if not path.is_file():
        return None

    try:
        data = pd.read_csv(path, sep=";")
        if "Date" not in data.columns:
            first_column = data.columns[0] if len(data.columns) else None
            if first_column is None:
                return None
            data = data.rename(columns={first_column: "Date"})
        if "Symbol" not in data.columns:
            return None

        data["Symbol"] = data["Symbol"].astype(str).str.strip().str.upper()
        data = data[data["Symbol"] == symbol]
        if data.empty:
            return None

        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        data = data.dropna(subset=["Date"]).sort_values("Date")
        if data.empty:
            return None

        row = data.iloc[-1]
        return {
            "as_of": row["Date"].date().isoformat(),
            **{
                column: _display_number(row.get(column))
                for column in VALUATION_COLUMNS
            },
            "series": [
                {
                    "date": _format_date(item["Date"]),
                    "reported_date": _format_date(item.get("reportedDate")),
                    **{
                        column: _display_number(item.get(column))
                        for column in VALUATION_COLUMNS
                    },
                }
                for item in data.to_dict(orient="records")
            ],
        }
    except Exception:
        logger.exception("No se pudieron leer métricas Full Ratio guardadas para %s", symbol)
        return None


def _load_saved_recommendations(full_ratio_path):
    path = Path(full_ratio_path) / "FR_diario.csv"
    if not path.is_file():
        return {
            "as_of": None,
            "recommendations": {},
            "metrics": {},
            "valuation_symbols": set(),
        }

    try:
        data = pd.read_csv(path, sep=";")
        if "Date" not in data.columns:
            first_column = data.columns[0] if len(data.columns) else None
            if first_column is None:
                return {
                    "as_of": None,
                    "recommendations": {},
                    "metrics": {},
                    "valuation_symbols": set(),
                }
            data = data.rename(columns={first_column: "Date"})
        if "Symbol" not in data.columns:
            return {
                "as_of": None,
                "recommendations": {},
                "metrics": {},
                "valuation_symbols": set(),
            }

        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        data["Symbol"] = data["Symbol"].astype(str).str.strip().str.upper()
        data = data.dropna(subset=["Date"])
        if data.empty:
            return {
                "as_of": None,
                "recommendations": {},
                "metrics": {},
                "valuation_symbols": set(),
            }

        global_date = data["Date"].max()
        global_rows = data[data["Date"] == global_date].drop_duplicates(
            subset=["Symbol"], keep="last"
        )
        metrics_by_symbol = {
            str(row["Symbol"]).strip().upper(): {
                column: _display_number(row.get(column))
                for column in VALUATION_COLUMNS
            }
            for row in global_rows.to_dict(orient="records")
        }

        from trading_engine.utils.Calculos_Financieros import generar_seleccion_activos

        selection = generar_seleccion_activos(data.set_index("Date"), logger)
        if selection.empty or "Recomendación" not in selection.columns:
            recommendations = {}
        else:
            recommendations = {
                str(symbol).strip().upper(): str(recommendation)
                for symbol, recommendation in selection["Recomendación"].items()
            }
        return {
            "as_of": _format_date(global_date),
            "recommendations": recommendations,
            "metrics": metrics_by_symbol,
            "valuation_symbols": set(data["Symbol"].dropna()),
        }
    except Exception:
        logger.exception("No se pudieron leer recomendaciones Full Ratio guardadas")
        return {
            "as_of": None,
            "recommendations": {},
            "metrics": {},
            "valuation_symbols": set(),
        }


def _evaluation_status(
    eps_records,
    valid_periods,
    latest_reported_date,
    valuation_at_global_date,
    global_date,
):
    if eps_records.empty:
        return "No", "No hay EPS diluido en la caché fundamental normalizada."
    if latest_reported_date is None:
        return "No", "Falta reportedDate utilizable para evitar look-ahead."
    if valid_periods < 4:
        return "No", "Faltan 4 trimestres EPS válidos con reportedDate utilizable."

    if valuation_at_global_date is None:
        as_of_label = global_date or "la fecha global"
        if valid_periods < 20:
            return (
                "Parcial",
                f"No hay métricas guardadas para {as_of_label}; hay menos de 20 periodos EPS utilizables para formar 20 PER.",
            )
        return "Parcial", f"No hay valoración guardada para la fecha global {as_of_label}."

    if valuation_at_global_date.get("PER") is None:
        return "Parcial", "Falta PER válido en las métricas guardadas."
    if valuation_at_global_date.get("PER M5Y") is None:
        if valid_periods < 20:
            return (
                "Parcial",
                "Falta histórico EPS suficiente para formar los 20 PER requeridos por PER M5Y.",
            )
        return (
            "Parcial",
            "PER M5Y no está disponible; FR_diario.csv no permite distinguir si falta histórico PER válido o la métrica guardada.",
        )

    missing_metrics = [
        metric
        for metric in ("LTM EPS %", "Margen de seguridad", "Full Ratio")
        if valuation_at_global_date.get(metric) is None
    ]
    if missing_metrics:
        return "Parcial", "Faltan métricas calculadas: " + ", ".join(missing_metrics) + "."
    return "Sí", "Hay datos y métricas guardadas para una valoración completa."


def _short_valuation(recommendation):
    if not recommendation:
        return "No evaluable"
    if recommendation.startswith("Mantener"):
        return "Mantener"
    if recommendation.startswith("Desestimar"):
        return "Desestimar"
    return "No evaluable"


def _display_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _format_date(value):
    if value is None or pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.strftime("%Y-%m-%d")


def _format_datetime(value):
    if value is None or pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else parsed.isoformat()


def _saved_metric_series(valuation, metric):
    points = []
    for item in valuation.get("series", []) if valuation else []:
        value = _display_number(item.get(metric))
        date_value = pd.to_datetime(item.get("date"), errors="coerce")
        if value is None or pd.isna(date_value):
            continue
        points.append(
            {
                "date": date_value,
                "reported_date": item.get("reported_date") or "No disponible",
                "value": value,
            }
        )
    return points


def _build_chart_group(
    title,
    metrics,
    series_by_metric,
    default_metrics,
    x_axis_label,
    group_id,
):
    available = {
        metric: series_by_metric.get(metric, [])
        for metric in metrics
        if series_by_metric.get(metric)
    }
    if not available:
        return column(
            Div(text=f"<h3>{title}</h3>", name=f"{group_id}_title"),
            Div(
                text="Sin datos disponibles para este grupo",
                name=f"{group_id}_empty",
                styles={"color": "#64748b", "font-size": "12px"},
            ),
            name=group_id,
            sizing_mode="stretch_width",
        )

    selector = CheckboxGroup(
        labels=list(available),
        active=[
            index
            for index, metric in enumerate(available)
            if metric in default_metrics
        ],
        sizing_mode="stretch_width",
    )
    chart_type = RadioButtonGroup(
        labels=["Línea", "Puntos", "Línea + puntos"],
        active=2,
        sizing_mode="stretch_width",
    )
    plot = figure(
        x_axis_type="datetime",
        x_axis_label=x_axis_label,
        y_axis_label="Valor",
        height=300,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    palette = Category10[10]
    line_renderers = {}
    point_renderers = {}
    legend_items = []

    for index, (metric, points) in enumerate(available.items()):
        source = ColumnDataSource(
            {
                "date": [point["date"] for point in points],
                "reported_date": [point["reported_date"] for point in points],
                "value": [point["value"] for point in points],
            }
        )
        color = palette[index % len(palette)]
        selected = metric in default_metrics
        line_renderer = plot.line(
            x="date",
            y="value",
            source=source,
            line_width=2,
            color=color,
            visible=selected,
        )
        point_renderer = plot.scatter(
            x="date",
            y="value",
            source=source,
            size=7,
            color=color,
            visible=selected,
        )
        line_renderers[metric] = line_renderer
        point_renderers[metric] = point_renderer
        legend_items.append(
            LegendItem(label=metric, renderers=[line_renderer, point_renderer])
        )

    if legend_items:
        plot.add_layout(Legend(items=legend_items, click_policy="hide"), "right")
        plot.add_tools(
            HoverTool(
                tooltips=[
                    ("Fecha", "@date{%F}"),
                    ("Valor", "@value{0.00}"),
                    ("reportedDate", "@reported_date"),
                ],
                formatters={"@date": "datetime"},
                mode="vline",
            )
        )

    update_renderers = CustomJS(
        args={
            "metric_selector": selector,
            "chart_type": chart_type,
            "line_renderers": line_renderers,
            "point_renderers": point_renderers,
        },
        code="""
            const selected = new Set(
                metric_selector.active.map((index) => metric_selector.labels[index])
            );
            const mode = chart_type.active;
            for (const metric of Object.keys(line_renderers)) {
                const enabled = selected.has(metric);
                line_renderers[metric].visible = enabled && (mode === 0 || mode === 2);
                point_renderers[metric].visible = enabled && (mode === 1 || mode === 2);
            }
        """,
    )
    selector.js_on_change("active", update_renderers)
    chart_type.js_on_change("active", update_renderers)

    missing = [metric for metric in metrics if metric not in available]
    no_data = (
        Div(
            text="Sin datos disponibles: " + ", ".join(missing),
            styles={"color": "#64748b", "font-size": "12px"},
        )
        if missing
        else Div(text="", height=1)
    )
    controls = row(
        column(
            Div(
                text='<strong>Métricas</strong> <i class="bi bi-question-circle" tabindex="0" data-bs-toggle="tooltip" title="Selecciona una o varias métricas de este grupo; no se combinan grupos distintos."></i>'
            ),
            selector,
            sizing_mode="stretch_width",
        ),
        column(
            Div(
                text='<strong>Tipo de gráfico</strong> <i class="bi bi-question-circle" tabindex="0" data-bs-toggle="tooltip" title="Elige Línea, Puntos o Línea + puntos para las métricas seleccionadas."></i>'
            ),
            chart_type,
            sizing_mode="stretch_width",
        ),
        sizing_mode="stretch_width",
    )
    return column(
        Div(text=f"<h3>{title}</h3>", name=f"{group_id}_title"),
        controls,
        no_data,
        plot,
        name=group_id,
        sizing_mode="stretch_width",
    )


def _build_eps_chart_series(records):
    eps_series = []
    if not records.empty:
        eps = records[records["metric"] == "diluted_eps"].copy()
        eps["fiscal_date"] = pd.to_datetime(eps["fiscal_date"], errors="coerce")
        eps["reported_date"] = pd.to_datetime(eps["reported_date"], errors="coerce")
        eps["value"] = pd.to_numeric(eps["value"], errors="coerce")
        eps["_provider_priority"] = eps["provider"].map(
            {"yahoo": 0, "alpha_vantage": 1}
        ).fillna(2)
        eps = eps.dropna(subset=["fiscal_date", "reported_date", "value"])
        eps = eps[eps["value"].map(lambda value: np.isfinite(value))]
        eps = eps.sort_values(["fiscal_date", "_provider_priority", "updated_at"])
        eps = eps.drop_duplicates(subset=["fiscal_date"], keep="first")
        eps_series = [
            {
                "date": item["fiscal_date"],
                "reported_date": _format_date(item["reported_date"]),
                "value": float(item["value"]),
            }
            for item in eps.to_dict(orient="records")
        ]
    return eps_series


def _metric_chart_group_specs():
    return [
        {
            "group_id": "chart_group_a_benefit",
            "title": "Grupo A · Beneficio",
            "metrics": ("Diluted EPS", "LTM EPS"),
            "default_metrics": ("Diluted EPS",),
            "x_axis_label": "Fecha fiscal para Diluted EPS; fecha de mercado para métricas LTM",
        },
        {
            "group_id": "chart_group_b_per_valuation",
            "title": "Grupo B · Valoración PER",
            "metrics": ("PER", "PER M5Y"),
            "default_metrics": ("PER", "PER M5Y"),
            "x_axis_label": "Fecha de mercado",
        },
        {
            "group_id": "chart_group_c_growth_comparison",
            "title": "Grupo C · Crecimiento y comparación",
            "metrics": ("LTM EPS %", "% PER vs PER M5Y", "Margen de seguridad"),
            "default_metrics": ("LTM EPS %", "Margen de seguridad"),
            "x_axis_label": "Fecha de mercado",
        },
        {
            "group_id": "chart_group_d_full_ratio",
            "title": "Grupo D · Full Ratio",
            "metrics": ("Full Ratio",),
            "default_metrics": ("Full Ratio",),
            "x_axis_label": "Fecha de mercado",
        },
    ]


def _build_metric_charts(records, valuation):
    valuation_series = {
        metric: _saved_metric_series(valuation, metric)
        for metric in VALUATION_COLUMNS
    }
    series_by_metric = {
        **valuation_series,
        "Diluted EPS": _build_eps_chart_series(records),
    }
    groups = [
        _build_chart_group(
            **group_spec,
            series_by_metric=series_by_metric,
        )
        for group_spec in _metric_chart_group_specs()
    ]
    script, div = components(column(*groups, sizing_mode="stretch_width"))
    return script, div, CDN.render()


def _load_dashboard_rows(symbols, fundamentals_path, full_ratio_path):
    root = Path(fundamentals_path)
    store = FundamentalStore(root) if root.is_dir() else None
    bootstrap_path = root / "bootstrap_state.json"
    try:
        bootstrap_states = (
            BootstrapStateStore(bootstrap_path).load()
            if bootstrap_path.is_file()
            else {}
        )
    except Exception:
        logger.exception("No se pudo leer el estado persistente de bootstrap")
        bootstrap_states = {}

    saved_selection = _load_saved_recommendations(full_ratio_path)
    global_date = saved_selection["as_of"]
    dashboard_rows = []

    for symbol in symbols:
        records = store.load(symbol) if store is not None else pd.DataFrame(columns=STORE_COLUMNS)
        records = records.reindex(columns=STORE_COLUMNS)
        eps_records = records[records["metric"] == "diluted_eps"]
        fiscal_dates = pd.to_datetime(eps_records["fiscal_date"], errors="coerce").dropna()
        eps_periods = int(eps_records["fiscal_date"].nunique())

        valid_eps_records = eps_records[
            eps_records["provider"].isin(["yahoo", "alpha_vantage"])
        ].copy()
        valid_eps_records["reported_date"] = pd.to_datetime(
            valid_eps_records["reported_date"], errors="coerce"
        )
        valid_eps_records["fiscal_date"] = pd.to_datetime(
            valid_eps_records["fiscal_date"], errors="coerce"
        )
        valid_eps_records["value"] = pd.to_numeric(
            valid_eps_records["value"], errors="coerce"
        )
        valid_eps_records = valid_eps_records.dropna(
            subset=["reported_date", "fiscal_date", "value"]
        )
        finite_value_mask = valid_eps_records["value"].map(math.isfinite).astype(bool)
        valid_eps_records = valid_eps_records.loc[finite_value_mask]
        if not valid_eps_records.empty:
            valid_eps_records["_provider_priority"] = valid_eps_records[
                "provider"
            ].map({"yahoo": 0, "alpha_vantage": 1})
            valid_eps_records = valid_eps_records.sort_values(
                ["fiscal_date", "_provider_priority", "updated_at"],
                na_position="first",
            ).drop_duplicates(subset=["fiscal_date"], keep="first")

        valid_periods = int(valid_eps_records["fiscal_date"].nunique())
        latest_reported_date = (
            _format_date(valid_eps_records["reported_date"].max())
            if not valid_eps_records.empty
            else None
        )
        valuation_at_global_date = saved_selection["metrics"].get(symbol)
        per_m5y_available = bool(
            valuation_at_global_date
            and valuation_at_global_date.get("PER M5Y") is not None
        )
        full_ratio_metrics_available = bool(
            valuation_at_global_date
            and any(value is not None for value in valuation_at_global_date.values())
        )
        evaluation_status, evaluation_reason = _evaluation_status(
            eps_records,
            valid_periods,
            latest_reported_date,
            valuation_at_global_date,
            global_date,
        )
        saved_recommendation = saved_selection["recommendations"].get(symbol)
        state = bootstrap_states.get(symbol)

        dashboard_rows.append(
            {
                "symbol": symbol,
                "records": int(len(records)),
                "unique_fiscal_periods": eps_periods,
                "first_fiscal_date": (
                    fiscal_dates.min().date().isoformat()
                    if not fiscal_dates.empty
                    else None
                ),
                "last_fiscal_date": (
                    fiscal_dates.max().date().isoformat()
                    if not fiscal_dates.empty
                    else None
                ),
                "latest_reported_date": latest_reported_date,
                "providers": sorted(
                    records["provider"].dropna().astype(str).unique().tolist()
                ),
                "coverage_status": _coverage_label(eps_periods),
                "evaluation_status": evaluation_status,
                "evaluation_reason": evaluation_reason,
                "valuation_label": _short_valuation(saved_recommendation),
                "valuation_explanation": (
                    saved_recommendation or "No evaluable (Datos insuficientes)"
                ),
                "metrics": {
                    column: valuation_at_global_date.get(column)
                    if valuation_at_global_date is not None
                    else None
                    for column in VALUATION_COLUMNS
                },
                "valuation_as_of": global_date,
                "ltm_depth": (
                    "Suficiente (4 trimestres)"
                    if valid_periods >= 4
                    else "Insuficiente (<4)"
                ),
                "per_m5y_depth": (
                    "Suficiente (20 PER válidos)"
                    if per_m5y_available
                    else "Insuficiente (<20 PER válidos)"
                    if symbol in saved_selection["valuation_symbols"]
                    else "No calculado"
                ),
                "full_ratio_status": (
                    "Disponibles" if full_ratio_metrics_available else "No disponibles"
                ),
                "bootstrap_status": state.status if state is not None else "pending",
            }
        )

    return dashboard_rows


def _load_dashboard_data(symbols,fundamentals_path,full_ratio_path,build_charts=True):
    root = Path(fundamentals_path)
    store = FundamentalStore(root) if root.is_dir() else None
    bootstrap_path = root / "bootstrap_state.json"
    try:
        bootstrap_states = (
            BootstrapStateStore(bootstrap_path).load()
            if bootstrap_path.is_file()
            else {}
        )
    except Exception:
        logger.exception("No se pudo leer el estado persistente de bootstrap")
        bootstrap_states = {}
    saved_selection = _load_saved_recommendations(full_ratio_path)
    global_date = saved_selection["as_of"]
    dashboard_rows = []
    details = {}

    for symbol in symbols:
        records = store.load(symbol) if store is not None else pd.DataFrame(columns=STORE_COLUMNS)
        coverage = (
            store.coverage_summary(symbol)
            if store is not None
            else {
                "records": 0,
                "unique_fiscal_periods": 0,
                "first_fiscal_date": None,
                "last_fiscal_date": None,
                "providers": [],
            }
        )
        eps_records = records[records["metric"] == "diluted_eps"]
        eps_periods = int(coverage["unique_fiscal_periods"])
        adapted_eps = (
            build_legacy_eps_dataframe([symbol], root)
            if store is not None
            else pd.DataFrame(columns=["fiscalDateEnding", "Diluted EPS"])
        )
        valid_periods = int(adapted_eps["fiscalDateEnding"].nunique()) if not adapted_eps.empty else 0
        valuation = _load_saved_valuation(full_ratio_path, symbol)
        valuation_at_global_date = saved_selection["metrics"].get(symbol)
        per_m5y_available = bool(
            valuation_at_global_date
            and valuation_at_global_date.get("PER M5Y") is not None
        )
        full_ratio_metrics_available = bool(
            valuation_at_global_date
            and any(value is not None for value in valuation_at_global_date.values())
        )
        reported_dates = (
            pd.to_datetime(adapted_eps["reportedDate"], errors="coerce").dropna()
            if not adapted_eps.empty
            else pd.Series(dtype="datetime64[ns]")
        )
        latest_reported_date = (
            _format_date(reported_dates.max()) if not reported_dates.empty else None
        )
        state = bootstrap_states.get(symbol)
        bootstrap_status = state.status if state is not None else "pending"
        evaluation_status, evaluation_reason = _evaluation_status(
            eps_records,
            valid_periods,
            latest_reported_date,
            valuation_at_global_date,
            global_date,
        )
        saved_recommendation = saved_selection["recommendations"].get(symbol)

        row = {
            "symbol": symbol,
            "records": int(len(records)),
            "unique_fiscal_periods": eps_periods,
            "first_fiscal_date": coverage["first_fiscal_date"],
            "last_fiscal_date": coverage["last_fiscal_date"],
            "latest_reported_date": latest_reported_date,
            "providers": sorted(records["provider"].dropna().astype(str).unique().tolist()),
            "coverage_status": _coverage_label(eps_periods),
            "evaluation_status": evaluation_status,
            "evaluation_reason": evaluation_reason,
            "valuation_label": _short_valuation(saved_recommendation),
            "valuation_explanation": saved_recommendation or "No evaluable (Datos insuficientes)",
            "metrics": {
                column: valuation_at_global_date.get(column)
                if valuation_at_global_date is not None
                else None
                for column in VALUATION_COLUMNS
            },
            "valuation_as_of": global_date,
            "ltm_depth": "Suficiente (4 trimestres)" if valid_periods >= 4 else "Insuficiente (<4)",
            "per_m5y_depth": (
                "Suficiente (20 PER válidos)"
                if per_m5y_available
                else "Insuficiente (<20 PER válidos)"
                if valuation is not None
                else "No calculado"
            ),
            "full_ratio_status": (
                "Disponibles" if full_ratio_metrics_available else "No disponibles"
            ),
            "bootstrap_status": bootstrap_status,
        }
        dashboard_rows.append(row)

        eps_records = eps_records.sort_values(
            ["fiscal_date", "provider"]
        ) if not eps_records.empty else eps_records
        table_records = []
        for record in records.sort_values(
            ["fiscal_date", "metric", "provider"], na_position="last", ascending=[False, True, True]
        ).to_dict(orient="records"):
            reported_date = _format_date(record.get("reported_date"))
            table_records.append(
                {
                    "fiscal_date": _format_date(record.get("fiscal_date")) or "No disponible",
                    "reported_date": reported_date or "No disponible",
                    "availability": (
                        f"Disponible desde {reported_date}"
                        if reported_date
                        else "Sin reported_date; no disponible históricamente"
                    ),
                    "metric": record.get("metric") or "No disponible",
                    "value": _display_number(record.get("value")),
                    "provider": record.get("provider") or "No disponible",
                    "source_type": record.get("source_type") or "No disponible",
                    "updated_at": _format_datetime(record.get("updated_at")) or "No disponible",
                }
            )

        if build_charts:
            chart_script, chart_div, chart_resources = _build_metric_charts(
                records,
                valuation,
            )
        else:
            chart_script = None
            chart_div = None
            chart_resources = None

        details[symbol] = {
            "summary": row,
            "records": table_records,
            "missing_reported_date_count": int(eps_records["reported_date"].isna().sum()) if not eps_records.empty else 0,
            "valuation": valuation,
            "metrics": row["metrics"],
            "chart_script": chart_script,
            "chart_div": chart_div,
            "chart_resources": chart_resources,
        }

    return dashboard_rows, details


def _dashboard_paths(username):
    full_ratio_path = global_full_ratio_path(BACKTESTING_BASE_DIR)
    migrate_legacy_valuation_cache(
        full_ratio_path,
        BACKTESTING_BASE_DIR / "Run_Results",
    )
    return DATA_FILES_BASE_PATH / "Fundamentals", full_ratio_path


@fundamentals_bp.route("", methods=["GET"])
def dashboard():
    user, symbols, response = _current_user_and_symbols()
    if response is not None:
        return response

    try:
        fundamentals_path, full_ratio_path = _dashboard_paths(user.username)
        rows = _load_dashboard_rows(symbols, fundamentals_path, full_ratio_path)
    except Exception:
        logger.exception("No se pudo cargar el dashboard fundamental")
        rows = [
            {
                "symbol": symbol,
                "records": 0,
                "unique_fiscal_periods": 0,
                "first_fiscal_date": None,
                "last_fiscal_date": None,
                "latest_reported_date": None,
                "providers": [],
                "coverage_status": "Sin datos",
                "evaluation_status": "No",
                "evaluation_reason": "No hay fundamentales normalizados.",
                "valuation_label": "No evaluable",
                "valuation_explanation": "No evaluable (Datos insuficientes)",
                "metrics": {column: None for column in VALUATION_COLUMNS},
                "ltm_depth": "No disponible",
                "per_m5y_depth": "No calculado",
                "full_ratio_status": "No disponibles",
                "bootstrap_status": "pending",
            }
            for symbol in symbols
        ]

    return render_template(
        "fundamentals/dashboard.html",
        symbols=rows,
        user_name=user.username,
        sidebar_page="fundamentals",
        active_nav="fundamentals",
    )


@fundamentals_bp.route("/update", methods=["POST"])
def update_selected_fundamentals():
    user, symbols, error = _selected_symbols_from_request()
    if error is not None:
        return error

    try:
        fundamentals_path, _ = _dashboard_paths(user.username)
        results = _update_normalized_fundamentals(symbols, fundamentals_path)
        if not results:
            return jsonify({"status": "error", "message": "No se recibieron resultados de actualización."}), 500

        errors, no_data, updated_count, quota_blocked_count = _update_result_counts(results)
        if errors or no_data or quota_blocked_count:
            message = (
                f"Actualización parcial: {updated_count} activos actualizados · "
            f"{errors + no_data + quota_blocked_count} con error, sin datos o bloqueados por cuota."
            )
            status = "partial"
        else:
            message = f"Fundamentales actualizados para {updated_count} activos."
            status = "success"
        return jsonify({"status": status, "message": message, "processed": len(results)})
    except Exception:
        logger.exception("No se pudieron actualizar fundamentales desde el dashboard")
        return jsonify({"status": "error", "message": "No se pudieron actualizar los fundamentales."}), 500


@fundamentals_bp.route("/evaluate", methods=["POST"])
def evaluate_selected_fundamentals():
    user, symbols, error = _selected_symbols_from_request()
    if error is not None:
        return error

    try:
        fundamentals_path, full_ratio_path = _dashboard_paths(user.username)
        evaluation = _evaluate_selected_symbols(
            symbols,
            fundamentals_path,
            full_ratio_path,
            use_legacy_eps=True,
        )
        evaluated_count = evaluation["evaluated_count"]
        insufficient_count = evaluation["insufficient_count"]
        if insufficient_count:
            message = (
                f"{evaluated_count} evaluados · {insufficient_count} con datos insuficientes. "
                "Actualiza fundamentales para completar la valoración."
            )
            status = "partial"
        else:
            message = f"{evaluated_count} activos evaluados."
            status = "success"
        return jsonify(
            {
                "status": status,
                "message": message,
                "evaluated": evaluated_count,
                "insufficient": insufficient_count,
                "rows": evaluation["rows"],
            }
        )
    except Exception:
        logger.exception("No se pudieron evaluar fundamentales desde el dashboard")
        return jsonify({"status": "error", "message": "No se pudo completar la evaluación."}), 500


def _update_normalized_fundamentals(symbols, fundamentals_path):
    from trading_engine.utils.Data_download import update_normalized_fundamentals

    return update_normalized_fundamentals(symbols, fundamentals_path)


def _update_result_counts(results):
    errors = sum(
        result.yahoo_status == "error"
        or result.bootstrap_status == "error"
        for result in results
    )
    no_data = sum(result.yahoo_status == "no_data" for result in results)
    updated_count = sum(
        result.yahoo_status in {"updated", "no_new_data"}
        for result in results
    )
    quota_blocked_count = sum(
        result.bootstrap_status == "quota_blocked"
        for result in results
    )
    return errors, no_data, updated_count, quota_blocked_count


def _build_normalized_eps_dataframe(symbols, fundamentals_path):
    frames = []
    store = FundamentalStore(fundamentals_path)

    for symbol in symbols:
        records = store.load(symbol).reindex(columns=STORE_COLUMNS)
        records = records[
            (records["metric"] == "diluted_eps")
            & records["provider"].isin(["yahoo", "alpha_vantage"])
        ].copy()
        if records.empty:
            continue

        records["reported_date"] = pd.to_datetime(
            records["reported_date"], errors="coerce"
        )
        records["fiscal_date"] = pd.to_datetime(
            records["fiscal_date"], errors="coerce"
        )
        records["value"] = pd.to_numeric(records["value"], errors="coerce")
        records = records.dropna(
            subset=["reported_date", "fiscal_date", "value"]
        )
        records = records[records["value"].map(math.isfinite)]
        if records.empty:
            continue

        records["_provider_priority"] = records["provider"].map(
            {"yahoo": 0, "alpha_vantage": 1}
        )
        records = records.sort_values(
            ["fiscal_date", "_provider_priority", "updated_at"],
            na_position="first",
        ).drop_duplicates(subset=["fiscal_date"], keep="first")
        records["Symbol"] = symbol
        records["fiscalDateEnding"] = records["fiscal_date"]
        records["reportedDate"] = records["reported_date"]
        records["Diluted EPS"] = records["value"]
        frames.append(
            records[["Symbol", "fiscalDateEnding", "reportedDate", "Diluted EPS"]]
        )

    columns = ["Symbol", "fiscalDateEnding", "reportedDate", "Diluted EPS"]
    if not frames:
        return pd.DataFrame(columns=columns)
    return (
        pd.concat(frames, ignore_index=True)
        .sort_values(["Symbol", "fiscalDateEnding"])
        .reset_index(drop=True)
    )


def _evaluate_selected_symbols(
    symbols,
    fundamentals_path,
    full_ratio_path,
    *,
    use_legacy_eps,
):
    from trading_engine.utils.Calculos_Financieros import (
        calcular_fullratio_OHLCV,
        generar_seleccion_activos,
    )
    from trading_engine.utils.Data_download import load_or_download_full_ohlcv

    financial_data = (
        build_legacy_eps_dataframe(symbols, fundamentals_path)
        if use_legacy_eps
        else _build_normalized_eps_dataframe(symbols, fundamentals_path)
    )
    periods_by_symbol = (
        financial_data.groupby("Symbol")["fiscalDateEnding"].nunique()
        if not financial_data.empty
        else pd.Series(dtype="int64")
    )
    eligible_symbols = [
        symbol for symbol in symbols if int(periods_by_symbol.get(symbol, 0)) >= 4
    ]
    insufficient_symbols = set(symbols) - set(eligible_symbols)

    ohlcv_data = (
        load_or_download_full_ohlcv(
            eligible_symbols,
            intervalo="1d",
            data_files_path=DATA_FILES_BASE_PATH,
        )
        if eligible_symbols
        else pd.DataFrame()
    )
    price_symbols = (
        set(ohlcv_data["Symbol"].dropna().astype(str).str.upper())
        if not ohlcv_data.empty and "Symbol" in ohlcv_data.columns
        else set()
    )
    insufficient_symbols.update(set(eligible_symbols) - price_symbols)

    recalculated = pd.DataFrame()
    selection = pd.DataFrame()
    if price_symbols:
        evaluation_financials = financial_data[
            financial_data["Symbol"].isin(price_symbols)
        ].copy()
        evaluation_ohlcv = ohlcv_data[
            ohlcv_data["Symbol"].astype(str).str.upper().isin(price_symbols)
        ].copy()
        recalculated = calcular_fullratio_OHLCV(
            evaluation_ohlcv,
            evaluation_financials,
        )
        if not recalculated.empty:
            selection = generar_seleccion_activos(recalculated, logger)

    merged = _persist_selected_valuation(full_ratio_path, recalculated, symbols)
    recommendations = (
        selection["Recomendación"].to_dict()
        if not selection.empty and "Recomendación" in selection.columns
        else {}
    )
    evaluated_count = sum(
        str(recommendation).startswith(("Mantener", "Desestimar"))
        for recommendation in recommendations.values()
    )
    insufficient_count = max(
        len(symbols) - evaluated_count,
        len(insufficient_symbols),
    )
    return {
        "evaluated_count": evaluated_count,
        "insufficient_count": insufficient_count,
        "rows": len(merged),
    }


@fundamentals_bp.route("/update-and-evaluate", methods=["POST"])
def update_and_evaluate_selected_fundamentals():
    user, symbols, error = _selected_symbols_from_request()
    if error is not None:
        return error

    try:
        fundamentals_path, full_ratio_path = _dashboard_paths(user.username)
        update_results = _update_normalized_fundamentals(
            symbols,
            fundamentals_path,
        )
        update_unavailable = not update_results
        update_results = update_results or []
        errors, no_data, updated_count, quota_blocked_count = _update_result_counts(
            update_results
        )
        evaluation = _evaluate_selected_symbols(
            symbols,
            fundamentals_path,
            full_ratio_path,
            use_legacy_eps=False,
        )
        evaluated_count = evaluation["evaluated_count"]
        insufficient_count = evaluation["insufficient_count"]
        api_key_configured = bool(os.getenv("ALPHA_VANTAGE_KEY"))
        is_partial = bool(
            update_unavailable
            or quota_blocked_count
            or errors
            or no_data
            or insufficient_count
            or evaluated_count < len(symbols)
        )

        if quota_blocked_count and evaluated_count:
            if insufficient_count:
                message = (
                    f"{evaluated_count} activos evaluados. Alpha Vantage ha alcanzado "
                    f"la cuota diaria; {insufficient_count} activos quedan pendientes "
                    "de histórico."
                )
            else:
                message = (
                    f"{evaluated_count} activos evaluados. Alpha Vantage ha alcanzado "
                    "la cuota diaria; se usaron los datos disponibles de Yahoo y la caché local."
                )
        elif quota_blocked_count:
            message = (
                "Alpha Vantage ha alcanzado la cuota diaria. Se han utilizado los datos "
                "disponibles de Yahoo y la caché local. Algunos activos pueden quedar "
                "pendientes de histórico."
            )
        elif insufficient_count and not api_key_configured:
            message = (
                f"{evaluated_count} activos evaluados. {insufficient_count} activos "
                "quedan pendientes por falta de histórico suficiente; se han usado "
                "Yahoo y la caché local."
            )
        elif is_partial:
            if update_unavailable:
                message = (
                    f"{evaluated_count} activos evaluados con la caché local. "
                    "No se pudo completar la actualización de fundamentales."
                )
            else:
                message = (
                    f"{evaluated_count} activos evaluados. {insufficient_count} activos "
                    "quedan pendientes; se han utilizado los datos fundamentales disponibles."
                )
        else:
            message = (
                f"Actualización y evaluación completadas: {updated_count} activos "
                f"actualizados y {evaluated_count} evaluados."
            )

        return jsonify(
            {
                "status": "partial" if is_partial else "success",
                "message": message,
                "updated_count": updated_count,
                "evaluated_count": evaluated_count,
                "insufficient_count": insufficient_count,
                "quota_blocked_count": quota_blocked_count,
            }
        )
    except Exception:
        logger.exception("No se pudo actualizar y evaluar fundamentales desde el dashboard")
        return jsonify(
            {
                "status": "error",
                "message": "No se pudo completar la actualización y evaluación.",
                "updated_count": 0,
                "evaluated_count": 0,
                "insufficient_count": len(symbols),
                "quota_blocked_count": 0,
            }
        ), 500


@fundamentals_bp.route("/<symbol>", methods=["GET"])
def symbol_detail(symbol):
    user, symbols, response = _current_user_and_symbols()
    if response is not None:
        return response

    normalized_symbol = str(symbol).strip().upper()
    if normalized_symbol not in symbols:
        abort(404)

    try:
        fundamentals_path, full_ratio_path = _dashboard_paths(user.username)
        _, details = _load_dashboard_data(
            [normalized_symbol],
            fundamentals_path,
            full_ratio_path,
        )
        detail = details[normalized_symbol]
    except Exception:
        logger.exception("No se pudo cargar el detalle fundamental de %s", normalized_symbol)
        detail = {
            "summary": {
                "symbol": normalized_symbol,
                "latest_reported_date": None,
                "evaluation_status": "No",
                "evaluation_reason": "No se pudo leer la caché normalizada.",
                "valuation_label": "No evaluable",
                "valuation_explanation": "No evaluable (Datos insuficientes)",
                "coverage_status": "Sin datos",
                "unique_fiscal_periods": 0,
                "first_fiscal_date": None,
                "last_fiscal_date": None,
                "providers": [],
                "ltm_depth": "No disponible",
                "per_m5y_depth": "No calculado",
                "full_ratio_status": "No disponibles",
                "bootstrap_status": "pending",
            },
            "records": [],
            "missing_reported_date_count": 0,
            "valuation": None,
            "metrics": {column: None for column in VALUATION_COLUMNS},
            "chart_script": None,
            "chart_div": None,
            "chart_resources": None,
        }

    return render_template(
        "fundamentals/detail.html",
        detail=detail,
        user_name=user.username,
        sidebar_page="fundamentals",
        active_nav="fundamentals",
    )