# process.py — Old version
import cv2
from ultralytics import YOLO

def process_image(img_path):
    model = YOLO("models/yolo.pt")
    results = model(img_path)
    for result in results:
        for box in result.boxes:
            conf = box.conf[0]
            if conf > 0.5:
                x1, y1, x2, y2 = box.xyxy[0]
                cv2.rectangle(result.orig_img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
    cv2.imwrite("output.jpg", result.orig_img)