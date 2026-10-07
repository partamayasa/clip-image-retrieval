import logging
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm

from src import config
from src.models.clip_engine import CLIPEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ImageIndexer:
    """Precomputes offline image embeddings for the evaluation subset."""

    def __init__(
        self,
        metadata_path: Path = config.SUBSET_1500_PATH,
        images_dir: Path = config.IMAGES_DIR,
        batch_size: int = config.BATCH_SIZE,
    ):
        self.metadata_path = Path(metadata_path)
        self.images_dir = Path(images_dir)
        self.batch_size = batch_size
        self.engine = CLIPEngine()

    def build_index(
        self,
        output_embeddings_path: Path = config.IMAGE_EMBEDDINGS_PATH,
        output_ids_path: Path = config.IMAGE_IDS_PATH,
        output_metadata_cache: Path = config.METADATA_CACHE_PATH,
    ):
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Subset file not found: {self.metadata_path}")

        df = pd.read_csv(self.metadata_path)
        logger.info(f"Building image index for {len(df)} products from {self.metadata_path}")
        logger.info(f"Target images directory: {self.images_dir}")

        # Dynamic verification: Only index products whose image file physically exists
        valid_indices = []
        missing_count = 0
        for idx, row in df.iterrows():
            img_path = self.images_dir / f"{row['id']}.jpg"
            if img_path.is_file():
                valid_indices.append(idx)
            else:
                missing_count += 1

        if missing_count > 0:
            logger.info(
                f"Dynamic image filter: Found {len(valid_indices)} available images on disk. "
                f"Skipped {missing_count} missing images cleanly without errors."
            )
            df = df.loc[valid_indices].reset_index(drop=True)

        if len(df) == 0:
            raise FileNotFoundError(
                f"No valid image files found in '{self.images_dir}'! "
                f"Please verify IMAGES_DIR in your .env configuration."
            )

        all_embeddings = []
        valid_ids = []
        valid_rows = []

        total_batches = (len(df) + self.batch_size - 1) // self.batch_size

        for i in tqdm(range(total_batches), desc="Computing Image Embeddings"):
            batch_df = df.iloc[i * self.batch_size : (i + 1) * self.batch_size]
            batch_images = []
            batch_ids = []
            batch_subrows = []

            for _, row in batch_df.iterrows():
                img_path = self.images_dir / f"{row['id']}.jpg"
                try:
                    img = Image.open(img_path).convert("RGB")
                    batch_images.append(img)
                    batch_ids.append(int(row["id"]))
                    batch_subrows.append(row)
                except Exception as e:
                    logger.debug(f"Could not load image for ID {row['id']}: {e}")

            if batch_images:
                batch_vecs = self.engine.encode_images(batch_images)
                all_embeddings.append(batch_vecs)
                valid_ids.extend(batch_ids)
                valid_rows.extend(batch_subrows)

        final_embeddings = np.vstack(all_embeddings).astype(np.float32)
        final_ids = np.array(valid_ids, dtype=np.int64)
        clean_subset_df = pd.DataFrame(valid_rows).reset_index(drop=True)

        # Save to disk
        output_embeddings_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(output_embeddings_path, final_embeddings)
        np.save(output_ids_path, final_ids)
        clean_subset_df.to_parquet(output_metadata_cache, index=False)

        logger.info(f"Saved {final_embeddings.shape[0]} embeddings to {output_embeddings_path} (Shape: {final_embeddings.shape})")
        logger.info(f"Saved IDs array to {output_ids_path}")
        logger.info(f"Saved metadata cache to {output_metadata_cache}")

        try:
            from src.data.database import seed_db
            seed_db()
            logger.info("Synchronized indexed products into SQLite database.")
        except Exception as e:
            logger.warning(f"Could not update SQLite products: {e}")

        return final_embeddings, final_ids, clean_subset_df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compute image embeddings")
    parser.add_argument("--subset", type=int, default=1500, choices=[500, 1500], help="Subset size (500 or 1500)")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size")
    args = parser.parse_args()

    target_path = config.SUBSET_1500_PATH if args.subset == 1500 else config.SUBSET_500_PATH
    indexer = ImageIndexer(metadata_path=target_path, batch_size=args.batch_size)
    indexer.build_index()
