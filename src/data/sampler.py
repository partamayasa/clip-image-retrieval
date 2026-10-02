import json
import logging
from pathlib import Path
from typing import List, Tuple
import pandas as pd

from src import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class DatasetSampler:
    """Creates reproducible stratified subsets for EDA and retrieval evaluation."""

    def __init__(
        self,
        clean_metadata_path: Path = config.CLEAN_METADATA_PATH,
        images_dir: Path = config.IMAGES_DIR,
        target_article_types: List[str] = None,
        random_seed: int = config.RANDOM_SEED,
    ):
        self.clean_metadata_path = Path(clean_metadata_path)
        self.images_dir = Path(images_dir)
        self.target_article_types = target_article_types or config.TARGET_ARTICLE_TYPES
        # Include Kurtas along with Dress if present in dataset
        if "Kurtas" not in self.target_article_types:
            self.target_article_types = list(self.target_article_types) + ["Kurtas"]
        self.random_seed = random_seed

    def load_and_filter(self) -> pd.DataFrame:
        """Loads clean metadata and filters by target article types and physical image existence."""
        if not self.clean_metadata_path.exists():
            raise FileNotFoundError(
                f"Clean metadata not found at {self.clean_metadata_path}. Please run validator.py first."
            )

        df = pd.read_csv(self.clean_metadata_path)
        logger.info(f"Loaded {len(df)} records from clean metadata.")

        # Filter target article types
        filtered_df = df[df["articleType"].isin(self.target_article_types)].copy()
        logger.info(
            f"Filtered by target article types ({self.target_article_types}): {len(filtered_df)} records remaining."
        )

        # Dynamic physical image verification: only keep records whose image exists in images_dir
        if self.images_dir.exists():
            existing_images = set(p.name for p in self.images_dir.glob("*.jpg"))
            if existing_images:
                initial_count = len(filtered_df)
                filtered_df = filtered_df[filtered_df["id"].apply(lambda x: f"{x}.jpg" in existing_images)].copy()
                dropped = initial_count - len(filtered_df)
                if dropped > 0:
                    logger.info(
                        f"Dynamically verified images in '{self.images_dir}': "
                        f"excluded {dropped} records with missing image files ({len(filtered_df)} verified records ready)."
                    )

        return filtered_df

    def sample_stratified(self, df: pd.DataFrame, n_samples: int) -> pd.DataFrame:
        """
        Samples n_samples stratifying by articleType and gender.
        If any stratum has fewer samples than required, it falls back to proportional allocation.
        """
        if n_samples >= len(df):
            logger.warning(f"Requested {n_samples} samples, but dataset only has {len(df)}. Returning full dataset.")
            return df.sample(frac=1, random_state=self.random_seed).reset_index(drop=True)

        # Create stratification key
        df = df.copy()
        df["stratum"] = df["articleType"].astype(str) + "_" + df["gender"].astype(str)

        # Handle very small strata (<2 items) by grouping into 'other' for stratification
        stratum_counts = df["stratum"].value_counts()
        rare_strata = stratum_counts[stratum_counts < 2].index
        df.loc[df["stratum"].isin(rare_strata), "stratum"] = "Other_Strata"

        # Proportional sampling per stratum
        sampled_df = (
            df.groupby("stratum", group_keys=False)
            .apply(lambda x: x.sample(n=max(1, int(round(len(x) / len(df) * n_samples))), random_state=self.random_seed))
            .reset_index(drop=True)
        )

        # Adjust size to exact n_samples if rounding caused slight variance
        if len(sampled_df) > n_samples:
            sampled_df = sampled_df.sample(n=n_samples, random_state=self.random_seed).reset_index(drop=True)
        elif len(sampled_df) < n_samples:
            remaining_pool = df[~df["id"].isin(sampled_df["id"])]
            needed = n_samples - len(sampled_df)
            additional_samples = remaining_pool.sample(n=needed, random_state=self.random_seed)
            sampled_df = pd.concat([sampled_df, additional_samples], ignore_index=True)

        sampled_df = sampled_df.drop(columns=["stratum"], errors="ignore")
        logger.info(f"Successfully created stratified subset of {len(sampled_df)} items.")
        return sampled_df

    def generate_subsets(
        self,
        size_eda: int = getattr(config, "SUBSET_EDA_SIZE", 500),
        size_eval: int = getattr(config, "SUBSET_EVAL_SIZE", 1500),
        output_eda_path: Path = config.SUBSET_500_PATH,
        output_eval_path: Path = config.SUBSET_1500_PATH,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Generates both EDA subset and evaluation subset containing all ground-truth products."""
        filtered_df = self.load_and_filter()

        # Check if user benchmark ground truth exists in SQLite database
        gt_ids = set()
        try:
            from src.data.database import get_ground_truth_product_ids
            gt_ids = get_ground_truth_product_ids()
            if gt_ids:
                logger.info(f"Loaded {len(gt_ids)} benchmark ground truth product IDs from SQLite database.")
        except Exception as e:
            logger.warning(f"Could not load ground truth product IDs from DB: {e}")

        if not gt_ids and config.GROUND_TRUTH_JSON_PATH.exists():
            with open(config.GROUND_TRUTH_JSON_PATH, "r", encoding="utf-8") as f:
                gt_data = json.load(f)
            for item in gt_data.values():
                gt_ids.update(item.get("relevant_product_ids", []))
            logger.info(f"Loaded {len(gt_ids)} user ground truth product IDs from fallback JSON.")

        # Subset Eval: Prioritize all ground truth products, then fill up to size_eval
        if gt_ids:
            gt_df = filtered_df[filtered_df["id"].isin(gt_ids)].copy()
            remaining_pool = filtered_df[~filtered_df["id"].isin(gt_ids)].copy()
            needed = max(0, size_eval - len(gt_df))
            additional_df = remaining_pool.sample(n=min(needed, len(remaining_pool)), random_state=self.random_seed)
            df_eval = pd.concat([gt_df, additional_df], ignore_index=True).sample(frac=1, random_state=self.random_seed).reset_index(drop=True)
            logger.info(f"Constructed benchmark eval dataset with {len(gt_df)} ground truth items + {len(additional_df)} distractors = {len(df_eval)} total.")
        else:
            df_eval = self.sample_stratified(filtered_df, n_samples=size_eval)

        output_eval_path.parent.mkdir(parents=True, exist_ok=True)
        df_eval.to_csv(output_eval_path, index=False)
        logger.info(f"Saved evaluation subset to: {output_eval_path}")

        # Subset 500 for EDA
        df_500 = self.sample_stratified(df_eval, n_samples=min(size_eda, len(df_eval)))
        output_eda_path.parent.mkdir(parents=True, exist_ok=True)
        df_500.to_csv(output_eda_path, index=False)
        logger.info(f"Saved EDA subset to: {output_eda_path}")

        # Save metadata info & filtering criteria
        criteria_path = output_eval_path.parent / "subset_criteria.json"
        criteria = {
            "random_seed": self.random_seed,
            "target_article_types": self.target_article_types,
            "ground_truth_products_count": len(gt_ids),
            "subset_eda_size": len(df_500),
            "subset_eval_size": len(df_eval),
            "eval_articleType_dist": df_eval["articleType"].value_counts().to_dict(),
        }
        with open(criteria_path, "w", encoding="utf-8") as f:
            json.dump(criteria, f, indent=2)
        logger.info(f"Saved subset criteria and distribution report to: {criteria_path}")

        return df_500, df_eval


if __name__ == "__main__":
    sampler = DatasetSampler()
    df_500, df_1500 = sampler.generate_subsets()
    print("\n--- Subset Generation Complete ---")
    print(f"EDA Subset (500): {len(df_500)} records")
    print(f"Eval Subset (1500): {len(df_1500)} records")
    print("\nArticleType Distribution (Subset 1500):")
    print(df_1500["articleType"].value_counts())
