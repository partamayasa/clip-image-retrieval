import json
from pathlib import Path
import pandas as pd

from src import config

def build_csv():
    from src.data.database import get_benchmark_ground_truth_dict
    data = get_benchmark_ground_truth_dict()
    if not data:
        json_path = config.GROUND_TRUTH_JSON_PATH
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            print("No ground truth found in database or JSON!")
            return

    styles_df = pd.read_csv(config.STYLES_CSV_PATH, on_bad_lines="skip")
    styles_df["id"] = pd.to_numeric(styles_df["id"], errors="coerce").dropna().astype(int)
    meta_map = styles_df.set_index("id").to_dict("index")

    rows = []
    for q_id, q_info in data.items():
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
    csv_path = config.GROUND_TRUTH_CSV_PATH
    out_df.to_csv(csv_path, index=False)
    print(f"Generated {csv_path} with {len(out_df)} relevance rows.")

if __name__ == "__main__":
    build_csv()
