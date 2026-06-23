"""
Model Manager — Download and manage DeepDoc ONNX models.

Downloads models from HuggingFace 'InfiniFlow/deepdoc' repository.
Caches models locally in the configured model directory.
"""

import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models", "deepdoc",
)

HUGGINGFACE_REPO_ID = "InfiniFlow/deepdoc"

# Required model files for layout recognition
LAYOUT_MODEL_FILE = "layout.onnx"
TABLE_MODEL_FILE = "tsr.onnx"


def get_model_dir() -> str:
    """Get the model directory path from environment or default."""
    return os.environ.get("DEEPDOC_MODEL_DIR", DEFAULT_MODEL_DIR)


def is_model_available(model_name: str = LAYOUT_MODEL_FILE) -> bool:
    """Check if a model file exists in the model directory."""
    model_dir = get_model_dir()
    model_path = os.path.join(model_dir, model_name)
    return os.path.exists(model_path)


def download_models(force: bool = False) -> str:
    """
    Download DeepDoc models from HuggingFace.

    Args:
        force: If True, re-download even if models exist

    Returns:
        Path to the model directory

    Raises:
        RuntimeError: If download fails
    """
    model_dir = get_model_dir()

    if not force and is_model_available():
        logger.info("Models already available at %s", model_dir)
        return model_dir

    logger.info(
        "Downloading DeepDoc models from HuggingFace repo: %s",
        HUGGINGFACE_REPO_ID,
    )

    try:
        from huggingface_hub import snapshot_download

        downloaded_dir = snapshot_download(
            repo_id=HUGGINGFACE_REPO_ID,
            local_dir=model_dir,
            local_dir_use_symlinks=False,
            allow_patterns=["*.onnx"],
        )
        logger.info("Models downloaded to: %s", downloaded_dir)
        return downloaded_dir

    except ImportError:
        raise RuntimeError(
            "huggingface-hub is required for model download. "
            "Install it with: pip install huggingface-hub"
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to download models from {HUGGINGFACE_REPO_ID}: {e}"
        )


def ensure_layout_model() -> str:
    """
    Ensure the layout model is available, downloading if necessary.

    Returns:
        Path to the model directory

    Raises:
        RuntimeError: If model cannot be obtained
    """
    model_dir = get_model_dir()

    if is_model_available():
        return model_dir

    # Try to download
    return download_models()


def ensure_table_model() -> str:
    """
    Ensure the table structure model (tsr.onnx) is available.

    Returns:
        Path to the model directory

    Raises:
        RuntimeError: If model cannot be obtained
    """
    model_dir = get_model_dir()

    if is_model_available(TABLE_MODEL_FILE):
        return model_dir

    # Download all models (includes tsr.onnx)
    return download_models()


def get_model_info() -> dict:
    """Get information about available models."""
    model_dir = get_model_dir()
    info = {
        "model_dir": model_dir,
        "available": is_model_available(),
        "models": {},
    }

    if os.path.exists(model_dir):
        for f in os.listdir(model_dir):
            if f.endswith(".onnx"):
                path = os.path.join(model_dir, f)
                info["models"][f] = {
                    "path": path,
                    "size_mb": round(os.path.getsize(path) / (1024 * 1024), 2),
                }

    return info
