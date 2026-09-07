import json
from datetime import datetime

from .helpers import (
    _build_strategy_short_title_from_params,
    _normalize_symbol_token,
    _sanitize_filename_component,
)


def _extract_symbols_from_form_data(form_data):
    contenido = form_data.get('symbols_content', '') or ''
    raw_activos = contenido.replace(';', ',').replace('\n', ',').replace('\r', ',')
    normalized = [_normalize_symbol_token(s) for s in raw_activos.split(',')]
    return list(dict.fromkeys([s for s in normalized if s]))


def _build_config_params_from_form_data(form_data, boolean_fields, include_dates=False):
    excluded = {'symbols_content', 'action', 'config_file_name'}
    if not include_dates:
        excluded.update({'end_date', 'fecha_fin'})

    config_params = {k: v for k, v in form_data.items() if k not in excluded}

    for field in boolean_fields:
        config_params[field] = 'True' if field in form_data else 'False'

    if include_dates:
        end_date_value = form_data.get('end_date') or form_data.get('fecha_fin')
        if end_date_value:
            config_params['end_date'] = end_date_value

    return config_params


def _build_default_snapshot_filename(username, config_params):
    stamp = datetime.now().strftime('%Y%m%d')
    strategy_title = _sanitize_filename_component(
        _build_strategy_short_title_from_params(config_params)
    )
    username_part = _sanitize_filename_component(username)
    return f"{stamp}-{strategy_title}-{username_part}.json"


def _build_effective_graph_config(resultado, base_config):
    try:
        params = json.loads(resultado.params_tecnicos) if resultado.params_tecnicos else {}
        if not isinstance(params, dict):
            params = {}
    except Exception:
        params = {}

    config_final = {**base_config, **params}

    start_date = resultado.fecha_inicio_datos or config_final.get('start_date') or config_final.get('START_DATE')
    end_date = resultado.fecha_fin_datos or config_final.get('end_date') or config_final.get('END_DATE')
    intervalo = resultado.intervalo or config_final.get('intervalo') or config_final.get('INTERVAL') or '1d'

    if not start_date or not end_date:
        return None

    config_final['start_date'] = start_date
    config_final['START_DATE'] = start_date
    config_final['end_date'] = end_date
    config_final['END_DATE'] = end_date
    config_final['intervalo'] = intervalo
    config_final['INTERVAL'] = intervalo

    return config_final, start_date, end_date, intervalo
