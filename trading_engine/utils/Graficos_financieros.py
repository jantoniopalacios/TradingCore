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
# --- FUNCIÓN PRINCIPAL DE DIBUJO ---
# ----------------------------------------------------------------------

def dibujar_graficos(ratios: pd.DataFrame, output_path: str = None, show_plot: bool = False):
    """
    Función : dibujar_graficos
    Descripción : Genera y guarda gráficos de ratios financieros.
    
    Entrada: 
        - ratios: DataFrame con datos (output de calcular_fullratio_OHLCV).
        - output_path: Ruta donde se guardará la imagen. Si es None, no guarda.
        - show_plot: Si es True, abre la ventana del gráfico (plt.show()).
    """
    
    if ratios.empty:
        print("Aviso: DataFrame de ratios vacío. No se puede graficar.")
        return

    # --- LÓGICA DE PREPARACIÓN DE DATOS ---
    try:
        # Aseguramos que Date sea una columna para el pivot
        df_plot = ratios.copy()
        if df_plot.index.name == 'Date':
            df_plot = df_plot.reset_index()
            
        # Normalizar nombres de columnas
        if 'Price' in df_plot.columns:
            df_plot.rename(columns={'Price': 'Precio'}, inplace=True)
            
        if 'Precio' not in df_plot.columns or 'Margen de seguridad' not in df_plot.columns:
            print("Error: Faltan columnas clave ('Precio' o 'Margen de seguridad').")
            return

        ratios_to_plot = df_plot[["Date", "Symbol", "Margen de seguridad", "Precio"]]

    except Exception as e:
        print(f"Error al preparar datos para gráfico: {e}")
        return

    # --- DIBUJO CON MATPLOTLIB ---
    fig, ax1 = plt.subplots(figsize=(12, 6))

    for symbol in ratios_to_plot["Symbol"].unique():
        data_symbol = ratios_to_plot[ratios_to_plot["Symbol"] == symbol]
        
        # Eje principal: Precio
        ax1.plot(data_symbol["Date"], data_symbol["Precio"], label=f"Precio {symbol}", linewidth=2)
        ax1.set_xlabel("Fecha")
        ax1.set_ylabel("Precio", color="blue")
        
        # Eje secundario: Margen de Seguridad (suelen tener escalas distintas)
        ax2 = ax1.twinx()
        ax2.plot(data_symbol["Date"], data_symbol["Margen de seguridad"], 
                 label=f"MdS {symbol}", linestyle="--", alpha=0.7, color="orange")
        ax2.set_ylabel("Margen de Seguridad", color="orange")

    plt.title("Evolución: Precio vs Margen de Seguridad")
    ax1.grid(True, which='both', linestyle='--', alpha=0.5)
    fig.tight_layout()
    
    # --- GESTIÓN DE GUARDADO (INYECTADA) ---
    if output_path:
        charts_dir = Path(output_path)
        charts_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = charts_dir / f"ratios_financieros_{timestamp}.png"
        
        try:
            fig.savefig(file_path)
            print(f"✅ Gráfico guardado en: {file_path}")
        except Exception as e:
            print(f"❌ Error al guardar gráfico: {e}")

    if show_plot:
        plt.show()
    else:
        plt.close(fig) # Liberar memoria si no se muestra