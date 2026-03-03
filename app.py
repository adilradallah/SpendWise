import streamlit as st
import pandas as pd

from src.extract_pdf import extract_text_from_pdf_bytes
from src.parse_transactions import parse_transactions_from_text
from src.quality import assess_quality
from src.privacy import sanitize_transactions
from src.llm_analyze import analyze_transactions_with_llm
from src.alternatives import load_catalog, build_alternatives


# ---------------- Page config ----------------
st.set_page_config(page_title="Spendwise", page_icon="💳", layout="wide")


# ---------------- Minimal UI CSS ----------------
CSS = """
<style>
/* Layout spacing */
.block-container { padding-top: 1.7rem; max-width: 1200px; }
h1, h2, h3 { letter-spacing: -0.02em; }
h1 { font-size: 2.2rem; margin-bottom: .2rem; }
p { margin-bottom: .4rem; }

/* Remove extra top padding in main area */
section[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,.08); }
hr { border: none; height: 1px; background: rgba(255,255,255,.10); margin: 12px 0; }

/* Cards */
.card {
  background: rgba(255,255,255,.05);
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 16px;
  padding: 16px;
}
.card-tight {
  background: rgba(255,255,255,.05);
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 16px;
  padding: 12px 14px;
}
.muted { color: rgba(255,255,255,.70); font-size: .92rem; }
.badges { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
.badge {
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.04);
  font-size: .85rem;
  color: rgba(255,255,255,.80);
}

/* Tabs: reduce visual noise */
div[data-testid="stTabs"] button {
  font-size: .95rem;
  padding: 8px 14px;
}
div[data-testid="stTabs"] button[aria-selected="true"]{
  border-bottom: 2px solid rgba(255,255,255,.75) !important;
}

/* Dataframes */
div[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid rgba(255,255,255,.10); }

/* Make file uploader cleaner */
div[data-testid="stFileUploader"] section {
  border: 1px dashed rgba(255,255,255,.22);
  border-radius: 14px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------- Helpers ----------------
def fmt_eur(x: float) -> str:
    try:
        s = f"{abs(float(x)):.2f}".replace(".", ",")
        return f"{s} €"
    except:
        return "—"

def card_kpi(label: str, value: str, sub: str = ""):
    st.markdown(
        f"""
        <div class="card-tight">
          <div class="muted">{label}</div>
          <div style="font-weight:800;font-size:1.4rem;margin-top:2px;">{value}</div>
          <div class="muted" style="margin-top:6px;">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def card_title(title: str, subtitle: str = ""):
    st.markdown(f"<div style='font-weight:800;font-size:1.1rem;margin-bottom:2px;'>{title}</div>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<div class='muted'>{subtitle}</div>", unsafe_allow_html=True)


# ---------------- Header ----------------
st.markdown("Spendwise")
st.markdown("<div class='muted'>Copilote financier — PDF → extraction → anonymisation → IA → recommandations + alternatives.</div>", unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)


# ---------------- Sidebar (minimal, pro) ----------------
with st.sidebar:
    st.markdown("### Réglages")
    show_debug = st.toggle("Afficher Debug", value=False)
    enable_alts = st.toggle("Alternatives", value=True)

    st.markdown("### IA")
    model = st.secrets.get("OPENAI_MODEL", "gpt-5-mini")
    st.caption("Le PDF brut n’est jamais envoyé à l’IA.")
    api_key = st.secrets.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        st.error("OPENAI_API_KEY manquante (Settings → Secrets).")


# ---------------- Tabs (real tabs) ----------------
tab_upload, tab_ai, tab_cats, tab_alts, tab_debug = st.tabs(
    ["📄 Upload", "🧠 Analyse", "📊 Catégories", "✨ Alternatives", "🛠️ Debug"]
)

# ---------------- Upload + pipeline ----------------
with tab_upload:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    card_title("Importer un relevé bancaire", "PDF uniquement. Ensuite l’analyse démarre automatiquement.")
    pdf = st.file_uploader(" ", type=["pdf"], label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "doc" not in st.session_state:
    st.session_state.doc = None
if "txs" not in st.session_state:
    st.session_state.txs = None
if "sanitized" not in st.session_state:
    st.session_state.sanitized = None
if "quality" not in st.session_state:
    st.session_state.quality = None
if "analysis" not in st.session_state:
    st.session_state.analysis = None

def run_pipeline(pdf_bytes: bytes):
    doc = extract_text_from_pdf_bytes(pdf_bytes)
    txs = parse_transactions_from_text(doc.raw_text)
    q = assess_quality(txs)
    sanitized = sanitize_transactions(txs) if txs else []
    return doc, txs, q, sanitized

if "pdf" in locals() and pdf is not None:
    st.session_state.pdf_bytes = pdf.getvalue()
    with st.spinner("Extraction & parsing…"):
        doc, txs, q, sanitized = run_pipeline(st.session_state.pdf_bytes)
    st.session_state.doc = doc
    st.session_state.txs = txs
    st.session_state.quality = q
    st.session_state.sanitized = sanitized
    st.session_state.analysis = None  # reset analysis on new upload

# If no PDF yet -> stop after Upload tab
if not st.session_state.pdf_bytes:
    st.stop()

doc = st.session_state.doc
txs = st.session_state.txs or []
q = st.session_state.quality
sanitized = st.session_state.sanitized or []

if not sanitized:
    st.error("Aucune transaction détectée. (Il faut adapter le parsing pour ce format.)")
    st.stop()

# KPIs (always visible under header)
total_spend = sum(t["amount"] for t in sanitized if t["amount"] < 0)
total_income = sum(t["amount"] for t in sanitized if t["amount"] > 0)
net = total_income + total_spend

k1, k2, k3, k4 = st.columns(4)
with k1: card_kpi("Dépenses", fmt_eur(total_spend), "sur la période")
with k2: card_kpi("Revenus", fmt_eur(total_income), "salaires / virements")
with k3: card_kpi("Net", fmt_eur(net), "revenus − dépenses")
with k4: card_kpi("Transactions", f"{len(sanitized)}", "lignes analysées")

# Extraction QA in Upload tab (compact)
with tab_upload:
    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        card_title("Qualité d’extraction")
        st.markdown(
            f"<div class='badges'>"
            f"<span class='badge'>Pages: {doc.num_pages}</span>"
            f"<span class='badge'>PDF texte: {'Oui' if doc.is_text_pdf else 'Non'}</span>"
            f"<span class='badge'>Qualité: {int(q.confidence*100)}%</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        if q.issues:
            st.warning("Points d’attention :\n- " + "\n- ".join(q.issues))
        else:
            st.success("OK.")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        card_title("Aperçu (anonymisé)")
        st.dataframe(pd.DataFrame(sanitized).head(20), use_container_width=True, height=320)
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- AI analysis (run once, cached in session) ----------------
def ensure_analysis():
    if st.session_state.analysis is None:
        if not api_key:
            return {"error": "missing_api_key"}
        with st.spinner("Analyse IA…"):
            st.session_state.analysis = analyze_transactions_with_llm(
                sanitized, api_key=api_key, model=model
            )
    return st.session_state.analysis

analysis = ensure_analysis()
if isinstance(analysis, dict) and analysis.get("error"):
    if analysis["error"] == "missing_api_key":
        st.error("Ajoute OPENAI_API_KEY dans Streamlit → Settings → Secrets.")
    else:
        st.error("Erreur IA")
        st.code(analysis.get("raw_output", analysis.get("error")))
    st.stop()

# ---------------- Analyse tab (clean, not verbose) ----------------
with tab_ai:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    card_title("Priorités", "Les meilleurs leviers d’économie, dans l’ordre.")
    st.markdown("</div>", unsafe_allow_html=True)

    actions = analysis.get("actions", [])[:6]
    if not actions:
        st.info("Aucune action proposée.")
    else:
        for a in actions:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            title = a.get("title", "Action")
            impact = int(float(a.get("impact_estimate_eur_per_month", 0) or 0))
            st.markdown(f"<div style='font-weight:800;font-size:1.05rem;'>{title}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='badges'><span class='badge'>Impact estimé : {impact} €/mois</span></div>", unsafe_allow_html=True)
            steps = a.get("steps", [])[:4]
            if steps:
                for s in steps:
                    st.write(f"• {s}")
            notes = a.get("notes", "")
            if notes:
                st.caption(notes)
            st.markdown("</div>", unsafe_allow_html=True)

    anomalies = analysis.get("anomalies", [])[:5]
    if anomalies:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        card_title("À vérifier", "Points suspects ou incohérents.")
        st.markdown("</div>", unsafe_allow_html=True)

        for an in anomalies:
            st.markdown("<div class='card-tight'>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-weight:750'>{an.get('title','Point')}</div>", unsafe_allow_html=True)
            st.caption(an.get("detail", ""))
            st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Categories tab (clear chart + table) ----------------
with tab_cats:
    cats = analysis.get("categories", [])
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    card_title("Catégories", "Vue simple et lisible. Clique pour trier dans le tableau.")
    st.markdown("</div>", unsafe_allow_html=True)

    if not cats:
        st.info("Pas de catégories.")
    else:
        df = pd.DataFrame(cats)
        # Ensure numeric
        if "total" in df.columns:
            df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0.0)
        if "share" in df.columns:
            df["share"] = pd.to_numeric(df["share"], errors="coerce").fillna(0.0)

        df = df.sort_values("total", ascending=False)
        top = df.head(10).copy()

        c1, c2 = st.columns([1.2, 1])
        with c1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            card_title("Top catégories (dépenses)")
            chart = top.set_index("category")["total"]
            st.bar_chart(chart)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            card_title("Détails")
            df_show = df.copy()
            df_show["total (€)"] = df_show["total"].map(lambda x: float(x))
            df_show["part"] = df_show["share"].map(lambda x: f"{int(float(x)*100)}%")
            df_show = df_show[["category", "total (€)", "part"]]
            st.dataframe(df_show, use_container_width=True, height=360)
            st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Alternatives tab (clean cards + top 5 offers) ----------------
with tab_alts:
    if not enable_alts:
        st.info("Alternatives désactivées (sidebar).")
        st.stop()

    subs = analysis.get("subscriptions", [])[:12]
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    card_title("Alternatives d’abonnements", "Catalogue FR (stable). Prochaine étape : option “live” sans envoyer tes données.")
    st.markdown("</div>", unsafe_allow_html=True)

    if not subs:
        st.info("Aucun abonnement détecté.")
    else:
        catalog = load_catalog("data/alternatives_fr.json")
        items = build_alternatives(subs, catalog)

        for it in items:
            cur = it["current"]
            offers = it["offers"][:5]

            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-weight:850;font-size:1.05rem;'>{cur.get('merchant','Abonnement')}</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='badges'>"
                f"<span class='badge'>Actuel: {fmt_eur(cur.get('amount_typical',0))}</span>"
                f"<span class='badge'>Fréquence: {cur.get('frequency','unknown')}</span>"
                f"<span class='badge'>Confiance: {cur.get('confidence',0):.2f}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            if cur.get("evidence"):
                st.caption(cur["evidence"])

            st.markdown("<hr/>", unsafe_allow_html=True)
            if not offers:
                st.write("Aucune alternative trouvée dans le catalogue (à enrichir).")
            else:
                df_off = pd.DataFrame(offers)
                df_off = df_off[["name", "price_eur_per_month", "estimated_saving_eur_per_month", "why", "url"]]
                df_off = df_off.rename(columns={
                    "name": "Alternative",
                    "price_eur_per_month": "Prix/mois (€)",
                    "estimated_saving_eur_per_month": "Économie estimée (€)",
                    "why": "Pourquoi",
                    "url": "Lien"
                })
                st.dataframe(df_off, use_container_width=True, height=220)

            st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Debug tab (hidden by default) ----------------
with tab_debug:
    if not show_debug:
        st.info("Active 'Afficher Debug' dans la sidebar.")
        st.stop()

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    card_title("Debug", "Données brutes et anonymisées + sortie IA complète.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("**Transactions brutes**")
    df_raw = pd.DataFrame([{"date": t.date, "label_raw": t.label_raw, "amount": t.amount} for t in txs])
    st.dataframe(df_raw, use_container_width=True, height=320)

    st.markdown("**Transactions anonymisées**")
    st.dataframe(pd.DataFrame(sanitized), use_container_width=True, height=320)

    st.markdown("**Sortie IA**")
    st.json(analysis)
