import streamlit as st
import pandas as pd

from src.extract_pdf import extract_text_from_pdf_bytes
from src.parse_transactions import parse_transactions_from_text
from src.quality import assess_quality
from src.privacy import sanitize_transactions
from src.llm_analyze import analyze_transactions_with_llm

st.set_page_config(page_title="Spendwise", page_icon="💳", layout="wide")

st.title("Spendwise 💳")
st.caption("Upload PDF → extraction → anonymisation → analyse → recommandations (MVP).")

pdf = st.file_uploader("Upload ton relevé bancaire (PDF)", type=["pdf"])

if pdf:
    pdf_bytes = pdf.getvalue()

    with st.spinner("Extraction du contenu PDF..."):
        doc = extract_text_from_pdf_bytes(pdf_bytes)

    st.write(f"Pages détectées : **{doc.num_pages}** · PDF texte : **{doc.is_text_pdf}**")

    with st.spinner("Parsing des transactions..."):
        txs = parse_transactions_from_text(doc.raw_text)

    q = assess_quality(txs)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Transactions détectées", len(txs))
        st.metric("Confidence score", f"{int(q.confidence*100)}%")

    with col2:
        if q.issues:
            st.warning("Points d’attention :\n- " + "\n- ".join(q.issues))
        else:
            st.success("Extraction OK (aucun problème détecté).")

    if txs:
        df = pd.DataFrame([{"date": t.date, "label_raw": t.label_raw, "amount": t.amount} for t in txs])
        st.subheader("Transactions (brutes)")
        st.dataframe(df, use_container_width=True)

        sanitized = sanitize_transactions(txs)
        st.subheader("Transactions (anonymisées)")
        st.dataframe(pd.DataFrame(sanitized), use_container_width=True)

        st.subheader("Analyse & recommandations (V0)")
        result = analyze_transactions_with_llm(sanitized)
        st.json(result)
