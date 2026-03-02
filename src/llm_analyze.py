from __future__ import annotations
from typing import Dict, List, Any


def analyze_transactions_with_llm(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    V0 : Pas encore branché à une vraie IA.
    On fait un résumé simple pour valider le pipeline complet.
    """

    total_spend = sum(t["amount"] for t in transactions if t["amount"] < 0)
    total_income = sum(t["amount"] for t in transactions if t["amount"] > 0)

    # Détection simple "pseudo récurrent" (même label plusieurs fois)
    label_counts = {}
    for t in transactions:
        label_counts[t["label"]] = label_counts.get(t["label"], 0) + 1

    potential_recurring = [
        {"label": label, "count": count}
        for label, count in label_counts.items()
        if count >= 2
    ]

    return {
        "summary": {
            "total_spend": round(total_spend, 2),
            "total_income": round(total_income, 2),
            "transaction_count": len(transactions),
        },
        "potential_recurring_transactions": potential_recurring,
        "subscriptions": [],
        "categories": [],
        "actions": [
            {
                "title": "Activer l’analyse IA avancée",
                "detail": "Brancher un modèle IA sur les transactions anonymisées pour détecter abonnements réels, catégories précises et recommandations optimisées."
            }
        ]
    }
