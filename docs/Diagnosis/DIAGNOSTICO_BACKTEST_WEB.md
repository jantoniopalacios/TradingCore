# Diagnostico: Backtest web no genera resultados

## Problema Reportado
El backtest funcionaba por linea de comandos, pero fallaba silenciosamente al lanzarse desde la web.

## Cambios implementados

### 1. `Backtest.py` - `ejecutar_backtest()`
Problema identificado: falta de manejo de excepciones en operaciones criticas.

Solucion aplicada:
- Agregado try-catch comprehensivo alrededor de toda la función
- Logging detallado en cada paso (9 pasos identificados)
- Validaciones explícitas en cada fase:
  - Configuración cargada ✓
  - Usuario encontrado en BD ✓
  - Símbolos disponibles ✓
  - Datos descargados ✓
  - Ratios calculados ✓
  - Backtest ejecutado ✓
  - Gráficos generados ✓
  - Resultados guardados en BD ✓
- Traceback completo en logs de errores

### 2. `main_bp.py` - `run_backtest_and_save()`
Problema identificado: falta de logging en la funcion de hilo.

Solucion aplicada:
- Agregado logger estructurado
- Validaciones explícitas de resultados
- Manejo de errores de sesión DB
- Mensajes informativos en cada fase

### 3. `main_bp.py` - `launch_strategy()`
Problema identificado: baja trazabilidad de configuracion enviada al motor.

Solucion aplicada:
- Logging de configuración inicial
- Detalles de parámetros:
  - Usuario y ID
  - Tanda de ejecución
  - Indicadores activos
  - Cantidad de símbolos
- Confirmación al iniciar hilo
- Traceback en caso de error

## Como diagnosticar problemas

### Paso 1: Activar logs en detalle
Verificar configuracion de logging en Flask (`app.py` o `__init__.py`):

```python
import logging
import logging.handlers
from pathlib import Path

# Crear directorio de logs si no existe
logs_dir = Path("./logs")
logs_dir.mkdir(exist_ok=True)

# Configurar logging global
logging.basicConfig(
    level=logging.DEBUG,  # Cambiar a DEBUG para ver TODO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / "trading_app.log"),
        logging.StreamHandler()  # También mostrar en consola
    ]
)

# Específicamente para Backtest
logging.getLogger("Ejecucion").setLevel(logging.DEBUG)
logging.getLogger("BacktestExecution").setLevel(logging.DEBUG)
logging.getLogger("LaunchStrategy").setLevel(logging.DEBUG)
```

### Paso 2: Monitorear logs en tiempo real

**Opción A: Desde PowerShell (recomendado)**
```powershell
# Monitorear archivo de log en tiempo real
Get-Content -Path ".\logs\trading_app.log" -Wait
```

**Opción B: Desde terminal**
```bash
# En Windows PowerShell
tail -f .\logs\trading_app.log

# En Linux/Mac
tail -f ./logs/trading_app.log
```

### Paso 3: Ejecutar desde web y observar

1. **Abre la aplicación web**
2. **Configura los parámetros** (símbolos, periodos, indicadores)
3. **Haz clic en "Lanzar Backtest"**
4. **Monitorea los logs** en tiempo real

Ejemplo de logs esperados:
```
[LAUNCH] Usuario admin lanzando backtest...
[LAUNCH] Cargando configuración base para admin
[LAUNCH] Configuración preparada:
  - Usuario: admin (ID=1)
  - Tanda: #1
  - Indicadores activos: 3
  - Símbolos: 1
[LAUNCH] ✅ Iniciando hilo de backtest...

======================================================================
🚀 INICIANDO BACKTEST | Usuario: admin | Tanda: 1
======================================================================
[1/9] Cargando configuración para usuario: admin
✅ Configuración cargada
[2/9] Sincronizando parámetros System
✅ System sincronizado
[3/9] Buscando símbolos del usuario en BD
✅ 1 símbolos encontrados: ['NKE']
[4/9] Descargando datos históricos de Yahoo Finance
✅ Datos descargados: 11386 registros
[5/9] Procesando datos fundamentales
✅ Datos fundamentales procesados
[6/9] Calculando ratios OHLCV
✅ Ratios calculados
[8/9] Ejecutando motor de backtest multi-símbolo
  Procesando 1 símbolos...
✅ Backtest completado: 1 resultados
[9/9] Generando gráficos
  Generando gráfico: NKE
  ✅ Gráfico guardado: ./Graph/NKE_backtest.html
Guardando resultados en base de datos
✅ 1/1 resultados guardados en BD
✨ Ciclo completado exitosamente en 15.32s
```

## Errores comunes y soluciones

### Usuario no registrado
```
❌ Usuario 'admin' no registrado en BD.
```
**Solución:**
- Verifica que el usuario existe en la tabla `usuarios`
- Comprueba que la sesión tiene `user_mode` correcto

### Usuario sin simbolos
```
⚠️  Usuario 'admin' no tiene símbolos asignados
```
**Solución:**
- Ve a la interfaz web y asegúrate de que el usuario tiene al menos 1 símbolo seleccionado
- Verifica en BD que la tabla `simbolos` tiene registros con `usuario_id` correcto

### Sin datos historicos descargados
```
❌ Sin datos históricos descargados
```
**Solución:**
- Verifica que `descargar_datos_YF()` está funcionando
- Comprueba directorios: `data_files_path` existe y es accesible
- Revisa si hay archivos CSV en `Data_files/`
- Aumenta los logs en `Data_download.py`

### Motor sin resultados
```
⚠️  El motor de backtest no retornó resultados
```
**Solución:**
- Revisa `run_multi_symbol_backtest()` en `trading_engine/core/Backtest_Runner.py`
- Verifica que la clase Strategy está configurada correctamente
- Asegúrate de que hay datos válidos para backtest

### Error guardando resultado
```
❌ Error calculando la sesión ... para Symbol NKE: 
```
**Solución:**
- Verifica conexión a PostgreSQL
- Comprueba que tablas existen: `resultados_backtest`, `trades`
- Revisa si hay violaciones UK/FK en BD

## Estructura de logs recomendada

Archivo sugerido en la raiz: `logging_config.py`.

```python
import logging
import logging.handlers
from pathlib import Path

def setup_logging(app=None):
    """Configura logging global para toda la app"""
    
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Formato estándar
    formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)-8s] - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para archivo general
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "trading_app.log",
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Loggers específicos del app
    for logger_name in ['Ejecucion', 'BacktestExecution', 'LaunchStrategy', 'Backtest_Runner']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
    
    if app:
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.DEBUG)
    
    return root_logger

# Uso en app.py:
# from logging_config import setup_logging
# setup_logging(app)
```

## Checklist de diagnostico

- [ ] **Logs configurados** - Verifica que `logging_config.py` está activo
- [ ] **Directorio logs existe** - `./logs/` debe existir y ser escribible
- [ ] **Usuario en BD** - Verifica tabla `usuarios` tiene el usuario
- [ ] **Símbolos asignados** - Verifica tabla `simbolos` tiene registros
- [ ] **Datos disponibles** - Archivos CSV existen en `Data_files/`
- [ ] **Conexión BD** - PostgreSQL está corriendo y accesible
- [ ] **Permisos de archivo** - Carpetas `Data_files/`, `Graph/`, `logs/` son escribibles
- [ ] **Variables de entorno** - `data_files_path`, `graph_dir` configurados en config

## Proximos pasos

1. **Implementa logging según estructura recomendada**
2. **Lanza un backtest desde web**
3. **Monitorea los logs en tiempo real**
4. **Identifica el punto exacto donde falla**
5. **Reporta el error específico** con logs relevantes

Con esta estructura, el punto de fallo queda visible en logs.

## Notas tecnicas

### Por que pueden fallar silenciosamente en web
1. **Flask/Gunicorn captura excepciones** sin mostrarlas
2. **Hilos separados** no comparten stderr/stdout
3. **Sesiones de BD** en hilo separado requieren contexto especial
4. **Buffering de output** en servidores web

### Como se soluciona
- try-catch en todos los niveles
- logging con `FileHandler`
- traceback capturado y registrado
- validaciones explicitas entre pasos
- contexto Flask preservado en hilos
