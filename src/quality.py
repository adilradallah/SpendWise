from dataclasses import dataclass
from typing import List
from dateutil import parser as dateparser


@dataclass
class QualityReport:
    confidence: float
    issues: List[str]


def assess_quality(txs) -> QualityReport:
    issues = []
    n = len(txs)

    if n == 0:
        return QualityReport(0.0, ["Aucune transaction détectée."])

    if n < 5:
        issues.append("Peu de transactions détectées.")

    dates = []
    for t in txs:
        try:
            dates.append(dateparser.parse(t.date).date())
        except:
            issues.append("Dates invalides.")
            break

    confidence = 1.0
    if issues:
        confidence -= 0.3

    confidence = max(0.0, min(1.0, confidence))
    return QualityReport(confidence, issues)
