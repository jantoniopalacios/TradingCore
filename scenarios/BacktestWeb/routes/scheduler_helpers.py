import json
import os
import subprocess


def _is_scheduler_running_from_pid(pid_path) -> bool:
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text(encoding='utf-8').strip())
    except Exception:
        return False

    if os.name == 'nt':
        # Use tasklist on Windows because OpenProcess/GetExitCodeProcess can fail
        # with permission/flag combinations for detached processes.
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}"],
                text=True,
                encoding='utf-8',
                errors='ignore',
            )
            return str(pid) in out and "No tasks are running" not in out
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False


def _read_scheduler_status_file(status_path) -> dict:
    if not status_path.exists():
        return {}
    try:
        return json.loads(status_path.read_text(encoding='utf-8'))
    except Exception:
        return {}