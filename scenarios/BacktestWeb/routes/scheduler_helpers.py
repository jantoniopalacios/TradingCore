import json
import os
import subprocess


def _remove_orphan_pid_file(pid_path) -> None:
    try:
        pid_path.unlink()
    except Exception:
        pass


def _is_scheduler_running_from_pid(pid_path) -> bool:
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text(encoding='utf-8').strip())
        if pid <= 0:
            _remove_orphan_pid_file(pid_path)
            return False
    except Exception:
        _remove_orphan_pid_file(pid_path)
        return False

    if os.name == 'nt':
        # Use Get-CimInstance para verificar tanto la existencia del PID como
        # que el proceso corresponde realmente al backtest_scheduler.py.
        try:
            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"(Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\").CommandLine",
                ],
                text=True,
                encoding='utf-8',
                errors='ignore',
            )
            if "backtest_scheduler.py" in out.lower():
                return True
            _remove_orphan_pid_file(pid_path)
            return False
        except Exception:
            _remove_orphan_pid_file(pid_path)
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            _remove_orphan_pid_file(pid_path)
            return False


def _read_scheduler_status_file(status_path) -> dict:
    if not status_path.exists():
        return {}
    try:
        return json.loads(status_path.read_text(encoding='utf-8'))
    except Exception:
        return {}