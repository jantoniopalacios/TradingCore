import threading
from datetime import datetime, timezone


BACKTEST_STATUS_BY_USER = {}
BACKTEST_STATUS_LOCK = threading.Lock()


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _init_backtest_status(user_mode, run_id, tanda_id):
    with BACKTEST_STATUS_LOCK:
        BACKTEST_STATUS_BY_USER[user_mode] = {
            'run_id': run_id,
            'tanda_id': tanda_id,
            'status': 'queued',
            'phase_index': 0,
            'phase_total': 0,
            'phase': 'En cola',
            'message': 'Backtest en cola de ejecucion',
            'events': [{
                'timestamp': _utc_now_iso(),
                'phase': 'En cola',
                'message': 'Backtest en cola de ejecucion'
            }],
            'started_at': _utc_now_iso(),
            'updated_at': _utc_now_iso(),
            'finished_at': None,
            'result_count': 0,
            'error': None,
        }


def _append_backtest_event(user_mode, phase, message):
    with BACKTEST_STATUS_LOCK:
        state = BACKTEST_STATUS_BY_USER.get(user_mode)
        if not state:
            return
        state['events'].append({
            'timestamp': _utc_now_iso(),
            'phase': str(phase),
            'message': str(message),
        })
        state['events'] = state['events'][-120:]
        state['updated_at'] = _utc_now_iso()


def _set_backtest_progress(user_mode, phase_index, phase_total, phase, message, status='running'):
    with BACKTEST_STATUS_LOCK:
        state = BACKTEST_STATUS_BY_USER.get(user_mode)
        if not state:
            return
        state['status'] = status
        state['phase_index'] = int(phase_index)
        state['phase_total'] = int(phase_total)
        state['phase'] = str(phase)
        state['message'] = str(message)
        state['updated_at'] = _utc_now_iso()
    _append_backtest_event(user_mode, phase, message)


def _finish_backtest_status(user_mode, status, message, result_count=0, error=None):
    with BACKTEST_STATUS_LOCK:
        state = BACKTEST_STATUS_BY_USER.get(user_mode)
        if not state:
            return
        state['status'] = status
        state['message'] = str(message)
        state['result_count'] = int(result_count or 0)
        state['error'] = str(error) if error else None
        state['finished_at'] = _utc_now_iso()
        state['updated_at'] = _utc_now_iso()
        state['events'].append({
            'timestamp': _utc_now_iso(),
            'phase': 'Finalizado' if status == 'completed' else 'Error',
            'message': str(message),
        })
        state['events'] = state['events'][-120:]