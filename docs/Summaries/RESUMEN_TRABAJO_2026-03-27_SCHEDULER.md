# Resumen de trabajo - 2026-03-27

## Contexto y objetivo del dia

Se realizo una mejora integral del flujo de ejecucion automatica de backtests y su exposicion en la aplicacion web.

Objetivos cubiertos:
- Analizar el envio de mails de resultados de estrategia.
- Identificar si existia script independiente para este flujo.
- Evolucionar el scheduler de backtests a un servicio robusto.
- Exponer control operativo del scheduler en la web para usuario admin.
- Corregir bugs detectados durante pruebas y revisar estabilidad.

## Analisis inicial realizado

### Envio de mails
Se reviso el circuito completo de envio de correos y se localizaron los puntos clave:
- Logica SMTP y utilidades de mail.
- Construccion de resultados en backtest.
- Carga de configuracion por usuario.
- Persistencia y uso de parametros desde base de datos.

### Script independiente
No se encontro un script dedicado exclusivamente al envio de mails.
El proceso quedo integrado en:
- Flujo de BacktestWeb.
- Scheduler de backtests (ejecucion por usuarios habilitados).

## Implementacion principal: scheduler automatico

Archivo principal trabajado:
- Utils/backtest_scheduler.py

Cambios funcionales:
- Reescritura a servicio APScheduler en modo continuo.
- Mapeo de intervalo de datos a triggers:
  - 1m, 2m, 5m, 15m, 30m, 60m, 1h, 90m -> IntervalTrigger por minutos.
  - 1d -> CronTrigger lun-vie 22:00.
  - 1wk -> CronTrigger lunes 09:00.
  - 1mo -> CronTrigger dia 1 09:00.
- Modos CLI agregados:
  - --ahora: ejecuta inmediatamente los usuarios elegibles.
  - --estado: muestra jobs sin arrancar scheduler continuo.
  - --dashboard: vista de estado en consola por refresco.
- Refresco de jobs cada 6 horas para releer configuraciones de BD sin reinicio.
- Ejecucion secuencial forzada para evitar colisiones:
  - ThreadPoolExecutor max_workers=1.
  - coalesce=True, max_instances=1, misfire_grace_time=3600.
- Persistencia de estado en JSON:
  - logs/backtest_scheduler_status.json
- Persistencia de PID:
  - logs/backtest_scheduler.pid

## Integracion en web (panel Scheduler admin)

Rutas Flask agregadas en scenarios/BacktestWeb/routes/main_bp.py:
- GET /scheduler/status
- POST /scheduler/start
- POST /scheduler/stop

Plantillas UI:
- Nueva pestana y javascript en scenarios/BacktestWeb/templates/index.html
- Nuevo parcial scenarios/BacktestWeb/templates/_tab_scheduler.html

Capacidades en UI:
- Boton Iniciar Scheduler.
- Boton Detener Scheduler.
- Boton Refrescar.
- Visualizacion de:
  - estado del scheduler,
  - jobs activos,
  - proxima ejecucion,
  - ultimas ejecuciones por usuario.
- Polling automatico cada 5 segundos cuando la pestana esta activa.

## Bugs detectados y corregidos

### 1) end_date None en Backtest
Archivo: scenarios/BacktestWeb/Backtest.py
- Se agrego fallback a fecha de ayer cuando end_date no viene informado.
- Evita fallos en parseo de fechas.

### 2) Log de exito enganoso
Archivo: Utils/backtest_scheduler.py
- Se corrigio el criterio de exito para no marcar ejecucion correcta si el backtest devolvia resultado invalido.

### 3) Riesgo de ejecucion concurrente
Archivo: Utils/backtest_scheduler.py
- Se limito el ejecutor para que no haya ejecuciones simultaneas de usuarios en paralelo.

### 4) Estado web inconsistente (running/crashed)
Archivo: scenarios/BacktestWeb/routes/main_bp.py
- Se ajusto deteccion de proceso vivo en Windows usando tasklist por PID.
- Se agrego reconciliacion del estado cuando JSON queda desfasado respecto al proceso real.

### 5) next_run_time vacio en dashboard
Archivo: Utils/backtest_scheduler.py
- Se ajusto el momento de marcado de estado running para que el snapshot se capture con jobs ya iniciados por APScheduler.

### 6) DeprecationWarning por utcnow
Archivo: Utils/backtest_scheduler.py
- Reemplazo de datetime.utcnow por datetime.now(timezone.utc).

## Observabilidad y logs

Se mejoro visibilidad de ejecucion desde web:
- Log dedicado para arranque web del scheduler:
  - logs/backtest_scheduler_web.log
- Status operativo en JSON para lectura por API/UI.

## Validaciones realizadas

- Compilacion sintactica Python de archivos modificados: OK.
- Verificacion de errores de editor/linter en archivos principales: sin errores relevantes.
- Prueba de comando --estado: OK.
- Prueba de comando --ahora: flujo ejecutado y trazas correctas.
- Prueba de panel web Scheduler: estado visible y funcionamiento correcto tras ajustes.

## Dependencias

Archivo actualizado:
- requirements.txt

Cambio:
- apscheduler==3.11.2

## Entrega en Git

Commit principal del dia:
- 3442fd42c37b1b01f8c8ca68d651575c02824794
- Mensaje: Add admin scheduler panel with web start/stop and APScheduler service hardening

Archivos incluidos en commit:
- Utils/backtest_scheduler.py
- requirements.txt
- scenarios/BacktestWeb/Backtest.py
- scenarios/BacktestWeb/routes/main_bp.py
- scenarios/BacktestWeb/templates/_tab_scheduler.html
- scenarios/BacktestWeb/templates/index.html

Push remoto:
- main -> origin/main completado.

## Operacion recomendada

### CLI
- python Utils/backtest_scheduler.py
- python Utils/backtest_scheduler.py --estado
- python Utils/backtest_scheduler.py --ahora
- python Utils/backtest_scheduler.py --dashboard

### Web (admin)
- Abrir pestana Scheduler.
- Iniciar/Detener scheduler.
- Revisar estado, jobs y ultimas ejecuciones.

## Estado final

La funcionalidad queda operativa de extremo a extremo:
- Scheduler robusto en background.
- Control y observabilidad desde web.
- Correcciones de estabilidad aplicadas.
- Cambios versionados y subidos al repositorio remoto.
