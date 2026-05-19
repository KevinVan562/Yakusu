from PIL import Image
from app.core.config import get_settings
from app.models.schemas import TextBlock

# The services we wrote
from app.services.bubble_detector import detector
from app.services.manga_ocr_engine import ocr_engine
from app.services.translator import get_translator
from app.services.typesetter import typesetter, RenderBlock

# Global settings
settings = get_settings()

class MangaTextPipeline:
    """
    This is the main class that connects all our services together.
    It takes an image and goes from:
    Detection -> OCR -> Translation -> Final Image
    """

    def __init__(self):
        self.detector = detector
        self.manga_ocr = ocr_engine
        self.translator = get_translator(settings)
        self.typesetter = typesetter

    def extract_blocks(self, image: Image.Image) -> list[TextBlock]:
        """
        Just get the text and positions without translating
        """
        detections = self.detector.detect(image)
        blocks = []

        for i, d in enumerate(detections):
            # Crop the image to where the bubble is
            bubble_crop = image.crop(d.box)
            # Run OCR on the crop
            text = self.manga_ocr.extract_text(bubble_crop)
            
            # Skip it if it's just noise or empty
            if not text.strip():
                continue

            blocks.append(
                TextBlock(
                    id=i + 1,
                    bounding_box=list(d.box),
                    confidence=d.confidence,
                    class_name=d.class_name,
                    text=text
                )
            )
        return blocks

    def render_translation(self, image: Image.Image, target_language: str = "English") -> Image.Image:
        """
        Translate the text and draw it back on the image
        """
        # 1. Detect bubbles and get OCR text
        detections = self.detector.detect(image)
        source_texts = []
        bubbles_to_translate = []

        for d in detections:
            text = self.manga_ocr.extract_text(image.crop(d.box))
            if text.strip():
                source_texts.append(text)
                bubbles_to_translate.append(d)

        # 2. Translate everything in one go
        translations = self.translator.translate_many(source_texts, target_language)

        # 3. Create the blocks for the typesetter
        render_blocks = []
        for i in range(len(bubbles_to_translate)):
            bubble = bubbles_to_translate[i]
            translation = translations[i]
            
            render_blocks.append(
                RenderBlock(
                    box=bubble.box,
                    text=translation.translated_text,
                    polygon=bubble.polygon
                )
            )

        # 4. Render the final image
        return self.typesetter.render(image, render_blocks)

pipeline = MangaTextPipeline()
