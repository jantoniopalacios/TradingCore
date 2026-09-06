import gzip
import json
import logging
import os
import threading
import time
from pathlib import Path

from ..configuracion import BACKTESTING_BASE_DIR
from .helpers import _sanitize_filename_component


GRAPH_CACHE_BASE_DIR = BACKTESTING_BASE_DIR / 'Graphics' / 'cache'
GRAPH_CACHE_TTL_SECONDS = int(os.getenv('BACKTEST_GRAPH_CACHE_TTL_SECONDS', '86400'))
GRAPH_CACHE_CLEANUP_INTERVAL_SECONDS = int(os.getenv('BACKTEST_GRAPH_CACHE_CLEANUP_INTERVAL_SECONDS', '3600'))
_LAST_GRAPH_CACHE_CLEANUP_TS = 0.0
_GRAPH_CACHE_CLEANUP_LOCK = threading.Lock()


def _graph_cache_file_for_result(resultado):
    symbol_safe = _sanitize_filename_component(resultado.symbol or 'N/A')
    user_dir = GRAPH_CACHE_BASE_DIR / f"user_{resultado.usuario_id}"
    return user_dir / f"bt_{resultado.id}_{symbol_safe}.html"


def _graph_snapshot_file_for_result(resultado):
    symbol_safe = _sanitize_filename_component(resultado.symbol or 'N/A')
    user_dir = GRAPH_CACHE_BASE_DIR / f"user_{resultado.usuario_id}"
    return user_dir / f"bt_{resultado.id}_{symbol_safe}_snapshot.json.gz"


def _read_graph_snapshot_payload(resultado):
    snapshot_file = _graph_snapshot_file_for_result(resultado)
    if not snapshot_file.exists():
        return None
    try:
        with gzip.open(snapshot_file, 'rt', encoding='utf-8') as gz:
            return json.load(gz)
    except Exception as snapshot_err:
        logging.getLogger(__name__).warning("No se pudo leer snapshot de grafico %s: %s", snapshot_file, snapshot_err)
        return None


def _remove_graph_artifacts_for_result(resultado):
    try:
        _graph_cache_file_for_result(resultado).unlink(missing_ok=True)
    except Exception:
        pass
    try:
        _graph_snapshot_file_for_result(resultado).unlink(missing_ok=True)
    except Exception:
        pass


def _is_graph_cache_valid(cache_file: Path, ttl_seconds: int = GRAPH_CACHE_TTL_SECONDS) -> bool:
    if not cache_file.exists():
        return False
    if ttl_seconds <= 0:
        return True
    try:
        age_seconds = time.time() - cache_file.stat().st_mtime
        return age_seconds <= ttl_seconds
    except Exception:
        return False


def _prune_expired_graph_cache(force: bool = False):
    """
    Limpia archivos de cache vencidos y carpetas vacias.
    Se ejecuta de forma periodica para evitar crecimiento indefinido de disco.
    """
    global _LAST_GRAPH_CACHE_CLEANUP_TS

    now_ts = time.time()
    if not force and GRAPH_CACHE_CLEANUP_INTERVAL_SECONDS > 0:
        if (now_ts - _LAST_GRAPH_CACHE_CLEANUP_TS) < GRAPH_CACHE_CLEANUP_INTERVAL_SECONDS:
            return 0

    deleted = 0
    with _GRAPH_CACHE_CLEANUP_LOCK:
        # Revalidar dentro del lock para evitar limpieza duplicada en concurrencia.
        now_ts = time.time()
        if not force and GRAPH_CACHE_CLEANUP_INTERVAL_SECONDS > 0:
            if (now_ts - _LAST_GRAPH_CACHE_CLEANUP_TS) < GRAPH_CACHE_CLEANUP_INTERVAL_SECONDS:
                return 0

        try:
            if GRAPH_CACHE_BASE_DIR.exists():
                for cache_file in GRAPH_CACHE_BASE_DIR.rglob('*.html'):
                    if not _is_graph_cache_valid(cache_file):
                        try:
                            cache_file.unlink(missing_ok=True)
                            deleted += 1
                        except Exception as file_err:
                            logging.getLogger(__name__).warning(
                                "No se pudo eliminar cache vencido %s: %s", cache_file, file_err
                            )

                # Borrar directorios vacios (de abajo hacia arriba).
                for dir_path in sorted(
                    [d for d in GRAPH_CACHE_BASE_DIR.rglob('*') if d.is_dir()],
                    key=lambda p: len(p.parts),
                    reverse=True,
                ):
                    try:
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                    except Exception:
                        pass
        finally:
            _LAST_GRAPH_CACHE_CLEANUP_TS = time.time()

    return deleted