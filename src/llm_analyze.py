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
    Retourne un JSON calibré pour une UI:
    - actions max 6 (courtes, concrètes)
    - abonnements clairs
    - catégories triées
    - anomalies limitées
    """

    client = OpenAI(api_key=api_key)

    system = """
Tu es Spendwise, copilote financier.
Tu reçois des transactions anonymisées (date, label, amount en EUR).
amount < 0 = dépense ; amount > 0 = revenu.

Objectifs:
1) Résumer la période et les totaux.
2) Détecter les abonnements/récurrences (même 1 occurrence si très probable).
3) Catégoriser les dépenses (10-14 catégories max) et calculer total + part (0..1).
4) Détecter anomalies (doublons, libellé incohérent, dépenses atypiques) max 6.
5) Proposer 4 à 6 actions prioritaires, très concrètes, avec étapes courtes.

Contraintes UI:
- Tout en FR.
- Phrases courtes.
- Pas de blabla.
- Réponds STRICTEMENT en JSON valide, sans texte autour.
"""

    user = {
        "transactions": transactions,
        "schema": {
            "summary": {
                "period_start": "YYYY-MM-DD",
                "period_end": "YYYY-MM-DD",
                "total_spend": 0.0,
                "total_income": 0.0,
                "net": 0.0,
                "transaction_count": 0
            },
            "subscriptions": [
                {"merchant": "string", "amount_typical": 0.0, "frequency": "weekly|monthly|quarterly|yearly|unknown", "confidence": 0.0, "evidence": "string"}
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

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system.strip()},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
        )
        content = resp.choices[0].message.content or ""

        # Parse robuste
        try:
            out = json.loads(content)
        except Exception:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != -1:
                out = json.loads(content[start:end])
            else:
                return {"error": "JSON parse failed", "raw_output": content}

        # Post-calibrage UI (tri + limites)
        out["subscriptions"] = (out.get("subscriptions") or [])[:12]
        cats = out.get("categories") or []
        try:
            cats = sorted(cats, key=lambda x: float(x.get("total", 0)), reverse=True)
        except Exception:
            pass
        out["categories"] = cats[:14]
        out["anomalies"] = (out.get("anomalies") or [])[:6]
        out["actions"] = (out.get("actions") or [])[:6]
        return out

    except Exception as e:
        return {"error": str(e)}
