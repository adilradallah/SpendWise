from typing import Dict, List, Any
from openai import OpenAI
import json


def analyze_transactions_with_llm(
    transactions: List[Dict[str, Any]],
    *,
    api_key: str,
    model: str,
) -> Dict[str, Any]:

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "Tu es Spendwise, un analyste financier. "
        "Tu reçois des transactions anonymisées (date, label, amount). "
        "Detecte abonnements, catégories, anomalies et recommandations actionnables. "
        "Retourne uniquement du JSON valide."
    )

    user_prompt = json.dumps({
        "transactions": transactions,
        "rules": "amount < 0 = dépense, amount > 0 = revenu"
    })

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    return json.loads(content)
