from __future__ import annotations

from dataclasses import dataclass
from typing import List
from dateutil import parser as dateparser


@dataclass
class QualityReport:
    confidence: float
    issues: List[str]


def assess_quality(txs) -> QualityReport:
    issues: List[str] = []
    n = len(txs)

    if n == 0:
        return QualityReport(confidence=0.0, issues=["Aucune transaction détectée."])

    if n < 5:
        issues.append("Peu de transactions détectées (moins de 5).")

    # Cohérence dates
    dates = []
    for t in txs:
        try:
            dates.append(dateparser.parse(t.date).date())
        except Exception:
            issues.append("Certaines dates ne sont pas parseables.")
            break

    if dates:
        span_days = (max(dates) - min(dates)).days
        if span_days > 370:
            issues.append("Période détectée très longue (> 12 mois). Parsing possiblement incorrect.")
        if span_days < 1 and n > 20:
            issues.append("Beaucoup de transactions sur une période très courte. Parsing possiblement incorrect.")

    # Montants
    zeros = sum(1 for t in txs if abs(float(t.amount)) < 1e-9)
    if zeros / n > 0.2:
        issues.append("Trop de montants à 0.00 (parsing suspect).")

    # Confidence simple (V0)
    confidence = 1.0
    if any("Aucune transaction" in i for i in issues):
        confidence -= 0.50
    if any("Peu de transactions" in i for i in issues):
        confidence -= 0.15
    if any("Parsing possiblement incorrect" in i for i in issues):
        confidence -= 0.20
    if any("0.00" in i for i in issues):
        confidence -= 0.10

    confidence = max(0.0, min(1.0, confidence))
    return QualityReport(confidence=confidence, issues=issues)
