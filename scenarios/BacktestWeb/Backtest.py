"""
Script orquestador del ESCENARIO WEB.
Optimizado con imports estructurados y gestión de rutas mediante Pathlib.
"""

# 1. Standard Library
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# 2. Third Party (Data & Viz)
import numpy as np
import pandas as pd
from bokeh.embed import file_html
from bokeh.resources import CDN
from flask import current_app

# 3. Gestión de Rutas (Inyectamos la raíz antes de los imports del motor)
script_path = Path(__file__).resolve()
project_root = script_path.parents[2]  # Sube a /TradingCore/

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 4. Imports del Motor (Ahora que sys.path es correcto)
try:
    from trading_engine.core.Backtest_Runner import run_multi_symbol_backtest 
    from trading_engine.utils.Data_download import descargar_datos_YF, manage_fundamental_data
    from trading_engine.utils.Calculos_Financieros import calcular_fullratio_OHLCV, generar_seleccion_activos
    from trading_engine.utils.utils_mail import send_email
    from trading_engine.core.constants import COLUMNAS_HISTORICO 
except ImportError as e:
    print(f"❌ ERROR CRÍTICO: Estructura 'trading_engine' no hallada: {e}", file=sys.stderr)
    sys.exit(1)

# 5. Imports Locales y Persistencia
from .database import db, Simbolo, Usuario
from .DBStore import save_backtest_run
from .configuracion import cargar_y_asignar_configuracion, asignar_parametros_a_system
from .estrategia_system import System

# Configuración de Logger
logger = logging.getLogger("Ejecucion")

# ----------------------------------------------------------------------

def ejecutar_backtest(config_dict: dict):
    """
    Versión profesional: utiliza el contexto de Flask y evita re-imports.
    Con manejo completo de excepciones y logging detallado.
    """
    start_time = time.time()
    user_mode = config_dict.get('user_mode', 'invitado')
    
    try:
        # 1. Cargar configuración base y mezclar con la de la Web
        logger.info(f"[1/9] Cargando configuración para usuario: {user_mode}")
        datos_base = cargar_y_asignar_configuracion(user_mode)
        config_final = {**datos_base, **config_dict}
        logger.info("✅ Configuración cargada")

        # 2. Sincronizar Clase Global System
        logger.info("[2/9] Sincronizando parámetros System")
        asignar_parametros_a_system(config_final, config_final)
        logger.info("✅ System sincronizado")

        # 3. Extraer rutas y parámetros
        start_date = config_final.get('start_date') 
        end_date = config_final.get('end_date')
        intervalo = config_final.get('intervalo', '1d')
        filtro_fundamental = config_final.get('filtro_fundamental', False) 
        data_files_path = Path(config_final.get('data_files_path'))
        fundamentals_path = Path(config_final.get('fundamentals_path'))

        logger.info(f"🚀 Ejecución Web | Usuario: {user_mode} | Rango: {start_date} a {end_date} | Intervalo: {intervalo}")

        # 4. Lógica de Base de Datos
        logger.info("[3/9] Buscando símbolos del usuario en BD")
        u_actual = Usuario.query.filter_by(username=user_mode).first()
        if not u_actual:
            logger.error(f"❌ Usuario '{user_mode}' no registrado en BD.")
            return None, None, {}

        simbolos_usuario = Simbolo.query.filter_by(usuario_id=u_actual.id).all()
        if not simbolos_usuario:
            logger.warning(f"⚠️  Usuario '{user_mode}' no tiene símbolos asignados")
            return None, None, {}
        
        simbolos_df = pd.DataFrame([{"Symbol": s.symbol, "Name": s.name} for s in simbolos_usuario])
        logger.info(f"✅ {len(simbolos_df)} símbolos encontrados: {simbolos_df['Symbol'].tolist()}")
        
        # 5. Descarga y Procesamiento
        logger.info("[4/9] Descargando datos históricos de Yahoo Finance")
        stocks_data = descargar_datos_YF(simbolos_df, start_date, end_date, intervalo, data_files_path) 
        if stocks_data is None or stocks_data.empty:
            logger.error("❌ Sin datos históricos descargados")
            return None, None, {}
        logger.info(f"✅ Datos descargados: {len(stocks_data)} registros")

        logger.info("[5/9] Procesando datos fundamentales")
        try:
            financial_data = manage_fundamental_data(
                simbolos_df, 
                config_final.get('ALPHA_VANTAGE_KEY', "TU_KEY_POR_DEFECTO"), 
                fundamentals_path
            )
            logger.info("✅ Datos fundamentales procesados")
        except Exception as e:
            logger.warning(f"⚠️  Error en datos fundamentales (continuando): {e}")
            financial_data = None
        
        logger.info("[6/9] Calculando ratios OHLCV")
        try:
            stocks_data = calcular_fullratio_OHLCV(
                stocks_data, 
                financial_data, 
                output_path=config_final.get('full_ratio_path')
            )
            logger.info("✅ Ratios calculados")
        except Exception as e:
            logger.warning(f"⚠️  Error en ratios (continuando con datos básicos): {e}")

        # 6. Selección y Filtros
        simbolos_a_procesar = simbolos_df["Symbol"].tolist()
        if filtro_fundamental:
            logger.info("[7/9] Aplicando filtro fundamental")
            try:
                lista_activos = generar_seleccion_activos(stocks_data, logger)
                if not lista_activos.empty:
                    simbolos_filtrados = lista_activos[lista_activos["Recomendación"] == "Mantener (Atractivo)"].index.tolist()
                    logger.info(f"✅ Filtro fundamental: {len(simbolos_filtrados)} de {len(simbolos_a_procesar)} símbolos")
                    simbolos_a_procesar = simbolos_filtrados
            except Exception as e:
                logger.warning(f"⚠️  Error en filtro fundamental: {e}")

        # 7. Motor de Backtest
        logger.info("[8/9] Ejecutando motor de backtest multi-símbolo")
        stocks_data_dict = {
            s: stocks_data[stocks_data["Symbol"] == s] 
            for s in stocks_data["Symbol"].unique()
            if s in simbolos_a_procesar
        }
        
        if not stocks_data_dict:
            logger.warning("⚠️  No hay datos para procesar después de filtros")
            return None, None, {}
        
        logger.info(f"  Procesando {len(stocks_data_dict)} símbolos...")
        resultados_df, trades_df, backtest_objects = run_multi_symbol_backtest(
            stocks_data_dict, System, config_final, simbolos_a_procesar, 20, logger
        )
        
        if resultados_df is None or resultados_df.empty:
            logger.warning("⚠️  El motor de backtest no retornó resultados")
            return None, None, {}
        
        logger.info(f"✅ Backtest completado: {len(resultados_df)} resultados")

        # 8. Renderizado de Gráficos (Bokeh)
        logger.info("[9/9] Generando gráficos")
        diccionario_graficos_html = {}
        graph_dir = Path(config_final.get('graph_dir'))
        
        # Crear directorio si no existe
        graph_dir.mkdir(parents=True, exist_ok=True)

        for symbol, bt_results in backtest_objects.items():
            try:
                if bt_results:
                    graph_file = graph_dir / f"{symbol}_backtest.html"
                    logger.info(f"  Generando gráfico: {symbol}")
                    bt_results.plot(filename=str(graph_file), open_browser=False)
                    
                    if graph_file.exists():
                        with open(graph_file, 'r', encoding='utf-8') as f:
                            diccionario_graficos_html[symbol] = f.read()
                        logger.info(f"  ✅ Gráfico guardado: {graph_file}")
                    else:
                        logger.warning(f"  ⚠️  Gráfico no se guardó en {graph_file}")
            except Exception as e:
                logger.error(f"  ❌ Error generando gráfico para {symbol}: {e}")

        # 9. Persistencia Delegada
        logger.info("Guardando resultados en base de datos")
        if not resultados_df.empty:
            try:
                current_user_id = config_dict.get('user_id', u_actual.id)
                saved_count = 0
                for _, row in resultados_df.iterrows():
                    ticker = row.get('Symbol', 'UNKNOWN')
                    try:
                        save_backtest_run(
                            user_id=current_user_id,
                            stats=row.to_dict(),
                            config_dict=config_final,
                            trades_df=trades_df[trades_df['Symbol'] == ticker] if not trades_df.empty else None,
                            grafico_html=diccionario_graficos_html.get(ticker)
                        )
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"  ❌ Error guardando resultado para {ticker}: {e}")
                
                logger.info(f"✅ {saved_count}/{len(resultados_df)} resultados guardados en BD")
            except Exception as e:
                logger.error(f"❌ Error crítico en persistencia: {e}")
                import traceback
                traceback.print_exc()
        else:
            logger.warning("⚠️  No hay resultados para guardar")

        elapsed = time.time() - start_time
        logger.info(f"✨ Ciclo completado exitosamente en {elapsed:.2f}s")
        return resultados_df, trades_df, diccionario_graficos_html
    
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ ERROR CRÍTICO EN EJECUCIÓN (después de {elapsed:.2f}s): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None, {}