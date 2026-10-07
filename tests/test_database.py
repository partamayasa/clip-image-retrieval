import pytest
import sqlite3
from pathlib import Path
from src import config
from src.data.database import (
    get_db_connection,
    get_system_configs,
    get_target_article_types,
    get_audit_samples,
    get_retrieval_insights,
    get_benchmark_queries,
    get_benchmark_report_from_db,
    get_eda_report_from_db,
    get_products_dict,
    get_benchmark_ground_truth_dict,
    get_ground_truth_product_ids,
)


def test_sqlite_db_exists():
    assert config.DB_PATH.exists()
    conn = get_db_connection()
    assert isinstance(conn, sqlite3.Connection)
    conn.close()


def test_system_configs():
    configs = get_system_configs()
    assert isinstance(configs, dict)
    assert "clip_model_name" in configs
    assert "embedding_dim" in configs
    assert configs["embedding_dim"] == "512"


def test_target_article_types():
    types = get_target_article_types()
    assert isinstance(types, list)
    assert len(types) >= 12
    assert "Tshirts" in types
    assert "Casual Shoes" in types
    assert "Watches" in types


def test_audit_samples():
    samples = get_audit_samples()
    assert isinstance(samples, list)
    assert len(samples) == 20
    assert samples[0]["no"] == 1
    assert (samples[0].get("validation_status") or samples[0].get("status_validasi")) in ("Consistent", "Sesuai", "Konsisten")


def test_retrieval_insights():
    insights = get_retrieval_insights()
    assert isinstance(insights, list)
    assert len(insights) == 5
    assert "topic" in insights[0]
    assert "observation" in insights[0]
    assert "retrieval_implication" in insights[0]


def test_benchmark_queries():
    queries = get_benchmark_queries(with_relevant_ids=True)
    assert isinstance(queries, list)
    assert len(queries) == 30
    q1 = queries[0]
    assert q1["id"] == "Q01"
    assert q1["level"] in ("General", "Umum")
    assert len(q1["relevant_ids"]) > 0


def test_benchmark_ground_truth_dict():
    gt = get_benchmark_ground_truth_dict()
    assert isinstance(gt, dict)
    assert len(gt) == 30
    assert "Q01" in gt
    assert "query_text" in gt["Q01"]
    assert "relevant_product_ids" in gt["Q01"]
    assert len(gt["Q01"]["relevant_product_ids"]) > 0


def test_ground_truth_product_ids():
    ids = get_ground_truth_product_ids()
    assert isinstance(ids, set)
    assert len(ids) >= 1300


def test_products_table():
    prods = get_products_dict()
    assert isinstance(prods, dict)
    assert len(prods) >= 1500
    sample_id = next(iter(prods))
    assert "articleType" in prods[sample_id]
    assert "baseColour" in prods[sample_id]


def test_benchmark_report_from_db():
    report = get_benchmark_report_from_db()
    if report is None:
        from src.data.database import save_benchmark_report_to_db
        mock_report = {
            "total_queries": 30,
            "total_corpus_items": 1500,
            "k_eval": 10,
            "overall_metrics": {"precision@5": 0.8, "precision@10": 0.75, "precision@20": 0.65},
            "metrics_by_level": {
                "General": {"precision@5": 0.9, "precision@10": 0.85, "precision@20": 0.75},
                "Medium": {"precision@5": 0.8, "precision@10": 0.75, "precision@20": 0.65},
                "Specific": {"precision@5": 0.7, "precision@10": 0.65, "precision@20": 0.55},
            },
            "query_details": [
                {"id": f"Q{i:02d}", "level": "General", "query": f"query {i}", "ground_truth_pool": 10, "precision@10": 0.8}
                for i in range(1, 31)
            ],
        }
        save_benchmark_report_to_db(mock_report)
        report = get_benchmark_report_from_db()

    assert report is not None
    assert "overall_metrics" in report
    assert "precision@10" in report["overall_metrics"]
    assert "query_details" in report
    assert len(report["query_details"]) == 30
    assert report["total_queries"] == 30
    assert report["total_corpus_items"] == 1500
    assert report["k_eval"] == 10
    assert "General" in report["metrics_by_level"]


def test_eda_report_from_db():
    eda = get_eda_report_from_db()
    assert eda is not None
    assert eda["total_records"] == 1500
    assert "distribution_articleType" in eda
    assert "visual_verification_20_pairs" in eda
    assert len(eda["visual_verification_20_pairs"]) == 20
    assert all(bool(s.get("productDisplayName")) for s in eda["visual_verification_20_pairs"])
    assert len(eda["insights"]) == 5
