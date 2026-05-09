import cv2
import numpy as np
import threading
from ultralytics import YOLO
import config

# Carga del modelo YOLO global para evitar múltiples cargas en memoria.
_modelo_yolo = None
_yolo_lock = threading.Lock()

def get_yolo_model():
    global _modelo_yolo
    if _modelo_yolo is None:
        _modelo_yolo = YOLO(config.MODELO_YOLO_PATH)
    return _modelo_yolo

def preprocesar_imagen(img_full):
    scale = config.YOLO_INPUT_SIZE / max(img_full.shape[:2])
    w, h = int(img_full.shape[1] * scale), int(img_full.shape[0] * scale)
    return cv2.resize(img_full, (w, h)), scale

def detectar_elementos(img_full):
    """
    Recibe la imagen original y devuelve las cajas de ubicaciones y HUs encontradas.
    """
    model = get_yolo_model()
    img_resized, scale = preprocesar_imagen(img_full)
    
    # Inferencia con Lock para evitar colisiones de memoria en CPU multihilo
    with _yolo_lock:
        results = model.predict(img_resized, conf=config.CONF_GLOBAL, verbose=False)[0]
    
    elementos = []
    
    if results.boxes:
        for box, cls_id, conf in zip(results.boxes.xyxy.cpu().numpy(), results.boxes.cls.cpu().numpy(), results.boxes.conf.cpu().numpy()):
            cls_idx = int(cls_id)
            if cls_idx == 1: continue # Ignorar cantidad
            if float(conf) < config.UMBRALES_CLASE.get(cls_idx, 0.10): continue
            
            x1, y1, x2, y2 = (box / scale).astype(int)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img_full.shape[1], x2), min(img_full.shape[0], y2)
            
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            crop = img_full[y1:y2, x1:x2]
            
            elementos.append({
                'cls': cls_idx,
                'conf': float(conf),
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                'cx': cx, 'cy': cy,
                'crop': crop
            })
            
    return elementos

def dibujar_debug(img_debug, elem, texto_final, color):
    x1, y1, x2, y2 = elem['x1'], elem['y1'], elem['x2'], elem['y2']
    conf = elem['conf']
    etiqueta_vis = config.MAPA_CLASES_CORREGIDO.get(elem['cls'], str(elem['cls']))
    
    cv2.rectangle(img_debug, (x1, y1), (x2, y2), color, 8)
    lbl_yolo = f"{etiqueta_vis} {conf:.2f}"
    (w1, h1), _ = cv2.getTextSize(lbl_yolo, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
    cv2.rectangle(img_debug, (x1, y1 - h1 - 15), (x1 + w1 + 10, y1), color, -1)
    cv2.putText(img_debug, lbl_yolo, (x1 + 5, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, config.COLOR_WHITE, 3)
    
    if texto_final != "NO_LEIDO":
        lbl_read = f"READ: {texto_final}"
        (w2, h2), _ = cv2.getTextSize(lbl_read, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
        pos_x = max(x1 + w1 + 20, x2 - w2)
        if pos_x + w2 > img_debug.shape[1]: 
            pos_x = img_debug.shape[1] - w2 - 10
        cv2.rectangle(img_debug, (pos_x - 5, y1 - h2 - 15), (pos_x + w2 + 5, y1), config.COLOR_WHITE, -1)
        cv2.putText(img_debug, lbl_read, (pos_x, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, config.COLOR_BLACK, 3)
