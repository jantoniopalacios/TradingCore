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
from datetime import datetime, timedelta
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

def ejecutar_backtest(config_dict: dict, progress_callback=None):
    """
    Versión profesional: utiliza el contexto de Flask y evita re-imports.
    Con manejo completo de excepciones y logging detallado.
    """
    start_time = time.time()
    user_mode = config_dict.get('user_mode', 'invitado')

    def _progress(phase_index, phase_total, phase, message):
        if callable(progress_callback):
            try:
                progress_callback(phase_index, phase_total, phase, message)
            except Exception as cb_err:
                logger.warning(f"⚠️  Error reportando progreso: {cb_err}")
    
    try:
        # 1. Cargar configuración base y mezclar con la de la Web
        _progress(1, 11, 'Configuracion', 'Cargando configuracion base y parametros web')
        logger.info(f"[1/9] Cargando configuración para usuario: {user_mode}")
        datos_base = cargar_y_asignar_configuracion(user_mode)
        config_final = {**datos_base, **config_dict}
        logger.info("✅ Configuración cargada")

        # 2. Sincronizar Clase Global System
        _progress(2, 11, 'System', 'Sincronizando parametros globales de estrategia')
        logger.info("[2/9] Sincronizando parámetros System")
        asignar_parametros_a_system(config_final, config_final)
        logger.info("✅ System sincronizado")

        # 3. Extraer rutas y parámetros
        start_date = config_final.get('start_date') 
        end_date = config_final.get('end_date')
        if not end_date:
            end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            config_final['end_date'] = end_date
            logger.info(f"ℹ️ end_date no definido; se usará por defecto: {end_date}")
        intervalo = config_final.get('intervalo', '1d')
        filtro_fundamental = config_final.get('filtro_fundamental', False) 
        data_files_path = Path(config_final.get('data_files_path'))
        fundamentals_path = Path(config_final.get('fundamentals_path'))

        logger.info(f"🚀 Ejecución Web | Usuario: {user_mode} | Rango: {start_date} a {end_date} | Intervalo: {intervalo}")

        # 4. Lógica de Base de Datos
        _progress(3, 11, 'Base de datos', 'Cargando simbolos configurados para el usuario')
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
        _progress(4, 11, 'Datos de mercado', 'Descargando historicos desde Yahoo Finance')
        logger.info("[4/9] Descargando datos históricos de Yahoo Finance")
        stocks_data = descargar_datos_YF(simbolos_df, start_date, end_date, intervalo, data_files_path) 
        if stocks_data is None or stocks_data.empty:
            logger.error("❌ Sin datos históricos descargados")
            return None, None, {}
        logger.info(f"✅ Datos descargados: {len(stocks_data)} registros")

        financial_data = None
        if filtro_fundamental:
            _progress(5, 11, 'Fundamentales', 'Procesando datos fundamentales y ratios')
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
        else:
            _progress(5, 11, 'Fundamentales', 'Filtro fundamental desactivado; se omite esta fase')

        # 6. Selección y Filtros
        _progress(6, 11, 'Filtros', 'Aplicando filtros y seleccion final de activos')
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
        _progress(7, 11, 'Motor', 'Ejecutando backtest multi-simbolo')
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
        _progress(8, 11, 'Graficos', 'Generando visualizaciones por activo')
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
        _progress(9, 11, 'Persistencia', 'Guardando resultados y operaciones en SQL')
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
        _progress(10, 11, 'Cierre', f'Ciclo principal completado en {elapsed:.2f}s')
        logger.info(f"✨ Ciclo completado exitosamente en {elapsed:.2f}s")

        # --- ENVÍO DE MAIL DE RECOMENDACIONES SI ESTÁ ACTIVADO ---
        enviar_mail = config_final.get('enviar_mail', False)
        destinatario_email = config_final.get('destinatario_email', None)
        usuario_nombre = user_mode
        if enviar_mail and destinatario_email:
            _progress(11, 11, 'Notificacion', 'Enviando email de recomendaciones')
            try:
                # Construir tabla de recomendaciones SOLO para activos procesados
                activos_procesados = resultados_df['Symbol'].tolist() if resultados_df is not None else []
                # Recomendación: última operación realizada por el backtest para cada activo
                recomendaciones = []
                for symbol in activos_procesados:
                    trades_symbol = trades_df[trades_df['Symbol'] == symbol] if not trades_df.empty else None
                    reco = 'Sin operaciones'
                    fecha_op = ''
                    if trades_symbol is not None and not trades_symbol.empty:
                        # Buscar la última operación (por fecha de cierre si existe, si no por fecha de entrada)
                        if 'Exit Time' in trades_symbol.columns and trades_symbol['Exit Time'].notnull().any():
                            last_trade = trades_symbol.sort_values('Exit Time').iloc[-1]
                            fecha_op = str(last_trade['Exit Time'])
                        elif 'Fecha' in trades_symbol.columns:
                            last_trade = trades_symbol.sort_values('Fecha').iloc[-1]
                            fecha_op = str(last_trade['Fecha'])
                        elif 'Entry Time' in trades_symbol.columns:
                            last_trade = trades_symbol.sort_values('Entry Time').iloc[-1]
                            fecha_op = str(last_trade['Entry Time'])
                        else:
                            last_trade = trades_symbol.iloc[-1]
                            fecha_op = ''
                        # Determinar tipo de última operación
                        if 'Tipo' in last_trade:
                            tipo = str(last_trade['Tipo']).strip().lower()
                            if tipo == 'compra':
                                reco = 'Compra'
                            elif tipo == 'venta':
                                reco = 'Venta'
                            else:
                                reco = str(last_trade['Tipo'])
                        elif 'Side' in last_trade:
                            if last_trade['Side'] == 'buy':
                                reco = 'Compra'
                            elif last_trade['Side'] == 'sell':
                                reco = 'Venta'
                            else:
                                reco = str(last_trade['Side'])
                        elif 'Operacion' in last_trade:
                            op = str(last_trade['Operacion']).lower()
                            if 'compra' in op:
                                reco = 'Compra'
                            elif 'venta' in op:
                                reco = 'Venta'
                            else:
                                reco = str(last_trade['Operacion'])
                        else:
                            reco = 'Operación'
                    recomendaciones.append((symbol, reco, fecha_op))
                # Ordenar por fecha_op descendente (más reciente primero)
                def parse_fecha(fecha):
                    try:
                        return pd.to_datetime(fecha)
                    except Exception:
                        return pd.NaT
                recomendaciones.sort(key=lambda x: parse_fecha(x[2]), reverse=True)

                now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                subject = f"Recomendaciones cartera {usuario_nombre} {now_str}"
                header = f"{now_str} - Recomendaciones cartera {usuario_nombre}\n"
                # Formato de tabla de texto plano
                col1, col2, col3 = 'Activo', 'Ultima operación', 'Fecha Última Operación'
                ancho1 = max(len(col1), max((len(str(s)) for s,_,_ in recomendaciones), default=6))
                ancho2 = max(len(col2), max((len(str(r)) for _,r,_ in recomendaciones), default=13))
                ancho3 = max(len(col3), max((len(str(f)) for _,_,f in recomendaciones), default=22))
                sep = f"{'-'*ancho1} {'-'*ancho2} {'-'*ancho3}"
                table = f"{col1.ljust(ancho1)} {col2.ljust(ancho2)} {col3.ljust(ancho3)}\n{sep}\n"
                for symbol, reco, fecha_op in recomendaciones:
                    table += f"{str(symbol).ljust(ancho1)} {str(reco).ljust(ancho2)} {str(fecha_op).ljust(ancho3)}\n"
                body = header + '\n' + table
                mail_config_path = str(project_root / "trading_engine" / "utils" / "Config" / "setup_mail.env")
                send_email(subject, body, destinatario_email, config_path=mail_config_path)
                logger.info(f"✉️  Mail de recomendaciones enviado a {destinatario_email}")
            except Exception as e:
                logger.error(f"❌ Error enviando mail de recomendaciones: {e}")
        else:
            _progress(11, 11, 'Notificacion', 'Envio de email desactivado')

        return resultados_df, trades_df, diccionario_graficos_html
    
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ ERROR CRÍTICO EN EJECUCIÓN (después de {elapsed:.2f}s): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None, {}