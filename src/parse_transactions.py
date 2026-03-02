import re
from dataclasses import dataclass
from typing import List
from dateutil import parser as dateparser


@dataclass
class Transaction:
    date: str
    label_raw: str
    amount: float


DATE_PATTERNS = [
    r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",
    r"\b\d{4}[/-]\d{2}[/-]\d{2}\b",
]

AMOUNT_PATTERN = r"[-+]?\d{1,3}(?:[ .]\d{3})*(?:[.,]\d{2})"


def parse_transactions_from_text(raw_text: str) -> List[Transaction]:
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    txs = []

    date_regex = re.compile("|".join(DATE_PATTERNS))
    amount_regex = re.compile(AMOUNT_PATTERN)

    for line in lines:
        date_match = date_regex.search(line)
        amount_matches = amount_regex.findall(line)

        if not date_match or not amount_matches:
            continue

        date_str = date_match.group(0)
        amount_str = amount_matches[-1]

        try:
            iso_date = dateparser.parse(date_str, dayfirst=True).date().isoformat()
        except:
            continue

        amount = float(amount_str.replace(" ", "").replace(".", "").replace(",", "."))

        label = line
        label = label.replace(date_str, " ")
        for a in amount_matches:
            label = label.replace(a, " ")
        label = re.sub(r"\s+", " ", label).strip()

        signed_amount = -abs(amount) if "-" in amount_str else amount

        txs.append(Transaction(date=iso_date, label_raw=label, amount=signed_amount))

    return txs
