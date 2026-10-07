import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
from PIL import Image
from tqdm import tqdm

from src import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class DatasetValidator:
    """Validates raw dataset metadata and image integrity."""

    def __init__(self, styles_path: Path = config.STYLES_CSV_PATH, images_dir: Path = config.IMAGES_DIR):
        self.styles_path = Path(styles_path)
        self.images_dir = Path(images_dir)

    def load_raw_metadata(self) -> pd.DataFrame:
        """Loads styles.csv safely, skipping malformed lines."""
        if not self.styles_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.styles_path}")

        logger.info(f"Loading raw metadata from: {self.styles_path}")
        df = pd.read_csv(self.styles_path, on_bad_lines="skip")
        logger.info(f"Loaded {len(df)} initial rows from metadata.")
        return df

    def validate_and_clean(self, verify_images_readable: bool = True) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Validates metadata and images:
        1. Checks duplicate product IDs.
        2. Drops rows with missing critical attributes (articleType, baseColour, gender, usage).
        3. Verifies corresponding image file exists on disk.
        4. Optionally verifies image readability with PIL.
        """
        df = self.load_raw_metadata()
        total_initial = len(df)

        # 1. Clean ID and check duplicates
        df["id"] = pd.to_numeric(df["id"], errors="coerce")
        df = df.dropna(subset=["id"])
        df["id"] = df["id"].astype(int)

        duplicates_count = df.duplicated(subset=["id"]).sum()
        if duplicates_count > 0:
            logger.warning(f"Found {duplicates_count} duplicate IDs. Dropping duplicates.")
            df = df.drop_duplicates(subset=["id"], keep="first")

        # 2. Check missing values in critical columns
        critical_cols = ["gender", "masterCategory", "subCategory", "articleType", "baseColour", "usage"]
        missing_stats = df[critical_cols].isna().sum().to_dict()
        logger.info(f"Missing attributes counts before cleaning: {missing_stats}")

        df = df.dropna(subset=critical_cols)

        # Standardize strings (strip whitespace)
        for col in critical_cols + ["productDisplayName"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        # 3. Verify image file existence and readability
        logger.info(f"Verifying image files existence in {self.images_dir}")
        valid_indices = []
        missing_images = 0
        corrupt_images = 0

        # Create quick set of existing filenames for fast lookup
        existing_images = set(p.name for p in self.images_dir.glob("*.jpg"))
        logger.info(f"Found {len(existing_images)} total image files in {self.images_dir}")

        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Validating images"):
            img_filename = f"{row['id']}.jpg"
            if img_filename not in existing_images:
                missing_images += 1
                continue

            if verify_images_readable:
                img_path = self.images_dir / img_filename
                try:
                    with Image.open(img_path) as img:
                        img.verify()
                    valid_indices.append(idx)
                except Exception:
                    corrupt_images += 1
            else:
                valid_indices.append(idx)

        clean_df = df.loc[valid_indices].copy()
        clean_df["image_filename"] = clean_df["id"].apply(lambda x: f"{x}.jpg")

        validation_report = {
            "total_initial_rows": total_initial,
            "duplicate_ids_removed": int(duplicates_count),
            "missing_attributes_cleaned": missing_stats,
            "missing_image_files": missing_images,
            "corrupt_images": corrupt_images,
            "total_valid_records": len(clean_df),
        }

        logger.info(f"Validation complete. Valid records: {len(clean_df)} / {total_initial}")
        return clean_df, validation_report

    def save_clean_data(self, clean_df: pd.DataFrame, output_path: Path = config.CLEAN_METADATA_PATH) -> Path:
        """Saves validated metadata to CSV."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        clean_df.to_csv(output_path, index=False)
        logger.info(f"Saved clean dataset to {output_path}")
        return output_path


if __name__ == "__main__":
    validator = DatasetValidator()
    # verify_images_readable=False for fast initial validation, or True for thoroughness
    clean_df, report = validator.validate_and_clean(verify_images_readable=False)
    validator.save_clean_data(clean_df)
    print("\n--- Validation Summary ---")
    for k, v in report.items():
        print(f"{k}: {v}")
