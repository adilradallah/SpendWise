from __future__ import annotations

import json
from typing import Any, Dict, List

from openai import OpenAI


def analyze_transactions_with_llm(
    transactions: List[Dict[str, Any]],
    api_key: str,
    model: str = "gpt-5-mini",
) -> Dict[str, Any]:
    """
    Copilote financier:
    - Abonnements
    - Catégories
    - Anomalies
    - Actions priorisées
    Retour en JSON propre.
    """

    client = OpenAI(api_key=api_key)

    system_prompt = """
Tu es Spendwise, copilote financier intelligent.
Tu reçois uniquement des transactions anonymisées (date, label, amount en EUR).
amount < 0 = dépense, amount > 0 = revenu.

Objectif:
1) Normaliser les marchands.
2) Détecter abonnements/récurrences (même si 1 occurrence, si très probable).
3) Catégoriser les dépenses et calculer les totaux et parts.
4) Détecter anomalies (doublons, libellé incohérent, montant inhabituel).
5) Proposer 5 à 10 actions priorisées, concrètes, orientées économies.

Règles:
- Réponds STRICTEMENT en JSON valide, sans texte autour.
- Si tu n’es pas sûr, mets une confidence plus faible.
- Ne demande pas d’infos personnelles.
"""

    user_payload = {
        "transactions": transactions,
        "output_schema": {
            "summary": {
                "period_start": "YYYY-MM-DD",
                "period_end": "YYYY-MM-DD",
                "total_spend": 0.0,
                "total_income": 0.0,
                "net": 0.0,
                "transaction_count": 0
            },
            "subscriptions": [
                {
                    "merchant": "string",
                    "amount_typical": 0.0,
                    "frequency": "weekly|monthly|quarterly|yearly|unknown",
                    "confidence": 0.0,
                    "evidence": "string"
                }
            ],
            "categories": [
                {"category": "string", "total": 0.0, "share": 0.0}
            ],
            "anomalies": [
                {"type": "string", "title": "string", "detail": "string", "confidence": 0.0}
            ],
            "actions": [
                {"title": "string", "impact_estimate_eur_per_month": 0.0, "steps": ["string"], "notes": "string"}
            ]
        }
    }

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    )

    content = resp.choices[0].message.content or ""

    # parse JSON robuste (au cas où le modèle entoure par du texte)
    try:
        return json.loads(content)
    except Exception:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end != -1:
            return json.loads(content[start:end])
        return {"error": "JSON parse failed", "raw_output": content}
