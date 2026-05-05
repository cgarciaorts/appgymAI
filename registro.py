# registro.py — guarda y carga logs de sesiones (peso, reps, RPE, tolerancia)
import os, json
from datetime import date
from typing import Optional

LOGS_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

def _log_path(fecha: str) -> str:
    return os.path.join(LOGS_DIR, f"log_{fecha}.json")

def save_session_log(fecha: str, log: dict) -> str:
    path = _log_path(fecha)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    return path

def load_session_log(fecha: str) -> Optional[dict]:
    path = _log_path(fecha)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def list_logs() -> list[str]:
    files = [f for f in os.listdir(LOGS_DIR) if f.startswith("log_") and f.endswith(".json")]
    labels = [f.replace("log_", "").replace(".json", "") for f in files]
    labels.sort(reverse=True)
    return labels

def get_exercise_history(exercise_id) -> list[dict]:
    """Devuelve el historial de cargas de un ejercicio concreto (todos los logs)."""
    history = []
    for label in list_logs():
        log = load_session_log(label)
        if not log:
            continue
        for entry in log.get("ejercicios", []):
            if str(entry.get("id", "")) == str(exercise_id):
                history.append({
                    "fecha": label,
                    "peso": entry.get("peso", ""),
                    "reps_hechas": entry.get("reps_hechas", ""),
                    "esfuerzo": entry.get("esfuerzo", ""),
                    "tolerancia": entry.get("tolerancia", ""),
                    "sustituido": entry.get("sustituido", False),
                })
    return sorted(history, key=lambda x: x["fecha"])

def get_last_log() -> Optional[dict]:
    labels = list_logs()
    if not labels:
        return None
    return load_session_log(labels[0])

def suggest_progression(exercise_id, sets: str, reps: str) -> str:
    """Sugiere progresión basada en histórico."""
    hist = get_exercise_history(exercise_id)
    if not hist:
        return ""
    last = hist[-1]
    try:
        last_peso = float(str(last.get("peso", 0)).replace(",", ".") or 0)
        last_esfuerzo = int(last.get("esfuerzo", 5) or 5)
        last_tol = last.get("tolerancia", "bien")
        if last_tol == "mal":
            return f"⚠️ Última vez mal tolerado — mantén o baja carga"
        if last_esfuerzo <= 6 and last_peso > 0:
            return f"✅ Sube 2-5 kg respecto a {last_peso} kg (última sesión RPE {last_esfuerzo})"
        if last_esfuerzo >= 9:
            return f"⚠️ Última vez muy duro (RPE {last_esfuerzo}) — mantén {last_peso} kg"
        if last_peso > 0:
            return f"📋 Última vez: {last_peso} kg · RPE {last_esfuerzo}"
    except Exception:
        pass
    return ""
