import os
import re
import shutil
import csv
from datetime import datetime
from pathlib import Path
# Asumimos que PROJECT_ROOT y BACKTESTING_BASE_DIR se definen en configuracion.py
from .configuracion import PROJECT_ROOT, BACKTESTING_BASE_DIR

# ----------------------------------------------------------------------
# --- CONSTANTES DE RUTA CENTRALIZADAS ---
# ----------------------------------------------------------------------

BACKTESTING_DIR = BACKTESTING_BASE_DIR

# ----------------------------------------------------------------------
# --- CONTROL DE ACCESO A DOCUMENTACIÓN (docs/) POR ROL ---
# ----------------------------------------------------------------------

# Documentos visibles/abribles por un usuario normal (rutas relativas a docs/).
# Para ampliar el acceso de usuarios normales basta con añadir entradas aquí.
DOCS_ALLOWED_FOR_USER = frozenset({
    Path("README.md"),
    Path("Guides/GUIA_COMBINACION_INDICADORES.md"),
    Path("Guides/GUIA_STOPS_Y_PROTECCION.md"),
    Path("Guides/QUICK_START_BACKTEST_WEB.md"),
})


def is_docs_path_allowed(relative_path, is_admin=False):
    """
    Determina si una ruta relativa a docs/ puede verse/abrirse según el rol.

    - admin: True para cualquier ruta válida dentro de docs/.
    - usuario normal: True solo para los documentos en DOCS_ALLOWED_FOR_USER
      y para los directorios padre necesarios para construir el árbol
      (p.ej. 'Guides' es visible porque contiene documentos permitidos).
    - cualquier ruta absoluta o con '..' (traversal) se rechaza, incluso para admin.
    """
    # Normalizamos separadores sin tocar el sistema de archivos (no resolvemos symlinks aquí).
    normalized = Path(str(relative_path).replace('\\', '/'))

    if normalized.is_absolute() or '..' in normalized.parts:
        return False

    if is_admin:
        return True

    # Raíz de docs (ruta vacía): necesaria para poder empezar a construir el árbol.
    if not normalized.parts:
        return True

    if normalized in DOCS_ALLOWED_FOR_USER:
        return True

    # Directorio padre (parcial) de algún documento permitido.
    parts = normalized.parts
    for allowed in DOCS_ALLOWED_FOR_USER:
        if len(parts) < len(allowed.parts) and allowed.parts[:len(parts)] == parts:
            return True

    return False

# ----------------------------------------------------------------------
# --- FUNCIONES DE MANEJO DE DIRECTORIOS Y ARCHIVOS ---
# ----------------------------------------------------------------------

def clean_run_results_dir(results_path): 
    """Elimina y recrea el directorio de resultados."""
    try:
        if results_path.exists():
            shutil.rmtree(results_path) 
        results_path.mkdir(parents=True, exist_ok=True)
        return True, f"El directorio '{results_path.name}' ha sido limpiado."
    except Exception as e:
        return False, f"Error crítico al limpiar '{results_path.name}': {e}"

def get_directory_tree(path, is_admin=False, base_path=None, path_filter=None):
    """Genera el árbol de directorios para el explorador web en formato de diccionario.

    path_filter : callable(relative_path: Path, is_admin: bool) -> bool, opcional.
        Si se indica, se evalúa para cada elemento (relativo a `base_path`, o a la
        raíz de partida si no se indica `base_path`) y los elementos no autorizados
        se excluyen del árbol. Se usa para restringir docs/ por rol sin afectar
        a otros árboles (p.ej. logs), que se llaman sin este parámetro.
    """
    # Si recibimos una lista de paths, los procesamos recursivamente
    if isinstance(path, list):
        combined_tree = []
        for p in path:
            combined_tree.extend(get_directory_tree(p, is_admin, base_path=base_path, path_filter=path_filter))
        return combined_tree

    # La raíz para calcular rutas relativas se fija en la primera llamada y se propaga.
    root_for_relative = base_path if base_path is not None else path

    tree = []
    if not path.exists():
        return tree
    
    try:
        for item in path.iterdir():
            # Filtro de seguridad para logs
            if item.name == "trading_app.log" and not is_admin:
                continue

            if path_filter is not None:
                try:
                    relative_item_path = item.relative_to(root_for_relative)
                except ValueError:
                    relative_item_path = Path(item.name)
                if not path_filter(relative_item_path, is_admin):
                    continue

            if item.is_dir():
                children = get_directory_tree(
                    item, is_admin, base_path=root_for_relative, path_filter=path_filter
                )
                # Si el filtro de docs dejó la carpeta sin hijos visibles, no la mostramos.
                if path_filter is not None and not is_admin and not children:
                    continue
                # Formato diccionario para compatibilidad con el frontend
                tree.append({
                    "name": item.name,
                    "is_dir": True,
                    "children": children,
                    "type": "Folder",
                    "path": item.name
                })
            else:
                dt = datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                tree.append({
                    "name": item.name,
                    "is_dir": False,
                    "children": [],
                    "type": "File",
                    "date": dt,
                    "path": item.name
                })
    except Exception as e:
        print(f"Error al acceder a {path}: {e}")
    
    # Ordenar: primero carpetas, luego archivos, ambos alfabéticamente
    return sorted(tree, key=lambda x: (not x["is_dir"], x["name"].lower()))

# ----------------------------------------------------------------------
# --- FUNCIONES DE CONFIGURACIÓN (.ENV) ---
# ----------------------------------------------------------------------

def read_config_with_metadata(config_path):
    """Lee el archivo .env extrayendo variables y sus comentarios previos."""
    variables = {}
    comments = {}
    var_regex = re.compile(r'^\s*(\w+)\s*=\s*([^\n#]+)', re.MULTILINE)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            variables['__full_content__'] = content 
            
            lines = content.split('\n')
            current_comment_block = []
            
            for line in lines:
                trimmed_line = line.strip()
                match = var_regex.match(line)
                
                if trimmed_line.startswith('#'):
                    if trimmed_line.replace('#', '').strip() != '---':
                        current_comment_block.append(trimmed_line.lstrip('#').strip())
                elif match:
                    name = match.group(1).strip()
                    value = match.group(2).strip().strip('"').strip("'")
                    variables[name] = value
                    comments[name] = "\n".join(current_comment_block) if current_comment_block else "Sin documentación."
                    current_comment_block = []
                else:
                    if trimmed_line == '' and not current_comment_block:
                        pass
                    elif current_comment_block:
                        current_comment_block = [] 
            
    except FileNotFoundError:
        return None, None 
    except Exception as e:
        raise Exception(f"Error al leer .env ({config_path}): {e}")
        
    return variables, comments

def write_config(new_values, full_content, config_path):
    """Escribe los nuevos valores en el .env preservando comentarios."""
    new_content = full_content
    for name, value in new_values.items():
        pattern = re.compile(rf'^\s*{re.escape(name)}\s*=\s*([^\n#]+)', re.MULTILINE)
        formatted_value = str(value).strip()
        if isinstance(value, bool) or str(value).lower() in ('true', 'false'):
            formatted_value = "True" if str(value).lower() in ('true', 'on') else "False"
        elif not (str(value).isnumeric() or re.match(r'^-?\d*\.?\d+$', formatted_value)):
            formatted_value = f'"{formatted_value.strip(chr(34))}"'

        new_content, count = pattern.subn(f'{name} = {formatted_value}', new_content)
        if count == 0:
            new_content += f"\n{name} = {formatted_value}"

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(new_content.strip() + "\n")
    except Exception as e:
        raise Exception(f"Error al escribir en {config_path}: {e}")
    return True

# ----------------------------------------------------------------------
# --- FUNCIONES DE MANEJO CSV (RAW Y MÉTRICAS) ---
# ----------------------------------------------------------------------

def read_symbols_raw(symbols_path):
    """Lee el archivo de símbolos como texto plano."""
    try:
        with open(symbols_path, mode='r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return "Symbol,Name\n" 
    except Exception as e:
        raise Exception(f"Error al leer {symbols_path}: {e}")

def write_symbols_raw(content, symbols_path): 
    """Escribe el contenido de símbolos asegurando formato CSV."""
    try:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        content_to_write = "\n".join(lines)
        if content_to_write:
            content_to_write += "\n"
        with open(symbols_path, mode='w', newline='', encoding='utf-8') as file:
            file.write(content_to_write)
        return True
    except Exception as e:
        raise Exception(f"Error al escribir en {symbols_path}: {e}")

def extraer_metricas_backtest(ruta_csv):
    """Extrae métricas finales de resultados_estrategia.csv."""
    metricas = {
        'beneficio_neto': 0.0,
        'drawdown_max': 0.0,
        'num_operaciones': 0,
        'win_rate': 0.0
    }

    path = Path(ruta_csv)
    if not path.exists():
        return metricas

    try:
        with open(path, mode='r', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))
            if not reader:
                return metricas

            ultima_fila = reader[-1]
            metricas['beneficio_neto'] = float(ultima_fila.get('Net Profit', 0))
            metricas['drawdown_max'] = float(ultima_fila.get('Max DD', 0))
            metricas['num_operaciones'] = int(float(ultima_fila.get('Total Trades', 0)))
            
            wr = str(ultima_fila.get('Win Rate', '0')).replace('%', '').strip()
            metricas['win_rate'] = float(wr)

    except Exception as e:
        print(f"DEBUG: Error procesando métricas del CSV {path.name}: {e}")

    return metricas