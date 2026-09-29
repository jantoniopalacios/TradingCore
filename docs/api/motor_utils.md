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
- la capa `trading_engine/fundamentals/` (`models`, `store`, proveedores Yahoo/Alpha Vantage, `updater`, `bootstrap`, `service` y `legacy_adapter`) mantiene el modelo EPS normalizado;
- Yahoo actualiza datos operativos; Alpha Vantage usa EARNINGS para bootstrap histórico (una llamada por símbolo) solo si existe `ALPHA_VANTAGE_KEY`;
- `Data_download.load_fundamental_data_with_fallback(...)` conserva los datos normalizados para símbolos cubiertos y limita `manage_fundamental_data` / `download_fundamentals_AlphaV` a los símbolos faltantes. La caché Q vive en `Data_Files/Fundamentals_Legacy/`, no en `Data_Files/Fundamentals/`; los resultados se combinan en memoria y prevalece normalizado en duplicados por símbolo/periodo.
- el dashboard `/fundamentals` y su detalle `/fundamentals/<symbol>` son de solo lectura; no descargan proveedores ni recalculan ratios.
- el detalle de estados, disponibilidad temporal y formulas fundamentales se mantiene en [la arquitectura canonica](../ARCHITECTURE.md#fundamentales-actualizacion-estado-y-fallback).

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
