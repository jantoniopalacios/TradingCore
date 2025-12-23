# Referencia API: Utilidades del Motor (motor_utils)

Este apartado documenta las funciones y herramientas auxiliares que son utilizadas por los módulos principales del motor (Core e Indicadores).

## Cálculos Financieros

Módulo que contiene funciones para operaciones financieras y gestión de capital, como cálculo de riesgo, valoración de posiciones o gestión de stop-loss.

::: trading_engine.utils.Calculos_Financieros
    options:
      show_root_heading: true
      show_root_members_full_path: false
      show_source: false
      members: 
        - calcular_fundamentales
        - calcular_fullratio_OHLCV
        - generar_seleccion_activos
        - calcular_ratios

## Cálculos Técnicos

Funciones auxiliares para realizar cálculos básicos de indicadores y métricas técnicas que no pertenecen a la lógica central de indicadores, como promedios simples o desviaciones.

::: trading_engine.utils.Calculos_Tecnicos
    options:
      show_root_heading: true
      show_root_members_full_path: false
      show_source: false
      members:
        - es_ascendente
        - es_descendente
        - es_minimo_local
        - es_maximo_local
        - verificar_estado_indicador

## Descarga de Datos (Data_download)

Módulo responsable de la conexión con APIs externas o fuentes de datos para la descarga y pre-procesamiento de datos históricos de precios y volumen.

::: trading_engine.utils.Data_download
    options:
      show_root_heading: true
      show_root_members_full_path: false
      show_source: false
      members: 
        - descargar_datos_YF
        - manage_fundamental_data
        - download_fundamentals_AlphaV
        - update_fundamentals_YF_overwrite

## Gráficos Financieros

Módulo de ayuda para la visualización de datos y el renderizado de gráficos de precios, indicadores y posiciones.

::: trading_engine.utils.Graficos_financieros
    options:
      show_root_heading: true
      show_root_members_full_path: false
      show_source: false
      members:
         - dibujar_graficos

## Gestión de Histórico (Historico_manager)

Clases y funciones para manejar el almacenamiento, recuperación y manipulación de datos históricos de precios dentro del entorno de la aplicación.

::: trading_engine.utils.Historico_manager
    options:
      show_root_heading: true
      show_root_members_full_path: false
      show_source: false
      members:
        - guardar_historico

## Utilidades de Correo (utils_mail)

Funciones para enviar notificaciones y alertas de trading por correo electrónico.

::: trading_engine.utils.utils_mail
    options:
      show_root_heading: true
      show_root_members_full_path: false
      show_source: false
      members:
        - send_email