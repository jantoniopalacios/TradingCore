"""
Fichero : Calculos_Financieros.py

Descripción : Funciones generales para calcular ratios financieros que usan datos descargados de cotizaciones y fundamentales

FUNCIONES :

def calcular_fundamentales(ohlcv_data, financial_data)       # Calcula FCF/UFCF intermedios
def calcular_fullratio_OHLCV(ohlcv_data, financial_data)   # FUNCIÓN PRINCIPAL: genera el ratio diario
def calcular_ratios(ohlcv_data, financial_data)           # Mantenida como ejemplo/plantilla

"""

import os
import pandas as pd
import numpy as np
from pathlib import Path  # Importamos Pathlib

# Importar la clase System para acceder a las rutas estáticas configuradas
try:
    from estrategia_system import System
except ImportError:
    # 🎯 Ruta de fallback si la clase System no está accesible.
    # Esto garantiza que las funciones puedan crear directorios sin fallar.
    class System:
        # Se asumen estas rutas porque se usan en las funciones.
        FULLRATIO_PATH = Path("./Data files/FullRatio")
        # Si tienes otras rutas importantes, deberían ir aquí.
        # Por ejemplo: CHARTS_PATH = Path("./Data files/Charts") 
        pass

# ----------------------------------------------------------------------
# --- FUNCIÓN DE CÁLCULO DE MÉTRICAS INTERMEDIAS ---
# ----------------------------------------------------------------------
# Calcular los indicadores de robustez de la compañía y la evolucion periodo contra periodo

"""
1. Ventas (Revenue)
Descripción: Representa el ingreso total generado por la venta de bienes o servicios.

Interpretación: Un incremento en las ventas sugiere crecimiento en la demanda y posiblemente una mayor cuota de mercado. Una disminución puede indicar problemas en la comercialización o en la demanda de productos.

2. EBIT (Earnings Before Interest and Taxes)
Descripción: Beneficio antes de intereses e impuestos.

Interpretación: Un aumento en el EBIT indica que la empresa está generando más ingresos operativos y es más eficiente en su operación. Una caída puede señalar problemas operativos.

3. Net Income
Descripción: Ingreso neto después de todos los gastos, impuestos y otros costos.

Interpretación: El aumento del ingreso neto es una señal positiva de rentabilidad y eficiencia. Un descenso puede significar mayores costos operativos o una disminución en los ingresos.

4. EPS (Earnings Per Share) (Idem BPA)
Descripción: Ganancias por acción, calculadas dividiendo el ingreso neto por las acciones en circulación.

Interpretación: Un incremento en el EPS indica que la empresa es más rentable por acción. Es una medida importante para los inversores, ya que refleja el valor que la empresa está generando por acción.

5. Free Cash Flow
Descripción: Flujo de caja libre, calculado como el flujo de caja operativo menos los gastos de capital.

Interpretación: Un alto flujo de caja libre significa que la empresa tiene efectivo disponible después de cubrir sus gastos operativos y de inversión, lo cual es favorable para los dividendos, recompra de acciones o reducción de deuda.

6. Free Cash Flow / Ventas
Descripción: Relación entre el flujo de caja libre y las ventas.

Interpretación: Un mayor valor de esta relación indica una alta eficiencia en la generación de flujo de caja libre a partir de las ventas. Es un indicador de una buena gestión operativa.

7. ROE (Return on Equity)
Descripción: Retorno sobre el patrimonio, calculado como el ingreso neto dividido por el patrimonio de los accionistas.

Interpretación: Un ROE alto indica que la empresa está utilizando eficientemente el capital de los accionistas para generar beneficios. Un ROE bajo puede indicar una mala gestión del capital.

8. ROCE sin goodwill (Return on Capital Employed)
Descripción: Retorno sobre el capital empleado, excluyendo el goodwill, calculado como EBIT dividido por el capital empleado (equity + deuda - goodwill).

Interpretación: Este indicador mide la eficiencia y rentabilidad de la empresa en el uso de su capital. Un ROCE alto sin goodwill indica una gestión eficiente y una alta rentabilidad.

9. ROCE con goodwill (goodwill = fondo de comercio, valor intangible de la imagen de la empresa)
Descripción: Similar al ROCE sin goodwill, pero incluye el goodwill en el capital empleado.

Interpretación: Un ROCE alto con goodwill también indica una buena rentabilidad, pero toma en cuenta el valor intangibles de la empresa, proporcionando una visión más completa.

Interpretación del porcentaje de cambio
Ventas %, EBIT %, Net Income %, EPS %, Free Cash Flow %, Flujo Caja / Ventas %, ROE %, ROCE sin goodwill %, y ROCE con goodwill %: 
Estos porcentajes muestran cómo ha cambiado cada indicador en comparación con el periodo anterior.

Incremento (%): Señal positiva, indica crecimiento y mejora.

Decremento (%): Señal negativa, indica deterioro o desafíos.

"""


def calcular_fundamentales(ohlcv_data, financial_data):
    """
    Función para calcular indicadores financieros fundamentales a partir de datos OHLCV y reportes financieros.

    Parámetros:
    - ohlcv_data: DataFrame con datos de precios de las acciones (Open, High, Low, Close, Volume).
                  Debe incluir una columna 'Symbol' para identificar cada activo.
    - financial_data: DataFrame con datos financieros (ingresos, EBIT, flujo de caja, etc.).
                      Debe incluir una columna 'Symbol' y 'fiscalDateEnding' como índice.

    Salida:
    - DataFrame con indicadores financieros calculados para cada símbolo.
    """

    # Verificar y ajustar los índices para asegurar compatibilidad
    if ohlcv_data.index.name != "Date":
        ohlcv_data.reset_index(inplace=True)
        ohlcv_data["Date"] = pd.to_datetime(ohlcv_data["Date"])  # Convertir a datetime
        ohlcv_data.set_index("Date", inplace=True)  # Establecer índice de fechas

    if financial_data.index.name != "fiscalDateEnding":
        financial_data.reset_index(inplace=True)
        financial_data["fiscalDateEnding"] = pd.to_datetime(
            financial_data["fiscalDateEnding"]
        )  # Convertir fechas
        financial_data.set_index(
            "fiscalDateEnding", inplace=True
        )  # Establecer índice fiscal

    # Crear un DataFrame vacío para almacenar los indicadores calculados
    indicadores = pd.DataFrame()

    # Iterar sobre cada símbolo único en los datos financieros
    for symbol in financial_data["Symbol"].unique():
        # Filtrar datos financieros y de precios por el símbolo actual
        symbol_data = financial_data[financial_data["Symbol"] == symbol]
        symbol_ohlcv = ohlcv_data[ohlcv_data["Symbol"] == symbol]

        # Unir los datos financieros con los datos de cierre de precios
        merged_data = symbol_data.join(symbol_ohlcv[["Close"]], how="left")

        # Asegurar que los precios de cierre coincidan con el índice fiscal
        merged_data["Close"] = symbol_ohlcv[["Close"]].reindex(
            merged_data.index, method="bfill"
        )

        # Crear un DataFrame temporal para los cálculos
        temp_df = pd.DataFrame(index=merged_data.index)

        # Indicadores financieros fundamentales
        temp_df["Ventas"] = merged_data["totalRevenue"]  # Total de ingresos generados
        temp_df["Ventas %"] = (temp_df["Ventas"].pct_change() * 100).round(
            2
        )  # Variación porcentual de ingresos

        temp_df["EBIT"] = merged_data[
            "ebit"
        ]  # Beneficio antes de intereses e impuestos
        temp_df["EBIT %"] = (temp_df["EBIT"].pct_change() * 100).round(
            2
        )  # Variación porcentual del EBIT

        # Cálculo del flujo de caja libre (Free Cash Flow)
        temp_df["Free Cash Flow"] = (
            merged_data["operatingCashflow"] - merged_data["capitalExpenditures"]
        )
        temp_df["Free Cash Flow %"] = (
            temp_df["Free Cash Flow"].pct_change() * 100
        ).round(2)  # Variación porcentual

        # Relación entre flujo de caja y ventas
        temp_df["Flujo Caja / Ventas"] = (
            temp_df["Free Cash Flow"] / merged_data["totalRevenue"]
        )
        temp_df["Flujo Caja / Ventas %"] = (
            temp_df["Flujo Caja / Ventas"].pct_change() * 100
        ).round(2)

        # Rentabilidad sobre el patrimonio (ROE)
        temp_df["ROE"] = (
            merged_data["netIncome_x"] / merged_data["totalShareholderEquity"]
        )
        temp_df["ROE %"] = (temp_df["ROE"].pct_change() * 100).round(2)

        # Cálculo del Retorno sobre el capital empleado (ROCE) sin goodwill
        capital_empleado_sin_goodwill = (
            merged_data["totalShareholderEquity"]
            + merged_data["totalLiabilities"]
            - merged_data["goodwill"]
        )
        temp_df["ROCE sin goodwill"] = (
            merged_data["ebit"] / capital_empleado_sin_goodwill
        )
        temp_df["ROCE sin goodwill %"] = (
            temp_df["ROCE sin goodwill"].pct_change() * 100
        ).round(2)

        # Cálculo del Retorno sobre el capital empleado (ROCE) con goodwill
        capital_empleado_con_goodwill = (
            merged_data["totalShareholderEquity"] + merged_data["totalLiabilities"]
        )
        temp_df["ROCE con goodwill"] = (
            merged_data["ebit"] / capital_empleado_con_goodwill
        )
        temp_df["ROCE con goodwill %"] = (
            temp_df["ROCE con goodwill"].pct_change() * 100
        ).round(2)

        # Asignar símbolo al DataFrame temporal
        temp_df["Symbol"] = symbol

        # Concatenar los resultados al DataFrame final
        indicadores = pd.concat([indicadores, temp_df])

    return indicadores


# ----------------------------------------------------------------------
# --- FUNCIÓN PRINCIPAL DE RATIO DIARIO (ADOPTANDO JOIN + FFILL) ---
# ----------------------------------------------------------------------

def calcular_fullratio_OHLCV(ohlcv_data: pd.DataFrame, financial_data: pd.DataFrame) -> pd.DataFrame:

    """
    Función : calcular_fullratio_OHLCV

    Descripción : 1. Calcula ratios avanzados (LTM, PER 5Y, Margen de Seguridad) a nivel trimestral.
                  2. Propaga estos valores a la serie de tiempo diaria (OHLCV) usando JOIN + FFILL.
                  3. Guarda el resultado diario consolidado.

    Entrada :
        - ohlcv_data: DataFrame con datos de cotizaciones (Price).
        - financial_data: DataFrame con datos fundamentales.
        
    Salida : DataFrame con la serie temporal diaria con todos los ratios.
    """
   
    if ohlcv_data.empty or financial_data.empty:
        print("Advertencia: Datos OHLCV o fundamentales vacíos. Imposible calcular Full Ratio.")
        return pd.DataFrame()
    
    # Configuración de Rutas y variables globales
    output_folder = System.FULLRATIO_PATH 
    output_folder.mkdir(parents=True, exist_ok=True)
    # Definir el nombre del archivo consolidado 
    consolidated_file = output_folder / "FR_diario.csv"
    
    # 1. Asegurar que los DataFrames estén bien indexados por fecha y ordenados

    # --- Manejo de OHLCV Data ---
    # Capturar el nombre del índice actual para un manejo robusto
    original_ohlcv_idx_name = ohlcv_data.index.name

    if original_ohlcv_idx_name != "Date":
        # Si el índice no es 'Date', lo reseteamos para convertirlo en columna
        ohlcv_data.reset_index(inplace=True)

        # Ahora, necesitamos asegurarnos de que la columna de fechas se llame 'Date'.
        # Si el índice original no tenía nombre (ej. RangeIndex), reset_index() crea 'index'.
        # Si tenía un nombre diferente a 'Date', reset_index() usa ese nombre.
        if "Date" not in ohlcv_data.columns:
            # Intentamos renombrar la columna que probablemente contiene las fechas
            if original_ohlcv_idx_name is None and "index" in ohlcv_data.columns:
                ohlcv_data.rename(columns={"index": "Date"}, inplace=True)
            elif (
                original_ohlcv_idx_name is not None
                and original_ohlcv_idx_name in ohlcv_data.columns
            ):
                ohlcv_data.rename(
                    columns={original_ohlcv_idx_name: "Date"}, inplace=True
                )
            else:
                raise KeyError(
                    "No se pudo encontrar la columna 'Date' en ohlcv_data "
                    "después de resetear el índice. Asegúrate de que los datos OHLCV "
                    "contengan una columna 'Date' o que el índice se llame 'Date'."
                )

        # Convertir la columna 'Date' a datetime, forzando errores a NaT
        ohlcv_data["Date"] = pd.to_datetime(ohlcv_data["Date"], errors="coerce")

        # Establecer 'Date' como el nuevo índice
        ohlcv_data.set_index("Date", inplace=True)
    else:  # Si ohlcv_data.index.name ES 'Date'
        # El índice ya se llama 'Date', solo asegurarnos de que sea tipo DatetimeIndex
        if not isinstance(ohlcv_data.index, pd.DatetimeIndex):
            ohlcv_data.index = pd.to_datetime(ohlcv_data.index, errors="coerce")

    # Ordenar el DataFrame por índice (fecha) y eliminar filas con índice NaT
    ohlcv_data = ohlcv_data.sort_index()
    ohlcv_data = ohlcv_data[
        ohlcv_data.index.notna()
    ]  # Correcto: filtrar el DataFrame por índice NaT

    # ESTANDARIZAR ZONA HORARIA OHLCV 🌟
    # Si el índice tiene zona horaria (tz-aware), la eliminamos (tz-naive).
    if ohlcv_data.index.tz is not None:
        ohlcv_data.index = ohlcv_data.index.tz_localize(None)

    # --- Manejo de Financial Data ---
    original_fin_idx_name = financial_data.index.name
    if original_fin_idx_name != "fiscalDateEnding":
        financial_data.reset_index(inplace=True)

        # Asegurar que la columna de fechas fiscales se llame 'fiscalDateEnding'
        if "fiscalDateEnding" not in financial_data.columns:
            if original_fin_idx_name is None and "index" in financial_data.columns:
                financial_data.rename(
                    columns={"index": "fiscalDateEnding"}, inplace=True
                )
            elif (
                original_fin_idx_name is not None
                and original_fin_idx_name in financial_data.columns
            ):
                financial_data.rename(
                    columns={original_fin_idx_name: "fiscalDateEnding"}, inplace=True
                )
            else:
                raise KeyError(
                    "No se pudo encontrar la columna 'fiscalDateEnding' en financial_data "
                    "después de resetear el índice. Asegúrate de que los datos financieros "
                    "contengan una columna 'fiscalDateEnding' o que el índice se llame 'fiscalDateEnding'."
                )

        financial_data["fiscalDateEnding"] = pd.to_datetime(
            financial_data["fiscalDateEnding"], errors="coerce"
        )
        financial_data.set_index("fiscalDateEnding", inplace=True)
    else:
        # El índice ya se llama 'fiscalDateEnding', solo asegurar que sea tipo DatetimeIndex
        if not isinstance(financial_data.index, pd.DatetimeIndex):
            financial_data.index = pd.to_datetime(financial_data.index, errors="coerce")

    # Ordenar el DataFrame por índice (fecha) y eliminar filas con índice NaT
    financial_data = financial_data.sort_index()
    financial_data = financial_data[
        financial_data.index.notna()
    ]  # Correcto: filtrar el DataFrame por índice NaT

    # ESTANDARIZAR ZONA HORARIA FINANCIALS 🌟
    # Si el índice tiene zona horaria (tz-aware), la eliminamos (tz-naive).
    if financial_data.index.tz is not None:
        financial_data.index = financial_data.index.tz_localize(None)


    # Convertir 'Diluted EPS' a numérico, manejando errores (NaN para no numéricos)
    financial_data["Diluted EPS"] = pd.to_numeric(
        financial_data["Diluted EPS"], errors="coerce"
    )
    # Eliminar filas donde 'Diluted EPS' es NaN, ya que es crucial para los cálculos de LTM EPS
    financial_data.dropna(subset=["Diluted EPS"], inplace=True)

    # 2. Inicializar las nuevas columnas en una copia de ohlcv_data para los resultados diarios
    ohlcv_con_full_ratio = ohlcv_data.copy()
    ohlcv_con_full_ratio["LTM EPS"] = np.nan
    ohlcv_con_full_ratio["PER"] = np.nan
    ohlcv_con_full_ratio["PER M5Y"] = np.nan
    ohlcv_con_full_ratio["LTM EPS %"] = np.nan
    ohlcv_con_full_ratio["% PER vs PER M5Y"] = np.nan
    ohlcv_con_full_ratio["Margen de seguridad"] = (np.nan)
    ohlcv_con_full_ratio["Full Ratio"] = (np.nan)
        # Nombre de columna que tú utilizas

    for symbol in financial_data["Symbol"].unique():
        print(f"Calculando indicadores diarios para: {symbol}")

        # 3. Filtrar datos financieros y OHLCV para el símbolo actual
        symbol_financials_q = financial_data[financial_data["Symbol"] == symbol].copy()
        symbol_ohlcv_d = ohlcv_con_full_ratio[
            ohlcv_con_full_ratio["Symbol"] == symbol
        ].copy()

        # Crear un DataFrame temporal con el índice diario del OHLCV del símbolo
        temp_daily_data = pd.DataFrame(index=symbol_ohlcv_d.index)
        temp_daily_data["Close"] = symbol_ohlcv_d["Close"].round(
            2
        )  # Precio de cierre diario

        # --- Cálculos de Métricas Trimestrales (que luego se propagarán a diario) ---

        # Calcular LTM EPS trimestral (suma de los últimos 4 trimestres de Diluted EPS)
        symbol_financials_q["LTM EPS_Q"] = (
            symbol_financials_q["Diluted EPS"]
            .rolling(window=4, min_periods=1)
            .sum()
            .round(2)
        )

        # Calcular Variación % del LTM EPS respecto al periodo anterior trimestral
        symbol_financials_q["LTM EPS %_Q"] = (
            symbol_financials_q["LTM EPS_Q"].pct_change() * 100
        ).round(2)

        # Para calcular PER M5Y_Q, necesitamos el PER Trimestral (PER_Q) primero.
        # Para PER_Q, necesitamos el precio de cierre en la fecha fiscal (o el más cercano).
        symbol_financials_q["Precio_at_FiscalDate"] = symbol_ohlcv_d["Close"].reindex(
            symbol_financials_q.index, method="bfill"
        )

        # Calcular PER Trimestral (PER_Q)
        symbol_financials_q["PER_Q"] = (
            symbol_financials_q["Precio_at_FiscalDate"]
            / symbol_financials_q["LTM EPS_Q"]
        ).round(2)
        # Manejar casos donde LTM EPS_Q es cero o negativo (PER no válido)
        symbol_financials_q.loc[
            symbol_financials_q["LTM EPS_Q"].fillna(0) <= 0, "PER_Q"
        ] = np.nan

        # Calcular PER M5Y_Q (media móvil de 5 años, que son 20 trimestres)
        per_window_quarters = 5 * 4
        symbol_financials_q["PER M5Y_Q"] = (
            symbol_financials_q["PER_Q"]
            .rolling(window=per_window_quarters, min_periods=1)
            .mean()
            .round(2)
        )

        # --- Propagar Métricas Trimestrales a Escala Diaria y Calcular Métricas Diarias ---

        # Unir las métricas trimestrales calculadas (LTM EPS_Q, LTM EPS %_Q, PER M5Y_Q)
        # a las fechas diarias del OHLCV. Esto crea NaNs en las fechas sin informe.
        """
        temp_daily_data = temp_daily_data.merge(
            symbol_financials_q[["LTM EPS_Q", "LTM EPS %_Q", "PER M5Y_Q"]],
            left_index=True,
            right_index=True,
            how="left",
        )
        """
        # 2.2. Realiza la unión usando pd.merge_asof()
        # Usaremos el índice de temp_daily_data para la unión (left_on)
        # Y el índice de symbol_financials_q para buscar coincidencias (right_on)
        # 'direction="backward"' significa que buscará la fecha más cercana *anterior o igual* en el DataFrame derecho.
        # Esto es lo que queremos: para cada viernes, queremos los datos del último informe trimestral publicado.
        temp_daily_data = pd.merge_asof(
            temp_daily_data, # Este es el DataFrame de la izquierda
            symbol_financials_q[["LTM EPS_Q", "LTM EPS %_Q", "PER M5Y_Q"]], # Este es el DataFrame de la derecha (columnas seleccionadas)
            left_index=True,
            right_index=True,
            direction="backward"
        )
        # Propagar los valores trimestrales hacia adelante (ffill) para rellenar los días intermedios.
        temp_daily_data["LTM EPS"] = temp_daily_data["LTM EPS_Q"].ffill()
        temp_daily_data["LTM EPS %"] = temp_daily_data["LTM EPS %_Q"].ffill()
        temp_daily_data["PER M5Y"] = temp_daily_data["PER M5Y_Q"].ffill()

        # Obtener la fecha del primer informe financiero disponible para el símbolo
        first_report_date = None
        if not symbol_financials_q.empty:
            first_report_date = symbol_financials_q.index.min()

        # Solo aplicar el ajuste si tenemos una fecha de primer informe válida (Timestamp)
        if pd.notna(first_report_date):
            # Eliminar los valores propagados que estén antes de la primera fecha de informe real
            temp_daily_data.loc[
                temp_daily_data.index < first_report_date,
                ["LTM EPS", "LTM EPS %", "PER M5Y"],
            ] = np.nan

        # Manejar casos donde LTM EPS propagado es cero o negativo en el día a día
        temp_daily_data.loc[temp_daily_data["LTM EPS"].fillna(0) <= 0, "LTM EPS"] = (
            np.nan
        )

        # Calcular PER diario (Precio de cierre diario / LTM EPS diario propagado)
        temp_daily_data["PER"] = (
            temp_daily_data["Close"] / temp_daily_data["LTM EPS"]
        ).round(2)
        temp_daily_data.loc[temp_daily_data["LTM EPS"].fillna(0) <= 0, "PER"] = (
            np.nan
        )  # PER inválido si LTM EPS es 0 o negativo

        # Calcular % PER vs PER M5Y diario (usando la fórmula que tú proporcionaste: / PER actual)
        temp_daily_data["% PER vs PER M5Y"] = np.nan  # Inicializar con NaN
        # Evitar división por cero o NaN en el denominador 'PER'
        valid_per_idx = temp_daily_data["PER"].fillna(0) != 0
        temp_daily_data.loc[valid_per_idx, "% PER vs PER M5Y"] = (
            100
            * (temp_daily_data["PER"] - temp_daily_data["PER M5Y"])
            / temp_daily_data["PER"]
        ).round(2)

        # Calcular Margen de seguridad (tu 'FULL RATIO') diario
        # Usando la fórmula que tú proporcionaste: (LTM EPS % - % PER vs PER M5Y)
        temp_daily_data["Margen de seguridad"] = (
            temp_daily_data["LTM EPS %"] - temp_daily_data["% PER vs PER M5Y"]
        ).round(2)
        
        # Calcular Full Ratio diario (tu 'FULL RATIO') diario
        temp_daily_data["Full Ratio"] = (
            temp_daily_data["Margen de seguridad"] / temp_daily_data["LTM EPS"]
        ).round(2)

        # 7. Asignar los resultados calculados al DataFrame principal ohlcv_con_full_ratio
        # Asegurarse de asignar solo a las filas correspondientes al símbolo actual
        columns_to_update = [
            "LTM EPS",
            "PER",
            "PER M5Y",
            "LTM EPS %",
            "% PER vs PER M5Y",
            "Margen de seguridad",
            "Full Ratio",
        ]
        ohlcv_con_full_ratio.loc[
            ohlcv_con_full_ratio["Symbol"] == symbol, columns_to_update
        ] = temp_daily_data[columns_to_update]

        # Mostrar los ratios
        print(ohlcv_con_full_ratio)

        ohlcv_con_full_ratio.to_csv(consolidated_file, sep=";")
        print(f"Datos guardados en {consolidated_file}.")

    # Eliminar las columnas temporales con sufijo '_Q' que se crearon en el proceso intermedio
    ohlcv_con_full_ratio.drop(
        columns=[col for col in ohlcv_con_full_ratio.columns if "_Q" in col],
        inplace=True,
        errors="ignore",
    )

    # La llamada a 'dibujar_graficos' aquí debe ser adaptada si quieres usar el DataFrame diario.
    # Por ejemplo, la función 'dibujar_graficos' necesitaría un parámetro 'symbol' para filtrar
    # el DataFrame diario y mostrar el gráfico de un símbolo específico.
    # dibujar_graficos(ohlcv_con_full_ratio)

    return ohlcv_con_full_ratio


# ----------------------------------------------------------------------
# --- FUNCIÓN DE SELECCIÓN Y RECOMENDACIÓN DE ACTIVOS ---
# ----------------------------------------------------------------------

def generar_seleccion_activos(stocks_data: pd.DataFrame, logger) -> pd.DataFrame:
    """
    Analiza el DataFrame diario stocks_data (resultado de calcular_fullratio_OHLCV) 
    en la fecha más reciente para seleccionar activos atractivos basados en ratios 
    fundamentales clave.

    Parámetros:
    - stocks_data: DataFrame consolidado con precios diarios y ratios propagados.
    - logger: Objeto logger para registrar información.

    Salida:
    - DataFrame con la lista de activos, ratios clave y la recomendación.
    """
    if stocks_data.empty:
        logger.warning("Error: El DataFrame de stocks_data está vacío para la selección.")
        return pd.DataFrame()

    # 1. Encontrar la fecha más reciente disponible
    try:
        fecha_actual = stocks_data.index.max()
        if pd.isna(fecha_actual):
            logger.warning("No se pudo determinar la fecha más reciente del índice.")
            return pd.DataFrame()
        logger.info(f"Analizando la selección de activos con datos del: {fecha_actual.strftime('%Y-%m-%d')}")
    except Exception as e:
        logger.error(f"Error al obtener la fecha máxima del índice: {e}")
        return pd.DataFrame()
    
    # 2. Filtrar los datos solo para esa fecha (último día de cotización)
    data_actual = stocks_data.loc[stocks_data.index == fecha_actual].copy()
    
    # 3. Asegurar que 'Symbol' esté en las columnas
    if 'Symbol' not in data_actual.columns:
         data_actual.reset_index(inplace=True)
         # Restaurar el índice original
         if stocks_data.index.name in data_actual.columns:
             data_actual.set_index(stocks_data.index.name, inplace=True)
         
    
    # 4. Seleccionar ratios clave y limpiar NaNs en Full Ratio
    columnas_clave = [
        "Symbol",
        "Close",
        "LTM EPS %", 
        "PER",
        "PER M5Y",
        "Margen de seguridad",
        "Full Ratio",
    ]
    
    # Filtrar solo las columnas que existen y eliminar NaNs en la columna de decisión 'Full Ratio'
    if "Symbol" in data_actual.columns:
        data_actual_indexed = data_actual[[col for col in columnas_clave if col in data_actual.columns]].dropna(
            subset=["Full Ratio"] 
        ).set_index("Symbol")
    else:
        logger.error("La columna 'Symbol' no se encontró en los datos actuales, no se puede realizar la selección por activo.")
        return pd.DataFrame()
        
    data_actual = data_actual_indexed 

    if data_actual.empty:
        logger.warning(f"Advertencia: Ningún activo tiene el 'Full Ratio' calculado en la fecha más reciente ({fecha_actual.strftime('%Y-%m-%d')}).")
        return pd.DataFrame()

    # 5. Lógica de Recomendación (Criterios de Atractivo Fundamental)
    # Criterios: LTM EPS % > 0, Margen de seguridad > 0, Full Ratio > 0
    criterios = (
        (data_actual["LTM EPS %"] > 0)
        & (data_actual["Margen de seguridad"] > 0)
        & (data_actual["Full Ratio"] > 0)
    )
    
    data_actual["Recomendación"] = np.where(
        criterios, "Mantener (Atractivo)", "Desestimar (No cumple criterios)"
    )
    
    # 6. Formato de presentación
    data_actual = data_actual.rename(columns={
        "Close": "Precio Cierre",
        "LTM EPS %": "Crecimiento LTM EPS (%)",
        "PER M5Y": "PER Media 5 Años"
    })
    
    # Ordenar para mostrar los atractivos primero
    data_actual.sort_values(by=["Recomendación", "Full Ratio"], 
                           ascending=[True, False], 
                           inplace=True)

    return data_actual


# ----------------------------------------------------------------------
# --- PLANTILLA FUTURA (conservada) ---
# ----------------------------------------------------------------------

def calcular_ratios(ohlcv_data: pd.DataFrame, financial_data: pd.DataFrame) -> pd.DataFrame:
    """
    Función : calcular_ratios

    Descripción : Combina datos OHLCV con datos financieros para calcular ratios (PER, Margen de Seguridad, etc.),
    utilizando lógica LTM (Last Twelve Months).
    
    Retorna un DataFrame con los ratios calculados indexados por la fecha fiscal de reporte.
    """
    if ohlcv_data.empty or financial_data.empty: 
        print("Advertencia: Datos de OHLCV o fundamentales vacíos. Imposible calcular ratios.")
        return pd.DataFrame()
        
    # Fusionar precios de cierre (Close) con datos financieros por Symbol y Date.
    # financial_data está indexado por fiscalDateEnding. ohlcv_data por Date.
    # 
    # El snippet sugiere que los precios se fusionan con la fecha de reporte fiscal (fiscalDateEnding).
    # Esto asume que el precio de cierre en la fecha de reporte es el 'Price' que se usará para calcular el ratio.
    
    financial_data = financial_data.reset_index().rename(columns={'fiscalDateEnding': 'Date'})
    ohlcv_data = ohlcv_data.reset_index()

    combined_data = pd.merge(
        financial_data, 
        ohlcv_data[['Symbol', 'Date', 'Close']].rename(columns={'Close': 'Price'}),
        on=['Symbol', 'Date'],
        how='left' # Usamos left para mantener todas las filas de reportes fiscales
    )
    
    combined_data.set_index('Date', inplace=True) # El índice es ahora la fecha fiscal de reporte
    combined_data.sort_index(inplace=True)

    final_ratios_list = []
    
    for symbol in combined_data['Symbol'].unique():
        symbol_ratios = combined_data[combined_data['Symbol'] == symbol].copy()
        
        # Rellenar precios faltantes (el precio de cierre no siempre cae en la fecha exacta del reporte fiscal)
        # Aquí se debería buscar el precio de cierre más cercano *después* de la fecha del reporte,
        # pero el snippet original simplemente asumía que el precio estaba allí o se rellenaba.
        # Por simplicidad, se propaga el último precio si faltara.
        symbol_ratios['Price'] = symbol_ratios['Price'].ffill().bfill() 

        # ----------------------------------------------------------------------
        # --- LÓGICA DE CÁLCULO DE RATIOS (Reconstruida del snippet) ---
        # ----------------------------------------------------------------------
        
        # Calcular LTM Diluted EPS (asumiendo que 'Diluted EPS' existe y es trimestral)
        symbol_ratios["LTM Diluted EPS"] = symbol_ratios["Diluted EPS"].rolling(window=4).sum()
        
        # Calcular LTM Price / Diluted EPS (PER basado en LTM)
        symbol_ratios["LTM Price / Diluted EPS"] = (
            symbol_ratios["Price"] / symbol_ratios["LTM Diluted EPS"]
        )

        # Calcular el promedio del PER en los últimos 5 años (20 trimestres)
        per_window = 5 * 4 
        symbol_ratios["PER de 5 años"] = (
            symbol_ratios["LTM Price / Diluted EPS"].rolling(window=per_window).mean()
        )

        # Calcular la variación porcentual del PER a 5 años
        symbol_ratios["Diferencial PER de 5 años (%)"] = (
            symbol_ratios["PER de 5 años"].pct_change() * 100
        )

        # Calcular el margen de seguridad
        symbol_ratios["Margen de seguridad"] = (
            symbol_ratios["LTM Diluted EPS"].pct_change() * 100
            - symbol_ratios["Diferencial PER de 5 años (%)"]
        )
        
        # Se añaden otros ratios asumidos del snippet (TEV/UFCF)
        if 'Unlevered Free Cash Flow' in symbol_ratios.columns:
             symbol_ratios["LTM Total Enterprise Value / Unlevered Free Cash Flow"] = (
                symbol_ratios["Total Enterprise Value"] / symbol_ratios["Unlevered Free Cash Flow"].rolling(window=4).sum()
            )


        symbol_ratios["Symbol"] = symbol
        final_ratios_list.append(symbol_ratios.dropna(subset=['Margen de seguridad']))

    if final_ratios_list:
        final_ratios_df = pd.concat(final_ratios_list)
        # El índice es la fecha fiscal de reporte
        return final_ratios_df
    else:
        return pd.DataFrame()