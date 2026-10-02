"""
Download CLIP Model Weights from Hugging Face for 100% Offline Inference.

This module downloads the required pretrained weights and tokenizer configurations
for 'openai/clip-vit-base-patch32' directly from Hugging Face Hub and saves them
into 'data/models/clip-vit-base-patch32/'.

Once downloaded, the entire multimodal retrieval system (indexer, searcher, web app)
operates completely offline with zero outbound network calls.

Usage:
    python -m src.models.downloader
    python -m src.models.downloader --force
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path if run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Default Hugging Face repository and target directory
DEFAULT_REPO_ID = "openai/clip-vit-base-patch32"
DEFAULT_TARGET_DIR = config.LOCAL_CLIP_DIR

# File patterns to exclude (saving bandwidth and disk storage by avoiding unnecessary frameworks)
# NOTE: *.bin is NOT excluded because openai/clip-vit-base-patch32 stores weights in pytorch_model.bin!
IGNORE_PATTERNS = [
    "*.h5",         # Exclude TensorFlow / Keras weights
    "*.ot",         # Exclude Rust / LibTorch weights
    "*.msgpack",    # Exclude Flax weights
    "*.onnx",       # Exclude ONNX weights
    "*.onnx_data",
    ".gitattributes",
]


def check_existing_weights(target_dir: Path) -> Path | None:
    """Checks if valid model weights already exist in the target directory."""
    safetensors_file = target_dir / "model.safetensors"
    bin_file = target_dir / "pytorch_model.bin"

    if safetensors_file.exists():
        return safetensors_file
    elif bin_file.exists():
        return bin_file
    return None


def convert_bin_to_safetensors(target_dir: Path) -> bool:
    """Converts pytorch_model.bin to model.safetensors for faster offline loading and smaller footprint."""
    bin_file = target_dir / "pytorch_model.bin"
    safetensors_file = target_dir / "model.safetensors"

    if not bin_file.exists():
        return False

    try:
        import torch
        from safetensors.torch import save_file

        logger.info("Converting pytorch_model.bin to model.safetensors for optimized offline inference")
        try:
            state_dict = torch.load(bin_file, map_location="cpu", weights_only=True)
        except (TypeError, Exception):
            state_dict = torch.load(bin_file, map_location="cpu")

        save_file(state_dict, str(safetensors_file))
        logger.info("Successfully converted weights to model.safetensors")

        # Remove the legacy bin file to reclaim ~605 MB disk space
        try:
            bin_file.unlink()
            logger.info("Cleaned up temporary pytorch_model.bin (freed ~605 MB).")
        except Exception as e:
            logger.warning(f"Could not delete pytorch_model.bin: {e}")

        return True
    except Exception as e:
        logger.warning(f"Could not convert to safetensors ({e}). Keeping pytorch_model.bin for inference.")
        return False


def download_clip_model(
    repo_id: str = DEFAULT_REPO_ID,
    target_dir: Path = DEFAULT_TARGET_DIR,
    force: bool = False,
    verify: bool = True,
) -> bool:
    """
    Downloads model weights, tokenizer, and config files from Hugging Face Hub
    into the specified target directory (data/models/clip-vit-base-patch32).
    """
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    print("Hugging Face Model Downloader for Offline Inference")
    print(f"Source Repository : {repo_id}")
    print(f"Target Directory  : {target_dir}")

    # Check if already downloaded
    existing_weights = check_existing_weights(target_dir)
    if not force and existing_weights is not None:
        logger.info(f"Model already exists at: {target_dir}")
        logger.info(
            f"Found model weights: {existing_weights.name} "
            f"({existing_weights.stat().st_size / (1024 * 1024):.1f} MB)"
        )

        # If only pytorch_model.bin exists, attempt conversion to safetensors
        if existing_weights.name == "pytorch_model.bin":
            convert_bin_to_safetensors(target_dir)

        print("\n[NOTE] Use --force to re-download all files.\n")
        if verify:
            return verify_downloaded_model(target_dir)
        return True

    # Temporarily unset offline flags to allow downloading from Hugging Face Hub
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)
    os.environ["HF_HUB_OFFLINE"] = "0"
    os.environ["TRANSFORMERS_OFFLINE"] = "0"

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        logger.error(
            "The 'huggingface_hub' library is not installed. "
            "Please run: pip install huggingface-hub"
        )
        return False

    logger.info(f"Starting download of '{repo_id}' to '{target_dir}'")
    logger.info("Downloading weights (pytorch_model.bin / safetensors), configs, and tokenizer")

    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(target_dir),
            ignore_patterns=IGNORE_PATTERNS,
            max_workers=4,
            force_download=force,
        )
        logger.info("Download completed successfully")
    except Exception as e:
        logger.error(f"Download failed with error: {e}")
        return False

    # Convert pytorch_model.bin to safetensors if needed
    if (target_dir / "pytorch_model.bin").exists() and not (target_dir / "model.safetensors").exists():
        convert_bin_to_safetensors(target_dir)

    # List all files downloaded
    print("\nDownloaded files:")
    for file in sorted(target_dir.glob("*")):
        if file.is_file():
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f" - {file.name:<25} ({size_mb:6.2f} MB)")

    # Run verification
    if verify:
        return verify_downloaded_model(target_dir)

    return True


def verify_downloaded_model(target_dir: Path) -> bool:
    """
    Verifies that the downloaded model can be loaded strictly offline
    without any network calls.
    """
    logger.info("Verifying model for 100% offline compatibility")

    # Enforce strictly offline flags for verification
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    try:
        from transformers import CLIPModel, CLIPProcessor

        logger.info("Verifying CLIP processor offline loading")
        processor = CLIPProcessor.from_pretrained(str(target_dir), local_files_only=True)

        logger.info("Verifying CLIP model offline loading")
        model = CLIPModel.from_pretrained(str(target_dir), local_files_only=True)

        logger.info("Verification Successful")
        logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
        logger.info("The model is ready for 100% offline inference in data/models/")
        return True
    except Exception as e:
        logger.error(f"Offline verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Download CLIP model weights and tokenizer from Hugging Face into data/models/"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_REPO_ID,
        help=f"Hugging Face repository ID (default: {DEFAULT_REPO_ID})",
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        default=str(DEFAULT_TARGET_DIR),
        help=f"Target directory path (default: {DEFAULT_TARGET_DIR})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if model files already exist",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip offline verification test after downloading",
    )

    args = parser.parse_args()

    success = download_clip_model(
        repo_id=args.model,
        target_dir=Path(args.target_dir),
        force=args.force,
        verify=not args.skip_verify,
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
