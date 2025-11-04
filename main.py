# process.py — Refactored version
import cv2
from ultralytics import YOLO
from pathlib import Path

def load_model(model_path: str):
    """Load YOLO model dynamically."""
    return YOLO(model_path)

def draw_boxes(image, boxes, color=(0, 255, 0), thickness=2):
    """Draw bounding boxes on an image."""
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
    return image

def process_image(img_path: str, model_path: str, threshold: float = 0.5, output_path: str = "output.jpg"):
    """Run inference on a single image and save annotated output."""
    model = load_model(model_path)
    results = model(img_path)
    for result in results:
        filtered_boxes = [box for box in result.boxes if box.conf[0] >= threshold]
        annotated = draw_boxes(result.orig_img, filtered_boxes)
        cv2.imwrite(output_path, annotated)
        print(f"Saved annotated image to {Path(output_path).resolve()}")