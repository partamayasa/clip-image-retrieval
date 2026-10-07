import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from src import config
from src.models.clip_engine import CLIPEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class RetrievalSearcher:
    """Performs real-time cosine similarity search over precomputed image embeddings."""

    def __init__(
        self,
        embeddings_path: Path = config.IMAGE_EMBEDDINGS_PATH,
        ids_path: Path = config.IMAGE_IDS_PATH,
        metadata_cache_path: Path = config.METADATA_CACHE_PATH,
        clip_engine: Optional[CLIPEngine] = None,
    ):
        self.embeddings_path = Path(embeddings_path)
        self.ids_path = Path(ids_path)
        self.metadata_cache_path = Path(metadata_cache_path)

        if not self.embeddings_path.exists() or not self.ids_path.exists():
            raise FileNotFoundError(
                f"Embedding files not found. Run indexer.py first! Looking for: {self.embeddings_path}"
            )

        logger.info(f"Loading precomputed embeddings from {self.embeddings_path}")
        self.image_embeddings = np.load(self.embeddings_path)  # [N, 512]
        self.image_ids = np.load(self.ids_path)  # [N]
        # Load product metadata: prioritize SQLite database
        try:
            from src.data.database import get_products_dict
            db_meta = get_products_dict()
            if db_meta:
                self.id_to_meta = db_meta
                logger.info(f"Loaded {len(self.id_to_meta)} product metadata records from SQLite database.")
            else:
                self.metadata_df = pd.read_parquet(self.metadata_cache_path)
                self.id_to_meta = self.metadata_df.set_index("id").to_dict(orient="index")
        except Exception as e:
            logger.warning(f"Could not load products from SQLite, falling back to parquet cache: {e}")
            self.metadata_df = pd.read_parquet(self.metadata_cache_path)
            self.id_to_meta = self.metadata_df.set_index("id").to_dict(orient="index")

        if not hasattr(self, "metadata_df") or self.metadata_df is None:
            if self.metadata_cache_path.exists():
                self.metadata_df = pd.read_parquet(self.metadata_cache_path)
            else:
                self.metadata_df = pd.DataFrame.from_dict(self.id_to_meta, orient="index")

        logger.info(f"Loaded {len(self.image_ids)} indexed product embeddings (dim: {self.image_embeddings.shape[1]}).")
        self.engine = clip_engine or CLIPEngine()

    def search(self, query_text: str, top_k: int = 10, filter_gender: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes real-time retrieval:
        1. Encodes query string to L2-normalized text vector.
        2. Computes matrix dot product: Sim(Q, V) = Q . V^T
        3. Sorts and retrieves Top-K ranking.
        """
        query_vec = self.engine.encode_text(query_text)  # [1, 512]
        
        # Cosine similarity matrix multiplication (already unit-normalized)
        similarities = np.dot(query_vec, self.image_embeddings.T).flatten()  # [N]

        # Top-K indices sorted descending
        if top_k >= len(similarities):
            sorted_indices = np.argsort(similarities)[::-1]
        else:
            partitioned = np.argpartition(similarities, -top_k)[-top_k:]
            sorted_indices = partitioned[np.argsort(similarities[partitioned])[::-1]]

        results = []
        rank = 1
        for idx in sorted_indices:
            prod_id = int(self.image_ids[idx])
            score = float(similarities[idx])
            meta = self.id_to_meta.get(prod_id, {})

            if filter_gender and meta.get("gender") != filter_gender:
                continue

            results.append({
                "rank": rank,
                "id": prod_id,
                "score": round(score, 4),
                "image_filename": f"{prod_id}.jpg",
                "articleType": meta.get("articleType", "Unknown"),
                "baseColour": meta.get("baseColour", "Unknown"),
                "gender": meta.get("gender", "Unknown"),
                "usage": meta.get("usage", "Unknown"),
                "productDisplayName": meta.get("productDisplayName", "Unknown"),
            })
            rank += 1
            if len(results) >= top_k:
                break

        return results


if __name__ == "__main__":
    searcher = RetrievalSearcher()
    res = searcher.search("red dress", top_k=5)
    for r in res:
        print(f"Rank {r['rank']} | Score: {r['score']} | {r['gender']} {r['baseColour']} {r['articleType']} - {r['productDisplayName']}")
