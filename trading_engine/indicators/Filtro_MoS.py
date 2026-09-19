# indicadores_tecnicos/Filtro_MOS.py
"""
Módulo para la lógica del Margen de Seguridad (MoS).

Generalmente utilizado como un filtro fundamental (condición AND) que requiere
que la valoración esté por encima de un umbral de seguridad y, opcionalmente,
confirmaciones de estado (mínimo y/o tendencia ascendente).
"""

from typing import Any, Callable, Optional, Tuple


def update_mos_state(strategy_self: Any, verificar_estado_indicador_func: Callable):
    """
    Actualiza los estados dinámicos del Margen de Seguridad (MoS).
    """
    if strategy_self.margen_seguridad_active and hasattr(strategy_self, "margen_seguridad_ind"):
        if strategy_self.margen_seguridad_ind is not None and len(strategy_self.margen_seguridad_ind) > 3:
            estado_mos = verificar_estado_indicador_func(strategy_self.margen_seguridad_ind)
            strategy_self.margen_seguridad_minimo_STATE = estado_mos["minimo"]
            strategy_self.margen_seguridad_maximo_STATE = estado_mos["maximo"]
            strategy_self.margen_seguridad_ascendente_STATE = estado_mos["ascendente"]
            strategy_self.margen_seguridad_descendente_STATE = estado_mos["descendente"]


def apply_mos_filter(strategy_self: Any) -> Tuple[bool, Optional[str]]:
    """
    Aplica el filtro fundamental de Margen de Seguridad (MoS).

    Condiciones:
    1. El MoS actual debe superar ``margen_seguridad_threshold``.
    2. Si ``margen_seguridad_minimo`` está activo, debe cumplirse
       ``margen_seguridad_minimo_STATE``.
    3. Si ``margen_seguridad_ascendente`` está activo, debe cumplirse
       ``margen_seguridad_ascendente_STATE``.

    Las condiciones activadas se combinan con AND. Si el filtro MoS está
    desactivado, la entrada no se bloquea.
    """
    if not getattr(strategy_self, "margen_seguridad_active", False):
        return True, None

    margen_ind = getattr(strategy_self, "margen_seguridad_ind", None)
    if margen_ind is None or margen_ind[-1] is None:
        return False, "MOS Faltan Datos"

    mos_value = margen_ind[-1]
    threshold = getattr(strategy_self, "margen_seguridad_threshold", 0.0)
    cond_mos_valoracion = mos_value > threshold

    setting_mos_minimo = bool(getattr(strategy_self, "margen_seguridad_minimo", False))
    state_mos_minimo = bool(getattr(strategy_self, "margen_seguridad_minimo_STATE", False))
    cond_mos_minimo = state_mos_minimo if setting_mos_minimo else True

    setting_mos_ascendente = bool(getattr(strategy_self, "margen_seguridad_ascendente", False))
    state_mos_ascendente = bool(getattr(strategy_self, "margen_seguridad_ascendente_STATE", False))
    cond_mos_ascendente = state_mos_ascendente if setting_mos_ascendente else True

    cond_mos_final = (
        cond_mos_valoracion
        and cond_mos_minimo
        and cond_mos_ascendente
    )

    if not cond_mos_final:
        return False, None

    log_parts = [f"MOS:{round(mos_value, 2)}"]
    if setting_mos_minimo:
        log_parts.append("Mínimo")
    if setting_mos_ascendente:
        log_parts.append("Ascendente")

    return True, " ".join(log_parts)
