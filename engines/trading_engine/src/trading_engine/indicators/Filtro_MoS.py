# indicadores_tecnicos/Filtro_MOS.py
"""
Módulo para la lógica del Margen de Seguridad (MoS).

Generalmente utilizado como un **filtro fundamental (condición AND)** que requiere 
que la valoración esté por encima de un umbral de seguridad y, opcionalmente, que su tendencia
sea ascendente. Este módulo contiene la lógica para actualizar el estado dinámico y aplicar el filtro.
"""

from typing import Callable, Tuple, Optional, Any
# Se asume que 'verificar_estado_indicador' será importado o pasado como argumento.

# ----------------------------------------------------------------------
# --- Actualización de Estado ---
# ----------------------------------------------------------------------
def update_mos_state(strategy_self: Any, verificar_estado_indicador_func: Callable):
    """
    Actualiza el estado dinámico (STATE) del Margen de Seguridad (MoS).
    
    Este estado indica si el MoS ha alcanzado un mínimo/máximo o si su tendencia es ascendente/descendente
    en la vela actual. Los resultados se asignan a las variables de estado dinámicas
    (e.g., :py:attr:`strategy_self.margen_seguridad_ascendente_STATE`).

    Parameters
    ----------
    strategy_self : strategy_system.System
        Instancia de la estrategia (clase Logica_Trading) que contiene el indicador MoS.
    verificar_estado_indicador_func : Callable
        Función auxiliar utilizada para calcular el estado dinámico (mínimo, máximo, ascendente, descendente) 
        a partir de la serie histórica del MoS.

    Returns
    -------
    None
    """
    if strategy_self.margen_seguridad_active and hasattr(strategy_self, 'margen_seguridad_ind'):
        # Solo verificamos el estado si tenemos suficientes datos cargados para el MoS
        if strategy_self.margen_seguridad_ind is not None and len(strategy_self.margen_seguridad_ind) > 3:
            estado_mos = verificar_estado_indicador_func(strategy_self.margen_seguridad_ind)
            strategy_self.margen_seguridad_minimo_STATE = estado_mos['minimo']
            strategy_self.margen_seguridad_maximo_STATE = estado_mos['maximo']
            strategy_self.margen_seguridad_ascendente_STATE = estado_mos['ascendente']
            strategy_self.margen_seguridad_descendente_STATE = estado_mos['descendente']

# ----------------------------------------------------------------------
# --- Filtro Fundamental (Condición AND) ---
# ----------------------------------------------------------------------
def apply_mos_filter(strategy_self: Any) -> Tuple[bool, Optional[str]]:
    """
    Aplica el filtro fundamental de Margen de Seguridad (MoS).

    Este filtro actúa como una **condición AND** para la entrada a la posición, requiriendo dos sub-condiciones:

    1.  **Condición de Valoración:** El MoS actual debe ser superior al umbral configurado 
        (ej. :py:attr:`strategy_self.margen_seguridad_threshold`).
    2.  **Condición de Dinamismo (Opcional):** Si el usuario requiere que el MoS sea ascendente
        (:py:attr:`strategy_self.margen_seguridad_ascendente` = True), esta condición debe cumplirse
        en el estado actual (:py:attr:`strategy_self.margen_seguridad_ascendente_STATE`).

    Si el filtro no está activo, se devuelve `True` por defecto.

    Parameters
    ----------
    strategy_self : strategy_system.System
        Instancia de la estrategia.

    Returns
    -------
    tuple[bool, str | None]
        - bool: `True` si el filtro es válido (o inactivo), `False` si lo invalida.
        - str | None: Razón del log si el filtro es válido (e.g., "MOS:15.2 Ascendente") o `None`.
    """
    if strategy_self.margen_seguridad_active:
        if hasattr(strategy_self, 'margen_seguridad_ind') and strategy_self.margen_seguridad_ind is not None and strategy_self.margen_seguridad_ind[-1] is not None:
            
            # 1. Condición de Valoración (MoS > Umbral)
            cond_mos_valoracion = strategy_self.margen_seguridad_ind[-1] > strategy_self.margen_seguridad_threshold
            
            # 2. Condición de Dinamismo (si está requerido por el usuario)
            setting_mos_dinamismo = strategy_self.margen_seguridad_ascendente if strategy_self.margen_seguridad_ascendente is not None else False
            state_mos_dinamismo = strategy_self.margen_seguridad_ascendente_STATE if hasattr(strategy_self, 'margen_seguridad_ascendente_STATE') else False
            
            # Lógica: Si el dinamismo está requerido, DEBE cumplirse en el estado. Si no está requerido, se ignora (True).
            if setting_mos_dinamismo:
                cond_mos_dinamismo_final = state_mos_dinamismo
            else:
                cond_mos_dinamismo_final = True

            # Decisión final: (Valoración Ok) AND (Dinamismo Ok O no requerido)
            cond_mos_final = cond_mos_valoracion and cond_mos_dinamismo_final
            
            log_reason = None
            if cond_mos_final:
                mos_value = round(strategy_self.margen_seguridad_ind[-1], 2)
                mos_dinamismo_info = " Ascendente" if setting_mos_dinamismo and state_mos_dinamismo else "" 
                log_reason = f"MOS:{mos_value}{mos_dinamismo_info}"
            
            return cond_mos_final, log_reason
            
        else:
            # Si el filtro está activo pero no hay datos, se asume NO CUMPLIDA (AND)
            return False, "MOS Faltan Datos"
    
    # El filtro MoS no está activo, por lo que la condición fundamental es TRUE por defecto.
    return True, None