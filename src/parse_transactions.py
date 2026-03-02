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


# Dates possibles dans les relevés FR:
# - 22.12 (BNP)
# - 22/12/2025
# - 2025-12-22
DATE_PATTERNS = [
    r"\b\d{2}\.\d{2}\b",                # 22.12
    r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",     # 22/12/2025
    r"\b\d{4}[/-]\d{2}[/-]\d{2}\b",     # 2025-12-22
]

# Montants typiques dans ce relevé (virgule décimale)
# Ex: 11,99  | 1 234,56 | 900,00
AMOUNT_PATTERN = r"[-+]?\d{1,3}(?:[ .]\d{3})*(?:,\d{2})"

# Période BNP (texte)
# "du 21 décembre 2025 au 21 janvier 2026"
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

    # Détecte la période pour déduire l’année quand on a des dates "dd.mm"
    period = _extract_statement_period(raw_text)  # (start_year, start_month, end_year, end_month) ou None

    date_regex = re.compile("|".join(DATE_PATTERNS))
    amount_regex = re.compile(AMOUNT_PATTERN)

    txs: List[Transaction] = []

    for line in lines:
        # On cherche une date + un montant (sinon ce n’est pas une transaction)
        date_tokens = date_regex.findall(line)
        amount_tokens = amount_regex.findall(line)

        if not date_tokens or not amount_tokens:
            continue

        # BNP met souvent 2 dates en début de ligne (date op + date valeur)
        # On prend la 1ère comme date opération
        op_date_token = date_tokens[0]

        # On prend le 1er montant qui ressemble à un montant (souvent juste après les dates)
        amount_token = amount_tokens[0]

        iso_date = _to_iso_date(op_date_token, period)
        amount = _to_float(amount_token)

        # Nettoie label : supprime dates + montants trouvés
        label = line
        for d in date_tokens:
            label = label.replace(d, " ")
        for a in amount_tokens:
            label = label.replace(a, " ")
        label = re.sub(r"\s+", " ", label).strip()

        # Heuristique de signe:
        # - par défaut: débit (négatif) car souvent colonne "Débit" collée au texte
        # - si on détecte un pattern de crédit
        signed_amount = -abs(amount)

        if _looks_like_credit(line):
            signed_amount = abs(amount)

        txs.append(Transaction(date=iso_date, label_raw=label, amount=signed_amount))

    return txs


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
            start_year, start_month, end_year, end_month = period

            # Si période sur 2 années (ex: déc 2025 -> jan 2026)
            if start_year != end_year:
                # règle simple: mois >= mois début => année début, sinon année fin
                year = start_year if month >= start_month else end_year
            else:
                year = start_year

        # fallback si on ne trouve pas la période: année courante (moins bien)
        if year is None:
            year = dateparser.parse("today").year

        return f"{year:04d}-{month:02d}-{day:02d}"

    # Autres formats avec année
    dt = dateparser.parse(date_token, dayfirst=True)
    if not dt:
        raise ValueError(f"Cannot parse date: {date_token}")
    return dt.date().isoformat()


def _to_float(s: str) -> float:
    # "1 234,56" -> 1234.56
    s2 = s.replace(" ", "").replace(".", "").replace(",", ".")
    return float(s2)


def _looks_like_credit(line: str) -> bool:
    # Heuristiques simples pour détecter des entrées crédit
    # (à améliorer plus tard avec des règles par banque)
    credit_keywords = [
        "SALAIRE", "VIR RECU", "VIREMENT RECU", "REMBOURSEMENT", "VERSEMENT",
        "CREDIT", "CRÉDIT", "INTERETS", "INTÉRÊTS", "REMBT", "REMISE",
    ]
    up = line.upper()
    return any(k in up for k in credit_keywords)
