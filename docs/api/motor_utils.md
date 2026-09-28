# Referencia API: Utilidades del Motor (`motor_utils`)

Ultima actualizacion: 29/09/2026

Este documento resume las funciones y herramientas auxiliares utilizadas por el motor central y los indicadores.

## Calculos Financieros

Funciones relacionadas con calculos fundamentales, ratios y seleccion de activos.

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

## Calculos Tecnicos

Funciones auxiliares para evaluar estados tecnicos y patrones simples utilizados por los indicadores.

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

## Descarga de Datos (`Data_download`)

Modulo responsable de descarga y gestion de datos de mercado y fundamentales.

En el flujo productivo actual:
- los datos historicos de mercado se obtienen principalmente mediante Yahoo Finance;
- la capa `trading_engine/fundamentals/` actualiza EPS reciente con Yahoo y utiliza Alpha Vantage para bootstrap historico;
- `Data_download` intenta adaptar la cache normalizada y mantiene `manage_fundamental_data` / `download_fundamentals_AlphaV` como compatibilidad cuando falta cobertura para algun simbolo o falla el adaptador.
- el detalle de estados, disponibilidad temporal y formulas fundamentales se mantiene en [la arquitectura canonica](../ARCHITECTURE.md#fundamentales-actualizacion-y-estado).

::: trading_engine.utils.Data_download
    options:
      show_root_heading: true
      show_root_members_full_path: false
      show_source: false
      members:
        - descargar_datos_YF
        - manage_fundamental_data
        - download_fundamentals_AlphaV
        - update_normalized_fundamentals
        - update_normalized_fundamentals_if_enabled
        - load_fundamental_data_with_fallback

      La capa normalizada incluye `FundamentalStore`, `FundamentalUpdater`, `AlphaVantageBootstrapper`, `FundamentalService` y `build_legacy_eps_dataframe`; su estado de bootstrap vive en `<fundamentals_path>/bootstrap_state.json`.

## Graficos Financieros

Utilidades para generar graficos financieros utilizados por los escenarios de la aplicacion.

::: trading_engine.utils.Graficos_financieros
    options:
      show_root_heading: true
      show_root_members_full_path: false
      show_source: false
      members:
        - dibujar_graficos

## Gestion de Historico (`Historico_manager`)

Funciones para almacenamiento y reutilizacion de datos historicos locales.

::: trading_engine.utils.Historico_manager
    options:
      show_root_heading: true
      show_root_members_full_path: false
      show_source: false
      members:
        - guardar_historico

## Utilidades de Correo (`utils_mail`)

Funciones auxiliares para enviar notificaciones por correo electronico.

::: trading_engine.utils.utils_mail
    options:
      show_root_heading: true
      show_root_members_full_path: false
      show_source: false
      members:
        - send_email

## Referencias

- Arquitectura canonica: `docs/ARCHITECTURE.md`
- Motor central: `docs/api/motor_core.md`
