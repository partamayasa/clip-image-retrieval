import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from tqdm import tqdm

from src import config
from src.retrieval.searcher import RetrievalSearcher
from src.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    is_item_relevant,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Executes evaluation across all benchmark queries and aggregates performance metrics (Precision & Recall)."""

    def __init__(self, searcher: RetrievalSearcher = None):
        self.searcher = searcher or RetrievalSearcher()
        self.metadata_df = self.searcher.metadata_df
        self.benchmark_queries = config.BENCHMARK_QUERIES

    def count_ground_truth_pool(self, query_spec: Dict[str, Any]) -> int:
        """Counts total relevant candidate items in the dataset."""
        if "relevant_ids" in query_spec and query_spec["relevant_ids"]:
            return len(query_spec["relevant_ids"])
        count = 0
        for _, row in self.metadata_df.iterrows():
            item_dict = row.to_dict()
            if is_item_relevant(item_dict, query_spec):
                count += 1
        return count

    def run_benchmark(self, k_eval: int = None) -> Dict[str, Any]:
        """Runs evaluation for all benchmark queries using Precision and Recall."""
        if k_eval is None:
            k_eval = getattr(config, "EVAL_K", 10)
        logger.info(f"Running benchmark on {len(self.benchmark_queries)} queries (K_eval={k_eval})")
        results = []

        for q in tqdm(self.benchmark_queries, desc="Evaluating Queries"):
            query_text = q["text"]
            retrieved = self.searcher.search(query_text, top_k=max(20, k_eval))

            total_pool = self.count_ground_truth_pool(q)
            p_5 = precision_at_k(retrieved, q, k=5)
            p_10 = precision_at_k(retrieved, q, k=10)
            p_20 = precision_at_k(retrieved, q, k=20)
            rec_5 = recall_at_k(retrieved, q, total_relevant=total_pool, k=5)
            rec_10 = recall_at_k(retrieved, q, total_relevant=total_pool, k=10)
            rec_20 = recall_at_k(retrieved, q, total_relevant=total_pool, k=20)

            # Failure sample
            false_positives = [
                f"{item['id']} ({item.get('gender')} {item.get('baseColour')} {item.get('articleType')})"
                for item in retrieved[:k_eval]
                if not is_item_relevant(item, q)
            ]

            results.append({
                "id": q["id"],
                "level": q["level"],
                "query": query_text,
                "ground_truth_pool": total_pool,
                "precision@5": round(p_5, 4),
                "precision@10": round(p_10, 4),
                "precision@20": round(p_20, 4),
                "recall@5": round(rec_5, 4),
                "recall@10": round(rec_10, 4),
                "recall@20": round(rec_20, 4),
                "false_positives_sample": false_positives[:3],
            })

        # Aggregation by level
        df_res = pd.DataFrame(results)
        metric_cols = [
            "precision@5",
            "precision@10",
            "precision@20",
            "recall@5",
            "recall@10",
            "recall@20",
        ]
        summary_by_level = df_res.groupby("level")[metric_cols].mean().to_dict(orient="index")
        overall_mean = df_res[metric_cols].mean().to_dict()

        report = {
            "total_queries": len(results),
            "total_corpus_items": len(self.searcher.image_ids),
            "k_eval": k_eval,
            "overall_metrics": {k: round(v, 4) for k, v in overall_mean.items()},
            "metrics_by_level": {
                level: {k: round(v, 4) for k, v in metrics.items()}
                for level, metrics in summary_by_level.items()
            },
            "query_details": results,
        }

        # Save benchmark output directly to SQLite database
        try:
            from src.data.database import save_benchmark_report_to_db
            save_benchmark_report_to_db(report)
            logger.info("Saved benchmark evaluation results directly into SQLite database.")
        except Exception as e:
            logger.warning(f"Could not persist benchmark report to SQLite: {e}")

        return report


if __name__ == "__main__":
    runner = BenchmarkRunner()
    report = runner.run_benchmark(k_eval=10)
    print("\n--- Benchmark Overall Metrics ---")
    print(report["overall_metrics"])
