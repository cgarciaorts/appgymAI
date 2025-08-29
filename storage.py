# storage.py (robusto)
import os, json, math
from datetime import date, timedelta
import pandas as pd
from typing import Any, Tuple, Optional

BASE_DIR = os.path.join(os.getcwd(), "planes")  # o fija a una ruta absoluta si prefieres
os.makedirs(BASE_DIR, exist_ok=True)

def week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())

def label_from_date(d: date) -> str:
    return week_monday(d).strftime("%Y-%m-%d")

def path_for_label(label: str) -> str:
    return os.path.join(BASE_DIR, f"plan_{label}.json")

# ---------- helpers json-safe ----------

def _to_json_safe(x: Any) -> Any:
    """Convierte recursivamente estructuras para que sean serializables en JSON."""
    # pandas DataFrame / Series
    if isinstance(x, pd.DataFrame):
        return x.to_dict(orient="records")
    if isinstance(x, pd.Series):
        return x.to_dict()

    # numpy / pandas scalars
    try:
        import numpy as np
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, (np.floating,)):
            # evitar NaN/Inf que arruinan el JSON legible
            if math.isnan(float(x)) or math.isinf(float(x)):
                return None
            return float(x)
        if isinstance(x, (np.bool_,)):
            return bool(x)
    except Exception:
        pass

    # tipos básicos
    if isinstance(x, (str, int, float, bool)) or x is None:
        # limpia NaN/Inf si llegaran como float
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return None
        return x

    # listas / tuplas / sets
    if isinstance(x, (list, tuple, set)):
        return [_to_json_safe(v) for v in x]

    # dict
    if isinstance(x, dict):
        return {str(k): _to_json_safe(v) for k, v in x.items()}

    # fallback: representarlo como string
    return str(x)

def _atomic_write_json(obj: Any, path: str) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

# ---------- API ----------

def save_week(plan: dict, label: Optional[str] = None) -> str:
    """Guarda el plan semanal convirtiendo a JSON-serializable y usando escritura atómica."""
    if label is None:
        label = label_from_date(date.today())
    path = path_for_label(label)
    safe = _to_json_safe(plan)
    _atomic_write_json(safe, path)
    return path

def load_week(label: str) -> dict:
    """Carga un plan. Lanza JSONDecodeError con detalle si el archivo está corrupto."""
    path = path_for_label(label)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def try_load_week(label: str) -> Tuple[Optional[dict], Optional[str]]:
    """Versión segura: no lanza; devuelve (plan, error_str)."""
    try:
        return load_week(label), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def list_weeks() -> list[str]:
    files = [f for f in os.listdir(BASE_DIR) if f.startswith("plan_") and f.endswith(".json")]
    labels = [f.replace("plan_", "").replace(".json", "") for f in files]
    labels.sort(reverse=True)
    return labels

def list_invalid_weeks() -> list[Tuple[str, str]]:
    """Devuelve [(label, error)] para los JSON que no se pueden leer."""
    bad = []
    for label in list_weeks():
        _, err = try_load_week(label)
        if err:
            bad.append((label, err))
    return bad

def ensure_autogen_today(plan_builder) -> tuple[bool, str | None]:
    """Si hoy es sábado, genera el plan del lunes próximo si no existe."""
    today = date.today()
    created = False
    label = None
    if today.weekday() == 5:  # sábado
        next_monday = week_monday(today + timedelta(days=2))
        label = label_from_date(next_monday)
        plan, err = try_load_week(label)
        if plan is None:  # no existe o corrupto
            safe_plan = plan_builder()
            save_week(safe_plan, label)
            created = True
    return created, label
