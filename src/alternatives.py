from __future__ import annotations

import json
from typing import Any, Dict, List


def load_catalog(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def build_alternatives(subscriptions: List[Dict[str, Any]], catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Pour chaque abonnement détecté:
    - match via keywords (merchant)
    - propose alternatives du catalogue
    - calcule économie estimée (vs amount_typical)
    """
    groups = catalog.get("groups", [])
    results = []

    for sub in subscriptions:
        merchant = sub.get("merchant", "")
        amount = float(sub.get("amount_typical", 0) or 0)
        m = _norm(merchant)

        best_group = None
        for g in groups:
            keywords = [k.lower() for k in g.get("keywords", [])]
            if any(k in m for k in keywords):
                best_group = g
                break

        offers_out = []
        if best_group:
            offers = best_group.get("offers", [])
            for o in offers:
                price = float(o.get("price_eur_per_month", 0) or 0)
                saving = round(max(0.0, amount - price), 2) if amount > 0 and price > 0 else 0.0
                offers_out.append({
                    "name": o.get("name", ""),
                    "type": o.get("type", best_group.get("group", "")),
                    "price_eur_per_month": price,
                    "why": o.get("why", ""),
                    "url": o.get("url", ""),
                    "estimated_saving_eur_per_month": saving,
                })

            # tri par économie puis prix
            offers_out.sort(key=lambda x: (-float(x["estimated_saving_eur_per_month"]), float(x["price_eur_per_month"])))

        results.append({
            "current": sub,
            "group": best_group.get("group") if best_group else None,
            "offers": offers_out[:8],
        })

    return results
