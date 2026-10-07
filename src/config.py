import os
import sys
from pathlib import Path

# Helper to load .env file without external dependencies
def _load_env_file():
    """Loads environment variables from .env file if it exists."""
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists() and env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if v != "" and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass
            break

_load_env_file()

# Enforce offline mode for Hugging Face Hub to eliminate redundant online calls & latency
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Base Paths (Configurable via .env or auto-detected)
_DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_env_project_root = (os.environ.get("PROJECT_ROOT") or "").strip()
if (
    _env_project_root
    and _env_project_root.lower() not in ("auto", "none", "detect", "default")
    and Path(_env_project_root).exists()
):
    PROJECT_ROOT = Path(_env_project_root).resolve()
else:
    PROJECT_ROOT = _DEFAULT_PROJECT_ROOT

# Ensure PROJECT_ROOT is in sys.path for robust module resolution
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_env_data_dir = os.environ.get("DATA_DIR")
if _env_data_dir and Path(_env_data_dir).exists():
    DATA_DIR = Path(_env_data_dir).resolve()
else:
    DATA_DIR = PROJECT_ROOT / "data"

_env_dataset_dir = os.environ.get("DATASET_DIR")
if _env_dataset_dir and Path(_env_dataset_dir).exists():
    DATASET_DIR = Path(_env_dataset_dir).resolve()
else:
    DATASET_DIR = DATA_DIR / "dataset"

PROCESSED_DATA_DIR = DATA_DIR / "processed"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"

_env_models_dir = os.environ.get("MODELS_DIR")
if _env_models_dir and Path(_env_models_dir).exists():
    MODELS_DIR = Path(_env_models_dir).resolve()
else:
    MODELS_DIR = DATA_DIR / "models"

def has_local_clip_weights(clip_dir: Path) -> bool:
    """Checks if local directory contains model weights (safetensors or bin)."""
    return clip_dir.exists() and (
        (clip_dir / "model.safetensors").exists()
        or (clip_dir / "pytorch_model.bin").exists()
    )

_env_local_clip = os.environ.get("LOCAL_CLIP_DIR")
if _env_local_clip and Path(_env_local_clip).exists():
    _p = Path(_env_local_clip).resolve()
    if has_local_clip_weights(_p):
        LOCAL_CLIP_DIR = _p
    elif (_p / "clip-vit-base-patch32").exists():
        LOCAL_CLIP_DIR = _p / "clip-vit-base-patch32"
    else:
        LOCAL_CLIP_DIR = _p
else:
    LOCAL_CLIP_DIR = MODELS_DIR / "clip-vit-base-patch32"

# Dataset Files & Images
ARCHIVE_DIR = PROJECT_ROOT / "archive"
FASHION_DATASET_DIR = PROJECT_ROOT / "fashion-dataset"

# Styles CSV Resolution (Overridable via .env)
_env_styles_csv = os.environ.get("STYLES_CSV_PATH")
if _env_styles_csv and Path(_env_styles_csv).exists():
    STYLES_CSV_PATH = Path(_env_styles_csv).resolve()
    DATASET_ROOT = STYLES_CSV_PATH.parent
elif (DATASET_DIR / "styles.csv").exists():
    DATASET_ROOT = DATASET_DIR
    STYLES_CSV_PATH = DATASET_DIR / "styles.csv"
elif (ARCHIVE_DIR / "styles.csv").exists():
    DATASET_ROOT = ARCHIVE_DIR
    STYLES_CSV_PATH = ARCHIVE_DIR / "styles.csv"
elif (FASHION_DATASET_DIR / "styles.csv").exists():
    DATASET_ROOT = FASHION_DATASET_DIR
    STYLES_CSV_PATH = FASHION_DATASET_DIR / "styles.csv"
else:
    DATASET_ROOT = DATASET_DIR
    STYLES_CSV_PATH = DATASET_DIR / "styles.csv"

# Images Directory Resolution (Overridable via .env, fallback to standard locations)
_env_images_dir = os.environ.get("IMAGES_DIR")
if _env_images_dir and Path(_env_images_dir).exists():
    IMAGES_DIR = Path(_env_images_dir).resolve()
elif (DATASET_DIR / "images").exists():
    IMAGES_DIR = DATASET_DIR / "images"
elif (ARCHIVE_DIR / "images").exists():
    IMAGES_DIR = ARCHIVE_DIR / "images"
elif (FASHION_DATASET_DIR / "images").exists():
    IMAGES_DIR = FASHION_DATASET_DIR / "images"
elif (DATA_DIR / "images").exists():
    IMAGES_DIR = DATA_DIR / "images"
elif (PROJECT_ROOT / "images").exists():
    IMAGES_DIR = PROJECT_ROOT / "images"
else:
    IMAGES_DIR = DATASET_DIR / "images"

# Processed Files
CLEAN_METADATA_PATH = PROCESSED_DATA_DIR / "clean_styles.csv"
SUBSET_500_PATH = PROCESSED_DATA_DIR / "subset_500_eda.csv"
SUBSET_1500_PATH = PROCESSED_DATA_DIR / "subset_1500_eval.csv"

# Precomputed Embeddings
IMAGE_EMBEDDINGS_PATH = EMBEDDINGS_DIR / "image_embeddings.npy"
IMAGE_IDS_PATH = EMBEDDINGS_DIR / "image_ids.npy"
METADATA_CACHE_PATH = EMBEDDINGS_DIR / "metadata_cache.parquet"

# SQLite Database Path
DB_PATH = DATA_DIR / "fashion_retrieval.db"

# Model Configurations (default values, overridable from .env and DB)
if has_local_clip_weights(LOCAL_CLIP_DIR):
    CLIP_MODEL_NAME = str(LOCAL_CLIP_DIR)
else:
    CLIP_MODEL_NAME = os.environ.get("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")

EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "512"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "32"))
RANDOM_SEED = int(os.environ.get("RANDOM_SEED", "42"))

# Device Configuration (auto, cuda, cpu)
_env_device = os.environ.get("DEVICE", "auto").strip().lower()
if _env_device in ("cuda", "cpu"):
    DEVICE = _env_device
else:
    try:
        import torch
        DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        DEVICE = "cpu"

# Retrieval & Evaluation Configurations
DEFAULT_TOP_K = int(os.environ.get("DEFAULT_TOP_K", "20"))
EVAL_K = int(os.environ.get("EVAL_K", "10"))
SUBSET_EVAL_SIZE = int(os.environ.get("SUBSET_EVAL_SIZE", "1500"))
SUBSET_EDA_SIZE = int(os.environ.get("SUBSET_EDA_SIZE", "500"))

# Web Server & Runtime Configurations
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
RELOAD = os.environ.get("RELOAD", "true").strip().lower() in ("true", "1", "yes")
WORKERS = int(os.environ.get("WORKERS", "1"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").strip().upper()

GROUND_TRUTH_JSON_PATH = PROJECT_ROOT / "data" / "benchmark_ground_truth.json"
GROUND_TRUTH_CSV_PATH = PROJECT_ROOT / "data" / "benchmark_ground_truth.csv"


def load_system_configs():
    """Loads system configuration key-values from SQLite database."""
    global CLIP_MODEL_NAME, EMBEDDING_DIM, BATCH_SIZE, RANDOM_SEED
    try:
        from src.data.database import get_system_configs
        configs = get_system_configs()
        if "clip_model_name" in configs:
            if has_local_clip_weights(LOCAL_CLIP_DIR):
                CLIP_MODEL_NAME = str(LOCAL_CLIP_DIR)
            else:
                CLIP_MODEL_NAME = configs["clip_model_name"]
        if "embedding_dim" in configs:
            EMBEDDING_DIM = int(configs["embedding_dim"])
        if "batch_size" in configs:
            BATCH_SIZE = int(configs["batch_size"])
        if "random_seed" in configs:
            RANDOM_SEED = int(configs["random_seed"])
        return configs
    except Exception:
        return {}


def load_target_article_types():
    """Loads target article types from SQLite database with fallback."""
    try:
        from src.data.database import get_target_article_types
        return get_target_article_types()
    except Exception:
        return [
            "Tshirts",
            "Shirts",
            "Casual Shoes",
            "Formal Shoes",
            "Sports Shoes",
            "Watches",
            "Backpacks",
            "Jackets",
            "Jeans",
            "Handbags",
            "Caps",
            "Sunglasses",
        ]


# Target Article Types loaded from SQLite
TARGET_ARTICLE_TYPES = load_target_article_types()


def load_benchmark_queries():
    """Loads 30 benchmark queries from SQLite database as primary source of truth."""
    try:
        from src.data.database import get_benchmark_queries
        queries = get_benchmark_queries(with_relevant_ids=True)
        if queries:
            return queries
        # Auto-seed database if table was not populated yet
        from src.data.database import seed_db
        seed_db()
        queries = get_benchmark_queries(with_relevant_ids=True)
        if queries:
            return queries
    except Exception:
        pass

    if GROUND_TRUTH_JSON_PATH.exists():
        import json
        with open(GROUND_TRUTH_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        queries = []
        for q_id, q_info in data.items():
            queries.append({
                "id": q_id,
                "level": q_info.get("specificity", "General"),
                "text": q_info.get("query_text", ""),
                "target_description": q_info.get("target_description", ""),
                "relevance_criteria": q_info.get("relevance_criteria", ""),
                "total_relevant": q_info.get("total_relevant_answers", len(q_info.get("relevant_product_ids", []))),
                "relevant_ids": set(q_info.get("relevant_product_ids", [])),
            })
        return queries
    return []


BENCHMARK_QUERIES = load_benchmark_queries()
load_system_configs()

