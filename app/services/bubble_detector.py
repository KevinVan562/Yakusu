from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from PIL import Image
from app.core.config import Settings, get_settings

@dataclass
class BubbleDetection:
    """A single bubble found by the YOLO model"""
    box: tuple[int, int, int, int]
    confidence: float
    class_name: str
    polygon: tuple[tuple[int, int], ...] | None = None

class BubbleDetector:
    """Uses a YOLOv8 model to find speech bubbles in an image"""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.model = None # We will load the model only when we need it

    def detect(self, image: Image.Image) -> list[BubbleDetection]:
        # Load the model if it hasn't been loaded yet
        if self.model is None:
            from ultralytics import YOLO
            self.model = YOLO(str(self.settings.yolo_model_path))

        # Run the detection
        results = self.model.predict(
            source=image,
            conf=self.settings.yolo_confidence,
            iou=self.settings.yolo_iou,
            imgsz=self.settings.yolo_image_size,
            save=False,
            verbose=False
        )
        
        if not results:
            return []

        result = results[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []

        # Get coordinates, confidence, and masks (if the model has them)
        xyxy_values = boxes.xyxy.cpu().numpy()
        confidence_values = boxes.conf.cpu().numpy()
        
        # Get polygons from masks for better accuracy
        mask_polygons = []
        if hasattr(result, "masks") and result.masks is not None:
            for raw_poly in result.masks.xy:
                points = []
                for px, py in raw_poly:
                    points.append((int(px), int(py)))
                mask_polygons.append(tuple(points))

        detections = []
        for i in range(len(xyxy_values)):
            raw_box = xyxy_values[i]
            
            # Clamp the coordinates so they are inside the image
            x1 = max(0, int(raw_box[0]) - 8)
            y1 = max(0, int(raw_box[1]) - 8)
            x2 = min(image.width, int(raw_box[2]) + 8)
            y2 = min(image.height, int(raw_box[3]) + 8)
            
            polygon = mask_polygons[i] if i < len(mask_polygons) else None
            
            detections.append(
                BubbleDetection(
                    box=(x1, y1, x2, y2),
                    confidence=float(confidence_values[i]),
                    class_name="bubble",
                    polygon=polygon
                )
            )

        # Sort the bubbles so they follow the Japanese reading order
        # (Top to bottom, Right to Left)
        detections.sort(key=lambda d: (d.box[1], -d.box[0]))
        return detections

detector = BubbleDetector()
