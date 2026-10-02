# Attribute-Based Text-to-Image Retrieval for Fashion Products

A *Multimodal Information Retrieval* research system designed to search, rank, and evaluate fashion product images based on multi-attribute natural language text queries (*articleType*, *baseColour*, *gender*, *usage*) leveraging the Shared Latent Space of OpenAI's **CLIP** (*Contrastive Language-Image Pre-training* - `openai/clip-vit-base-patch32`).

This project features a high-throughput offline vector indexing pipeline, an ultra-low latency real-time search engine driven by *in-memory matrix dot-product operations*, comprehensive automated evaluation across **30 Benchmark Queries** with verified ground truth, and an interactive modern research dashboard built on **AdminLTE v4.9.1**.

---

## Key Features

1. **Dual-Modal Latent Space (CLIP ViT-B/32)**:
   - Projects both textual descriptions and visual image features into a shared 512-dimensional $L_2$-normalized vector space.
   - Enables zero-shot open-vocabulary retrieval without relying on fragile lexical matching or catalog text tags.
2. **Offline Precomputation & In-Memory Vector Store**:
   - Image embedding vectors are precomputed once and serialized to disk (`image_embeddings.npy` and `metadata_cache.parquet`).
   - Lightning-fast matrix multiplication ($Q \times V^T$) executed directly in memory with average query response latency **< 30 ms**.
3. **Rigorous IR Evaluation (30 Benchmark Queries)**:
   - Evaluates 30 structured research queries categorized across three semantic ambiguity tiers: **General** (single-token category), **Medium** (category + color), and **Specific** (category + color + gender + usage).
   - Standard Information Retrieval metrics: **Precision@K** ($K \in \{5, 10, 20\}$), **Recall@K**, **MRR** (*Mean Reciprocal Rank*), **NDCG@10**, and fine-grained **Attribute Match Breakdown** (*Category*, *Color*, *Gender*).
4. **Interactive Research Dashboard (AdminLTE v4.9.1)**:
   - Modern enterprise-grade interface optimized with a clean, high-contrast light theme.
   - Live KPI Stat Cards: *Inference Latency*, *Precision@K*, *Category Alignment*, and *Color Fidelity*.
   - Quick-select selector for all 30 Benchmark Queries tagged with specificity badges.
   - Real-time interactive controls: Top-K depth ($K = 5, 10, 20, 50$, or full corpus) and gender filters (*Men*, *Women*, *Unisex*).
   - High-density product cards with Cosine Similarity scores, ground-truth match indicators, and product inspection modals.
   - Built-in modal report viewers for **Benchmark Evaluation** and **Exploratory Data Analysis (EDA)**.
5. **Robust Data Pipeline & Verification**:
   - Automated image integrity verification (detecting missing or corrupted image files via Pillow).
   - Reproducible stratified sampling (seed 42) creating a unified 1,500-product research corpus ($N = 1,500$) as the single source of truth for both EDA and multimodal evaluation.
6. **100% Offline CLIP Inference (Zero Network Calls)**:
   - Pretrained model weights and tokenizer configurations are saved locally in `data/models/clip-vit-base-patch32/` (`model.safetensors`).
   - Enforces offline operation (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`), eliminating any outbound API calls or commit checks to Hugging Face Hub, minimizing startup time and reducing search latency to **~27 ms**.
7. **Dedicated Ground Truth & Relevance Mapping Module**:
   - Comprehensive interactive module mapping all **2,014 deterministic Product &harr; Query relevance relations**.
   - Dual-mode visualization: **Data Table Mode** (Tabulator with live search, attribute filters, image lightbox zoom, and CSV/JSON export) and **Query Cards Mode** (visual accordion grouping with full product photo galleries).
   - Instant *"Test in Retrieval Lab"* action on any relation to evaluate retrieval performance in real-time.

---

## Project Directory Structure

```
clip/
├── .venv/                         # Python Virtual Environment
├── archive/                       # Alternative raw dataset location (styles.csv & images/)
├── data/
│   ├── dataset/                   # Active dataset directory (styles.csv & images/ ~44,000 files)
│   ├── models/                    # Offline CLIP Model Storage (Zero-Network Inference)
│   │   └── clip-vit-base-patch32/ # model.safetensors, config.json, tokenizer.json
│   ├── processed/                 # Curated metadata and subsets
│   │   ├── clean_styles.csv       # Clean metadata after integrity validation
│   │   └── subset_1500_eval.csv   # Unified 1,500-product corpus for EDA & evaluation
│   ├── embeddings/                # Precomputed vector store
│   │   ├── image_embeddings.npy   # Image embedding matrix [1500, 512] float32
│   │   ├── image_ids.npy          # Product IDs aligned with embedding rows
│   │   └── metadata_cache.parquet # Fast columnar metadata cache
│   └── fashion_retrieval.db       # Centralized SQLite single source of truth (10 tables: queries, GT, EDA, metrics, catalog)
├── src/
│   ├── __init__.py
│   ├── config.py                  # Global configurations, file paths, CLIP parameters, offline flags
│   ├── data/
│   │   ├── database.py            # Centralized SQLite schema, seed data, and ground-truth relations ORM
│   │   ├── validator.py           # Image integrity checks, missing attribute handling
│   │   ├── sampler.py             # Reproducible stratified sampling pipeline (seed 42)
│   │   ├── eda.py                 # Statistical dataset distribution analysis & report generator
│   │   ├── build_ground_truth.py  # Script for constructing benchmark ground-truth tables
│   │   └── sync_ground_truth.py   # Automated synchronization of ground truth with subsets
│   ├── models/
│   │   ├── clip_engine.py         # Offline CLIP (ViT-B/32) Text & Image Encoders wrapper
│   │   └── indexer.py             # Offline embedding extraction pipeline to .npy & .parquet
│   ├── retrieval/
│   │   └── searcher.py            # Cosine similarity matrix multiplication & Top-K ranking
│   ├── evaluation/
│   │   ├── metrics.py             # IR metrics: P@K, Recall@K, MRR, NDCG@K, Attribute Breakdown
│   │   └── benchmark.py           # Batch automated evaluation runner & report exporter
│   └── web/
│       ├── app.py                 # FastAPI backend server & static asset host
│       └── static/                # AdminLTE v4.9.1 frontend interface (HTML, CSS, JS)
│           ├── adminlte/          # Local AdminLTE v4.9.1 vendor assets
│           ├── vendor/            # Local vendor assets (Source Sans 3, Bootstrap Icons, Tabulator, ApexCharts, Bootstrap)
│           ├── js/
│           │   ├── app.js         # Core application controller & view switcher
│           │   ├── retrieval.js   # Retrieval Lab real-time search module
│           │   ├── groundtruth.js # Ground Truth interactive table & query card visualizer
│           │   ├── benchmark.js   # Quantitative Benchmark evaluation datatable module
│           │   ├── eda.js         # EDA ApexCharts distribution module
│           │   └── dataprep.js    # Data preparation pipeline waterfall module
│           ├── css/app.css        # Application custom styles & design tokens
│           └── index.html         # Interactive Multimodal Retrieval Dashboard
├── tests/
│   ├── test_config.py             # Pytest test suite for environment, paths, & hyperparameter configs
│   ├── test_database.py           # Pytest test suite for SQLite schema, relations, & entities
│   └── test_metrics.py            # Pytest test suite for Information Retrieval evaluation metrics
├── setup_pipeline.sh              # Automated end-to-end setup script (seed, sample, EDA, GT sync, index, eval)
├── start.sh                       # Production web dashboard runner script (Uvicorn FastAPI)
├── SYSTEM_DESIGN.md               # Comprehensive system architecture and theoretical analysis
├── requirements.txt               # Python package dependencies
└── README.md                      # Project documentation
```

## Technology Stack

- **Programming Language**: Python 3.10 - 3.13
- **Deep Learning & Vision**: PyTorch, Hugging Face Transformers (`openai/clip-vit-base-patch32` running 100% offline), Pillow
- **Data & Vector Processing**: NumPy, Pandas, PyArrow (Parquet)
- **Database & Storage**: SQLite (`data/fashion_retrieval.db`)
- **Backend Service**: FastAPI, Uvicorn
- **Frontend Dashboard**: AdminLTE v4.9.1, Bootstrap 5, Bootstrap Icons, Tabulator Tables v6.4, ApexCharts v3.37, Source Sans 3
- **Testing & Quality Assurance**: Pytest

---

## Installation & Automated Execution Guide

Open your application **Command Prompt (CMD)**, **PowerShell**, or **Terminal (Bash/Zsh)**, navigate into your target directory where the project code resides, and execute the following sequence of commands step by step:

```bash
# 1. Create a virtual environment dedicated to isolating project libraries
python -m venv .venv # Execute this command if you are using Windows
python3 -m venv .venv # Execute this command if you are using Linux/MacOS

# 2. Activate the newly created virtual environment based on your operating system
.venv\Scripts\activate # Execute this command if you are using Windows (Command Prompt / CMD)
.venv\Scripts\Activate.ps1 # Execute this command if you are using Windows (PowerShell)
source .venv/bin/activate # Execute this command if you are using Linux/MacOS

# 3. Upgrade pip and install all Python dependencies required by the system
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Download offline CLIP model weights (openai/clip-vit-base-patch32) into data/models/
python -m src.models.downloader

# [CRITICAL NOTE]: Ensure the fashion dataset is placed in the folder: data/dataset/
# Expected files: data/dataset/styles.csv and data/dataset/images/*.jpg (~44,000 files)
# (Optional GPU Acceleration for NVIDIA CUDA): pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 5. Run the core pipeline stages:
# Option A: Single-command execution (Linux / macOS / Git Bash):
bash setup_pipeline.sh

# Option B: Manual step-by-step execution:
python -m src.data.database # [1/6] Initialize & seed SQLite database schema and static data
python -m src.data.sampler # [2/6] Run data validation & stratified sampling (N=1,500)
python -m src.data.eda # [3/6] Run statistical EDA analysis & report generator
python -m src.data.sync_ground_truth # [4/6] Synchronize 30 benchmark queries with dataset
python -m src.models.indexer # [5/6] Compute offline image embeddings (CLIP ViT-B/32)
python -m src.evaluation.benchmark # [6/6] Run automated batch evaluation on benchmark queries

# 6. Run unit test suite (optional)
python -m pytest tests/ -v

# 7. Launch the interactive Research Dashboard server (FastAPI & AdminLTE) - keep this terminal window open
# Run this for isolated local access (localhost / development)
python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000 --reload
# Run this to allow access from any device on your network (Wi-Fi/LAN/Docker)
python -m uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser and visit:

- **Research Dashboard**: `http://127.0.0.1:8000`
- **Ground Truth View**: `http://127.0.0.1:8000/#groundtruth`
- **Interactive OpenAPI/Swagger Documentation**: `http://127.0.0.1:8000/docs`

---

## API Endpoints Documentation

FastAPI provides an automatic interactive Swagger UI documentation at `http://127.0.0.1:8000/docs`.

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/` | `GET` | Serves the interactive Research Dashboard (AdminLTE v4.9.1). |
| `/api/search` | `GET` | Performs real-time text-to-image retrieval. Parameters: `q` (query string), `top_k` (number of results, optional), `gender` (gender filter, optional). |
| `/api/ground-truth` | `GET` | Returns list of 2,014 ground truth product-to-query relevance relations with multi-attribute criteria and summary statistics. Parameters: `query_id`, `level`, `article_type`, `search` (optional). |
| `/api/benchmark-queries` | `GET` | Returns list of 30 benchmark queries with ground-truth criteria and ambiguity levels. |
| `/api/benchmark-report` | `GET` | Returns complete precomputed benchmark evaluation metrics directly from SQLite database. |
| `/api/eda-stats` | `GET` | Returns metadata completeness and attribute distribution statistics directly from SQLite database. |
| `/api/benchmark-ground-truth` | `GET` | Returns complete benchmark ground truth criteria and relevance mappings directly from SQLite database. |
| `/api/data-preparation` | `GET` | Returns pipeline stages, attrition waterfall, and corpus composition for research transparency. |
| `/api/db-status` | `GET` | Returns SQLite database status, file size, and table row counts. |
| `/api/images/{filename}` | `GET` | Streams catalog product images directly from the dataset directory. |


---

## Unit Testing

The test suite validates configuration settings, database integrity, and Information Retrieval evaluation metric formulas (`Precision@K`, `Recall@K`, and `is_item_relevant`):

```bash
python -m pytest tests/ -v
# or:
# pytest tests/ -v
```

Expected test execution output:

```text
tests/test_config.py::test_config_base_paths PASSED
tests/test_config.py::test_config_model_and_inference PASSED
tests/test_config.py::test_config_retrieval_and_eval PASSED
tests/test_config.py::test_config_web_server PASSED
tests/test_database.py::test_sqlite_db_exists PASSED
tests/test_database.py::test_system_configs PASSED
tests/test_database.py::test_target_article_types PASSED
tests/test_database.py::test_audit_samples PASSED
tests/test_database.py::test_retrieval_insights PASSED
tests/test_database.py::test_benchmark_queries PASSED
tests/test_database.py::test_benchmark_ground_truth_dict PASSED
tests/test_database.py::test_ground_truth_product_ids PASSED
tests/test_database.py::test_products_table PASSED
tests/test_database.py::test_benchmark_report_from_db PASSED
tests/test_database.py::test_eda_report_from_db PASSED
tests/test_metrics.py::test_is_item_relevant PASSED
tests/test_metrics.py::test_precision_at_k PASSED
tests/test_metrics.py::test_recall_at_k PASSED
============================== 18 passed in 3.39s ==============================
```

---

## References & Related Documents

- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md): Comprehensive system design blueprint, mathematical formulation of the *Shared Latent Space*, error taxonomy, and architectural patterns.
- Radford, A. et al. (2021). *Learning Transferable Visual Models From Natural Language Supervision (CLIP)*. OpenAI / ICML.
