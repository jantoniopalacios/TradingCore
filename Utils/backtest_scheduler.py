"""
backtest_scheduler.py – Scheduler automático de backtests por usuario.

Lee la configuración de cada usuario en la BD y programa la ejecución de su
estrategia a la frecuencia que corresponde a su intervalo de datos:

  1m / 2m / 5m / 15m / 30m / 60m / 1h / 90m  → cada N minutos
  1d                                            → lunes a viernes a las 22:00
  1wk                                           → cada lunes a las 09:00
  1mo                                           → el día 1 de cada mes a las 09:00

Solo se programan usuarios que tengan `enviar_mail=True` y `destinatario_email`
configurado. Al finalizar cada ejecución se envía el mail con el formato
estándar ya implementado en Backtest.py.

Uso:
    python Utils/backtest_scheduler.py
    python Utils/backtest_scheduler.py --ahora        # ejecuta todos de inmediato y sale

Refresco de configuración:
    Cada 6 horas el scheduler re-lee la BD y actualiza los jobs automáticamente
    (no es necesario reiniciar si el usuario cambia su configuración o activa el mail).
"""

import sys
import json
import logging
import argparse
import os
import time
from pathlib import Path
from datetime import datetime, timezone

from flask import Flask
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scenarios.BacktestWeb.Backtest import ejecutar_backtest
from scenarios.BacktestWeb.database import Usuario, db

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backtest_scheduler")

STATUS_FILE_PATH = project_root / "logs" / "backtest_scheduler_status.json"
PID_FILE_PATH = project_root / "logs" / "backtest_scheduler.pid"
ACTIVE_SCHEDULER = None
STATUS_STATE = {
    'scheduler': {
        'status': 'stopped',
        'started_at': None,
        'updated_at': None,
        'last_refresh_at': None,
        'message': 'Scheduler no iniciado',
    },
    'jobs': [],
    'runs': {},
}

# ---------------------------------------------------------------------------
# Flask / BD  (mismo DSN que la app principal)
# ---------------------------------------------------------------------------
app = Flask(__name__)
DB_USER = "postgres"
DB_PASS = "admin"
DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "trading_db"
DATABASE_URL = f"postgresql+pg8000://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db.init_app(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _es_verdadero(valor) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in {'true', '1', 'yes'}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _snapshot_job(job) -> dict:
    next_run = getattr(job, 'next_run_time', None)
    return {
        'id': job.id,
        'name': job.name,
        'trigger': str(job.trigger),
        'next_run_time': str(next_run) if next_run is not None else None,
    }


def _write_status_file() -> None:
    scheduler = ACTIVE_SCHEDULER
    if scheduler is not None:
        STATUS_STATE['jobs'] = [_snapshot_job(job) for job in scheduler.get_jobs()]

    STATUS_STATE['scheduler']['updated_at'] = _utc_now_iso()
    STATUS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE_PATH.write_text(
        json.dumps(STATUS_STATE, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


def _set_scheduler_status(status: str, message: str) -> None:
    STATUS_STATE['scheduler']['status'] = status
    STATUS_STATE['scheduler']['message'] = message
    if status == 'running' and STATUS_STATE['scheduler']['started_at'] is None:
        STATUS_STATE['scheduler']['started_at'] = _utc_now_iso()
    _write_status_file()


def _write_pid_file() -> None:
    PID_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE_PATH.write_text(str(os.getpid()), encoding='utf-8')


def _remove_pid_file() -> None:
    try:
        if PID_FILE_PATH.exists():
            PID_FILE_PATH.unlink()
    except Exception:
        pass


def _set_run_status(username: str, **fields) -> None:
    run_state = STATUS_STATE['runs'].setdefault(username, {})
    run_state.update(fields)
    _write_status_file()


def _trigger_para_intervalo(intervalo: str):
    """Devuelve el trigger de APScheduler adecuado al intervalo de datos."""
    mapa_minutos = {
        '1m':  1,
        '2m':  2,
        '5m':  5,
        '15m': 15,
        '30m': 30,
        '60m': 60,
        '1h':  60,
        '90m': 90,
    }
    if intervalo in mapa_minutos:
        return IntervalTrigger(minutes=mapa_minutos[intervalo])

    if intervalo == '1d':
        # Lunes a viernes a las 22:00 (tras el cierre de mercados EU/US)
        return CronTrigger(day_of_week='mon-fri', hour=22, minute=0, timezone='Europe/Madrid')

    if intervalo == '1wk':
        # Cada lunes a las 09:00
        return CronTrigger(day_of_week='mon', hour=9, minute=0, timezone='Europe/Madrid')

    if intervalo == '1mo':
        # El día 1 de cada mes a las 09:00
        return CronTrigger(day=1, hour=9, minute=0, timezone='Europe/Madrid')

    logger.warning(f"Intervalo desconocido '{intervalo}'; se usará trigger diario (22:00 L-V).")
    return CronTrigger(day_of_week='mon-fri', hour=22, minute=0, timezone='Europe/Madrid')


# ---------------------------------------------------------------------------
# Tarea por usuario
# ---------------------------------------------------------------------------

def _ejecutar_para_usuario(username: str) -> None:
    """Job que APScheduler llama para un usuario concreto."""
    logger.info(f"[{username}] Iniciando backtest programado")
    with app.app_context():
        usuario = Usuario.query.filter_by(username=username).first()
        if not usuario:
            logger.warning(f"[{username}] Usuario no encontrado en BD; saltando.")
            return

        config = {}
        if usuario.config_actual:
            try:
                config = json.loads(usuario.config_actual)
            except Exception as exc:
                logger.error(f"[{username}] Error parseando config_actual: {exc}")
                return

        enviar_mail     = config.get('enviar_mail', False)
        destinatario    = config.get('destinatario_email', '')
        intervalo       = config.get('intervalo', '1d')

        if not (_es_verdadero(enviar_mail) and str(destinatario).strip()):
            logger.info(f"[{username}] enviar_mail desactivado o sin destinatario; saltando.")
            return

        logger.info(f"[{username}] Ejecutando backtest (intervalo={intervalo}) → {destinatario}")
        _set_run_status(
            username,
            status='running',
            intervalo=intervalo,
            destinatario=destinatario,
            started_at=_utc_now_iso(),
            finished_at=None,
            message='Backtest en ejecución',
            last_result_count=None,
            last_trade_count=None,
            last_error=None,
        )
        try:
            resultados_df, trades_df, _ = ejecutar_backtest({
                'user_mode':         username,
                'enviar_mail':       True,
                'destinatario_email': destinatario,
            })
            if resultados_df is None:
                logger.error(f"[{username}] Backtest finalizado con error (sin resultados).")
                _set_run_status(
                    username,
                    status='error',
                    finished_at=_utc_now_iso(),
                    message='Backtest finalizado con error (sin resultados)',
                    last_result_count=None,
                    last_trade_count=None,
                    last_error='Sin resultados',
                )
            else:
                logger.info(
                    f"[{username}] Backtest completado correctamente "
                    f"(resultados={len(resultados_df)}, trades={0 if trades_df is None else len(trades_df)})."
                )
                _set_run_status(
                    username,
                    status='ok',
                    finished_at=_utc_now_iso(),
                    message='Backtest completado correctamente',
                    last_result_count=len(resultados_df),
                    last_trade_count=0 if trades_df is None else len(trades_df),
                    last_error=None,
                )
        except Exception as exc:
            logger.exception(f"[{username}] Error ejecutando backtest: {exc}")
            _set_run_status(
                username,
                status='error',
                finished_at=_utc_now_iso(),
                message='Excepción ejecutando backtest',
                last_result_count=None,
                last_trade_count=None,
                last_error=str(exc),
            )


# ---------------------------------------------------------------------------
# Registro / refresco de jobs
# ---------------------------------------------------------------------------

def registrar_jobs(scheduler: BlockingScheduler) -> None:
    """
    Lee todos los usuarios de la BD y crea (o actualiza) un job por cada uno
    que tenga enviar_mail=True y destinatario_email definido.
    Jobs de usuarios que ya no cumplen la condición son eliminados.
    """
    with app.app_context():
        usuarios = Usuario.query.all()
        usernames_activos = set()

        for usuario in usuarios:
            config = {}
            if usuario.config_actual:
                try:
                    config = json.loads(usuario.config_actual)
                except Exception:
                    continue

            enviar_mail  = config.get('enviar_mail', False)
            destinatario = config.get('destinatario_email', '')
            intervalo    = config.get('intervalo', '1d')

            job_id = f"backtest_{usuario.username}"

            if not (_es_verdadero(enviar_mail) and str(destinatario).strip()):
                # Si el job existía y ahora el usuario desactivó el mail, lo borramos
                if scheduler.get_job(job_id):
                    scheduler.remove_job(job_id)
                    logger.info(f"[{usuario.username}] Job eliminado (mail desactivado).")
                else:
                    logger.info(f"[{usuario.username}] Sin mail activo; no se programa.")
                continue

            trigger = _trigger_para_intervalo(intervalo)
            scheduler.add_job(
                func=_ejecutar_para_usuario,
                trigger=trigger,
                args=[usuario.username],
                id=job_id,
                name=f"Backtest {usuario.username} ({intervalo})",
                replace_existing=True,
            )
            job = scheduler.get_job(job_id)
            next_run = getattr(job, 'next_run_time', None)
            next_run_str = str(next_run) if next_run is not None else "pendiente (scheduler no iniciado)"
            logger.info(
                f"[{usuario.username}] Job programado | intervalo={intervalo} | próxima ejecución={next_run_str}"
            )
            usernames_activos.add(usuario.username)

    logger.info(f"Jobs activos tras registro: {len(usernames_activos)}")
    STATUS_STATE['scheduler']['last_refresh_at'] = _utc_now_iso()
    STATUS_STATE['scheduler']['message'] = f'Jobs activos: {len(usernames_activos)}'
    _write_status_file()


def _refrescar_jobs(scheduler: BlockingScheduler) -> None:
    """Job de mantenimiento: re-lee la BD y actualiza el scheduling sin reiniciar."""
    logger.info("Refrescando jobs desde BD...")
    registrar_jobs(scheduler)


def _crear_scheduler() -> BlockingScheduler:
    """Construye el scheduler con configuración segura para ejecución prolongada."""
    # Ejecución secuencial para evitar solapes entre usuarios.
    # Importante: la estrategia usa estado compartido de clase (System.*).
    executors = {
        'default': ThreadPoolExecutor(max_workers=1),
    }
    job_defaults = {
        'coalesce': True,
        'max_instances': 1,
        # Si el proceso estuvo parado o ocupado, toleramos un retraso razonable.
        'misfire_grace_time': 3600,
    }
    return BlockingScheduler(
        timezone='Europe/Madrid',
        executors=executors,
        job_defaults=job_defaults,
    )


def mostrar_estado_jobs() -> None:
    """Muestra por consola los jobs que quedarían programados en este momento."""
    logger.info("Modo --estado: construyendo jobs desde la configuración actual de BD.")
    scheduler = _crear_scheduler()
    registrar_jobs(scheduler)

    jobs = scheduler.get_jobs()
    print("\n=== ESTADO DEL SCHEDULER ===")
    print(f"Jobs programados: {len(jobs)}")

    if not jobs:
        print("No hay jobs activos (revisa enviar_mail y destinatario_email en cada usuario).")
        return

    for idx, job in enumerate(jobs, start=1):
        next_run = getattr(job, 'next_run_time', None)
        next_run_str = str(next_run) if next_run is not None else "pendiente (scheduler no iniciado)"
        print(f"{idx}. id={job.id}")
        print(f"   nombre={job.name}")
        print(f"   trigger={job.trigger}")
        print(f"   proxima_ejecucion={next_run_str}")


def mostrar_dashboard(refresh_seconds: int = 5) -> None:
    """Muestra un cuadro de mando en consola leyendo el JSON de estado."""
    if not STATUS_FILE_PATH.exists():
        print(f"No existe estado aún: {STATUS_FILE_PATH}")
        print("Arranca primero el scheduler continuo para generar el fichero de estado.")
        return

    try:
        while True:
            raw = json.loads(STATUS_FILE_PATH.read_text(encoding='utf-8'))
            os.system('cls' if os.name == 'nt' else 'clear')
            scheduler_state = raw.get('scheduler', {})
            jobs = raw.get('jobs', [])
            runs = raw.get('runs', {})

            print("=== DASHBOARD SCHEDULER ===")
            print(f"Estado: {scheduler_state.get('status')} | Mensaje: {scheduler_state.get('message')}")
            print(f"Iniciado: {scheduler_state.get('started_at')}")
            print(f"Ultima actualizacion: {scheduler_state.get('updated_at')}")
            print(f"Ultimo refresco jobs: {scheduler_state.get('last_refresh_at')}")
            print()
            print(f"Jobs activos: {len(jobs)}")
            for idx, job in enumerate(jobs, start=1):
                print(f"{idx}. {job.get('name')} | trigger={job.get('trigger')} | next={job.get('next_run_time')}")

            print()
            print(f"Ejecuciones registradas: {len(runs)}")
            for username, run_state in sorted(runs.items()):
                print(
                    f"- {username}: status={run_state.get('status')} | intervalo={run_state.get('intervalo')} "
                    f"| inicio={run_state.get('started_at')} | fin={run_state.get('finished_at')} "
                    f"| resultados={run_state.get('last_result_count')} | trades={run_state.get('last_trade_count')}"
                )
                if run_state.get('last_error'):
                    print(f"  error={run_state.get('last_error')}")

            print()
            print(f"Estado JSON: {STATUS_FILE_PATH}")
            print("Ctrl+C para salir")
            time.sleep(refresh_seconds)
    except KeyboardInterrupt:
        print("Dashboard detenido.")


# ---------------------------------------------------------------------------
# Ejecución inmediata (modo --ahora)
# ---------------------------------------------------------------------------

def ejecutar_todos_ahora() -> None:
    """Ejecuta el backtest de todos los usuarios elegibles de inmediato y termina."""
    logger.info("Modo --ahora: ejecutando todos los usuarios de forma inmediata.")
    with app.app_context():
        usuarios = Usuario.query.all()
        for usuario in usuarios:
            config = {}
            if usuario.config_actual:
                try:
                    config = json.loads(usuario.config_actual)
                except Exception:
                    continue
            enviar_mail  = config.get('enviar_mail', False)
            destinatario = config.get('destinatario_email', '')
            if _es_verdadero(enviar_mail) and str(destinatario).strip():
                _ejecutar_para_usuario(usuario.username)
    logger.info("Ejecución inmediata completada.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scheduler automático de backtests por usuario.")
    parser.add_argument(
        '--ahora', action='store_true',
        help="Ejecuta el backtest de todos los usuarios elegibles de inmediato y termina."
    )
    parser.add_argument(
        '--estado', action='store_true',
        help="Muestra los jobs programados actualmente y termina."
    )
    parser.add_argument(
        '--dashboard', action='store_true',
        help="Muestra un cuadro de mando en vivo leyendo el estado del scheduler."
    )
    args = parser.parse_args()

    if args.ahora:
        ejecutar_todos_ahora()
        sys.exit(0)

    if args.estado:
        mostrar_estado_jobs()
        sys.exit(0)

    if args.dashboard:
        mostrar_dashboard()
        sys.exit(0)

    logger.info("=== Iniciando backtest_scheduler (modo continuo) ===")
    scheduler = _crear_scheduler()
    ACTIVE_SCHEDULER = scheduler
    _write_pid_file()
    _set_scheduler_status('starting', 'Arrancando scheduler')

    # Registrar jobs según la config actual de la BD
    registrar_jobs(scheduler)

    # Job de mantenimiento: refresca la config cada 6 horas
    scheduler.add_job(
        func=_refrescar_jobs,
        trigger=IntervalTrigger(hours=6),
        args=[scheduler],
        id='_refresh_jobs',
        name='Refresco de configuración de usuarios',
    )

    # Actualizar status a 'running' DESPUÉS de que APScheduler asigne next_run_time.
    # APScheduler llama al listener 'scheduler_started' justo tras iniciar el bucle.
    def _on_scheduler_started(event):  # noqa: E306
        _set_scheduler_status('running', 'Scheduler activo')

    from apscheduler.events import EVENT_SCHEDULER_STARTED
    scheduler.add_listener(_on_scheduler_started, EVENT_SCHEDULER_STARTED)

    logger.info("Scheduler activo. Ctrl+C para detener.")
    # Nota: _set_scheduler_status se llama DESPUÉS de scheduler.start() para
    # que _snapshot_job capture los next_run_time reales (no tentative).
    try:
        scheduler.start()  # bloqueante — regresa sólo al detener
        # scheduler.start() lanza el bucle; cuando termina el proceso sigue aquí
        _set_scheduler_status('stopped', 'Scheduler detenido')
        logger.info("Scheduler detenido.")
    except (KeyboardInterrupt, SystemExit):
        _set_scheduler_status('stopped', 'Scheduler detenido')
        logger.info("Scheduler detenido.")
    except Exception as exc:
        _set_scheduler_status('crashed', f'Error inesperado: {exc}')
        logger.exception("Scheduler terminó con error.")
        raise
    finally:
        _remove_pid_file()
