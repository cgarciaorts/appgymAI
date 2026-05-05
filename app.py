# Falta que guarde no solo por fecha sino tambien por objetivo
#que cambie las sesiones de una semana a otra por objetivo también

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from patterns_bau import PATTERNS
from planner import plan_semana
from storage import save_week, load_week, list_weeks, label_from_date, ensure_autogen_today, week_monday
from objectives import OBJ_PROFILES
import time

# --- Config ---
st.set_page_config(layout="wide", page_title="Planificador Sesiones")

# ---- CSS global (cards) ----
st.markdown("""
<style>
/* ---- Cards móviles ---- */
.card {
  width: 100%;
  background: #0c1119;
  border: 1px solid #1f2633;
  border-radius: 14px;
  padding: 14px 14px 12px;
  margin: 10px 0 14px;
  color: #fff;
  box-shadow: 0 2px 10px rgba(0,0,0,.18);
}
.card-header {
  display:flex; align-items:center; justify-content:space-between;
  gap:8px; margin-bottom:6px;
}
.card-title { font-size: 18px; font-weight: 700; line-height:1.2; }
.badge { font-size: 12px; padding: 3px 8px; border-radius: 999px; border:1px solid #2a3240; color:#c8d1e8; }
.badge.primary { background:#10203a; border-color:#2c4f80; color:#bcd3ff; }
.badge.gray { background:#10151f; color:#c8d1e8; }
.meta {
  display:flex; gap:10px; flex-wrap:wrap; margin: 6px 0 8px;
}
.meta .chip{
  background:#10151f; border:1px solid #2a3240; color:#c8d1e8;
  padding:4px 8px; border-radius:8px; font-size:12px;
}
.card p { margin: 4px 0; font-size: 14px; line-height: 1.45; color:#e6ecff; }
.label { font-size:12px; color:#9fb0cc; text-transform:uppercase; letter-spacing:.04em; }
.actions { display:flex; gap:10px; margin-top:10px; flex-wrap:wrap; }
.btn {
  display:inline-flex; align-items:center; justify-content:center;
  gap:8px; padding:10px 14px; border-radius:10px; border:1px solid #2c4f80;
  background:#0f4db8; color:#fff; font-weight:700; text-decoration:none;
}
.btn.secondary { background:#0e1a2e; border-color:#2a3240; color:#cfe0ff; }
.btn:active { transform: translateY(1px); }
.small-note{ font-size:12px; color:#a9b8d0; margin-top:8px;}
hr.sep { border:0; border-top:1px dashed #273147; margin:10px 0; }
@media (min-width: 760px){
  .card-title{ font-size:20px; }
}
</style>
""", unsafe_allow_html=True)

st.title("Planificador sesiones")
if "regen" not in st.session_state:
    st.session_state["regen"] = 0

# ---------- CARGA DE DATOS ----------
def cargar_datos():
    posibles = ["datos_clasificado.xlsx"]
    df = pd.DataFrame()
    for nombre in posibles:
        try:
            df = pd.read_excel(nombre)
            print(f"Datos cargados desde **{nombre}**")
            break
        except FileNotFoundError:
            continue

    if df.empty:
        st.error("No encuentro ninguno de estos ficheros: datos_clasificado.xlsx")
        return df

    # Encabezados a minúscula simple
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Renombres mínimos seguros
    ren = {}
    if "tipo ejercicio" in df.columns: ren["tipo ejercicio"] = "tipo_ejercicio"
    if "categoría" in df.columns: ren["categoría"] = "categoria"
    if "subcategoría" in df.columns: ren["subcategoría"] = "subcategoria"
    if "sub-categoria" in df.columns: ren["sub-categoria"] = "subcategoria"
    if ren:
        df = df.rename(columns=ren)

    # Tipos suaves
    if 'prioridad' in df.columns:
        df['prioridad'] = pd.to_numeric(df['prioridad'], errors='coerce')
    for c in ['categoria','subcategoria','ejercicio','tipo_ejercicio','explicacion']:
        if c in df.columns:
            df[c] = df[c].astype(str)

    return df

# ---------- Cards (móvil) ----------
def _val(v, default=""):
    try:
        if pd.isna(v): return default
    except Exception:
        pass
    s = str(v).strip()
    return default if s.lower() in ("nan", "none") else s

def _norm_url(url: str) -> str:
    if not url: return ""
    s = str(url).strip()
    if s.lower().startswith(("http://","https://")): return s
    if any(dom in s.lower() for dom in ["youtube.com","youtu.be","vimeo.com","instagram.com","x.com","twitter.com","drive.google.com"]):
        return "https://" + s
    return ""

def render_items_cards(items):
    df_items = items if isinstance(items, pd.DataFrame) else pd.DataFrame(items)
    if df_items is None or df_items.empty:
        st.info("Bloque vacío."); return

    if 'orden' in df_items.columns:
        df_items = df_items.sort_values(['superserie','orden'], ignore_index=True)
    if 'RPE' in df_items.columns and 'rpe' not in df_items.columns:
        df_items = df_items.rename(columns={'RPE':'rpe'})

    for _, row in df_items.fillna("").iterrows():
        titulo = _val(row.get("ejercicio",""))
        series = _val(row.get("series",""))
        reps   = _val(row.get("repeticiones",""))
        rpe    = _val(row.get("rpe", row.get("RPE","")))
        tipo   = _val(row.get("tipo_ejercicio",""))
        sup    = _val(row.get("superserie",""))
        expl   = _val(row.get("explicacion",""))
        video  = _norm_url(row.get("video",""))

        dosis = f"{series} × {reps}" if series or reps else ""

        header = f"""
        <div class="card-header">
          <div class="badge gray">{'SUPERSET ' + sup if sup else 'EJERCICIO'}</div>
          <div class="badge primary">{tipo or 'Accesorio'}</div>
        </div>"""

        chips = []
        if dosis: chips.append(f"<span class=\"chip\">{dosis}</span>")
        if tipo:   chips.append(f"<span class=\"chip\">{tipo}</span>")
        meta = f"<div class=\"meta\">{''.join(chips)}</div>" if chips else ""

        body = f"<div class=\"label\">Explicación</div><p>{expl}</p>" if expl else ""

        btns = []
        # print(video)
        if video:
            btns.append(f"<a class=\"btn\" href=\"{video}\" target=\"_blank\" rel=\"noopener\">▶ Ver vídeo</a>")
        actions = f"<div class=\"actions\">{''.join(btns)}</div>" if btns else ""

        card_html = f"""
        <div class="card">
          {header}
          <div class="card-title">{titulo}</div>
          {meta}
          {body}
          {actions}
        </div>"""
        st.markdown(card_html, unsafe_allow_html=True)

def render_plan(plan: dict):
    if 'duracion_min' in plan:
        st.info(f"Caminar {plan['duracion_min']}′ · Inclinación {plan.get('inclinacion','')} · Ritmo {plan.get('ritmo_kmh','')}")
    elif 'sesion' in plan:
        st.info(f"{plan.get('tipo','Intervalos')}: {plan['sesion']}")
    else:
        st.info(str(plan))

def _render_ejercicio_card(row):
    titulo = _val(row.get("ejercicio",""))
    categoria = _val(row.get("categoria",""))
    subcategoria = _val(row.get("subcategoria",""))
    tipo = _val(row.get("tipo_ejercicio",""))
    expl = _val(row.get("explicacion",""))
    video = _norm_url(row.get("video",""))

    chips = []
    if categoria: chips.append(f"<span class=\"chip\">{categoria}</span>")
    if subcategoria: chips.append(f"<span class=\"chip\">{subcategoria}</span>")
    if tipo: chips.append(f"<span class=\"chip\">{tipo}</span>")
    meta = f"<div class=\"meta\">{''.join(chips)}</div>" if chips else ""
    body = f"<div class=\"label\">Explicación</div><p>{expl}</p>" if expl else ""
    btns = []
    if video:
        btns.append(f"<a class=\"btn\" href=\"{video}\" target=\"_blank\" rel=\"noopener\">▶ Ver vídeo</a>")
    actions = f"<div class=\"actions\">{''.join(btns)}</div>" if btns else ""

    card_html = f"""
    <div class="card">
      <div class="card-header">
        <div class="badge gray">{tipo or 'Ejercicio'}</div>
      </div>
      <div class="card-title">{titulo}</div>
      {meta}
      {body}
      {actions}
    </div>"""
    st.markdown(card_html, unsafe_allow_html=True)

#  ---------- CARGA ----------
df = cargar_datos()
if df.empty:
    st.stop()

# ---------- TABS PRINCIPALES ----------
tab_plan, tab_ejercicios = st.tabs(["📅 Planificador", "🔍 Ejercicios"])

# =========================================================
# TAB 1: PLANIFICADOR
# =========================================================
with tab_plan:

    # ---------- CONTROLES ----------
    from objectives import OBJ_PROFILES

    colA, colB, colC, colD = st.columns([1,1,1,2])

    with colA:
        semana = st.selectbox("Semana", [1,2,3,4], index=0)

    with colB:
        objetivo_nombre = st.selectbox("Objetivo", list(OBJ_PROFILES.keys()), index=0)
        objetivo_profile = OBJ_PROFILES[objetivo_nombre]

    with colC:
        base_date = week_monday(date.today()) + timedelta(
            days=7 if st.selectbox(
                "Plan a generar/guardar",
                ["Semana actual (desde lunes)", "Próxima semana (desde próximo lunes)"],
                index=0
            ).startswith("Próxima") else 0
        )
        label = label_from_date(base_date)
        st.text_input("Etiqueta (YYYY-MM-DD)", value=label, disabled=True)

    with colD:
        daily_seed = int(time.strftime("%Y%m%d"))  # misma semilla por día
        created, autolabel = ensure_autogen_today(
            lambda: plan_semana(
                df.sample(frac=1, random_state=daily_seed).reset_index(drop=True),
                PATTERNS, semana_mesociclo=1, objetivo_profile=OBJ_PROFILES["General (BAU)"]
            )
        )
        if created:
            st.success(f"Generado y guardado automáticamente el plan de la semana {autolabel}.")

    # ---------- GENERAR / GUARDAR ----------
    if st.button("Generar plan y guardar"):
        st.session_state["regen"] += 1
        MAX32 = (2**32) - 1

        # Semilla siempre dentro de rango
        seed = int(time.time_ns() + st.session_state["regen"]) % MAX32

        df_shuffled = df.sample(frac=1, random_state=seed).reset_index(drop=True)
        plan = plan_semana(
            df_shuffled,
            PATTERNS,
            semana_mesociclo=semana,
            objetivo_profile=objetivo_profile
        )

        path = save_week(plan, label)
        st.success(f"Plan guardado: {path} · Objetivo: {objetivo_nombre} · seed={seed}")

    # ---------- VISTA: semana actual ----------
    st.markdown("---")
    st.markdown("Semana actual")

    MAX32 = (2**32) - 1
    preview_seed = abs(hash((objetivo_nombre, semana, label, "preview"))) % MAX32
    df_preview = df.sample(frac=1, random_state=preview_seed).reset_index(drop=True)
    try:
        plan_preview = plan_semana(df_preview, PATTERNS, semana_mesociclo=semana, objetivo_profile=objetivo_profile)
    except Exception as _e:
        import traceback
        st.error(f"Error generando el plan: {type(_e).__name__}: {_e}")
        st.code(traceback.format_exc())
        plan_preview = {d: {"bloques": []} for d in ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]}

    dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

    for i, d in enumerate(dias):
        fecha = (base_date + timedelta(days=i)).strftime("%d-%m-%Y")
        data = plan_preview[d]

        tipo = (data.get("meta") or {}).get("titulo", "")
        titulo_tipo = f" · {tipo}" if tipo else ""
        with st.expander(f"📅 {d} · {fecha}{titulo_tipo}", expanded=False):
            bloques = data.get("bloques", [])
            if not bloques:
                st.info("Sin bloques para este día.")
                continue

            tabs = st.tabs([f"🔹 {b['tipo']}" for b in bloques])
            for tab, bloque in zip(tabs, bloques):
                with tab:
                    if "items" in bloque:
                        render_items_cards(bloque["items"])
                    elif "plan" in bloque:
                        render_plan(bloque["plan"])

    # ---------- HISTORIAL ----------
    st.markdown("### Historial de semanas")
    labels = list_weeks()
    if labels:
        sel = st.selectbox("Ver semana guardada", labels, index=0)
        stored = load_week(sel)

        try:
            from datetime import datetime as _dt
            base_hist = _dt.strptime(sel, "%Y-%m-%d").date()
        except Exception:
            base_hist = week_monday(date.today())

        if stored:
            dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
            for i, d in enumerate(dias):
                fecha = (base_hist + timedelta(days=i)).strftime("%d-%m-%Y")

                data = stored.get(d, {})
                tipo = (data.get("meta") or {}).get("titulo", "")
                titulo_tipo = f" · {tipo}" if tipo else ""
                with st.expander(f"📅 {d} · {fecha}{titulo_tipo}", expanded=False):
                    bloques = data.get("bloques", [])
                    if not bloques:
                        st.info("Sin bloques para este día.")
                        continue

                    tabs = st.tabs([f"🔹 {b['tipo']}" for b in bloques])
                    for tab, bloque in zip(tabs, bloques):
                        with tab:
                            if "items" in bloque and isinstance(bloque["items"], list) and bloque["items"]:
                                df_items = pd.DataFrame(bloque["items"])
                                render_items_cards(df_items)
                            elif "plan" in bloque:
                                render_plan(bloque["plan"])
    else:
        st.info("Aún no hay semanas guardadas.")

# =========================================================
# TAB 2: EJERCICIOS
# =========================================================
with tab_ejercicios:
    st.markdown("### Biblioteca de ejercicios")

    # --- Filtros ---
    col_search, col_cat, col_tipo = st.columns([3, 2, 2])

    with col_search:
        buscar = st.text_input("Buscar ejercicio...", placeholder="ej: sentadilla, press banca, remo...")

    with col_cat:
        cats = sorted([c for c in df["categoria"].dropna().unique()
                       if str(c).lower() not in ("nan","none","")]) if "categoria" in df.columns else []
        cat_sel = st.selectbox("Categoría", ["Todas"] + cats)

    with col_tipo:
        tipos = sorted([t for t in df["tipo_ejercicio"].dropna().unique()
                        if str(t).lower() not in ("nan","none","")]) if "tipo_ejercicio" in df.columns else []
        tipo_sel = st.selectbox("Tipo", ["Todos"] + tipos)

    # --- Aplicar filtros ---
    df_filtrado = df.copy()

    if buscar.strip():
        mask = df_filtrado["ejercicio"].str.contains(buscar.strip(), case=False, na=False)
        if "explicacion" in df_filtrado.columns:
            mask |= df_filtrado["explicacion"].str.contains(buscar.strip(), case=False, na=False)
        df_filtrado = df_filtrado[mask]

    if cat_sel != "Todas" and "categoria" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["categoria"] == cat_sel]

    if tipo_sel != "Todos" and "tipo_ejercicio" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["tipo_ejercicio"] == tipo_sel]

    st.caption(f"{len(df_filtrado)} ejercicio(s) encontrado(s)")

    if df_filtrado.empty:
        st.info("No hay ejercicios con esos filtros.")
    elif "categoria" in df_filtrado.columns and cat_sel == "Todas" and not buscar.strip():
        # Agrupados por categoría cuando no hay búsqueda activa
        for cat_name, grupo in df_filtrado.groupby("categoria", sort=True):
            if str(cat_name).lower() in ("nan","none",""): continue
            with st.expander(f"📂 {cat_name}  ({len(grupo)})", expanded=False):
                for _, row in grupo.fillna("").iterrows():
                    _render_ejercicio_card(row)
    else:
        for _, row in df_filtrado.fillna("").iterrows():
            _render_ejercicio_card(row)