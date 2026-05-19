from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Yakusu API"
    yolo_model_path: Path = PROJECT_ROOT / "models" / "manga-bubble-yolov8.pt"
    yolo_confidence: float = 0.25
    yolo_iou: float = 0.7
    yolo_image_size: int = 1024
    yolo_device: str | None = None
    cache_root: Path = PROJECT_ROOT / ".cache"
    manga_ocr_model_id: str = "kha-white/manga-ocr-base"

    llm_provider: str = ""
    llm_api_key: str | None = None
    llm_model_name: str | None = None
    llm_base_url: str | None = None

    model_config = SettingsConfigDict(env_prefix="YAKUSU_", env_file=".env", extra="ignore")

    def configure_runtime_dirs(self) -> None:
        huggingface_cache = self.cache_root / "huggingface"
        ultralytics_cache = self.cache_root / "ultralytics"

        huggingface_cache.mkdir(parents=True, exist_ok=True)
        (ultralytics_cache / "Ultralytics").mkdir(parents=True, exist_ok=True)

        os.environ.setdefault("HF_HOME", str(huggingface_cache))
        os.environ.setdefault("YOLO_CONFIG_DIR", str(ultralytics_cache))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.configure_runtime_dirs()
    return settings
