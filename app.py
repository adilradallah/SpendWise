import streamlit as st
import pandas as pd

from src.extract_pdf import extract_text_from_pdf_bytes
from src.parse_transactions import parse_transactions_from_text
from src.quality import assess_quality
from src.privacy import sanitize_transactions
from src.llm_analyze import analyze_transactions_with_llm

st.set_page_config(page_title="Spendwise", page_icon="💳", layout="wide")

st.title("Spendwise")
st.caption("Copilote financier intelligent — analyse de relevés bancaires (privacy-by-design).")

# Sidebar minimal
with st.sidebar:
    st.header("Paramètres")
    st.write("Le PDF brut n'est jamais envoyé à l'IA.")
    model = st.secrets.get("OPENAI_MODEL", "gpt-5-mini")
    st.text_input("Modèle IA", value=model, disabled=True)
    show_raw = st.toggle("Afficher les données brutes", value=False)

pdf = st.file_uploader("1) Upload ton relevé bancaire (PDF)", type=["pdf"])

if not pdf:
    st.info("Upload un PDF pour lancer l’analyse.")
    st.stop()

pdf_bytes = pdf.getvalue()

# --- Pipeline ---
with st.spinner("Extraction du contenu PDF..."):
    doc = extract_text_from_pdf_bytes(pdf_bytes)

with st.spinner("Parsing des transactions..."):
    txs = parse_transactions_from_text(doc.raw_text)

q = assess_quality(txs)
sanitized = sanitize_transactions(txs) if txs else []

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["Résumé", "Abonnements", "Catégories", "Détails & QA"])

# -------------- TAB 4 (QA & details) --------------
with tab4:
    st.subheader("Qualité d’extraction")
    c1, c2, c3 = st.columns(3)
    c1.metric("Pages", doc.num_pages)
    c2.metric("PDF texte", "Oui" if doc.is_text_pdf else "Non")
    c3.metric("Confidence", f"{int(q.confidence * 100)}%")

    if q.issues:
        st.warning("Points d’attention :\n- " + "\n- ".join(q.issues))
    else:
        st.success("Extraction OK.")

    if show_raw:
        st.subheader("Transactions (brutes)")
        if txs:
            df_raw = pd.DataFrame([{"date": t.date, "label_raw": t.label_raw, "amount": t.amount} for t in txs])
            st.dataframe(df_raw, use_container_width=True)
        else:
            st.info("Aucune transaction brute à afficher.")

    st.subheader("Transactions (anonymisées envoyées à l’IA)")
    if sanitized:
        st.dataframe(pd.DataFrame(sanitized), use_container_width=True)
    else:
        st.error("Aucune transaction détectée. Le parsing doit être amélioré pour ce format de relevé.")
        st.stop()

# -------------- IA call (once) --------------
api_key = st.secrets.get("OPENAI_API_KEY", "").strip()
if not api_key:
    st.error("Clé OpenAI manquante. Ajoute OPENAI_API_KEY dans Settings → Secrets.")
    st.stop()

with st.spinner("Analyse IA en cours..."):
    analysis = analyze_transactions_with_llm(
        sanitized,
        api_key=api_key,
        model=st.secrets.get("OPENAI_MODEL", "gpt-5-mini"),
    )

# -------------- TAB 1 (Summary) --------------
with tab1:
    st.subheader("Résumé")
    summary = analysis.get("summary", {})
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Dépenses", f"{summary.get('total_spend', 0):.2f} €")
    k2.metric("Revenus", f"{summary.get('total_income', 0):.2f} €")
    k3.metric("Net", f"{summary.get('net', 0):.2f} €")
    k4.metric("Transactions", int(summary.get("transaction_count", len(sanitized))))

    st.subheader("Priorités (actions)")
    actions = analysis.get("actions", [])
    if not actions:
        st.info("Aucune action proposée.")
    else:
        for a in actions:
            with st.container(border=True):
                st.markdown(f"**{a.get('title','Action')}**")
                st.caption(f"Impact estimé: {a.get('impact_estimate_eur_per_month', 0):.0f} €/mois")
                steps = a.get("steps", [])
                if steps:
                    st.markdown("**Étapes**")
                    for s in steps:
                        st.write(f"• {s}")
                notes = a.get("notes", "")
                if notes:
                    st.caption(notes)

    anomalies = analysis.get("anomalies", [])
    if anomalies:
        st.subheader("Anomalies / points à vérifier")
        for an in anomalies[:8]:
            with st.container(border=True):
                st.markdown(f"**{an.get('title','Point')}**")
                st.write(an.get("detail", ""))
                st.caption(f"Confiance: {an.get('confidence', 0):.2f}")

# -------------- TAB 2 (Subscriptions) --------------
with tab2:
    st.subheader("Abonnements détectés")
    subs = analysis.get("subscriptions", [])
    if not subs:
        st.info("Aucun abonnement détecté (ou confiance trop faible).")
    else:
        for s in subs:
            with st.container(border=True):
                st.markdown(f"**{s.get('merchant','Abonnement')}**")
                st.write(f"Montant typique: **{s.get('amount_typical', 0):.2f} €**")
                st.write(f"Fréquence: **{s.get('frequency','unknown')}** · Confiance: **{s.get('confidence',0):.2f}**")
                ev = s.get("evidence", "")
                if ev:
                    st.caption(ev)

# -------------- TAB 3 (Categories) --------------
with tab3:
    st.subheader("Catégories")
    cats = analysis.get("categories", [])
    if not cats:
        st.info("Pas de catégories.")
    else:
        df_c = pd.DataFrame(cats)
        # tri par total
        if "total" in df_c.columns:
            df_c = df_c.sort_values("total", ascending=True)
            st.bar_chart(df_c.set_index("category")["total"])
        st.dataframe(df_c, use_container_width=True)
