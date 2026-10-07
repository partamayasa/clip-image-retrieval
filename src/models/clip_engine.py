import logging
import os
from pathlib import Path
from typing import List, Union
import numpy as np
from PIL import Image
import torch
from transformers import CLIPModel, CLIPProcessor

from src import config

# Enforce offline mode across the board to completely prevent Hugging Face Hub calls
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class CLIPEngine:
    """Encapsulates CLIP model for generating shared text and image embeddings."""

    def __init__(self, model_name: str = None, device: str = None):
        self.device = device or getattr(config, "DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
        
        # Determine model path: prioritize local saved weights (100% offline)
        if config.has_local_clip_weights(config.LOCAL_CLIP_DIR):
            resolved_model = str(config.LOCAL_CLIP_DIR)
        elif model_name:
            resolved_model = model_name
        else:
            resolved_model = config.CLIP_MODEL_NAME

        logger.info(f"Initializing CLIPEngine with {resolved_model} on device: {self.device}")

        # Ensure offline environment flags are set
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

        try:
            self.model = CLIPModel.from_pretrained(resolved_model, local_files_only=True).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(resolved_model, local_files_only=True)
            logger.info("CLIP model and processor successfully loaded in 100% offline mode.")
        except Exception as e:
            logger.warning(f"Could not load strictly offline ({e}). Attempting download/online fallback.")
            os.environ.pop("HF_HUB_OFFLINE", None)
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
            self.model = CLIPModel.from_pretrained(resolved_model).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(resolved_model)
            # Re-enable offline flags after downloading
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"

        self.model.eval()



    @torch.no_grad()
    def encode_text(self, text_queries: Union[str, List[str]]) -> np.ndarray:
        """
        Generates L2-normalized text embedding vector(s).
        Returns:
            np.ndarray of shape [N, 512] (float32)
        """
        if isinstance(text_queries, str):
            text_queries = [text_queries]

        inputs = self.processor(text=text_queries, return_tensors="pt", padding=True).to(self.device)
        text_outputs = self.model.get_text_features(**inputs)
        if hasattr(text_outputs, "pooler_output") and text_outputs.pooler_output is not None:
            text_features = text_outputs.pooler_output
        elif isinstance(text_outputs, torch.Tensor):
            text_features = text_outputs
        else:
            text_features = text_outputs[0]

        # L2 Normalize
        text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
        return text_features.cpu().numpy().astype(np.float32)

    @torch.no_grad()
    def encode_images(self, images: List[Image.Image]) -> np.ndarray:
        """
        Generates L2-normalized image embedding vector(s).
        Returns:
            np.ndarray of shape [N, 512] (float32)
        """
        inputs = self.processor(images=images, return_tensors="pt", padding=True).to(self.device)
        image_outputs = self.model.get_image_features(**inputs)
        if hasattr(image_outputs, "pooler_output") and image_outputs.pooler_output is not None:
            image_features = image_outputs.pooler_output
        elif isinstance(image_outputs, torch.Tensor):
            image_features = image_outputs
        else:
            image_features = image_outputs[0]

        # L2 Normalize
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        return image_features.cpu().numpy().astype(np.float32)


if __name__ == "__main__":
    engine = CLIPEngine()
    test_vec = engine.encode_text(["red dress", "black formal shoes"])
    print(f"Text embedding shape: {test_vec.shape}")
    print(f"Norm of first vector: {np.linalg.norm(test_vec[0]):.4f}")
