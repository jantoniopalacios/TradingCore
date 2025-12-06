"""
Fichero : Graficos_financieros.py

Descripción : Funciones para generar y guardar gráficos de ratios financieros.

FUNCIONES :

def dibujar_graficos(ratios) # Selecciona ratios clave y genera el gráfico.

"""
import os
from datetime import datetime
from pathlib import Path
import pandas as pd # Necesario para reset_index, rename y pivot
import matplotlib.pyplot as plt 

# ----------------------------------------------------------------------
# --- IMPORTACIONES DE SISTEMA Y RUTA (BLOQUE ROBUSTO) ---
# ----------------------------------------------------------------------
try:
    from estrategia_system import System
except ImportError:
    # Ruta de fallback si la clase System no está accesible.
    class System:
        # Se asume esta ruta para que el guardado de archivos no falle.
        CHARTS_PATH = Path("./Data files/Charts") 
        pass

# ----------------------------------------------------------------------
# --- FUNCIÓN PRINCIPAL DE DIBUJO ---
# ----------------------------------------------------------------------

def dibujar_graficos(ratios: pd.DataFrame):
    """
    Función : dibujar_graficos

    Descripción : Selecciona y grafica ratios financieros clave (Margen de Seguridad y Precio) a lo largo del tiempo.
    Guarda el gráfico en la ruta definida estáticamente en System.CHARTS_PATH.
    
    Entrada: DataFrame que contiene la serie temporal de ratios y precios (e.g., el output de calcular_fullratio_OHLCV).
    """
    
    # ----------------------------------------------------------------------
    # --- FUNCIÓN AUXILIAR PARA GUARDAR GRÁFICOS ---
    # ----------------------------------------------------------------------
    def guardar_grafico(fig: plt.Figure, nombre_archivo: str):
        """
        Guarda un gráfico Matplotlib en la carpeta de Charts definida en System.
        """
        # 🎯 Obtener la ruta estática para Charts
        charts_dir = System.CHARTS_PATH
        
        # Asegurar que el directorio existe
        charts_dir.mkdir(parents=True, exist_ok=True)
        
        # Crear la ruta completa del archivo
        file_path = charts_dir / nombre_archivo 

        try:
            fig.savefig(file_path) 
            print(f"Gráfico guardado en: {file_path}")
        except Exception as e:
            print(f"Error al guardar el gráfico en {file_path}: {e}")
    # ----------------------------------------------------------------------

    # ----------------------------------------------------------------------
    # --- LÓGICA DE DIBUJO ---
    # ----------------------------------------------------------------------
    
    # Seleccionar las columnas disponibles y graficarlas
    try:
        # Se asume que el índice de 'ratios' es la fecha (Daily o Quarterly).
        # Nota: La columna 'Price' fue renombrada a 'Precio' en Calculos_Financieros.py
        # Si la entrada 'ratios' es el output de calcular_fullratio_OHLCV, ya tiene 'Precio'.
        
        # Si viene del output final (daily ratios) debería usar 'Precio'.
        if 'Precio' in ratios.columns:
            ratios_to_plot = ratios.reset_index()[["Symbol", "Margen de seguridad", "Precio"]]
        
        # Si viene de una fuente más antigua que usa 'Price', usamos tu lógica original
        elif 'Price' in ratios.columns:
            ratios_to_plot = ratios.reset_index()[["Symbol", "Margen de seguridad", "Price"]]
            ratios_to_plot.rename(columns={'Price': 'Precio'}, inplace=True)
        
        else:
            print("Error: No se encuentran las columnas 'Precio' o 'Price' necesarias para graficar.")
            return

    except KeyError as e:
        print(f"Error: No se encuentran las columnas necesarias para graficar. {e}")
        return

    fig = plt.figure(figsize=(10, 6))
    ax = fig.gca()
    
    # Pivotar por Symbol para que cada línea sea un valor y graficar
    # Se debe pivotar sobre la columna 'Date' (que es el índice tras reset_index)
    if not ratios_to_plot.empty:
        ratios_to_plot.pivot(index='Date', columns="Symbol").plot(ax=ax)
    
    plt.title("Ratios Financieros: Margen de Seguridad vs Precio")
    plt.xlabel("Fecha")
    plt.ylabel("Valor")
    # Leyenda: Margen de seguridad para cada Symbol y Precio para cada Symbol
    plt.legend(title="Ratios y Símbolos", bbox_to_anchor=(1.05, 1), loc="upper right") 
    plt.grid(True)
    
    # Llamada a la función auxiliar para guardar
    nombre_del_archivo = "ratios_financieros_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
    guardar_grafico(fig, nombre_del_archivo)

    # Nota: plt.show() puede ser útil para desarrollo, pero a menudo se elimina en scripts de backtesting automatizados.
    plt.show()