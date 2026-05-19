from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Some standard font paths for Linux
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]

@dataclass
class RenderBlock:
    """The text and position for a bubble we want to draw"""
    box: tuple[int, int, int, int]
    text: str
    polygon: tuple[tuple[int, int], ...] | None = None

class BubbleTypesetter:
    """
    Clears the original Japanese text and draws the new English text
    """

    def render(self, image: Image.Image, blocks: list[RenderBlock]) -> Image.Image:
        # Work on a copy of the image
        output = image.convert("RGB").copy()
        draw = ImageDraw.Draw(output)

        # 1. First, clear all the bubbles
        for b in blocks:
            if b.polygon:
                # Use the exact shape of the bubble
                draw.polygon(b.polygon, fill="white")
                draw.line(b.polygon + (b.polygon[0],), fill="black", width=2)
            else:
                # Use a rounded rectangle if no polygon is available
                # We add a tiny bit of extra padding to the clear area to be safe
                x1, y1, x2, y2 = b.box
                clear_box = (x1-2, y1-2, x2+2, y2+2)
                draw.rounded_rectangle(clear_box, radius=10, fill="white", outline="black", width=2)

        # 2. Then, draw the text in each bubble
        for b in blocks:
            self._draw_text(output, b)

        return output

    def _draw_text(self, image, block):
        draw = ImageDraw.Draw(image)
        
        # Calculate the area we can draw in
        x1, y1, x2, y2 = block.box
        width = x2 - x1
        height = y2 - y1
        
        # Smart padding: Very thin bubbles get almost no padding
        # so that text like "Who...?" can fit.
        if width < 50:
            pad_w = 2
        elif width < 100:
            pad_w = int(width * 0.08)
        else:
            pad_w = int(width * 0.15)
            
        pad_h = int(height * 0.1) if height < 100 else int(height * 0.15)
        
        text_area = (x1 + pad_w, y1 + pad_h, x2 - pad_w, y2 - pad_h)
        area_w = max(1, text_area[2] - text_area[0])
        area_h = max(1, text_area[3] - text_area[1])
        
        # Try different font sizes until one fits the bubble
        best_lines = []
        best_font = None
        best_font_size = 12
        
        # We allow the font to go down to 6 for really tiny bubbles
        for size in range(32, 5, -1):
            font = self._get_font(size)
            lines = self._wrap_text(draw, block.text, font, area_w)
            
            line_height = size + 2
            total_h = len(lines) * line_height
            
            # Check if this size fits both width and height
            fits_width = True
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                if (bbox[2] - bbox[0]) > area_w:
                    fits_width = False
                    break
            
            if fits_width and total_h <= area_h:
                best_lines = lines
                best_font = font
                best_font_size = size
                break
            
            # Keep track of the "least bad" option
            if not best_lines or size > best_font_size:
                best_lines = lines
                best_font = font
                best_font_size = size

        # Final drawing
        line_h = best_font_size + 2
        y = text_area[1] + (area_h - (len(best_lines) * line_h)) // 2
        
        for line in best_lines:
            bbox = draw.textbbox((0, 0), line, font=best_font)
            line_w = bbox[2] - bbox[0]
            x = text_area[0] + (area_w - line_w) // 2
            draw.text((x, y), line, fill="black", font=best_font)
            y += line_h

    def _wrap_text(self, draw, text, font, max_w):
        """Simple word wrapping helper"""
        # If the word itself is wider than max_w, we'll have to split it by character
        # but for an undergrad project, just splitting by words is a good start.
        words = text.split()
        if not words:
            return [""]
            
        lines = []
        current_line = []
        
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if (bbox[2] - bbox[0]) <= max_w:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Single word is too wide, just force it or split it?
                    # Let's just force it for now.
                    lines.append(word)
                    current_line = []
        
        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def _get_font(self, size):
        for p in FONT_PATHS:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

typesetter = BubbleTypesetter()
