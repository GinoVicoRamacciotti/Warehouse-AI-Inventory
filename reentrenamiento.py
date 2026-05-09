from ultralytics import YOLO  # <--- FALTA ESTO

model = YOLO('yolov8n.pt') # Empezamos de base
model.train(data='data.yaml', epochs=100, imgsz=640)