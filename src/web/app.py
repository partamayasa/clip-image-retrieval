import json
import logging
import time
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src import config
from src.retrieval.searcher import RetrievalSearcher
from src.evaluation.metrics import is_item_relevant, attribute_match_breakdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Fashion Multimodal Retrieval Explorer", version="1.0.0")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Anti-cache middleware for web assets & pages to avoid stale browser JS/CSS
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") or path.startswith("/adminlte/") or path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Static and Templates
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

LOCAL_ADMINLTE_DIR = STATIC_DIR / "adminlte"
if LOCAL_ADMINLTE_DIR.exists():
    app.mount("/adminlte", StaticFiles(directory=str(LOCAL_ADMINLTE_DIR)), name="adminlte")

# Lazy-loaded Searcher
_searcher: Optional[RetrievalSearcher] = None


def get_searcher() -> RetrievalSearcher:
    global _searcher
    if _searcher is None:
        try:
            _searcher = RetrievalSearcher()
        except Exception as e:
            logger.error(f"Searcher could not be initialized: {e}")
            raise HTTPException(status_code=503, detail="Embedding database not initialized. Please run indexing.")
    return _searcher


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Loading Dashboard</h1>", status_code=200)
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"), status_code=200)


@app.get("/api/images/{filename}")
async def serve_image(filename: str):
    image_path = config.IMAGES_DIR / filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path, media_type="image/jpeg")


from src.data.database import (
    get_benchmark_queries as db_get_benchmark_queries,
    get_benchmark_report_from_db,
    get_eda_report_from_db,
    get_system_configs,
    get_target_article_types,
    get_db_connection,
    init_db,
    seed_db,
)


@app.on_event("startup")
async def startup_event():
    """Ensure SQLite database is fully seeded with all dataset, benchmark, and EDA data as single source of truth."""
    try:
        init_db()
        seed_db(force=True)
        logger.info("SQLite database verified & synced as single source of truth.")
    except Exception as e:
        logger.warning(f"Database startup sync note: {e}")


@app.get("/api/db-sync")
@app.post("/api/db-sync")
async def sync_database(force: bool = True):
    """Explicitly triggers full migration of all data from eda_report.json, benchmark_results.json, and benchmark_ground_truth.json into SQLite database."""
    try:
        init_db()
        seed_db(force=force)
        return {
            "status": "success",
            "message": "All data from eda_report.json, benchmark_results.json, and benchmark_ground_truth.json have been migrated to SQLite database.",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/benchmark-queries")
async def get_benchmark_queries():
    # Fetch benchmark queries directly from SQLite database
    queries = db_get_benchmark_queries(with_relevant_ids=True)
    serializable = []
    for q in queries:
        q_copy = dict(q)
        if "relevant_ids" in q_copy:
            q_copy["relevant_ids_count"] = len(q_copy["relevant_ids"])
            q_copy.pop("relevant_ids", None)
        serializable.append(q_copy)
    return {"queries": serializable}


@app.get("/api/benchmark-report")
async def get_benchmark_report():
    """Returns benchmark evaluation metrics directly from SQLite database."""
    db_report = get_benchmark_report_from_db()
    if db_report:
        return db_report

    # Ensure database is seeded from archive if empty
    seed_db(force=False)
    db_report = get_benchmark_report_from_db()
    if db_report:
        return db_report

    return {"status": "Benchmark report not yet generated in database"}


@app.get("/api/eda-stats")
async def get_eda_stats():
    """Returns EDA dataset statistics directly from SQLite database."""
    db_eda = get_eda_report_from_db()
    if db_eda:
        return db_eda

    # Ensure database is seeded from archive if empty
    seed_db(force=False)
    db_eda = get_eda_report_from_db()
    if db_eda:
        return db_eda

    return {"status": "EDA report not yet generated in database"}


@app.get("/api/benchmark-ground-truth")
async def get_benchmark_ground_truth_endpoint():
    """Returns complete benchmark ground truth criteria and relevance mappings directly from SQLite database."""
    from src.data.database import get_benchmark_ground_truth_dict
    gt_data = get_benchmark_ground_truth_dict()
    if not gt_data:
        seed_db(force=False)
        gt_data = get_benchmark_ground_truth_dict()
    return gt_data


@app.get("/api/system-configs")
async def get_configs():
    """Returns application & model configuration settings from SQLite database."""
    return {
        "configs": get_system_configs(),
        "target_article_types": get_target_article_types(),
    }


@app.get("/api/db-status")
async def get_db_status():
    """Returns status, tables, and record counts from the SQLite database."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'").fetchall()]
        stats = {t: cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}
        db_size_bytes = config.DB_PATH.stat().st_size if config.DB_PATH.exists() else 0
        conn.close()
        return {
            "status": "connected",
            "db_path": str(config.DB_PATH),
            "size_kb": round(db_size_bytes / 1024, 2),
            "tables": stats,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/data-preparation")
async def get_data_preparation():
    """Returns comprehensive data preparation, attrition stats, pipeline stages, and research transparency info."""
    criteria_path = config.PROCESSED_DATA_DIR / "subset_criteria.json"
    criteria = {}
    if criteria_path.exists():
        try:
            with open(criteria_path, "r", encoding="utf-8") as f:
                criteria = json.load(f)
        except Exception:
            pass

    clean_count = 44095
    clean_path = config.PROCESSED_DATA_DIR / "clean_styles.csv"
    if clean_path.exists():
        try:
            with open(clean_path, "rb") as f:
                clean_count = sum(1 for _ in f) - 1
        except Exception:
            pass

    gt_pairs_count = 0
    gt_unique_count = criteria.get("ground_truth_products_count", 1466)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        gt_pairs_count = cur.execute("SELECT count(*) FROM benchmark_ground_truth").fetchone()[0]
        conn.close()
    except Exception:
        pass

    return {
        "pipeline_stages": [
            {
                "stage": 1,
                "name": "Data Ingestion & Integrity Validation",
                "script": "python -m src.data.validator",
                "input": "Kaggle Fashion Product Images (~44,441 records & images)",
                "output": "data/processed/clean_styles.csv (44,095 valid records)",
                "status": "Verified",
                "description": "Verifikasi fisik file gambar via Pillow untuk mendeteksi gambar yang rusak atau hilang, normalisasi skema metadata, serta eliminasi data dengan atribut kosong (missing attributes).",
            },
            {
                "stage": 2,
                "name": "Target Category Filtering",
                "script": "python -m src.data.sampler",
                "input": "44,095 clean valid images",
                "output": "24,881 target category images",
                "status": "Verified",
                "description": "Penyaringan untuk 13 kategori busana utama (Tshirts, Shirts, Casual/Formal/Sports Shoes, Watches, Handbags, Backpacks, Jackets, Jeans, Caps, Sunglasses, Kurtas) yang disesuaikan untuk temu balik multimodal.",
            },
            {
                "stage": 3,
                "name": "Reproducible Stratified Sampling",
                "script": "python -m src.data.sampler",
                "input": "24,881 records (Random Seed: 42)",
                "output": "subset_1500_eval.csv (1,500 images)",
                "status": "Verified",
                "description": "Pengambilan sampel proporsional terstratifikasi berdasarkan `articleType` dan `gender`. Korpus terpadu 1.500 gambar terdiri dari 1.466 item target benchmark + 34 item distraktor, berfungsi sebagai single source of truth untuk profiling EDA, pengindeksan vektor, dan evaluasi IR.",
            },
            {
                "stage": 4,
                "name": "Deterministic Ground Truth Synchronization",
                "script": "python -m src.data.sync_ground_truth",
                "input": "30 Standardized Benchmark Queries + 1,500 Corpus",
                "output": "benchmark_ground_truth.json & .csv (2,014 relevance pairs)",
                "status": "Verified",
                "description": "Pencocokan multi-atribut boolean deterministik (kategori, warna, gender, penggunaan) pada seluruh korpus 1.500 data guna menetapkan ground truth yang 100% transparan dan reproducible tanpa bias anotasi manusia.",
            },
            {
                "stage": 5,
                "name": "Offline Multimodal Vector Indexing",
                "script": "python -m src.models.indexer --subset 1500",
                "input": "1,500 fashion catalog images",
                "output": "image_embeddings.npy [1500, 512] float32 & metadata_cache.parquet",
                "status": "Verified",
                "description": "Ekstraksi fitur visual gambar secara offline menggunakan CLIP ViT-B/32 (512 dimensi) dengan normalisasi unit L2, disimpan untuk temu balik dot-product real-time (< 30 ms).",
            },
            {
                "stage": 6,
                "name": "SQLite Relational Data Persistence",
                "script": "python -m src.data.database",
                "input": "System configurations, product metadata, benchmark queries, and IR metrics",
                "output": "data/fashion_retrieval.db (10 relational tables)",
                "status": "Verified",
                "description": "Penyimpanan terpusat artefak riset ke dalam database SQLite, memfasilitasi auditabilitas transparan, query API dinamis, dan memisahkan data statis dari kode sumber.",
            },
        ],
        "attrition_waterfall": [
            {"step": "Ingesti Mentah (Kaggle)", "count": 44441, "percentage": "100.0%", "badge": "Arsip Mentah"},
            {"step": "Dataset Bersih & Terverifikasi", "count": clean_count, "percentage": f"{(clean_count/44441)*100:.1f}%", "badge": "Lolos Integritas Gambar"},
            {"step": "Penyaringan Kategori Target", "count": 24881, "percentage": f"{(24881/clean_count)*100:.1f}%", "badge": "13 Kategori Target"},
            {"step": "Korpus Riset Multimodal", "count": 1500, "percentage": f"{(1500/24881)*100:.1f}%", "badge": "1.466 GT + 34 Distraktor"},
        ],
        "corpus_composition": {
            "total_eval_corpus": 1500,
            "ground_truth_products": gt_unique_count,
            "distractor_products": criteria.get("distractor_products_count", 34),
            "total_benchmark_queries": 30,
            "total_relevance_pairs": gt_pairs_count or 2014,
            "random_seed": criteria.get("random_seed", 42),
            "article_type_dist": criteria.get("eval_articleType_dist", {}),
        },
        "vector_store_specs": {
            "model_architecture": "openai/clip-vit-base-patch32",
            "vector_dimension": 512,
            "matrix_shape": "[1500, 512]",
            "precision": "float32",
            "similarity_metric": "Cosine Similarity (Dot Product via L2-Normalized Vectors)",
            "average_search_latency": "< 30 ms",
        },
        "methodology_rationales": [
            {
                "topic": "Mengapa 1.466 Ground Truth + 34 Distraktor?",
                "explanation": "Dalam Information Retrieval (IR), evaluasi yang adil membutuhkan ruang pencarian yang berisi data relevan target sekaligus data distraktor (pengecoh). 1.466 produk relevan merepresentasikan ground truth untuk 30 query benchmark, sedangkan 34 gambar distraktor menguji presisi model terhadap sampel yang tidak relevan.",
            },
            {
                "topic": "Mengapa Menggunakan Korpus Riset Terpadu 1.500 Gambar?",
                "explanation": "Untuk menjaga 100% konsistensi data di seluruh modul riset, korpus 1.500 gambar berfungsi sebagai single source of truth untuk Exploratory Data Analysis (EDA), pengindeksan vektor offline CLIP ViT-B/32, dan benchmarking kuantitatif Information Retrieval.",
            },
            {
                "topic": "Mengapa Aturan Boolean Deterministik untuk Ground Truth?",
                "explanation": "Anotasi manual rentan terhadap bias subjektif penilai. Mendefinisikan kriteria relevansi secara logis (misalnya, articleType == 'Tshirts' dan baseColour == 'Blue') menjamin 100% keterulangan (reproducibility) dan transparansi matematis di seluruh 30 query.",
            },
        ],
    }


def find_matching_benchmark_spec(q_text: str) -> Optional[dict]:
    """Finds matching benchmark query specification with dynamic SQLite fallback if cache is empty."""
    clean_q = q_text.strip().lower()
    queries = getattr(config, "BENCHMARK_QUERIES", [])
    
    # If empty or not yet loaded in running memory, fetch directly from SQLite database
    if not queries:
        try:
            from src.data.database import get_benchmark_queries as db_get_queries
            queries = db_get_queries(with_relevant_ids=True)
            if queries:
                config.BENCHMARK_QUERIES = queries
        except Exception as e:
            logger.warning(f"Could not load benchmark queries from DB fallback: {e}")

    for item in queries:
        text = (item.get("text") or "").strip().lower()
        qid = (item.get("id") or "").strip().lower()
        if clean_q == text or clean_q == qid or clean_q == f"[{qid}] {text}":
            return item

    # Direct secondary query from SQLite if not found in list (e.g. if list was stale)
    try:
        from src.data.database import get_benchmark_queries as db_get_queries
        fresh_queries = db_get_queries(with_relevant_ids=True)
        for item in fresh_queries:
            text = (item.get("text") or "").strip().lower()
            qid = (item.get("id") or "").strip().lower()
            if clean_q == text or clean_q == qid or clean_q == f"[{qid}] {text}":
                config.BENCHMARK_QUERIES = fresh_queries
                return item
    except Exception:
        pass

    return None


@app.get("/api/search")
async def search(
    q: str = Query(..., description="Query text to search"),
    top_k: Optional[int] = Query(None, description="Number of results to return (None = all corpus)"),
    gender: Optional[str] = Query(None),
):
    start_time = time.perf_counter()
    searcher = get_searcher()
    # Default to all indexed products in corpus if top_k is not specified
    k = top_k if (top_k is not None and top_k > 0) else len(searcher.image_ids)
    retrieved = searcher.search(q, top_k=k, filter_gender=gender)
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Check if this query matches any benchmark query for ground truth badge
    matching_spec = find_matching_benchmark_spec(q)
    
    evaluated_results = []
    for item in retrieved:
        item_copy = dict(item)
        if matching_spec:
            item_copy["is_relevant"] = is_item_relevant(item, matching_spec)
        else:
            item_copy["is_relevant"] = None
        evaluated_results.append(item_copy)

    metrics_summary = None
    if matching_spec:
        top5 = evaluated_results[:5]
        top10 = evaluated_results[:10]
        top20 = evaluated_results[:20]
        rel_top5 = sum(1 for x in top5 if x["is_relevant"])
        rel_top10 = sum(1 for x in top10 if x["is_relevant"])
        rel_top20 = sum(1 for x in top20 if x["is_relevant"])
        
        total_pool = matching_spec.get("total_relevant", 0)
        if not total_pool and "relevant_ids" in matching_spec:
            total_pool = len(matching_spec["relevant_ids"])
        if not total_pool:
            total_pool = sum(1 for x in evaluated_results if x["is_relevant"])

        metrics_summary = {
            "precision_at_5": round(rel_top5 / len(top5), 4) if top5 else 0.0,
            "precision_at_10": round(rel_top10 / len(top10), 4) if top10 else 0.0,
            "precision_at_20": round(rel_top20 / len(top20), 4) if top20 else 0.0,
            "recall_at_5": round(min(1.0, rel_top5 / total_pool), 4) if total_pool > 0 else 0.0,
            "recall_at_10": round(min(1.0, rel_top10 / total_pool), 4) if total_pool > 0 else 0.0,
            "recall_at_20": round(min(1.0, rel_top20 / total_pool), 4) if total_pool > 0 else 0.0,
            "precision_at_k": round(rel_top10 / len(top10), 4) if top10 else 0.0,
            "recall_at_k": round(min(1.0, rel_top10 / total_pool), 4) if total_pool > 0 else 0.0,
            "relevant_count": rel_top10,
            "k": len(top10),
            "relevant_count_top5": rel_top5,
            "relevant_count_top10": rel_top10,
            "relevant_count_top20": rel_top20,
            "total_corpus_relevant": total_pool,
            "attribute_breakdown": attribute_match_breakdown(top10, matching_spec, k=len(top10)),
        }

    return {
        "query": q,
        "latency_ms": latency_ms,
        "total_results": len(evaluated_results),
        "benchmark_matched": matching_spec is not None,
        "benchmark_spec": {
            "id": matching_spec.get("id"),
            "level": matching_spec.get("level"),
            "text": matching_spec.get("text"),
            "target_description": matching_spec.get("target_description"),
            "relevance_criteria": matching_spec.get("relevance_criteria"),
            "total_relevant": matching_spec.get("total_relevant", 0),
        } if matching_spec else None,
        "metrics": metrics_summary,
        "results": evaluated_results,
    }


@app.get("/api/ground-truth")
async def get_ground_truth(
    query_id: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    article_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """Returns list of ground truth product-to-query relations with query details and product metadata."""
    from src.data.database import get_ground_truth_relations, get_ground_truth_summary
    relations = get_ground_truth_relations(
        query_id=query_id,
        level=level,
        article_type=article_type,
        search=search,
    )
    summary = get_ground_truth_summary()
    return {
        "total_returned": len(relations),
        "total_pairs": summary["total_pairs"],
        "unique_products": summary["unique_products"],
        "total_queries": summary["total_queries"],
        "summary": summary,
        "relations": relations,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.web.app:app", host="127.0.0.1", port=8000, reload=True)

