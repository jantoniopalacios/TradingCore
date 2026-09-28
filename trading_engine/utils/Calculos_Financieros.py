"""
Fichero : Calculos_Financieros.py

Descripción : Funciones generales para calcular ratios financieros que usan datos descargados de cotizaciones y fundamentales

FUNCIONES :

def calcular_fundamentales(ohlcv_data, financial_data)       # Calcula FCF/UFCF intermedios
def calcular_fullratio_OHLCV(ohlcv_data, financial_data)   # FUNCIÓN PRINCIPAL: genera el ratio diario
def calcular_ratios(ohlcv_data, financial_data)           # Mantenida como ejemplo/plantilla

"""

import pandas as pd
import numpy as np
from pathlib import Path  # Importamos Pathlib

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
    if ohlcv_data.empty or financial_data.empty:
        print("Advertencia: Datos OHLCV o fundamentales vacíos.")
        return pd.DataFrame()

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

def calcular_fullratio_OHLCV(ohlcv_data: pd.DataFrame, financial_data: pd.DataFrame, output_path: str = None) -> pd.DataFrame:
    """
    Versión con LOGS RESTAURADOS: Muestra una tabla resumen por símbolo.
    """
    if ohlcv_data.empty or financial_data.empty:
        print("⚠️ Datos vacíos. Cancelando cálculo.")
        return pd.DataFrame()

    # 1. Rutas
    consolidated_file = None
    if output_path:
        output_folder = Path(output_path)
        output_folder.mkdir(parents=True, exist_ok=True)
        consolidated_file = output_folder / "FR_diario.csv"

    # 2. Estandarización de Precios
    df_ohlcv = ohlcv_data.copy()
    if df_ohlcv.index.name == 'Date' or 'Date' not in df_ohlcv.columns:
        df_ohlcv = df_ohlcv.reset_index()
    date_col = 'Date' if 'Date' in df_ohlcv.columns else df_ohlcv.columns[0]
    df_ohlcv.rename(columns={date_col: "Date"}, inplace=True)
    df_ohlcv["Date"] = pd.to_datetime(df_ohlcv["Date"]).dt.tz_localize(None)
    df_ohlcv = df_ohlcv.sort_values(["Symbol", "Date"])

    # 3. Estandarización de Fundamentales
    df_fin = financial_data.copy()
    if df_fin.index.name == 'fiscalDateEnding' or 'fiscalDateEnding' not in df_fin.columns:
        df_fin = df_fin.reset_index()
    fin_date_col = 'fiscalDateEnding' if 'fiscalDateEnding' in df_fin.columns else df_fin.columns[0]
    df_fin.rename(columns={fin_date_col: "fiscalDateEnding"}, inplace=True)
    df_fin["fiscalDateEnding"] = pd.to_datetime(df_fin["fiscalDateEnding"]).dt.tz_localize(None)
    if "reportedDate" in df_fin.columns:
        df_fin["reportedDate"] = pd.to_datetime(
            df_fin["reportedDate"], errors="coerce"
        ).dt.tz_localize(None)
    else:
        df_fin["reportedDate"] = pd.NaT
    df_fin["Diluted EPS"] = pd.to_numeric(df_fin["Diluted EPS"], errors="coerce")
    df_fin = df_fin.dropna(subset=["Diluted EPS"]).sort_values("fiscalDateEnding")

    # 4. Cálculos Trimestrales y LOG por Símbolo
    all_symbol_fundamentals = []
    for symbol in df_fin["Symbol"].unique():
        symbol_q = df_fin[df_fin["Symbol"] == symbol].copy()
        
        # Ratios LTM
        symbol_q["LTM EPS_Q"] = symbol_q["Diluted EPS"].rolling(window=4, min_periods=1).sum().round(2)
        symbol_q["LTM EPS %_Q"] = (symbol_q["LTM EPS_Q"].pct_change() * 100).round(2)

        # Precio para PER histórico
        symbol_prices = df_ohlcv[df_ohlcv["Symbol"] == symbol][["Date", "Close"]].sort_values("Date")
        symbol_q = pd.merge_asof(
            symbol_q.sort_values("fiscalDateEnding"),
            symbol_prices,
            left_on="fiscalDateEnding",
            right_on="Date",
            direction="backward"
        )
        symbol_q["PER_Q"] = (symbol_q["Close"] / symbol_q["LTM EPS_Q"]).round(2)
        symbol_q.loc[symbol_q["LTM EPS_Q"] <= 0, "PER_Q"] = np.nan
        symbol_q["PER M5Y_Q"] = symbol_q["PER_Q"].rolling(window=20, min_periods=1).mean().round(2)
        
        all_symbol_fundamentals.append(symbol_q)

    df_fin_calc = pd.concat(all_symbol_fundamentals)

    # 5. Cruce Diario por Símbolo
    available_fundamentals = df_fin_calc.dropna(subset=["reportedDate"])
    if available_fundamentals.empty:
        stocks_data = df_ohlcv.copy()
        stocks_data["fiscalDateEnding"] = pd.NaT
        stocks_data["reportedDate"] = pd.NaT
        for column in ("LTM EPS_Q", "LTM EPS %_Q", "PER M5Y_Q"):
            stocks_data[column] = np.nan
    else:
        stocks_data = pd.merge_asof(
            df_ohlcv.sort_values("Date"),
            available_fundamentals[
                [
                    "reportedDate",
                    "fiscalDateEnding",
                    "Symbol",
                    "LTM EPS_Q",
                    "LTM EPS %_Q",
                    "PER M5Y_Q",
                ]
            ].sort_values("reportedDate"),
            left_on="Date",
            right_on="reportedDate",
            by="Symbol",
            direction="backward",
        )

    # 6. Ratios Diarios
    stocks_data["PER"] = (stocks_data["Close"] / stocks_data["LTM EPS_Q"]).round(2)
    valid_per = (stocks_data["PER"].notna()) & (stocks_data["PER"] != 0)
    stocks_data["% PER vs PER M5Y"] = np.nan
    stocks_data.loc[valid_per, "% PER vs PER M5Y"] = (
        100 * (stocks_data["PER"] - stocks_data["PER M5Y_Q"]) / stocks_data["PER"]
    ).round(2)
    stocks_data["Margen de seguridad"] = (stocks_data["LTM EPS %_Q"] - stocks_data["% PER vs PER M5Y"]).round(2)
    stocks_data["Full Ratio"] = (stocks_data["Margen de seguridad"] / stocks_data["PER"]).round(2)

    # --- 🌟 BLOQUE DE LOGS RESTAURADO ---
    for symbol in stocks_data["Symbol"].unique():
        print(f"\n📊 MUESTRA DE RATIOS CALCULADOS PARA: {symbol}")
        # Tomamos las últimas 5 filas calculadas para mostrar en el log
        print(stocks_data[stocks_data["Symbol"] == symbol][
            ["Date", "Close", "LTM EPS_Q", "PER", "PER M5Y_Q", "Margen de seguridad", "Full Ratio"]
        ].tail(5).to_string(index=False))
        print("-" * 80)

    # 7. Limpieza y guardado
    stocks_data.rename(columns={"LTM EPS_Q": "LTM EPS", "LTM EPS %_Q": "LTM EPS %", "PER M5Y_Q": "PER M5Y"}, inplace=True)
    stocks_data.drop(columns=["fiscalDateEnding", "Date_y"], inplace=True, errors="ignore")
    stocks_data.set_index("Date", inplace=True)

    if consolidated_file:
        stocks_data.to_csv(consolidated_file, sep=";")
        print(f"✅ Full Ratio guardado en: {consolidated_file}")

    return stocks_data


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