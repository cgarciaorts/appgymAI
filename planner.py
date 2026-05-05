# planner.py (v4.1) – robusto: _filter/_fallback sin KeyError + fix 'orden' superseries
from __future__ import annotations
import pandas as pd
from typing import Dict, Any, List

# --- scoring orientado a objetivo ---
def _norm_txt(s):
    from unicodedata import normalize
    if s is None: return ""
    t = str(s).lower().strip()
    t = normalize('NFD', t).encode('ascii', 'ignore').decode('ascii')
    return t

def _score_row_obj(row, keywords: List[str]) -> int:
    """Da puntos por presencia de keywords del objetivo."""
    txt = " ".join([
        _norm_txt(row.get('categoria')),
        _norm_txt(row.get('subcategoria')),
        _norm_txt(row.get('ejercicio'))
    ])
    score = 0
    for kw in keywords or []:
        if _norm_txt(kw) in txt:
            score += 10
    # bonus por compuestos si hay columna tipo_ejercicio
    te = _norm_txt(row.get('tipo_ejercicio'))
    if "compuesto" in te: score += 2
    return score


# ---------------- Utilidades internas ----------------

def _norm(s):
    if pd.isna(s):
        return ""
    return str(s).strip().lower()

def _match_patrones(row, patrones: List[str]) -> bool:
    if not patrones:
        return True
    texto = " ".join([_norm(row.get('categoria')), _norm(row.get('subcategoria')), _norm(row.get('ejercicio'))])
    pats = [p.lower() for p in patrones]
    return any(p in texto for p in pats)

def _match_tags(row, tags: List[str]) -> bool:
    if not tags:
        return True
    texto = " ".join([_norm(row.get('categoria')), _norm(row.get('subcategoria')), _norm(row.get('ejercicio'))])
    tgs = [t.lower() for t in tags]
    return all(t in texto for t in tgs)

def _match_tipo(row, tipo: str|None) -> bool:
    if not tipo:
        return True
    return _norm(row.get('tipo_ejercicio')) == _norm(tipo)

# ---------------- Filtro robusto ----------------
def _filter(df: pd.DataFrame, regla: Dict[str, Any]) -> pd.DataFrame:
    """Filtra candidatos de forma segura (sin crashear si faltan columnas o quedan 0 columnas)."""
    if df is None or df.empty:
        return df

    cand = df.copy()

    # --- Normaliza nombres esperados (por si vienen en mayúsculas/acentos) ---
    rename_map = {}
    for c in list(cand.columns):
        cl = str(c).strip().lower()
        if cl in ("ejercicio",):
            rename_map[c] = "ejercicio"
        elif cl in ("tipo_ejercicio", "tipo ejercicio"):
            rename_map[c] = "tipo_ejercicio"
        elif cl in ("categoria", "categoría"):
            rename_map[c] = "categoria"
        elif cl in ("subcategoria", "sub-categoria", "subcategoría"):
            rename_map[c] = "subcategoria"
        elif cl in ("prioridad",):
            rename_map[c] = "prioridad"
    if rename_map:
        cand = cand.rename(columns=rename_map)

    # Normaliza 'prioridad' si existe
    if "prioridad" in cand.columns:
        cand["prioridad"] = pd.to_numeric(cand["prioridad"], errors="coerce")

    # Filtros (solo si las columnas existen)
    if "tipo_ejercicio" in regla and regla["tipo_ejercicio"] and "tipo_ejercicio" in cand.columns:
        cand = cand[cand.apply(lambda r: _match_tipo(r, regla["tipo_ejercicio"]), axis=1)]

    if "patrones" in regla and regla["patrones"]:
        cand = cand[cand.apply(lambda r: _match_patrones(r, regla["patrones"]), axis=1)]

    if "tags_incluye" in regla and regla["tags_incluye"]:
        cand = cand[cand.apply(lambda r: _match_tags(r, regla["tags_incluye"]), axis=1)]

    if "prioridad" in regla and regla["prioridad"] is not None and "prioridad" in cand.columns:
        try:
            prio_val = int(regla["prioridad"])
            cand = cand[cand["prioridad"] == prio_val]
        except Exception:
            pass  # si no convierte, ignoramos filtro de prioridad

    # --- Si tras filtrar no quedan columnas, devolver DF vacío y salir limpio ---
    if cand.shape[1] == 0:
        return pd.DataFrame()

    # Drop dup sin asumir que exista 'ejercicio'
    if "ejercicio" in cand.columns:
        cand = cand.drop_duplicates(subset=["ejercicio"])
    else:
        # si no hay 'ejercicio' pero sí alguna columna, usamos la primera
        first_col = cand.columns[0] if len(cand.columns) else None
        if first_col is not None:
            cand = cand.drop_duplicates(subset=[first_col])

    return cand


def _fallback(df: pd.DataFrame, regla: Dict[str, Any]) -> pd.DataFrame:
    """Relaja filtros progresivamente para evitar bloques vacíos."""
    if df is None or df.empty:
        return df

    r2 = dict(regla)

    # 1) quitar prioridad
    r2.pop("prioridad", None)
    cand = _filter(df, r2)
    if not cand.empty:
        return cand

    # 2) quitar tipo
    r2.pop("tipo_ejercicio", None)
    cand = _filter(df, r2)
    if not cand.empty:
        return cand

    # 3) quitar patrones
    r2.pop("patrones", None)
    cand = _filter(df, r2)
    if not cand.empty:
        return cand

    # 4) último recurso: devolver algo con lo que haya
    if df.shape[1] == 0:
        return pd.DataFrame()
    if "ejercicio" in df.columns:
        return df.drop_duplicates(subset=["ejercicio"]).head(5)
    return df.drop_duplicates().head(5)


# ---------------- Parámetros / selección ----------------

def _set_params(df: pd.DataFrame, regla: Dict[str, Any], semana: int, bloque_tipo: str = "", objetivo_profile: Dict = None) -> pd.DataFrame:
    df = df.copy()
    # valores base de la regla
    series_rng = regla.get("series", (2,3))
    reps = regla.get("reps", "8-12")
    rpe_rng = regla.get("RPE", (7,8))

    # overrides por objetivo según tipo de bloque (p.ej. CircuitoPar)
    if objetivo_profile and objetivo_profile.get("rep_rpe_overrides"):
        over = objetivo_profile["rep_rpe_overrides"].get(bloque_tipo, {})
        reps = over.get("reps", reps)
        rpe_rng = over.get("RPE", rpe_rng)

    # progresión simple
    if semana == 2:
        series = max(series_rng)
        rpe = min(9, rpe_rng[-1])
    elif semana == 3:
        series = max(series_rng) + 1
        rpe = min(9, rpe_rng[-1])
    elif semana == 4:
        series = max(1, max(series_rng) - 1)
        rpe = rpe_rng[0]
    else:
        series = max(series_rng)
        rpe = rpe_rng[-1]

    if len(df) > 0:
        df['series'] = series
        df['repeticiones'] = reps
        df['RPE'] = rpe
        if 'descanso' not in df.columns: df['descanso'] = 60
        if 'tempo' not in df.columns: df['tempo'] = ""
    return df


def _elegir(df: pd.DataFrame, regla: Dict[str, Any], n: int, semana: int,
            objetivo_profile: Dict = None, used_ids: set | None = None,
            bloque_tipo: str = "") -> pd.DataFrame:
    cand = _filter(df, regla)
    if len(cand) == 0:
        cand = _fallback(df, regla)
    if len(cand) == 0:
        return cand

    # puntuación por objetivo
    keywords = (objetivo_profile or {}).get("keywords", [])
    cand = cand.copy()
    cand["__score"] = cand.apply(lambda r: _score_row_obj(r, keywords), axis=1)

    # penaliza repetición semanal
    if used_ids:
        def _pen(r):
            try:
                rid = int(r.get("id"))
                return -50 if rid in used_ids else 0
            except Exception:
                return 0
        cand["__score"] = cand["__score"] + cand.apply(_pen, axis=1)

    # criterio estable: score desc, prioridad desc (si existe), id asc
    sort_cols = ["__score"]
    ascending = [False]
    if "prioridad" in cand.columns:
        sort_cols.append("prioridad"); ascending.append(False)
    if "id" in cand.columns:
        sort_cols.append("id"); ascending.append(True)

    cand = cand.sort_values(sort_cols, ascending=ascending)

    sel = cand.head(n)
    # aplica reps/series/RPE con overrides del objetivo si tocan
    sel = _set_params(sel, regla, semana, bloque_tipo=bloque_tipo, objetivo_profile=objetivo_profile)

    # marca usados
    if used_ids is not None and "id" in sel.columns:
        for rid in sel["id"].dropna().tolist():
            try: used_ids.add(int(rid))
            except Exception: pass

    return sel


# ---------------- Constructores de bloques ----------------

from datetime import datetime, timedelta

WEEKDAY_ES = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
WEEKDAY_SHORT = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]

def _weekday_name_es(fecha: datetime) -> str:
    return WEEKDAY_ES[fecha.weekday()]

def plan_fecha(df: pd.DataFrame, patterns: Dict[str, Any], fecha: datetime, semana_mesociclo: int = 1) -> Dict[str, Any]:
    """Plan de un día por fecha real, incluyendo meta.titulo (tipo de sesión)."""
    dia_nombre = _weekday_name_es(fecha)
    ses = plan_dia(df, patterns, dia_nombre, semana_mesociclo=semana_mesociclo)  # usa tu lógica actual
    ses["fecha_iso"] = fecha.date().isoformat()
    ses["dia_semana"] = WEEKDAY_SHORT[fecha.weekday()]
    # seguridad por si no hay meta
    ses["meta"] = ses.get("meta", {}) or {}
    ses["meta"]["titulo"] = ses["meta"].get("titulo", dia_nombre)
    return ses

def sesion_a_dataframe(sesion: Dict[str, Any]) -> pd.DataFrame:
    """Convierte la salida de plan_fecha/plan_dia a una tabla plana."""
    rows = []
    fecha_iso = sesion.get("fecha_iso", "")
    dia_short = sesion.get("dia_semana", "")
    tipo_sesion = (sesion.get("meta") or {}).get("titulo", "")

    for bloque in sesion.get("bloques", []):
        bloque_nombre = bloque.get("tipo", "")
        # 1) Bloques con items (DataFrame de ejercicios)
        if isinstance(bloque.get("items"), pd.DataFrame) and not bloque["items"].empty:
            df_items = bloque["items"].copy()
            # columnas amables
            base_cols = [c for c in ["id","ejercicio","categoria","series","repeticiones","RPE","descanso","tempo","superserie","orden"] if c in df_items.columns]
            for _, r in df_items[base_cols].iterrows():
                rows.append({
                    "fecha": fecha_iso,
                    "dia": dia_short,
                    "tipo_sesion": tipo_sesion,
                    "bloque": bloque_nombre,
                    **{k: r.get(k) for k in base_cols}
                })
        # 2) Bloques con plan (p.ej. Caminar/Carrera)
        elif isinstance(bloque.get("plan"), dict):
            p = bloque["plan"]
            rows.append({
                "fecha": fecha_iso,
                "dia": dia_short,
                "tipo_sesion": tipo_sesion,
                "bloque": bloque_nombre,
                "detalle": "; ".join([f"{k}: {v}" for k,v in p.items()])
            })
        # 3) Bloques vacíos: nada
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=["fecha","dia","tipo_sesion","bloque","id","ejercicio","categoria","series","repeticiones","RPE","descanso","tempo","superserie","orden","detalle"])

def plan_rango_a_dataframe(df: pd.DataFrame, patterns: Dict[str, Any], start: datetime, days: int = 7, semana_mesociclo: int = 1) -> pd.DataFrame:
    """Construye varias fechas seguidas y las aplana en una sola tabla."""
    partes = []
    for i in range(days):
        ses = plan_fecha(df, patterns, start + timedelta(days=i), semana_mesociclo=semana_mesociclo)
        partes.append(sesion_a_dataframe(ses))
    if partes:
        out = pd.concat(partes, ignore_index=True)
        # orden bonito
        orden_cols = ["fecha","dia","tipo_sesion","bloque","superserie","orden","id","ejercicio","categoria","series","repeticiones","RPE","descanso","tempo","detalle"]
        orden_cols = [c for c in orden_cols if c in out.columns]
        return out[orden_cols]
    return pd.DataFrame()

def _construir_circuito_par(df: pd.DataFrame, regla: Dict[str, Any], semana: int,
                            objetivo_profile: Dict = None, used_ids: set | None = None) -> pd.DataFrame:
    parejas = regla.get("parejas", [])
    series_circuito = int(regla.get("series_circuito", 3))
    reps = regla.get("reps", "10-12")
    rpe_rng = regla.get("RPE", (7,8))
    descanso_entre_ej = int(regla.get("descanso_entre_ej", 0))
    descanso_entre_series = int(regla.get("descanso_entre_series", 60))

    filas = []
    nombre_super = ['A','B','C','D','E','F']
    idx_super = 0

    for par in parejas:
        if len(par) != 2:
            continue
        regla_a, regla_b = par
        a = _elegir(df, regla_a, 1, semana, objetivo_profile, used_ids, bloque_tipo="CircuitoPar")
        b = _elegir(df, regla_b, 1, semana, objetivo_profile, used_ids, bloque_tipo="CircuitoPar")
        if a.empty or b.empty:
            continue
        a = a.copy(); b = b.copy()
        sup_id = f"SS{nombre_super[idx_super % len(nombre_super)]}"
        idx_super += 1
        for parte, lado in [(a, '1'), (b, '2')]:
            # si el objetivo ha ajustado reps/RPE en _set_params, respetamos; si no, forzamos reps del circuito
            parte['repeticiones'] = reps
            parte['series'] = series_circuito
            parte['RPE'] = min(9, rpe_rng[-1] if semana in (2,3) else rpe_rng[0])
            parte['superserie'] = sup_id
            parte['descanso'] = descanso_entre_ej if lado == '1' else descanso_entre_series
            filas.append(parte)

    if not filas:
        return pd.DataFrame()

    out = pd.concat(filas, ignore_index=True)
    nums = pd.to_numeric(out['superserie'].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
    out['orden'] = nums.astype('Int64')
    out = out.sort_values(['superserie']).reset_index(drop=True)
    return out

def _bloque_pliometria(df: pd.DataFrame, regla: Dict[str, Any], semana: int,
                       objetivo_profile: Dict = None, used_ids: set | None = None) -> pd.DataFrame:
    n = int(regla.get('n', 1))
    return _elegir(df, {"tipo_ejercicio":"Pliometrico"}, n, semana, objetivo_profile, used_ids, bloque_tipo="Pliometria")

def _bloque_calentamiento(df: pd.DataFrame, regla: Dict[str, Any], semana: int,
                          objetivo_profile: Dict = None, used_ids: set | None = None) -> pd.DataFrame:
    base = {
        "tipo_ejercicio": regla.get("tipo_ejercicio","Movilidad"),
        "patrones": regla.get("patrones", []),
        "tags_incluye": regla.get("tags_incluye", ["movilidad"]),
        "prioridad": regla.get("prioridad", None)
    }
    n = int(regla.get("n", 1))
    sel = _elegir(df, base, n, semana, objetivo_profile, used_ids, bloque_tipo="Calentamiento")
    if 'descanso' in sel.columns:
        sel['descanso'] = 0
    return sel

def construir_bloque(df: pd.DataFrame, nombre: str, regla: Dict[str, Any], semana: int,
                     objetivo_profile: Dict = None, used_ids: set | None = None):
    tipo = regla.get("tipo", "")
    nom_low = nombre.lower()
    if tipo.lower() == "circuitopar":
        return {"tipo": nombre, "items": _construir_circuito_par(df, regla, semana, objetivo_profile, used_ids)}
    if tipo.lower() == "caminar":
        return {"tipo": nombre, "plan": _bloque_caminar(regla, semana)}
    if tipo.lower() == "carrera":
        plan = {"tipo": "Intervalos", "sesion": regla.get("sesion","6x400m Z4 rec 2'"), "indicaciones": "Calienta 10' + Enfría 10'"}
        return {"tipo": nombre, "plan": plan}
    if tipo.lower() == "pliometrico":
        return {"tipo": nombre, "items": _bloque_pliometria(df, regla, semana, objetivo_profile, used_ids)}
    if nom_low.startswith("calentamiento"):
        return {"tipo": nombre, "items": _bloque_calentamiento(df, regla, semana, objetivo_profile, used_ids)}
    items = _elegir(df, regla, int(regla.get('n',1)), semana, objetivo_profile, used_ids, bloque_tipo="Generico")
    return {"tipo": nombre, "items": items}

def construir_sesion(df: pd.DataFrame, plantilla: Dict[str, Any], semana: int,
                     objetivo_profile: Dict = None, used_ids: set | None = None):
    bloques = []
    reglas = plantilla.get("reglas", {})
    for bloque in plantilla.get("orden", []):
        r = reglas.get(bloque, {})
        bloques.append(construir_bloque(df, bloque, r, semana, objetivo_profile, used_ids))
    return bloques

def plan_dia(df: pd.DataFrame, patterns: Dict[str, Any], dia: str, semana_mesociclo: int = 1,
             objetivo_profile: Dict = None, used_ids: set | None = None) -> Dict[str, Any]:
    p = patterns.get(dia, {})
    if not p:
        return {"dia": dia, "bloques": []}
    return {"dia": dia, "meta": p.get("meta", {}), "bloques": construir_sesion(df, p, semana_mesociclo, objetivo_profile, used_ids)}

def plan_semana(df: pd.DataFrame, patterns: Dict[str, Any], semana_mesociclo: int = 1,
                objetivo_profile: Dict = None) -> Dict[str, Any]:
    dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    used_week = set() if (objetivo_profile or {}).get("weekly_repeat_penalty", False) else None
    return {
        d: plan_dia(df, patterns, d, semana_mesociclo, objetivo_profile, used_week)
        for d in dias
    }
