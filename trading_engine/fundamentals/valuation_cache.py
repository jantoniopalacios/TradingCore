from __future__ import annotations

import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)


@contextmanager
def _valuation_cache_lock(path):
    path = Path(path)
    lock_path = path.with_name(f".{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _normalize_date_column(frame):
    data = frame.copy()
    if "Date" not in data.columns:
        if data.index.name == "Date" or isinstance(data.index, pd.DatetimeIndex):
            data.reset_index(inplace=True)
            if "index" in data.columns and "Date" not in data.columns:
                data.rename(columns={"index": "Date"}, inplace=True)
        elif len(data.columns) and data.columns[0] not in {"Symbol", "Date"}:
            data.rename(columns={data.columns[0]: "Date"}, inplace=True)
    return data


def read_valuation_rows(path):
    data = _normalize_date_column(pd.read_csv(path, sep=";"))
    if not {"Date", "Symbol"}.issubset(data.columns):
        raise ValueError(
            f"{Path(path).name} existente no contiene Date y Symbol; se conserva sin modificar."
        )
    return data


def merge_valuation_rows(existing, recalculated, selected_symbols):
    selected_set = {str(symbol).strip().upper() for symbol in selected_symbols}
    old_data = _normalize_date_column(existing) if existing is not None else pd.DataFrame()
    new_data = _normalize_date_column(recalculated) if recalculated is not None else pd.DataFrame()

    if not old_data.empty and not {"Date", "Symbol"}.issubset(old_data.columns):
        raise ValueError(
            "FR_diario.csv existente no contiene Date y Symbol; "
            "se conserva sin modificar."
        )

    if not new_data.empty:
        if not {"Date", "Symbol"}.issubset(new_data.columns):
            raise ValueError("El cálculo Full Ratio no devolvió Date y Symbol.")
        new_data["Symbol"] = new_data["Symbol"].astype(str).str.strip().str.upper()
        new_data = new_data[new_data["Symbol"].isin(selected_set)].copy()

    recalculated_set = set(new_data["Symbol"].dropna()) if not new_data.empty else set()
    if not old_data.empty:
        old_data["Symbol"] = old_data["Symbol"].astype(str).str.strip().str.upper()
        old_data = old_data[~old_data["Symbol"].isin(recalculated_set)].copy()

    merged = pd.concat([old_data, new_data], ignore_index=True, sort=False)
    if merged.empty:
        return pd.DataFrame(
            columns=[
                "Date", "Symbol", "Open", "High", "Low", "Close", "Volume",
                "LTM EPS", "LTM EPS %", "PER", "PER M5Y", "% PER vs PER M5Y",
                "Margen de seguridad", "Full Ratio",
            ]
        )

    merged["Date"] = pd.to_datetime(merged["Date"], errors="coerce")
    valid_keys = merged["Symbol"].notna() & merged["Date"].notna()
    duplicate_indexes = merged.loc[valid_keys].index[
        merged.loc[valid_keys].duplicated(["Symbol", "Date"], keep="last")
    ]
    return (
        merged.drop(index=duplicate_indexes)
        .sort_values(["Symbol", "Date"], kind="stable")
        .reset_index(drop=True)
    )


def _write_atomic(path, data, *, replace):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        data.to_csv(temporary_path, sep=";", index=False, date_format="%Y-%m-%d")
        if replace:
            os.replace(temporary_path, path)
            return True
        try:
            os.link(temporary_path, path)
            return True
        except FileExistsError:
            return False
    finally:
        temporary_path.unlink(missing_ok=True)


def persist_valuation_rows(full_ratio_path, recalculated, selected_symbols):
    path = Path(full_ratio_path) / "FR_diario.csv"
    with _valuation_cache_lock(path):
        existing = read_valuation_rows(path) if path.is_file() else pd.DataFrame()
        merged = merge_valuation_rows(existing, recalculated, selected_symbols)
        _write_atomic(path, merged, replace=True)
    return merged


def migrate_legacy_valuation_cache(global_full_ratio_path, run_results_path):
    global_path = Path(global_full_ratio_path) / "FR_diario.csv"
    if global_path.exists():
        return False

    with _valuation_cache_lock(global_path):
        if global_path.exists():
            return False
        return _migrate_legacy_valuation_cache_locked(global_path, run_results_path)


def _migrate_legacy_valuation_cache_locked(global_path, run_results_path):

    run_results_path = Path(run_results_path)
    legacy_paths = sorted(
        run_results_path.glob("*/FullRatio/FR_diario.csv"),
        key=lambda path: path.as_posix().casefold(),
    )
    legacy_frames = []
    for legacy_path in legacy_paths:
        try:
            legacy_rows = read_valuation_rows(legacy_path)
        except (OSError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError):
            logger.warning("Se omite FR legacy inválido durante migración: %s", legacy_path)
            continue
        legacy_frames.append(legacy_rows)

    if not legacy_frames:
        return False
    legacy_rows = pd.concat(legacy_frames, ignore_index=True, sort=False)
    migrated = merge_valuation_rows(
        pd.DataFrame(),
        legacy_rows,
        legacy_rows["Symbol"].dropna().astype(str).tolist(),
    )
    return _write_atomic(global_path, migrated, replace=False)