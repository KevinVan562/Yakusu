from PIL import Image
from app.core.config import Settings, get_settings

class MangaOcrEngine:
    """
    This class handles the Japanese OCR. 
    It's lazy-loaded so we don't waste memory until we need it.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.manga_ocr = None

    def extract_text(self, image: Image.Image) -> str:
        # Load the model the first time this is called
        if self.manga_ocr is None:
            from manga_ocr import MangaOcr
            # This might take a while to download on the first run!
            self.manga_ocr = MangaOcr()

        # Run OCR on the image crop
        text = self.manga_ocr(image)
        return text

ocr_engine = MangaOcrEngine()
