import streamlit as st
import pandas as pd
from PIL import Image
from datetime import date, timedelta
from patterns_bau import PATTERNS
from planner import plan_semana
from storage import save_week, load_week, list_weeks, label_from_date, ensure_autogen_today, week_monday, save_today_session, load_today_session
from objectives import OBJ_PROFILES
from registro import save_session_log, load_session_log, list_logs, get_exercise_history, suggest_progression
import os, time, traceback

# ===================== CONFIG =====================
_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
_page_icon = Image.open(_icon_path) if os.path.exists(_icon_path) else "💪"
st.set_page_config(layout="wide", page_title="APP GYM David", page_icon=_page_icon)

st.markdown("""<style>
.card{width:100%;background:#0c1119;border:1px solid #1f2633;border-radius:14px;padding:14px 14px 12px;margin:10px 0 14px;color:#fff;box-shadow:0 2px 10px rgba(0,0,0,.18);}
.card-header{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px;}
.card-title{font-size:18px;font-weight:700;line-height:1.2;}
.badge{font-size:12px;padding:3px 8px;border-radius:999px;border:1px solid #2a3240;color:#c8d1e8;}
.badge.primary{background:#10203a;border-color:#2c4f80;color:#bcd3ff;}
.badge.gray{background:#10151f;color:#c8d1e8;}
.meta{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 8px;}
.meta .chip{background:#10151f;border:1px solid #2a3240;color:#c8d1e8;padding:4px 8px;border-radius:8px;font-size:12px;}
.card p{margin:4px 0;font-size:14px;line-height:1.45;color:#e6ecff;}
.label{font-size:12px;color:#9fb0cc;text-transform:uppercase;letter-spacing:.04em;}
.actions{display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:10px 14px;border-radius:10px;border:1px solid #2c4f80;background:#0f4db8;color:#fff;font-weight:700;text-decoration:none;}
.btn:active{transform:translateY(1px);}
.prog-hint{font-size:12px;color:#7ec8a0;margin-top:4px;}
.warn-hint{font-size:12px;color:#ffb84d;margin-top:4px;}
hr.sep{border:0;border-top:1px dashed #273147;margin:10px 0;}
@media(min-width:760px){.card-title{font-size:20px;}}
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}
header{visibility:hidden;}
</style>""", unsafe_allow_html=True)

# ===================== CARGA =====================
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_excel("datos_clasificado.xlsx")
    except FileNotFoundError:
        return pd.DataFrame()
    df.columns = [str(c).strip().lower() for c in df.columns]
    ren = {}
    if "tipo ejercicio" in df.columns: ren["tipo ejercicio"] = "tipo_ejercicio"
    if "categoría" in df.columns: ren["categoría"] = "categoria"
    if "subcategoría" in df.columns: ren["subcategoría"] = "subcategoria"
    if "sub-categoria" in df.columns: ren["sub-categoria"] = "subcategoria"
    if ren: df = df.rename(columns=ren)
    if "prioridad" in df.columns:
        df["prioridad"] = pd.to_numeric(df["prioridad"], errors="coerce")
    for c in ["categoria", "subcategoria", "ejercicio", "tipo_ejercicio", "explicacion"]:
        if c in df.columns: df[c] = df[c].astype(str)
    return df

df = cargar_datos()
if df.empty:
    st.error("No encuentro datos_clasificado.xlsx")
    st.stop()

# ===================== HELPERS =====================
def _val(v, default=""):
    try:
        if pd.isna(v): return default
    except Exception:
        pass
    s = str(v).strip()
    return default if s.lower() in ("nan", "none") else s

def _norm_url(url):
    if not url: return ""
    s = str(url).strip()
    if not s or s.lower() in ("nan", "none", ""): return ""
    if s.lower().startswith(("http://", "https://")): return s
    if any(d in s.lower() for d in ["youtube.com", "youtu.be", "vimeo.com", "instagram.com", "drive.google.com"]):
        return "https://" + s
    return ""

def get_sustitutos(row, df_all, n=5):
    """Sustitutos por misma subcategoría (mismo patrón e intención — método David)."""
    subcat = _val(row.get("subcategoria", ""))
    cat    = _val(row.get("categoria", ""))
    eid    = str(row.get("id", ""))
    if subcat and subcat.lower() not in ("nan", "none", ""):
        cands = df_all[(df_all["subcategoria"] == subcat) & (df_all["id"].astype(str) != eid)]
    else:
        cands = df_all[(df_all["categoria"] == cat) & (df_all["id"].astype(str) != eid)]
    return cands.head(n)

def adaptar_df_por_dolor(df_base, hombro, lumbar, rodilla):
    """Método David: primero adapta, no cancela a la primera.
    Solo elimina ejercicios cuando el dolor es alto (>=7).
    Entre 5-6 solo excluye compuestos pesados del patrón afectado."""
    df_f = df_base.copy()
    if "categoria" not in df_f.columns:
        return df_f
    cat_up = df_f["categoria"].str.upper()
    if hombro >= 7:
        df_f = df_f[~cat_up.str.contains("EMPUJE|TRICEPS", na=False)]
    elif hombro >= 5:
        mask = (cat_up.str.contains("EMPUJE", na=False)) & (df_f["tipo_ejercicio"].str.lower() == "compuesto")
        df_f = df_f[~mask]
    if lumbar >= 7:
        df_f = df_f[~cat_up.str.contains("OLIMPICO|ISQUIOSURALES", na=False)]
    if rodilla >= 7:
        df_f = df_f[~cat_up.str.contains("PIERNA", na=False)]
    return df_f

def alerta_ejercicio(row, ci):
    if not ci: return ""
    cat_up = _val(row.get("categoria", "")).upper()
    if ci.get("hombro", 0) >= 5 and any(k in cat_up for k in ["EMPUJE", "HOMBRO", "TRICEPS"]):
        return "⚠️ Hombro sensible — controla rango y carga"
    if ci.get("lumbar", 0) >= 5 and any(k in cat_up for k in ["GLUTEO", "ISQUIO", "OLIMPICO"]):
        return "⚠️ Lumbar sensible — técnica prioritaria, reduce peso"
    if ci.get("rodilla", 0) >= 5 and any(k in cat_up for k in ["PIERNA", "GLUTEO"]):
        return "⚠️ Rodilla sensible — controla rango de flexión"
    return ""

# Función del bloque (método David: cada bloque tiene un propósito claro)
BLOCK_FUNCTIONS = {
    "calentamiento": "Preparar el sistema nervioso y tejidos. Sin este bloque el estímulo principal pierde calidad.",
    "potencia":      "Bloque principal de alta intensidad. Máximo rendimiento neuromuscular con baja fatiga acumulada.",
    "circuito":      "Acumular volumen útil combinando patrones complementarios en superserie.",
    "caminar":       "Cierre aeróbico regenerativo. Facilita recuperación activa sin generar fatiga adicional.",
    "carrera":       "Estímulo cardiovascular y de capacidad atlética híbrida.",
}

def get_block_function(tipo_bloque):
    t = tipo_bloque.lower()
    for k, v in BLOCK_FUNCTIONS.items():
        if k in t:
            return v
    return ""

# ===================== RENDER CARD =====================
def render_exercise_card(row, key_prefix="", show_log=False, ci=None):
    row    = dict(row) if not isinstance(row, dict) else row
    titulo = _val(row.get("ejercicio", ""))
    cat    = _val(row.get("categoria", ""))
    subcat = _val(row.get("subcategoria", ""))
    tipo   = _val(row.get("tipo_ejercicio", ""))
    series = _val(row.get("series", ""))
    reps   = _val(row.get("repeticiones", ""))
    expl   = _val(row.get("explicacion", ""))
    video  = _norm_url(row.get("video", ""))
    eid    = str(row.get("id", ""))
    dosis  = f"{series} × {reps}" if (series and reps) else (series or reps)

    alert  = alerta_ejercicio(row, ci)
    prog   = suggest_progression(eid, series, reps) if eid else ""

    chips = []
    if dosis:                                         chips.append(f"<span class='chip'>{dosis}</span>")
    if tipo:                                          chips.append(f"<span class='chip'>{tipo}</span>")
    if subcat and subcat not in ("nan", "none", ""): chips.append(f"<span class='chip'>{subcat}</span>")

    meta    = f"<div class='meta'>{''.join(chips)}</div>" if chips else ""
    body    = f"<div class='label'>Explicación</div><p>{expl}</p>" if expl else ""
    alert_h = f"<p class='warn-hint'>{alert}</p>" if alert else ""
    prog_h  = f"<p class='prog-hint'>{prog}</p>" if prog else ""
    btn_vid = f"<a class='btn' href='{video}' target='_blank' rel='noopener'>▶ Ver vídeo</a>" if video else ""

    st.markdown(f"""<div class='card'>
      <div class='card-header'>
        <div class='badge gray'>{cat}</div>
        <div class='badge primary'>{tipo}</div>
      </div>
      <div class='card-title'>{titulo}</div>
      {meta}{alert_h}{body}{prog_h}
      <div class='actions'>{btn_vid}</div>
    </div>""", unsafe_allow_html=True)

    # Sustitutos (mismo patrón e intención — método David)
    key_s = f"sust_{key_prefix}_{eid}"
    if key_s not in st.session_state: st.session_state[key_s] = False
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("🔄 Cambiar ejercicio", key=f"bsust_{key_prefix}_{eid}"):
            st.session_state[key_s] = not st.session_state[key_s]
    with c2:
        if show_log:
            lk = f"log_{key_prefix}_{eid}"
            if lk not in st.session_state:
                st.session_state[lk] = {"peso": "", "reps": "", "esfuerzo": 5, "tolerancia": "bien"}
            with st.expander("📝 Registrar carga", expanded=False):
                st.session_state[lk]["peso"]       = st.text_input("Peso (kg)",    value=st.session_state[lk]["peso"],       key=f"p_{key_prefix}_{eid}")
                st.session_state[lk]["reps"]       = st.text_input("Reps hechas",  value=st.session_state[lk]["reps"],       key=f"r_{key_prefix}_{eid}")
                st.session_state[lk]["esfuerzo"]   = st.slider("Esfuerzo (RPE)",   1, 10, st.session_state[lk]["esfuerzo"],  key=f"e_{key_prefix}_{eid}")
                st.session_state[lk]["tolerancia"] = st.selectbox("Tolerancia",    ["bien", "regular", "mal"],               key=f"t_{key_prefix}_{eid}")

    if st.session_state[key_s]:
        sust = get_sustitutos(row, df, n=5)
        if sust.empty:
            st.caption("No hay sustitutos disponibles en este patrón.")
        else:
            st.caption("**Sustitutos válidos (mismo patrón e intención):**")
            for _, s in sust.iterrows():
                sv = _norm_url(s.get("video", ""))
                sn = _val(s.get("ejercicio", ""))
                sc1, sc2 = st.columns([3, 1])
                with sc1: st.write(f"• {sn}")
                with sc2:
                    if sv: st.markdown(f"[▶ Vídeo]({sv})")

def render_items_cards(items, key_prefix="", show_log=False, ci=None):
    df_items = items if isinstance(items, pd.DataFrame) else (pd.DataFrame(items) if items else pd.DataFrame())
    if df_items.empty: st.info("Bloque vacío."); return
    if "RPE" in df_items.columns and "rpe" not in df_items.columns:
        df_items = df_items.rename(columns={"RPE": "rpe"})
    for i, (_, row) in enumerate(df_items.fillna("").iterrows()):
        render_exercise_card(row, key_prefix=f"{key_prefix}_{i}", show_log=show_log, ci=ci)

def render_plan_info(plan):
    if "duracion_min" in plan:
        st.info(f"🚶 Caminar {plan['duracion_min']} min · Inclinación {plan.get('inclinacion', '')} · Ritmo {plan.get('ritmo_kmh', '')}")
    elif "sesion" in plan:
        st.info(f"🏃 {plan.get('tipo', 'Intervalos')}: {plan['sesion']}")
    else:
        st.info(str(plan))

# ===================== SESSION STATE INIT =====================
for k, v in [("checkin", None), ("plan_sesion", None), ("regen", 0)]:
    if k not in st.session_state: st.session_state[k] = v

# Auto-recuperar la sesión del día si el navegador fue recargado
if st.session_state["plan_sesion"] is None:
    _ci_saved, _seed_saved = load_today_session()
    if _ci_saved is not None and _seed_saved is not None:
        try:
            _obj_profile = OBJ_PROFILES[_ci_saved["objetivo_nombre"]]
            _df_saved = adaptar_df_por_dolor(
                df.sample(frac=1, random_state=int(_seed_saved)).reset_index(drop=True),
                _ci_saved["hombro"], _ci_saved["lumbar"], _ci_saved["rodilla"]
            )
            _plan_rec = plan_semana(_df_saved, PATTERNS, semana_mesociclo=int(_ci_saved["semana"]), objetivo_profile=_obj_profile)
            _dia_rec = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][date.today().weekday()]
            st.session_state["plan_sesion"] = {
                "dia": _dia_rec,
                "data": _plan_rec[_dia_rec],
                "plan_semana": _plan_rec
            }
            st.session_state["checkin"] = _ci_saved
        except Exception as _e:
            st.sidebar.error(f"⚠️ Error recuperando sesión: {_e}")

# ===================== TABS PRINCIPALES =====================
tab_ci, tab_sesion, tab_semana, tab_ejercicios, tab_historial = st.tabs([
    "🏁 Check-in", "💪 Sesión del día", "📅 Semana", "🔍 Ejercicios", "📊 Historial"
])

# =========================================================
# TAB 1: CHECK-IN (preguntas previas — método David)
# =========================================================
with tab_ci:
    st.markdown("## Check-in · ¿Cómo llegas hoy?")
    st.caption("David no programa sin saber en qué punto estás. Responde y la sesión se adapta.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Dolor por zonas** (0 = sin dolor · 10 = máximo)")
        hombro  = st.slider("🦾 Hombro derecho",  0, 10, 2, key="ci_h")
        lumbar  = st.slider("🔒 Lumbar",           0, 10, 1, key="ci_l")
        rodilla = st.slider("🦵 Rodilla",          0, 10, 0, key="ci_r")
    with col2:
        st.markdown("**Estado general**")
        energia    = st.slider("⚡ Energía (1=baja · 5=alta)",     1, 5, 3, key="ci_en")
        sueno      = st.slider("😴 Sueño (1=malo · 5=excelente)",  1, 5, 3, key="ci_su")
        tiempo     = st.selectbox("⏱️ Tiempo disponible", ["30 min", "45 min", "60 min", "90 min+"], index=2, key="ci_ti")
        como_quedo = st.selectbox("Última sesión ¿cómo quedaste?",
            ["Bien, recuperado", "Un poco cansado", "Muy cansado / agujetas fuertes", "No entrené"], key="ci_cq")
        molestia   = st.text_input("¿Algún gesto que duela hoy especialmente?", key="ci_mo",
            placeholder="ej: press sobre cabeza, sentadilla profunda...")

    objetivo_nombre = st.selectbox("Objetivo de la semana", list(OBJ_PROFILES.keys()), key="ci_obj")
    semana          = st.selectbox("Semana del mesociclo (1-4)", [1, 2, 3, 4], key="ci_sem")

    # Decisión adaptativa estilo David
    alertas = []
    vol_red = 0
    if hombro  >= 7:  alertas.append("🔴 Hombro alto — se eliminan empujes pesados directos")
    elif hombro >= 5: alertas.append("🟡 Hombro sensible — se adaptan plano, rango y carga de empujes")
    if lumbar  >= 7:  alertas.append("🔴 Lumbar alta — sin carga axial pesada ni bisagra en rangos extremos")
    elif lumbar >= 5: alertas.append("🟡 Lumbar sensible — técnica prioritaria, reduce carga en bisagra")
    if rodilla >= 6:  alertas.append("🟡 Rodilla sensible — dominantes de rodilla ligeros o sustituidos")
    if energia <= 2:  alertas.append("🟡 Energía baja — volumen reducido, prioriza calidad sobre cantidad"); vol_red += 1
    if sueno   <= 2:  alertas.append("🟡 Sueño deficiente — se reduce volumen total de la sesión"); vol_red += 1
    if como_quedo == "Muy cansado / agujetas fuertes":
        alertas.append("🟡 Fatiga acumulada — sesión más ligera, patrón menos cargado"); vol_red += 1

    if alertas:
        st.markdown("**Adaptaciones que aplicará hoy:**")
        for a in alertas: st.markdown(f"- {a}")
    else:
        st.success("✅ Perfil sin restricciones — sesión completa")

    if st.button("✅ Confirmar y generar sesión adaptada", type="primary"):
        ci_data = {
            "hombro": hombro, "lumbar": lumbar, "rodilla": rodilla,
            "energia": energia, "sueno": sueno, "tiempo": tiempo,
            "como_quedo": como_quedo, "molestia": molestia,
            "objetivo_nombre": objetivo_nombre, "semana": semana,
            "vol_red": vol_red, "alertas": alertas,
            "fecha": date.today().isoformat()
        }
        st.session_state["checkin"] = ci_data
        objetivo_profile = OBJ_PROFILES[objetivo_nombre]
        seed = int(time.time_ns()) % ((2 ** 32) - 1)
        df_adaptado = adaptar_df_por_dolor(
            df.sample(frac=1, random_state=seed).reset_index(drop=True),
            hombro, lumbar, rodilla
        )
        try:
            plan_completo = plan_semana(df_adaptado, PATTERNS, semana_mesociclo=semana, objetivo_profile=objetivo_profile)
            dia_hoy = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][date.today().weekday()]
            st.session_state["plan_sesion"] = {
                "dia": dia_hoy,
                "data": plan_completo[dia_hoy],
                "plan_semana": plan_completo
            }
            save_today_session(ci_data, seed)
            st.success(f"✅ Sesión generada para **{dia_hoy}** → ve a la pestaña 💪 Sesión del día")
        except Exception as e:
            st.error(f"Error generando sesión: {e}")
            st.code(traceback.format_exc())

# =========================================================
# TAB 2: SESIÓN DEL DÍA
# =========================================================
with tab_sesion:
    ci      = st.session_state.get("checkin")
    plan_s  = st.session_state.get("plan_sesion")

    if plan_s is None:
        st.info("👈 Primero completa el **Check-in** para generar tu sesión de hoy.")
    else:
        dia      = plan_s["dia"]
        data     = plan_s["data"]
        tipo_ses = (data.get("meta") or {}).get("titulo", "")
        bloques  = data.get("bloques", [])
        fecha_h  = date.today().strftime("%d-%m-%Y")

        st.markdown(f"## 💪 {dia} · {fecha_h}")
        if tipo_ses: st.markdown(f"**Tipo de sesión:** {tipo_ses}")

        if ci and ci.get("alertas"):
            with st.expander("⚠️ Adaptaciones activas hoy", expanded=False):
                for a in ci["alertas"]: st.markdown(f"- {a}")

        if not bloques:
            st.warning("No hay bloques para hoy. Vuelve al Check-in y regenera.")
        else:
            tabs_b = st.tabs([f"🔹 {b['tipo']}" for b in bloques])
            for tb, bloque in zip(tabs_b, bloques):
                with tb:
                    func = get_block_function(bloque.get("tipo", ""))
                    if func: st.caption(f"**Propósito del bloque:** {func}")
                    if "items" in bloque:
                        render_items_cards(bloque["items"],
                            key_prefix=f"ses_{dia}_{bloque['tipo']}", show_log=True, ci=ci)
                    elif "plan" in bloque:
                        render_plan_info(bloque["plan"])

        st.markdown("---")
        if st.button("💾 Guardar sesión de hoy", type="primary"):
            ejs_log = []
            for bloque in bloques:
                items = bloque.get("items")
                if items is None: continue
                items_l = items.fillna("").to_dict("records") if isinstance(items, pd.DataFrame) \
                          else (items if isinstance(items, list) else [])
                for i, it in enumerate(items_l):
                    eid    = str(it.get("id", ""))
                    tipo_b = bloque.get("tipo", "")
                    lk     = f"log_ses_{dia}_{tipo_b}_{i}_{eid}"
                    ld     = st.session_state.get(lk, {})
                    ejs_log.append({
                        "id": eid, "ejercicio": it.get("ejercicio", ""), "bloque": tipo_b,
                        "peso": ld.get("peso", ""), "reps_hechas": ld.get("reps", ""),
                        "esfuerzo": ld.get("esfuerzo", 5), "tolerancia": ld.get("tolerancia", "bien")
                    })
            save_session_log(date.today().isoformat(), {
                "fecha": date.today().isoformat(), "dia": dia, "tipo_sesion": tipo_ses,
                "checkin": ci, "ejercicios": ejs_log
            })
            st.success("✅ Sesión guardada. Los datos mejorarán tu próxima progresión.")

# =========================================================
# TAB 3: SEMANA COMPLETA
# =========================================================
with tab_semana:
    ci_s    = st.session_state.get("checkin")
    plan_s2 = st.session_state.get("plan_sesion")
    if plan_s2 is None:
        st.info("👈 Primero completa el **Check-in** para generar el plan semanal.")
    else:
        dia_hoy2 = plan_s2["dia"]
        plan_sem = plan_s2.get("plan_semana", {})
        base_d   = week_monday(date.today())
        dias_sem = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        st.markdown("### 📅 Semana completa")
        for i, d in enumerate(dias_sem):
            fecha_d = (base_d + timedelta(days=i)).strftime("%d-%m-%Y")
            dd      = plan_sem.get(d, {})
            tt      = (dd.get("meta") or {}).get("titulo", "")
            label_d = f"📅 {d} · {fecha_d}" + (f" · {tt}" if tt else "")
            with st.expander(label_d, expanded=(d == dia_hoy2)):
                bls = dd.get("bloques", [])
                if not bls: st.info("Sin bloques."); continue
                tabs_d = st.tabs([f"🔹 {b['tipo']}" for b in bls])
                for td, bd in zip(tabs_d, bls):
                    with td:
                        if "items" in bd:
                            render_items_cards(bd["items"], key_prefix=f"wk_{d}_{bd['tipo']}", ci=ci_s)
                        elif "plan" in bd:
                            render_plan_info(bd["plan"])

# =========================================================
# TAB 4: EJERCICIOS
# =========================================================
with tab_ejercicios:
    st.markdown("### 🔍 Biblioteca de ejercicios")
    cs, cc, ct = st.columns([3, 2, 2])
    with cs: buscar = st.text_input("Buscar...", placeholder="sentadilla, press, remo...")
    with cc:
        cats    = sorted([c for c in df["categoria"].dropna().unique()
                          if str(c).lower() not in ("nan", "none", "")]) if "categoria" in df.columns else []
        cat_sel = st.selectbox("Categoría", ["Todas"] + cats)
    with ct:
        tipos    = sorted([t for t in df["tipo_ejercicio"].dropna().unique()
                           if str(t).lower() not in ("nan", "none", "")]) if "tipo_ejercicio" in df.columns else []
        tipo_sel = st.selectbox("Tipo", ["Todos"] + tipos)

    df_lib = df.copy()
    if buscar.strip():
        m = df_lib["ejercicio"].str.contains(buscar.strip(), case=False, na=False)
        if "explicacion" in df_lib.columns:
            m = m | df_lib["explicacion"].str.contains(buscar.strip(), case=False, na=False)
        df_lib = df_lib[m]
    if cat_sel  != "Todas" and "categoria"     in df_lib.columns: df_lib = df_lib[df_lib["categoria"]     == cat_sel]
    if tipo_sel != "Todos" and "tipo_ejercicio" in df_lib.columns: df_lib = df_lib[df_lib["tipo_ejercicio"] == tipo_sel]

    st.caption(f"{len(df_lib)} ejercicio(s) encontrado(s)")
    if df_lib.empty:
        st.info("No hay ejercicios con esos filtros.")
    elif cat_sel == "Todas" and not buscar.strip():
        for cat_n, grp in df_lib.groupby("categoria", sort=True):
            if str(cat_n).lower() in ("nan", "none", ""): continue
            with st.expander(f"📂 {cat_n}  ({len(grp)})", expanded=False):
                for i, (_, row) in enumerate(grp.fillna("").iterrows()):
                    render_exercise_card(row, key_prefix=f"lib_{cat_n}_{i}")
    else:
        for i, (_, row) in enumerate(df_lib.fillna("").iterrows()):
            render_exercise_card(row, key_prefix=f"lib_s_{i}")

# =========================================================
# TAB 5: HISTORIAL Y PROGRESIÓN
# =========================================================
with tab_historial:
    st.markdown("### 📊 Historial de sesiones")
    logs = list_logs()
    if not logs:
        st.info("Aún no hay sesiones guardadas. Completa un entrenamiento en 💪 Sesión del día.")
    else:
        sel_log = st.selectbox("Ver sesión guardada", logs)
        ld = load_session_log(sel_log)
        if ld:
            ci_l = ld.get("checkin", {})
            st.markdown(f"**{ld.get('dia', '')} · {ld.get('tipo_sesion', '')}**")
            if ci_l:
                ca, cb, cc2, cd = st.columns(4)
                ca.metric("Energía",  f"{ci_l.get('energia', '-')}/5")
                cb.metric("Sueño",    f"{ci_l.get('sueno', '-')}/5")
                cc2.metric("Hombro",  f"{ci_l.get('hombro', '-')}/10")
                cd.metric("Lumbar",   f"{ci_l.get('lumbar', '-')}/10")
            ejs = ld.get("ejercicios", [])
            if ejs:
                rows_h = [{"Ejercicio": e.get("ejercicio", ""), "Bloque": e.get("bloque", ""),
                    "Peso (kg)": e.get("peso", ""), "Reps": e.get("reps_hechas", ""),
                    "RPE": e.get("esfuerzo", ""), "Tolerancia": e.get("tolerancia", "")} for e in ejs]
                st.dataframe(pd.DataFrame(rows_h), use_container_width=True)
            else:
                st.info("No se registraron cargas en esta sesión.")

    st.markdown("---")
    st.markdown("#### 📈 Evolución por ejercicio")
    ej_names = sorted(df["ejercicio"].dropna().unique().tolist())
    ej_sel   = st.selectbox("Selecciona ejercicio", ej_names, key="hist_ej")
    ej_row   = df[df["ejercicio"] == ej_sel]
    if not ej_row.empty:
        eid_h  = str(ej_row.iloc[0]["id"])
        hist_h = get_exercise_history(eid_h)
        if hist_h:
            st.dataframe(pd.DataFrame(hist_h), use_container_width=True)
        else:
            st.info("Sin registros todavía. Guarda sesiones para ver la evolución.")
