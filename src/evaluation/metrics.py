import re
from typing import List, Dict, Any, Set
import numpy as np


def eval_relevance_criteria(item: Dict[str, Any], criteria_str: str) -> bool:
    """Evaluates Boolean logic string against item attributes safely and deterministically."""
    if not criteria_str:
        return False
    env = {
        "id": int(item.get("id", -1)),
        "gender": str(item.get("gender", "")),
        "articleType": str(item.get("articleType", "")),
        "baseColour": str(item.get("baseColour", "")),
        "usage": str(item.get("usage", "")),
        "masterCategory": str(item.get("masterCategory", "")),
        "subCategory": str(item.get("subCategory", "")),
    }
    clean_crit = re.sub(r"\s*\([^)]*\)", "", criteria_str).strip()
    expr = clean_crit.replace("&", " and ").replace("|", " or ")
    expr = re.sub(r"(\w+)\s+contains\s+([\'\"][^\'\"]+[\'\"])", r"\2 in \1", expr)
    try:
        return bool(eval(expr, {"__builtins__": None}, env))
    except Exception:
        return False


def is_item_relevant(item: Dict[str, Any], query_spec: Dict[str, Any]) -> bool:
    """
    Evaluates whether a retrieved product matches query ground-truth criteria.
    1. Checks explicit relevant_ids membership if available.
    2. Falls back to evaluating query_spec['relevance_criteria'] expression.
    3. Falls back to checking individual attribute criteria (target_types, color, gender, usage).
    """
    if "relevant_ids" in query_spec and query_spec["relevant_ids"]:
        item_id = int(item.get("id", -1))
        if item_id in query_spec["relevant_ids"]:
            return True
        if "relevance_criteria" in query_spec and query_spec["relevance_criteria"]:
            return eval_relevance_criteria(item, query_spec["relevance_criteria"])
        return False

    if "relevance_criteria" in query_spec and query_spec["relevance_criteria"]:
        if eval_relevance_criteria(item, query_spec["relevance_criteria"]):
            return True

    if "target_types" in query_spec and query_spec["target_types"]:
        if item.get("articleType") not in query_spec["target_types"]:
            return False

    if "color" in query_spec and query_spec["color"]:
        item_color = str(item.get("baseColour", "")).lower()
        target_color = str(query_spec["color"]).lower()
        if target_color not in item_color:
            return False

    if "gender" in query_spec and query_spec["gender"]:
        item_gender = str(item.get("gender", "")).lower()
        target_gender = str(query_spec["gender"]).lower()
        # Allow Unisex as valid match for Men or Women
        if item_gender != target_gender and item_gender != "unisex":
            return False

    if "usage" in query_spec and query_spec["usage"]:
        item_usage = str(item.get("usage", "")).lower()
        target_usage = str(query_spec["usage"]).lower()
        if target_usage not in item_usage:
            return False

    return True


def precision_at_k(retrieved_items: List[Dict[str, Any]], query_spec: Dict[str, Any], k: int) -> float:
    """Precision@K = (# of relevant items in top K) / K"""
    top_k = retrieved_items[:k]
    if not top_k:
        return 0.0
    relevant_count = sum(1 for item in top_k if is_item_relevant(item, query_spec))
    return relevant_count / len(top_k)


def recall_at_k(retrieved_items: List[Dict[str, Any]], query_spec: Dict[str, Any], total_relevant: int, k: int) -> float:
    """Recall@K = (# of relevant items in top K) / (total relevant in dataset)"""
    if total_relevant <= 0:
        return 0.0
    top_k = retrieved_items[:k]
    relevant_count = sum(1 for item in top_k if is_item_relevant(item, query_spec))
    return min(1.0, relevant_count / total_relevant)


def reciprocal_rank(retrieved_items: List[Dict[str, Any]], query_spec: Dict[str, Any]) -> float:
    """RR = 1 / rank of first relevant item (or 0 if none found)"""
    for idx, item in enumerate(retrieved_items, start=1):
        if is_item_relevant(item, query_spec):
            return 1.0 / idx
    return 0.0


def ndcg_at_k(retrieved_items: List[Dict[str, Any]], query_spec: Dict[str, Any], k: int) -> float:
    """Normalized Discounted Cumulative Gain at K (binary relevance)."""
    top_k = retrieved_items[:k]
    if not top_k:
        return 0.0

    dcg = 0.0
    for idx, item in enumerate(top_k, start=1):
        rel = 1 if is_item_relevant(item, query_spec) else 0
        dcg += rel / np.log2(idx + 1)

    # Ideal DCG (all relevant items first)
    total_relevant = sum(1 for item in top_k if is_item_relevant(item, query_spec))
    idcg = sum(1.0 / np.log2(idx + 1) for idx in range(1, total_relevant + 1))

    return (dcg / idcg) if idcg > 0 else 0.0


def attribute_match_breakdown(retrieved_items: List[Dict[str, Any]], query_spec: Dict[str, Any], k: int) -> Dict[str, float]:
    """Computes fine-grained attribute match rates (Color %, Category %, Gender %)."""
    top_k = retrieved_items[:k]
    if not top_k:
        return {"category_acc": 0.0, "color_acc": 0.0, "gender_acc": 0.0}

    cat_matches = 0
    color_matches = 0
    gender_matches = 0

    target_types = query_spec.get("target_types", [])
    target_color = str(query_spec.get("color", "")).lower()
    target_gender = str(query_spec.get("gender", "")).lower()

    for item in top_k:
        if target_types and item.get("articleType") in target_types:
            cat_matches += 1
        if target_color and target_color in str(item.get("baseColour", "")).lower():
            color_matches += 1
        if target_gender:
            item_g = str(item.get("gender", "")).lower()
            if item_g == target_gender or item_g == "unisex":
                gender_matches += 1

    n = len(top_k)
    return {
        "category_match_rate": round(cat_matches / n, 4) if target_types else 1.0,
        "color_match_rate": round(color_matches / n, 4) if target_color else 1.0,
        "gender_match_rate": round(gender_matches / n, 4) if target_gender else 1.0,
    }
