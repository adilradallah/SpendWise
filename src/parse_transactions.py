from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from dateutil import parser as dateparser


@dataclass
class Transaction:
    date: str
    label_raw: str
    amount: float


DATE_PATTERNS = [
    r"\b\d{2}\.\d{2}\b",                # 22.12 (BNP)
    r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",     # 22/12/2025
    r"\b\d{4}[/-]\d{2}[/-]\d{2}\b",     # 2025-12-22
]

# Montants: accepte , OU . en décimal (et espaces/points en milliers)
AMOUNT_PATTERN = r"[-+]?\d{1,3}(?:[ .]\d{3})*(?:[.,]\d{2})"

# Période BNP (utile pour déduire l’année quand date=dd.mm)
PERIOD_PATTERN = re.compile(
    r"du\s+(\d{1,2})\s+([a-zA-Zéèêëàâîïôöùûüç]+)\s+(\d{4})\s+au\s+(\d{1,2})\s+([a-zA-Zéèêëàâîïôöùûüç]+)\s+(\d{4})",
    re.IGNORECASE,
)

FR_MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}


def parse_transactions_from_text(raw_text: str) -> List[Transaction]:
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    period = _extract_statement_period(raw_text)  # (start_year, start_month, end_year, end_month) or None

    date_regex = re.compile("|".join(DATE_PATTERNS))
    amount_regex = re.compile(AMOUNT_PATTERN)

    txs: List[Transaction] = []

    for line in lines:
        date_tokens = date_regex.findall(line)
        amount_tokens = amount_regex.findall(line)

        if not date_tokens or not amount_tokens:
            continue

        # 1) BNP: souvent 2 dates (op + valeur)
        op_date_token = date_tokens[0]
        iso_date = _to_iso_date(op_date_token, period)

        # 2) Retire les "montants" qui sont en fait des dates dd.mm (ex: 22.12)
        date_set = set(date_tokens)
        amount_candidates = [a for a in amount_tokens if a not in date_set]

        # Si jamais la date a été capturée autrement, on retire aussi tout ce qui ressemble à dd.mm
        amount_candidates = [a for a in amount_candidates if not re.fullmatch(r"\d{2}\.\d{2}", a)]

        if not amount_candidates:
            continue

        # 3) Choisir le bon montant si plusieurs (débit/crédit/solde)
        # Heuristique: on prend le candidat avec la plus petite valeur absolue (souvent la transaction, pas le solde)
        floats = []
        for a in amount_candidates:
            try:
                floats.append((_to_float_robust(a), a))
            except Exception:
                pass

        if not floats:
            continue

        amount_value, amount_token = min(floats, key=lambda x: abs(x[0]))

        # 4) Nettoyage du label (retire dates + montants)
        label = line
        for d in date_tokens:
            label = label.replace(d, " ")
        for a in amount_tokens:
            label = label.replace(a, " ")
        label = re.sub(r"\s+", " ", label).strip()

        # Filtrer récap/solde
        up_label = label.upper()
        if "SOLDE" in up_label or "TOTAL" in up_label:
            continue

        # 5) Signe (heuristique simple)
        signed_amount = -abs(amount_value)
        if _looks_like_credit(line):
            signed_amount = abs(amount_value)

        txs.append(Transaction(date=iso_date, label_raw=label, amount=signed_amount))

    # 6) Dédoublonnage strict (même date + label + montant)
    unique = {}
    for t in txs:
        key = (t.date, t.label_raw, round(float(t.amount), 2))
        unique[key] = t

    return list(unique.values())


def _extract_statement_period(raw_text: str) -> Optional[Tuple[int, int, int, int]]:
    m = PERIOD_PATTERN.search(raw_text)
    if not m:
        return None

    _, start_month_name, start_year, _, end_month_name, end_year = m.groups()

    sm = FR_MONTHS.get(start_month_name.lower())
    em = FR_MONTHS.get(end_month_name.lower())
    if not sm or not em:
        return None

    return int(start_year), sm, int(end_year), em


def _to_iso_date(date_token: str, period: Optional[Tuple[int, int, int, int]]) -> str:
    # Cas BNP: "22.12" (sans année)
    if re.fullmatch(r"\d{2}\.\d{2}", date_token):
        day = int(date_token[:2])
        month = int(date_token[3:5])

        year = None
        if period:
            start_year, start_month, end_year, _ = period
            if start_year != end_year:
                year = start_year if month >= start_month else end_year
            else:
                year = start_year

        if year is None:
            year = dateparser.parse("today").year

        return f"{year:04d}-{month:02d}-{day:02d}"

    dt = dateparser.parse(date_token, dayfirst=True)
    if not dt:
        raise ValueError(f"Cannot parse date: {date_token}")
    return dt.date().isoformat()


def _to_float_robust(s: str) -> float:
    """
    Gère:
    - 1 234,56
    - 1 234.56
    - 1234,56
    - 1234.56
    """
    s = s.strip().replace(" ", "")
    sign = -1 if s.startswith("-") else 1
    s = s.lstrip("+-")

    has_comma = "," in s
    has_dot = "." in s

    if has_comma and has_dot:
        # le dernier séparateur est le décimal
        if s.rfind(",") > s.rfind("."):
            dec, thousands = ",", "."
        else:
            dec, thousands = ".", ","
        s = s.replace(thousands, "")
        s = s.replace(dec, ".")
        return sign * float(s)

    if has_comma:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
            s = s.replace(".", "")
            s = s.replace(",", ".")
            return sign * float(s)
        s = s.replace(",", "")
        return sign * float(s)

    if has_dot:
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 2:
            s = s.replace(",", "")
            return sign * float(s)
        s = s.replace(".", "")
        return sign * float(s)

    return sign * float(s)


def _looks_like_credit(line: str) -> bool:
    credit_keywords = [
        "SALAIRE", "VIR RECU", "VIREMENT RECU", "REMBOURSEMENT", "VERSEMENT",
        "CREDIT", "CRÉDIT", "INTERETS", "INTÉRÊTS", "REMISE",
    ]
    up = line.upper()
    return any(k in up for k in credit_keywords)
