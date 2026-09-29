from __future__ import annotations

import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd
from bokeh.embed import components
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.palettes import Category10
from bokeh.plotting import figure
from bokeh.resources import CDN
from flask import Blueprint, abort, redirect, render_template, session, url_for

from trading_engine.fundamentals.bootstrap import BootstrapStateStore
from trading_engine.fundamentals.legacy_adapter import build_legacy_eps_dataframe
from trading_engine.fundamentals.store import FundamentalStore, STORE_COLUMNS

from ..configuracion import BACKTESTING_BASE_DIR, DATA_FILES_BASE_PATH
from ..database import Simbolo, Usuario


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


def _coverage_label(has_eps_records, available_periods, per_m5y_available):
    if not has_eps_records:
        return "Sin datos"
    if available_periods < 4:
        return "Cobertura insuficiente"
    if per_m5y_available:
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
                    "date": item["Date"],
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


def _build_eps_chart(records, symbol):
    eps_values = pd.to_numeric(records["value"], errors="coerce")
    finite_eps = eps_values.map(lambda value: pd.notna(value) and np.isfinite(value))
    eps_records = records[
        (records["metric"] == "diluted_eps") & finite_eps
    ].copy()
    if eps_records.empty:
        return None, None, None

    eps_records["fiscal_date"] = pd.to_datetime(
        eps_records["fiscal_date"], errors="coerce"
    )
    eps_records["reported_date"] = pd.to_datetime(
        eps_records["reported_date"], errors="coerce"
    )
    eps_records["value"] = pd.to_numeric(eps_records["value"], errors="coerce")
    eps_records = eps_records.dropna(subset=["fiscal_date", "value"]).sort_values(
        "fiscal_date"
    )
    if eps_records.empty:
        return None, None, None

    providers = sorted(eps_records["provider"].dropna().astype(str).unique())
    palette = Category10[10]
    colors = {provider: palette[index % len(palette)] for index, provider in enumerate(providers)}
    chart = figure(
        title=f"Diluted EPS histórico · {symbol}",
        x_axis_type="datetime",
        x_axis_label="Fiscal date",
        y_axis_label="Diluted EPS",
        height=320,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    chart.add_tools(
        HoverTool(
            tooltips=[
                ("Fiscal date", "@fiscal_date{%F}"),
                ("Reported date", "@reported_date"),
                ("Diluted EPS", "@value{0.000}"),
                ("Proveedor", "@provider"),
                ("Origen", "@source_type"),
                ("Disponibilidad", "@availability"),
            ],
            formatters={"@fiscal_date": "datetime"},
        )
    )

    for provider in providers:
        provider_rows = eps_records[eps_records["provider"] == provider]
        for has_reported_date, marker in ((True, "circle"), (False, "triangle")):
            points = provider_rows[provider_rows["reported_date"].notna() == has_reported_date]
            if points.empty:
                continue
            source = ColumnDataSource(
                {
                    "fiscal_date": points["fiscal_date"],
                    "reported_date": points["reported_date"].map(
                        lambda value: _format_date(value) or "No disponible"
                    ),
                    "value": points["value"],
                    "provider": points["provider"],
                    "source_type": points["source_type"],
                    "availability": [
                        "Disponible desde reported_date"
                        if has_reported_date
                        else "Sin reported_date; no disponible históricamente"
                    ] * len(points),
                }
            )
            chart.scatter(
                x="fiscal_date",
                y="value",
                source=source,
                marker=marker,
                size=9,
                color=colors[provider],
                alpha=0.85,
                legend_label=provider,
            )

    chart.legend.click_policy = "hide"
    script, div = components(chart)
    return script, div, CDN.render()


def _build_valuation_charts(valuation, symbol):
    if not valuation or not valuation.get("series"):
        return None, None

    chart_columns = ("PER", "PER M5Y", "Margen de seguridad", "Full Ratio")
    plots = []
    shared_x_range = None
    series = valuation["series"]
    dates = [pd.Timestamp(item["date"]) for item in series]

    for column_name in chart_columns:
        points = [
            (date_value, item.get(column_name))
            for date_value, item in zip(dates, series)
            if item.get(column_name) is not None
        ]
        if not points:
            continue
        plot = figure(
            title=column_name,
            x_axis_type="datetime",
            x_axis_label="Fecha de mercado",
            height=210,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
            x_range=shared_x_range,
        )
        if shared_x_range is None:
            shared_x_range = plot.x_range
        plot.line(
            [point[0] for point in points],
            [point[1] for point in points],
            line_width=2,
            color="#2563eb" if column_name in {"PER", "PER M5Y"} else "#0f766e",
        )
        plot.add_tools(
            HoverTool(
                tooltips=[("Fecha", "@x{%F}"), (column_name, "@y{0.00}")],
                mode="vline",
            )
        )
        plots.append(plot)

    if not plots:
        return None, None
    script, div = components(column(*plots, sizing_mode="stretch_width"))
    return script, div


def _load_dashboard_data(symbols, fundamentals_path, full_ratio_path):
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
        adapted_eps = (
            build_legacy_eps_dataframe([symbol], root)
            if store is not None
            else pd.DataFrame(columns=["fiscalDateEnding", "Diluted EPS"])
        )
        valid_periods = int(adapted_eps["fiscalDateEnding"].nunique()) if not adapted_eps.empty else 0
        valuation = _load_saved_valuation(full_ratio_path, symbol)
        per_m5y_available = bool(
            valuation is not None and valuation.get("PER M5Y") is not None
        )
        reported_dates = pd.to_datetime(
            eps_records["reported_date"], errors="coerce"
        ).dropna()
        latest_reported_date = (
            _format_date(reported_dates.max()) if not reported_dates.empty else None
        )
        state = bootstrap_states.get(symbol)
        bootstrap_status = state.status if state is not None else "pending"

        row = {
            "symbol": symbol,
            "records": int(len(records)),
            "unique_fiscal_periods": int(coverage["unique_fiscal_periods"]),
            "first_fiscal_date": coverage["first_fiscal_date"],
            "last_fiscal_date": coverage["last_fiscal_date"],
            "latest_reported_date": latest_reported_date,
            "providers": sorted(records["provider"].dropna().astype(str).unique().tolist()),
            "coverage_status": _coverage_label(
                not eps_records.empty,
                valid_periods,
                per_m5y_available,
            ),
            "ltm_depth": "Suficiente (4 trimestres)" if valid_periods >= 4 else "Insuficiente (<4)",
            "per_m5y_depth": (
                "Suficiente (20 PER válidos)"
                if per_m5y_available
                else "Insuficiente (<20 PER válidos)"
                if valuation is not None
                else "No calculado"
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

        chart_script, chart_div, chart_resources = _build_eps_chart(records, symbol)
        valuation_chart_script, valuation_chart_div = _build_valuation_charts(
            valuation,
            symbol,
        )
        details[symbol] = {
            "summary": row,
            "records": table_records,
            "missing_reported_date_count": int(eps_records["reported_date"].isna().sum()) if not eps_records.empty else 0,
            "valuation": valuation,
            "chart_script": chart_script,
            "chart_div": chart_div,
            "chart_resources": chart_resources,
            "valuation_chart_script": valuation_chart_script,
            "valuation_chart_div": valuation_chart_div,
        }

    return dashboard_rows, details


def _dashboard_paths(username):
    return (
        DATA_FILES_BASE_PATH / "Fundamentals",
        BACKTESTING_BASE_DIR / "Run_Results" / username / "FullRatio",
    )


@fundamentals_bp.route("", methods=["GET"])
def dashboard():
    user, symbols, response = _current_user_and_symbols()
    if response is not None:
        return response

    try:
        fundamentals_path, full_ratio_path = _dashboard_paths(user.username)
        rows, _ = _load_dashboard_data(symbols, fundamentals_path, full_ratio_path)
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
                "ltm_depth": "No disponible",
                "per_m5y_depth": "No calculado",
                "bootstrap_status": "pending",
            }
            for symbol in symbols
        ]

    return render_template(
        "fundamentals/dashboard.html",
        symbols=rows,
        user_name=user.username,
    )


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
            "summary": {"symbol": normalized_symbol, "bootstrap_status": "pending"},
            "records": [],
            "missing_reported_date_count": 0,
            "valuation": None,
            "chart_script": None,
            "chart_div": None,
            "chart_resources": None,
            "valuation_chart_script": None,
            "valuation_chart_div": None,
        }

    return render_template(
        "fundamentals/detail.html",
        detail=detail,
        user_name=user.username,
    )