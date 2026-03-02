import re


IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
ACCOUNT_NUM_RE = re.compile(r"\b\d{10,16}\b")


def sanitize_label(label: str) -> str:
    s = IBAN_RE.sub("[IBAN]", label)
    s = ACCOUNT_NUM_RE.sub("[ACCOUNT]", s)
    return re.sub(r"\s+", " ", s).strip()


def sanitize_transactions(txs):
    return [
        {
            "date": t.date,
            "label": sanitize_label(t.label_raw),
            "amount": float(t.amount),
        }
        for t in txs
    ]
