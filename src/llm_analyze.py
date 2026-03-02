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
    Envoie les transactions anonymisées à l'IA
    et retourne une analyse structurée.
    """

    client = OpenAI(api_key=api_key)

    system_prompt = """
Tu es un analyste financier intelligent.
Tu reçois une liste de transactions bancaires anonymisées.

Ta mission :
1. Identifier les abonnements récurrents.
2. Regrouper les dépenses par catégorie.
3. Identifier les dépenses élevées ou inhabituelles.
4. Proposer des recommandations concrètes d'optimisation.

Réponds STRICTEMENT en JSON valide avec ce format :

{
  "subscriptions": [],
  "categories": {},
  "unusual_expenses": [],
  "recommendations": []
}
"""

    user_prompt = f"""
Voici les transactions (format JSON) :

{json.dumps(transactions, ensure_ascii=False)}

Analyse-les.
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content

        # Sécurisation : si l'IA renvoie du texte autour du JSON
        try:
            return json.loads(content)
        except Exception:
            # tentative d'extraction JSON si entouré de texte
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(content[start:end])
            else:
                return {
                    "error": "Impossible de parser la réponse IA",
                    "raw_output": content,
                }

    except Exception as e:
        return {
            "error": str(e)
        }
