from __future__ import annotations

import re


IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
BIC_RE = re.compile(r"\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b")
ACCOUNT_NUM_RE = re.compile(r"\b\d{10,16}\b")


def sanitize_label(label: str) -> str:
    s = label
    s = IBAN_RE.sub("[IBAN_REDACTED]", s)
    s = BIC_RE.sub("[BIC_REDACTED]", s)
    s = ACCOUNT_NUM_RE.sub("[ACCOUNT_REDACTED]", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def sanitize_transactions(txs):
    """
    Input: list[Transaction] (date, label_raw, amount)
    Output: list[dict] minimal pour l'IA
    """
    out = []
    for t in txs:
        out.append({
            "date": t.date,
            "label": sanitize_label(t.label_raw),
            "amount": float(t.amount),
        })
    return out
