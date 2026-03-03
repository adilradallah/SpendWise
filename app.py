import streamlit as st
import pandas as pd

from src.extract_pdf import extract_text_from_pdf_bytes
from src.parse_transactions import parse_transactions_from_text
from src.quality import assess_quality
from src.privacy import sanitize_transactions
from src.llm_analyze import analyze_transactions_with_llm
from src.alternatives import load_catalog, build_alternatives


# ---------------- UI THEME (minimal, clean) ----------------
st.set_page_config(page_title="Spendwise", page_icon="💳", layout="wide")

CSS = """
<style>
:root { --card: rgba(255,255,255,.06); --border: rgba(255,255,255,.10); --muted: rgba(255,255,255,.70); }
.block-container { padding-top: 2.0rem; }
h1, h2, h3 { letter-spacing: -0.02em; }
.small-muted { color: var(--muted); font-size: 0.92rem; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 16px; }
.card-title { font-weight: 700; font-size: 1.03rem; margin-bottom: 6px; }
.badge { display:inline-block; padding: 4px 10px; border-radius: 999px; border: 1px solid var(--border); background: rgba(255,255,255,.04); font-size: 0.85rem; margin-right: 6px;}
.hr { height:1px; background: var(--border); margin: 12px 0; }
.kpi { background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 14px 14px; }
.kpi .label { color: var(--muted); font-size: 0.85rem; }
.kpi .value { font-weight: 800; font-size: 1.45rem; margin-top: 2px; }
.kpi .sub { color: var(--muted); font-size: 0.85rem; margin-top: 6px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.markdown("# Spendwise")
st.markdown("<div class='small-muted'>Copilote financier : PDF → extraction → anonymisation → IA → recommandations + alternatives d’abonnements.</div>", unsafe_allow_html=True)

# ---------------- Sidebar (clean controls) ----------------
with st.sidebar:
    st.markdown("### Paramètres")
    st.caption("Le PDF brut n’est jamais envoyé à l’IA. Seules des transactions anonymisées le sont.")
    show_debug = st.toggle("Mode debug (détails)", value=False)
    enable_alts = st.toggle("Afficher Alternatives", value=True)

    st.markdown("### IA")
    model = st.secrets.get("OPENAI_MODEL", "gpt-5-mini")
    st.text_input("Modèle", value=model, disabled=True)

    api_key = st.secrets.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        st.error("OPENAI_API_KEY manquante (Settings → Secrets).")

# ---------------- Stepper ----------------
STEP_TITLES = ["Upload", "Extraction", "Analyse IA", "Alternatives"]
step = st.radio("Étapes", STEP_TITLES, horizontal=True, label_visibility="collapsed")

# ---------------- Upload ----------------
pdf = st.file_uploader("Uploader un relevé bancaire (PDF)", type=["pdf"])

if not pdf:
    st.info("Commence par uploader un PDF.")
    st.stop()

pdf_bytes = pdf.getvalue()

@st.cache_data(show_spinner=False)
def _extract_and_parse(pdf_bytes: bytes):
    doc = extract_text_from_pdf_bytes(pdf_bytes)
    txs = parse_transactions_from_text(doc.raw_text)
    q = assess_quality(txs)
    sanitized = sanitize_transactions(txs) if txs else []
    return doc, txs, q, sanitized

with st.spinner("Extraction & parsing..."):
    doc, txs, q, sanitized = _extract_and_parse(pdf_bytes)

# ---------------- Top KPIs ----------------
def _fmt_eur(x):
    try:
        return f"{float(x):,.2f} €".replace(",", " ").replace(".", ",")
    except:
        return "—"

total_spend = sum(t["amount"] for t in sanitized if t["amount"] < 0) if sanitized else 0.0
total_income = sum(t["amount"] for t in sanitized if t["amount"] > 0) if sanitized else 0.0
net = total_income + total_spend

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f"<div class='kpi'><div class='label'>Dépenses</div><div class='value'>{_fmt_eur(abs(total_spend))}</div><div class='sub'>sur la période détectée</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='kpi'><div class='label'>Revenus</div><div class='value'>{_fmt_eur(total_income)}</div><div class='sub'>salaires / virements reçus</div></div>", unsafe_allow_html=True)
k3.markdown(f"<div class='kpi'><div class='label'>Net</div><div class='value'>{_fmt_eur(net)}</div><div class='sub'>revenus - dépenses</div></div>", unsafe_allow_html=True)
k4.markdown(f"<div class='kpi'><div class='label'>Transactions</div><div class='value'>{len(sanitized)}</div><div class='sub'>lignes analysées</div></div>", unsafe_allow_html=True)

# ---------------- Extraction view ----------------
if step in ["Extraction", "Upload"]:
    left, right = st.columns([1.3, 1])
    with left:
        st.markdown("## 1) Extraction")
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<span class='badge'>Pages: {doc.num_pages}</span><span class='badge'>PDF texte: {'Oui' if doc.is_text_pdf else 'Non'}</span><span class='badge'>Qualité: {int(q.confidence*100)}%</span>", unsafe_allow_html=True)
        st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

        if q.issues:
            st.warning("Points d’attention :\n- " + "\n- ".join(q.issues))
        else:
            st.success("Extraction OK.")

        if not sanitized:
            st.error("Aucune transaction détectée. (On devra adapter le parsing à ce format de relevé.)")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("## 2) Données envoyées à l’IA")
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.caption("Anonymisées (pas d’IBAN / pas de n° de compte).")
        st.dataframe(pd.DataFrame(sanitized).head(25), use_container_width=True, height=380)
        st.markdown("</div>", unsafe_allow_html=True)

    if show_debug:
        st.markdown("### Debug : transactions brutes")
        df_raw = pd.DataFrame([{"date": t.date, "label_raw": t.label_raw, "amount": t.amount} for t in txs])
        st.dataframe(df_raw, use_container_width=True, height=350)

# ---------------- AI analysis (cached) ----------------
@st.cache_data(show_spinner=False)
def _run_ai(sanitized, api_key, model):
    return analyze_transactions_with_llm(sanitized, api_key=api_key, model=model)

analysis = None
if step in ["Analyse IA", "Alternatives"]:
    if not api_key:
        st.stop()
    with st.spinner("Analyse IA…"):
        analysis = _run_ai(sanitized, api_key, model)

    if isinstance(analysis, dict) and analysis.get("error"):
        st.error("Erreur IA")
        st.code(analysis.get("raw_output", analysis.get("error")))
        st.stop()

# ---------------- AI view (pro UI) ----------------
if step == "Analyse IA":
    st.markdown("## 3) Analyse IA")

    summary = analysis.get("summary", {})
    actions = analysis.get("actions", [])
    subs = analysis.get("subscriptions", [])
    cats = analysis.get("categories", [])
    anomalies = analysis.get("anomalies", [])

    # Layout: Left = priorities, Right = subscriptions quick
    colA, colB = st.columns([1.4, 1])

    with colA:
        st.markdown("### Priorités (à faire)")
        if not actions:
            st.info("Aucune action proposée.")
        else:
            for a in actions[:6]:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(f"<div class='card-title'>{a.get('title','Action')}</div>", unsafe_allow_html=True)
                impact = a.get("impact_estimate_eur_per_month", 0.0)
                st.markdown(f"<span class='badge'>Impact estimé : {int(impact)} €/mois</span>", unsafe_allow_html=True)
                steps = a.get("steps", [])
                if steps:
                    st.markdown("**Étapes**")
                    for s in steps[:5]:
                        st.write(f"• {s}")
                notes = a.get("notes", "")
                if notes:
                    st.caption(notes)
                st.markdown("</div>", unsafe_allow_html=True)

        if anomalies:
            st.markdown("### À vérifier")
            for an in anomalies[:6]:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(f"<div class='card-title'>{an.get('title','Point à vérifier')}</div>", unsafe_allow_html=True)
                st.caption(an.get("detail", ""))
                st.markdown(f"<span class='badge'>Confiance : {an.get('confidence',0):.2f}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    with colB:
        st.markdown("### Abonnements détectés")
        if not subs:
            st.info("Aucun abonnement détecté.")
        else:
            for s in subs[:10]:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(f"<div class='card-title'>{s.get('merchant','Abonnement')}</div>", unsafe_allow_html=True)
                st.markdown(
                    f"<span class='badge'>{s.get('frequency','unknown')}</span>"
                    f"<span class='badge'>{_fmt_eur(s.get('amount_typical',0))}</span>"
                    f"<span class='badge'>Confiance {s.get('confidence',0):.2f}</span>",
                    unsafe_allow_html=True
                )
                ev = s.get("evidence", "")
                if ev:
                    st.caption(ev)
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### Catégories (top)")
        if cats:
            df_c = pd.DataFrame(cats)
            if "total" in df_c.columns:
                df_c = df_c.sort_values("total", ascending=False).head(10)
                df_plot = df_c.set_index("category")["total"]
                st.bar_chart(df_plot)
            st.dataframe(df_c, use_container_width=True, height=360)
        else:
            st.info("Pas de catégories.")

# ---------------- Alternatives view ----------------
if step == "Alternatives":
    st.markdown("## 4) Alternatives d’abonnements")

    subs = analysis.get("subscriptions", [])
    if not enable_alts:
        st.info("Alternatives désactivées (sidebar).")
        st.stop()

    if not subs:
        st.info("Aucun abonnement détecté. (Donc pas d’alternatives à proposer.)")
        st.stop()

    catalog = load_catalog("data/alternatives_fr.json")
    alts = build_alternatives(subs, catalog)

    st.caption("Basé sur un catalogue FR (stable). Étape suivante : ajout d’une option “live” (recherche web) sans envoyer tes données.")

    for item in alts:
        current = item["current"]
        offers = item["offers"]

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{current.get('merchant','Abonnement')}</div>", unsafe_allow_html=True)

        st.markdown(
            f"<span class='badge'>Actuel : {_fmt_eur(current.get('amount_typical',0))}</span>"
            f"<span class='badge'>Fréquence : {current.get('frequency','unknown')}</span>"
            f"<span class='badge'>Confiance : {current.get('confidence',0):.2f}</span>",
            unsafe_allow_html=True
        )
        if current.get("evidence"):
            st.caption(current["evidence"])

        st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
        st.markdown("**Alternatives proposées**")
        if not offers:
            st.write("Aucune alternative trouvée dans le catalogue (à enrichir).")
        else:
            df_off = pd.DataFrame(offers)
            # jolie vue
            df_off = df_off[["name", "price_eur_per_month", "type", "why", "url", "estimated_saving_eur_per_month"]]
            st.dataframe(df_off, use_container_width=True, height=260)

        st.markdown("</div>", unsafe_allow_html=True)

    if show_debug:
        st.markdown("### Debug : sortie complète IA")
        st.json(analysis)
