import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import date, timedelta
from patterns_bau import PATTERNS
from planner import plan_semana
from storage import save_week, load_week, list_weeks, label_from_date, ensure_autogen_today, week_monday

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

#  ---------- CARGA ----------
df = cargar_datos()
if df.empty:
    st.stop()

# ---------- CONTROLES ----------
colA, colB, colC, colD = st.columns([1,1,1,2])
with colA:
    semana = st.selectbox("Semana", [1,2,3,4], index=0)
with colB:
    objetivo_semana = st.selectbox("Plan a generar/guardar", ["Semana actual (desde lunes)","Próxima semana (desde próximo lunes)"], index=0)
with colC:
    base_date = week_monday(date.today()) + timedelta(days=7 if objetivo_semana.startswith("Próxima") else 0)
    label = label_from_date(base_date)
    st.text_input("Etiqueta (YYYY-MM-DD)", value=label, disabled=True)
with colD:
    created, autolabel = ensure_autogen_today(lambda: plan_semana(df, PATTERNS, semana_mesociclo=1))
    if created:
        st.success(f"Generado y guardado automáticamente el plan de la semana {autolabel}.")

# ---------- GENERAR / GUARDAR ----------
if st.button("Generar plan y guardar"):
    plan = plan_semana(df, PATTERNS, semana_mesociclo=semana)
    path = save_week(plan, label)
    st.success(f"Plan guardado: {path}")

# ---------- VISTA: semana actual (con fecha por día y expanders cerrados) ----------
st.markdown("---")
st.markdown("Semana actual")

plan_preview = plan_semana(df, PATTERNS, semana_mesociclo=semana)
dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

for i, d in enumerate(dias):
    fecha = (base_date + timedelta(days=i)).strftime("%d-%m-%Y")
    data = plan_preview[d]

    # Expander de DÍA (cerrado por defecto)
    tipo = (data.get("meta") or {}).get("titulo", "")
    titulo_tipo = f" · {tipo}" if tipo else ""
    with st.expander(f"📅 {d} · {fecha}{titulo_tipo}", expanded=False):
    # with st.expander(f"📅 {d} · {fecha}", expanded=False):
        bloques = data.get("bloques", [])
        if not bloques:
            st.info("Sin bloques para este día.")
            continue

        # Pestañas por bloque (sustituyen al expander anidado)
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

    # 'sel' es el lunes de esa semana (YYYY-MM-DD)
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
            # with st.expander(f"📅 {d} · {fecha}", expanded=False):
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