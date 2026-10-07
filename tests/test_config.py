from pathlib import Path
from src import config


def test_config_base_paths():
    assert isinstance(config.PROJECT_ROOT, Path)
    assert config.PROJECT_ROOT.exists()
    assert (config.PROJECT_ROOT / "src").exists()
    assert (config.PROJECT_ROOT / "src" / "config.py").exists()
    assert isinstance(config.DATA_DIR, Path)
    assert isinstance(config.DATASET_DIR, Path)
    assert isinstance(config.PROCESSED_DATA_DIR, Path)
    assert isinstance(config.EMBEDDINGS_DIR, Path)
    assert isinstance(config.MODELS_DIR, Path)
    assert isinstance(config.LOCAL_CLIP_DIR, Path)
    assert isinstance(config.DB_PATH, Path)
    assert isinstance(config.IMAGES_DIR, Path)


def test_config_model_and_inference():
    assert isinstance(config.CLIP_MODEL_NAME, str)
    assert len(config.CLIP_MODEL_NAME) > 0
    assert isinstance(config.EMBEDDING_DIM, int)
    assert config.EMBEDDING_DIM == 512
    assert isinstance(config.BATCH_SIZE, int)
    assert config.BATCH_SIZE > 0
    assert isinstance(config.RANDOM_SEED, int)
    assert config.DEVICE in ("cuda", "cpu")


def test_config_retrieval_and_eval():
    assert isinstance(config.DEFAULT_TOP_K, int)
    assert config.DEFAULT_TOP_K > 0
    assert isinstance(config.EVAL_K, int)
    assert config.EVAL_K > 0
    assert isinstance(config.SUBSET_EVAL_SIZE, int)
    assert config.SUBSET_EVAL_SIZE > 0
    assert isinstance(config.SUBSET_EDA_SIZE, int)
    assert config.SUBSET_EDA_SIZE > 0


def test_config_web_server():
    assert isinstance(config.HOST, str)
    assert isinstance(config.PORT, int)
    assert config.PORT > 0
    assert isinstance(config.RELOAD, bool)
    assert isinstance(config.WORKERS, int)
    assert isinstance(config.LOG_LEVEL, str)
