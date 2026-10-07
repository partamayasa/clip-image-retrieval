import json
import logging
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from PIL import Image

from src import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class EDAAnalyzer:
    """Performs Exploratory Data Analysis (EDA) on the fashion dataset subset."""

    def __init__(self, subset_path: Path = config.SUBSET_1500_PATH, images_dir: Path = config.IMAGES_DIR):
        self.subset_path = Path(subset_path)
        self.images_dir = Path(images_dir)

    def run_analysis(self) -> Dict[str, Any]:
        """Runs complete EDA and generates statistical breakdowns and retrieval insights."""
        if not self.subset_path.exists():
            raise FileNotFoundError(f"Subset file not found at: {self.subset_path}")

        df = pd.read_csv(self.subset_path)
        logger.info(f"Running EDA on subset: {self.subset_path} ({len(df)} records)")

        # 1. Overview and Completeness
        completeness = {col: f"{(1 - df[col].isna().mean()) * 100:.1f}%" for col in df.columns}

        # 2. Distributions
        dist_article_type = df["articleType"].value_counts().to_dict()
        dist_color = df["baseColour"].value_counts().head(10).to_dict()
        dist_gender = df["gender"].value_counts().to_dict()
        dist_usage = df["usage"].value_counts().to_dict()

        # 3. Visual Verification of 20 Representative Catalog Mode Samples (Lampiran A)
        # Dynamically fetched from SQLite database
        from src.data.database import get_audit_samples, get_retrieval_insights, save_eda_report_to_db
        audit_samples_meta = get_audit_samples()

        # Load clean dataset or current df to enrich each audit sample
        clean_styles_df = None
        clean_styles_path = config.PROCESSED_DATA_DIR / "clean_styles.csv"
        if clean_styles_path.exists():
            clean_styles_df = pd.read_csv(clean_styles_path)

        verification_samples = []
        for audit in audit_samples_meta:
            prod_id = audit["id"]
            row_match = df[df["id"] == prod_id]
            if row_match.empty and clean_styles_df is not None:
                row_match = clean_styles_df[clean_styles_df["id"] == prod_id]

            if not row_match.empty:
                row = row_match.iloc[0]
                master_cat = str(row.get("masterCategory", audit.get("masterCategory", "Apparel")))
                art_type = str(row.get("articleType", audit.get("articleType", "Tshirts")))
                gender = str(row.get("gender", audit.get("gender", "Men")))
                colour = str(row.get("baseColour", audit.get("baseColour", "Blue")))
                usage = str(row.get("usage", audit.get("usage", "Sports")))
                prod_name = str(row.get("productDisplayName", audit.get("productDisplayName", "")))
            else:
                master_cat = audit.get("masterCategory", "Apparel")
                art_type = audit.get("articleType", "Tshirts")
                gender = audit.get("gender", "Men")
                colour = audit.get("baseColour", "Blue")
                usage = audit.get("usage", "Sports")
                prod_name = audit.get("productDisplayName", "")

            img_path = self.images_dir / f"{prod_id}.jpg"
            img_exists = img_path.exists()
            img_size = "Unknown"
            if img_exists:
                try:
                    with Image.open(img_path) as img:
                        img_size = f"{img.width}x{img.height}"
                except Exception:
                    img_size = "Corrupted"

            verification_samples.append({
                "no": audit["no"],
                "id": prod_id,
                "image_filename": f"{prod_id}.jpg",
                "image_exists": img_exists,
                "resolution": img_size,
                "productDisplayName": prod_name,
                "masterCategory": master_cat,
                "articleType": art_type,
                "gender": gender,
                "baseColour": colour,
                "usage": usage,
                "validation_status": audit.get("validation_status", audit.get("status_validasi", "Consistent")),
                "finding_rationale": audit.get("finding_rationale", audit.get("alasan_temuan", "")),
            })

        # 4. Retrieval Insights (5 Humanized Research Insights)
        # Dynamically fetched from SQLite database
        insights = get_retrieval_insights()

        # 5. Multivariate & Co-occurrence Analysis
        from src.data.multivariate import MultivariateAnalyzer
        try:
            multivariate_analyzer = MultivariateAnalyzer(subset_path=self.subset_path)
            multivariate_report = multivariate_analyzer.run_full_analysis()
            logger.info("Successfully computed Multivariate & Co-occurrence metrics.")
        except Exception as e:
            logger.warning(f"Could not compute multivariate analysis: {e}")
            multivariate_report = None

        report = {
            "dataset_file": str(self.subset_path.name),
            "total_records": len(df),
            "metadata_completeness": completeness,
            "distribution_articleType": dist_article_type,
            "distribution_baseColour_top10": dist_color,
            "distribution_gender": dist_gender,
            "distribution_usage": dist_usage,
            "visual_verification_20_pairs": verification_samples[:20],
            "insights": insights,
            "multivariate_analysis": multivariate_report,
        }

        # Save EDA Report directly to SQLite database
        try:
            save_eda_report_to_db(report)
            logger.info("Saved EDA report directly into SQLite database.")
        except Exception as e:
            logger.warning(f"Could not persist EDA report to SQLite: {e}")

        # Also write JSON cache to disk
        try:
            cache_file = config.PROCESSED_DATA_DIR / "eda_report.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Saved EDA report cache to {cache_file}")
        except Exception as e:
            logger.warning(f"Could not write eda_report.json: {e}")

        return report


if __name__ == "__main__":
    analyzer = EDAAnalyzer()
    report = analyzer.run_analysis()
    print("EDA execution successful. Report saved to database.")
