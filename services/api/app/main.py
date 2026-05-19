from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.services.bubble_detector import detector
from app.services.manga_ocr_engine import ocr_engine


settings = get_settings()

app = FastAPI(title=settings.app_name)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def warm_runtime_models() -> None:
    detector.load_model()
    ocr_engine.load_model()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
