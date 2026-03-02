from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List
from dateutil import parser as dateparser


@dataclass
class Transaction:
    date: str           # ISO yyyy-mm-dd
    label_raw: str
    amount: float       # debit negative, credit positive


DATE_PATTERNS = [
    r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",  # 31/12/2024
    r"\b\d{4}[/-]\d{2}[/-]\d{2}\b",  # 2024-12-31
]

AMOUNT_PATTERN = r"[-+]?\d{1,3}(?:[ .]\d{3})*(?:[.,]\d{2})"


def parse_transactions_from_text(raw_text: str) -> List[Transaction]:
    """
    V0 parser heuristique :
    Détecte les lignes contenant une date + au moins un montant.
    """
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    txs: List[Transaction] = []

    date_regex = re.compile("|".join(DATE_PATTERNS))
    amount_regex = re.compile(AMOUNT_PATTERN)

    for line in lines:
        date_match = date_regex.search(line)
        amount_matches = amount_regex.findall(line)

        if not date_match or not amount_matches:
            continue

        date_str = date_match.group(0)
        amount_str = amount_matches[-1]

        iso_date = _to_iso_date(date_str)
        amount = _to_float(amount_str)

        # Nettoyage du label
        label = line
        label = label.replace(date_str, " ")
        for a in amount_matches:
            label = label.replace(a, " ")
        label = re.sub(r"\s+", " ", label).strip()

        # Heuristique simple signe
        signed_amount = amount
        if "-" in amount_str or re.search(r"\b(débit|debit)\b", line, re.IGNORECASE):
            signed_amount = -abs(amount)

        txs.append(Transaction(
            date=iso_date,
            label_raw=label,
            amount=signed_amount,
        ))

    return txs


def _to_iso_date(s: str) -> str:
    dt = dateparser.parse(s, dayfirst=True)
    if not dt:
        raise ValueError(f"Cannot parse date: {s}")
    return dt.date().isoformat()


def _to_float(s: str) -> float:
    # "1 234,56" -> 1234.56
    s2 = s.replace(" ", "").replace(".", "").replace(",", ".")
    return float(s2)
