from manga_ocr import MangaOcr
from app.core.config import get_settings

def warmup():
    print("Pre-downloading manga-ocr model...")
    settings = get_settings()
    # Initializing MangaOcr triggers the download of the model weights
    _ = MangaOcr(model_id=settings.manga_ocr_model_id)
    print("manga-ocr model downloaded successfully.")

if __name__ == "__main__":
    warmup()
