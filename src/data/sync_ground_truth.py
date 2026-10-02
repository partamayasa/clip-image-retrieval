import json
import re
from pathlib import Path
import pandas as pd

from src import config

def sync_benchmark_ground_truth():
    json_path = config.GROUND_TRUTH_JSON_PATH
    csv_path = config.GROUND_TRUTH_CSV_PATH
    parquet_path = config.METADATA_CACHE_PATH

    from src.data.database import get_benchmark_ground_truth_dict, save_benchmark_ground_truth_to_db
    gt_data = get_benchmark_ground_truth_dict()
    if not gt_data and json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

    if not gt_data or not parquet_path.exists():
        print("Required ground truth or parquet cache not found!")
        return

    df = pd.read_parquet(parquet_path)
    print(f"Loaded {len(df)} products from {parquet_path}")

    def eval_criteria(row, crit):
        env = {
            "id": int(row["id"]),
            "gender": str(row.get("gender", "")),
            "articleType": str(row.get("articleType", "")),
            "baseColour": str(row.get("baseColour", "")),
            "usage": str(row.get("usage", "")),
            "masterCategory": str(row.get("masterCategory", "")),
            "subCategory": str(row.get("subCategory", "")),
        }
        # Clean any trailing comments in parentheses
        clean_crit = re.sub(r"\s*\([^)]*\)", "", crit).strip()
        expr = clean_crit.replace("&", " and ").replace("|", " or ")
        # convert `var contains 'Val'` to `'Val' in var`
        expr = re.sub(r"(\w+)\s+contains\s+([\'\"][^\'\"]+[\'\"])", r"\2 in \1", expr)
        try:
            return bool(eval(expr, {"__builtins__": None}, env))
        except Exception as e:
            print(f"Error evaluating '{expr}': {e}")
            return False

    changes = []
    total_added = 0

    for q_id, q_info in gt_data.items():
        crit = q_info["relevance_criteria"]
        old_ids = list(q_info["relevant_product_ids"])
        old_set = set(old_ids)

        matching_rows = [r for _, r in df.iterrows() if eval_criteria(r, crit)]
        new_ids = sorted([int(r["id"]) for r in matching_rows])
        new_set = set(new_ids)

        added = new_set - old_set
        removed = old_set - new_set

        q_info["total_relevant_answers"] = len(new_ids)
        q_info["relevant_product_ids"] = new_ids

        total_added += len(added)
        changes.append({
            "id": q_id,
            "query": q_info["query_text"],
            "old_count": len(old_ids),
            "new_count": len(new_ids),
            "added": len(added),
            "removed": len(removed),
        })

    # Save updated JSON if present as backup
    if json_path.exists():
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(gt_data, f, indent=2)
        print(f"Successfully updated {json_path} with exhaustive criteria matching!")

    # Rebuild CSV if present
    if csv_path.exists():
        rows = []
        meta_map = df.set_index("id").to_dict("index")
        for q_id, q_info in gt_data.items():
            for prod_id in q_info["relevant_product_ids"]:
                m = meta_map.get(prod_id, {})
                try:
                    rel_img_path = str((config.IMAGES_DIR / f"{prod_id}.jpg").relative_to(config.PROJECT_ROOT)).replace("\\", "/")
                except ValueError:
                    rel_img_path = f"data/dataset/images/{prod_id}.jpg"

                rows.append({
                    "query_id": q_id,
                    "query_text": q_info["query_text"],
                    "specificity_level": q_info["specificity"],
                    "relevant_product_id": prod_id,
                    "product_name": m.get("productDisplayName", ""),
                    "category": f"{m.get('masterCategory', '')} / {m.get('articleType', '')}",
                    "base_colour": m.get("baseColour", ""),
                    "gender": m.get("gender", ""),
                    "usage": m.get("usage", ""),
                    "relevance_label": 1,
                    "image_path": rel_img_path,
                })

        out_df = pd.DataFrame(rows)
        out_df.to_csv(csv_path, index=False)
        print(f"Successfully regenerated {csv_path} with {len(out_df)} relevance rows.")

    # Update subset_criteria.json with exact ground truth unique count
    criteria_path = config.PROCESSED_DATA_DIR / "subset_criteria.json"
    unique_gt_ids = set()
    for q_info in gt_data.values():
        unique_gt_ids.update(q_info.get("relevant_product_ids", []))

    if criteria_path.exists():
        try:
            with open(criteria_path, "r", encoding="utf-8") as f:
                criteria = json.load(f)
            criteria["ground_truth_products_count"] = len(unique_gt_ids)
            distractor_count = max(0, criteria.get("subset_eval_size", len(df)) - len(unique_gt_ids))
            criteria["distractor_products_count"] = distractor_count
            with open(criteria_path, "w", encoding="utf-8") as f:
                json.dump(criteria, f, indent=2)
            print(f"Updated {criteria_path}: {len(unique_gt_ids)} ground truth products + {distractor_count} distractors.")
        except Exception as e:
            print(f"Warning: Could not update subset_criteria.json: {e}")

    try:
        save_benchmark_ground_truth_to_db(gt_data)
        print("Successfully synchronized benchmark queries and ground truth into SQLite database!")
    except Exception as e:
        print(f"Warning: Could not sync to SQLite: {e}")

    for ch in changes:
        if ch["added"] > 0 or ch["removed"] > 0:
            print(f"{ch['id']} ({ch['query']}): {ch['old_count']} -> {ch['new_count']} (+{ch['added']}, -{ch['removed']})")

if __name__ == "__main__":
    sync_benchmark_ground_truth()
