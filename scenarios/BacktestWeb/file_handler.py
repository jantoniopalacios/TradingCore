# file_handler.py (CÓDIGO REFACTORIZADO Y MODULAR)

import os
import re
import shutil 
from datetime import datetime
from pathlib import Path
# Asumimos que PROJECT_ROOT se define en configuracion.py
from .configuracion import PROJECT_ROOT 

# ----------------------------------------------------------------------
# --- CONSTANTES DE RUTA CENTRALIZADAS ---
# ----------------------------------------------------------------------

from .configuracion import BACKTESTING_BASE_DIR

# Y sustituye cualquier ruta manual por:
BACKTESTING_DIR = BACKTESTING_BASE_DIR

# ----------------------------------------------------------------------
# --- FUNCIONES DE MANEJO DE DIRECTORIOS Y ARCHIVOS ---
# ----------------------------------------------------------------------

def clean_run_results_dir(results_path): 
    """
    Elimina y recrea el directorio Run_results. 
    Recibe la ruta de resultados desde el módulo de configuración.
    Devuelve (éxito, mensaje).
    """
    try:
        # results_path debería ser un objeto Path
        if results_path.exists():
            shutil.rmtree(results_path) 
        results_path.mkdir(parents=True, exist_ok=True)
        return True, f"El directorio '{results_path.name}' ha sido limpiado y recreado correctamente."
    except Exception as e:
        error_message = f"Error crítico al intentar limpiar el directorio '{results_path.name}': {e}"
        return False, error_message

def get_directory_tree(path, is_admin=False): # <--- Añade is_admin=False aquí
    tree = []
    if not path.exists():
        return tree
    
    for item in path.iterdir():
        # Filtro de seguridad: si es el log y NO es admin, saltar
        if item.name == "trading_app.log" and not is_admin:
            continue
            
        if item.is_dir():
            tree.append((item.name, True, get_directory_tree(item, is_admin), "Folder"))
        else:
            dt = datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            tree.append((item.name, False, [], dt))
    
    # Ordenar: carpetas primero, luego archivos
    return sorted(tree, key=lambda x: (not x[1], x[0].lower()))

# ----------------------------------------------------------------------
# --- FUNCIONES DE CONFIGURACIÓN (.ENV) ---
# ----------------------------------------------------------------------

def read_config_with_metadata(config_path):
    """
    Lee el archivo de configuración (.env) y extrae variables, comentarios y el contenido completo.
    """
    variables = {}
    comments = {}
    # Captura VAR = VALOR, ignorando el resto de la línea, incluyendo comentarios de fin de línea.
    var_regex = re.compile(r'^\s*(\w+)\s*=\s*([^\n#]+)', re.MULTILINE)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Guardamos el contenido completo para preservación de comentarios/estructura
            variables['__full_content__'] = content 
            
            lines = content.split('\n')
            current_comment_block = []
            
            for line in lines:
                trimmed_line = line.strip()
                match = var_regex.match(line)
                
                if trimmed_line.startswith('#'):
                    # Si es una línea de comentario, la guardamos
                    if trimmed_line.replace('#', '').strip() != '---':
                        current_comment_block.append(trimmed_line.lstrip('#').strip())
                elif match:
                    # Si es una línea de variable
                    name = match.group(1).strip()
                    # Limpiamos el valor de posibles comillas (simples o dobles)
                    value = match.group(2).strip().strip('"').strip("'")
                    
                    variables[name] = value
                    # Asignamos el comentario recopilado
                    comments[name] = "\n".join(current_comment_block) if current_comment_block else "Sin documentación específica."
                    
                    # Reiniciamos el bloque de comentarios para la siguiente variable
                    current_comment_block = []
                else:
                    # Líneas de contenido que no son ni comentario ni variable activa
                    if trimmed_line == '' and not current_comment_block:
                        pass
                    elif current_comment_block:
                        current_comment_block = [] 
            
    except FileNotFoundError:
        return None, None 
    except Exception as e:
        raise Exception(f"Error al leer el archivo de configuración ({config_path}): {e}")
        
    return variables, comments

def write_config(new_values, full_content, config_path):
    """
    Reescribe el archivo de configuración (.env) con los nuevos valores, preservando la estructura.
    """
    
    new_content = full_content
    
    for name, value in new_values.items():
        pattern = re.compile(rf'^\s*{re.escape(name)}\s*=\s*([^\n#]+)', re.MULTILINE)
        
        # Formateo de valor (Booleano o String con comillas)
        formatted_value = str(value).strip()
        if isinstance(value, bool) or str(value).lower() in ('true', 'false'):
            formatted_value = "True" if str(value).lower() in ('true', 'on') else "False"
        elif not (str(value).isnumeric() or re.match(r'^-?\d*\.?\d+$', formatted_value)):
            formatted_value = f'"{formatted_value.strip(chr(34))}"'

        # Intentar reemplazar
        new_content, count = pattern.subn(f'{name} = {formatted_value}', new_content)
        
        # SI LA VARIABLE NO EXISTÍA (count == 0), la añadimos al final
        if count == 0:
            new_content += f"\n{name} = {formatted_value}"

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(new_content.strip() + "\n")
    except Exception as e:
        raise Exception(f"No se pudo escribir en el archivo {config_path}: {e}")
    
    return True

# ----------------------------------------------------------------------
# --- FUNCIONES DE MANEJO CSV (RAW) ---
# ----------------------------------------------------------------------

def read_symbols_raw(symbols_path):
    """
    Lee el archivo symbols.csv y devuelve su contenido como una cadena de texto sin procesar.
    """
    try:
        with open(symbols_path, mode='r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return "Symbol,Name\n" 
    except Exception as e:
        raise Exception(f"Error al leer {symbols_path}: {e}")

def write_symbols_raw(content, symbols_path): 
    """
    Escribe una cadena de texto directamente en el archivo symbols.csv.
    """
    try:
        # 1. Limpieza de líneas vacías
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        
        # 2. Reúne las líneas
        content_to_write = "\n".join(lines)
        
        # 3. Asegura un único salto de línea final para un formato CSV estándar
        if content_to_write:
            content_to_write += "\n"
            
        with open(symbols_path, mode='w', newline='', encoding='utf-8') as file:
            file.write(content_to_write)
            
        return True
    except Exception as e:
        raise Exception(f"No se pudo escribir en el archivo {symbols_path}: {e}")