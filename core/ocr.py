import os
import cv2
import re
import logging
import pytesseract
from pyzbar.pyzbar import decode as decode_barcode
from pylibdmtx.pylibdmtx import decode as decode_dmtx
import config

# Configuración y carga de Tesseract
TESSERACT_HABILITADO = False
if os.path.exists(config.RUTA_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = config.RUTA_TESSERACT
    TESSERACT_HABILITADO = True

# Carga de PaddleOCR
PADDLE_DISPONIBLE = False
paddle_reader = None

def init_paddle():
    global paddle_reader, PADDLE_DISPONIBLE
    if paddle_reader is not None:
        return
    try:
        from paddleocr import PaddleOCR
        logging.getLogger("ppocr").setLevel(logging.ERROR)
        paddle_reader = PaddleOCR(
            det_model_dir=os.path.join(config.RUTA_BASE_IA, 'det_v3'),
            cls_model_dir=os.path.join(config.RUTA_BASE_IA, 'cls_v2'),
            rec_model_dir=os.path.join(config.RUTA_BASE_IA, 'modelo_final_real', 'mi_modelo_final'),
            rec_char_dict_path=os.path.join(config.RUTA_BASE_IA, 'modelo_final_real', 'mi_modelo_final', 'en_dict.txt'),
            use_angle_cls=True,
            ocr_version='PP-OCRv3',
            lang='en',
            show_log=False,
            use_gpu=False
        )
        PADDLE_DISPONIBLE = True
        print("[OK] IA CUSTOM (PaddleOCR) CARGADA EXITOSAMENTE")
    except Exception as e:
        print(f"[ERROR] Error cargando IA: {e}")

# Carga de EasyOCR
EASYOCR_DISPONIBLE = False
lector_easyocr = None

def init_easyocr():
    global lector_easyocr, EASYOCR_DISPONIBLE
    if lector_easyocr is not None:
        return
    try:
        import easyocr
        # Desactivar GPU por seguridad en threads CPU
        lector_easyocr = easyocr.Reader(['en'], gpu=False, verbose=False)
        EASYOCR_DISPONIBLE = True
        print("[OK] EasyOCR CARGADO EXITOSAMENTE")
    except Exception as e:
        print(f"[ERROR] Error cargando EasyOCR: {e}")

# Funciones de apoyo
def limpiar_texto_basico(txt):
    return re.sub(r'[^A-Z0-9 ]', '', str(txt).strip().upper())

def obtener_nivel(texto_ubicacion):
    try:
        if not re.match(config.REGEX_UBICACION, texto_ubicacion): return None
        return int(texto_ubicacion[3])
    except: 
        return None

def agregar_padding(img, pixels):
    return cv2.copyMakeBorder(img, pixels, pixels, pixels, pixels, cv2.BORDER_CONSTANT, value=[255, 255, 255])

def leer_barcode_super(img_crop):
    img_padded = agregar_padding(img_crop, 50)
    try:
        res = decode_barcode(img_padded)
        if res: 
            return res[0].data.decode("utf-8").strip(), "Scanner-Zbar"
    except: 
        pass
    return None, "FALLO"

def leer_ubicacion_con_diagnostico(img_crop, debug_name):
    h_orig, w_orig = img_crop.shape[:2]
    
    # NIVEL 1: DataMatrix
    try:
        img_dm = agregar_padding(img_crop, 40)
        res_dm = decode_dmtx(img_dm, timeout=60)
        if res_dm:
            txt_raw = res_dm[0].data.decode("utf-8").upper().strip()
            if "BIS" in txt_raw and " BIS" not in txt_raw: txt_raw = txt_raw.replace("BIS", " BIS")
            txt = limpiar_texto_basico(txt_raw)
            if re.match(config.REGEX_UBICACION, txt): 
                return txt, "DataMatrix"
    except: 
        pass

    # NIVEL 2: IA CUSTOM (Paddle)
    if PADDLE_DISPONIBLE:
        recortes = [("FULL", img_crop), ("CROP35", img_crop[:, int(w_orig*0.35):])]
        for nombre, img_test in recortes:
            img_zoom = cv2.resize(img_test, (0,0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            try:
                img_rgb = cv2.cvtColor(img_zoom, cv2.COLOR_BGR2RGB)
                res = paddle_reader.ocr(img_rgb, cls=True)
                if res and res[0]:
                    for linea in res[0]:
                        txt_raw = linea[1][0].upper().strip()
                        if "BIS" in txt_raw and " BIS" not in txt_raw: txt_raw = txt_raw.replace("BIS", " BIS")
                        txt_final = limpiar_texto_basico(txt_raw)
                        if re.match(config.REGEX_UBICACION, txt_final): 
                            return txt_final, f"IA-{nombre}"
            except: 
                pass

    # NIVEL 3: EasyOCR
    if EASYOCR_DISPONIBLE:
        try:
            # Recorte derecho igual que en tesseract
            img_rec = img_crop[:, int(w_orig*0.35):]
            img_zoom = cv2.resize(img_rec, (0,0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            resultados = lector_easyocr.readtext(img_zoom)
            if resultados:
                # Ordenar por confianza (opcional) o tomar el primero
                txt_raw = resultados[0][1].upper().strip()
                if "BIS" in txt_raw and " BIS" not in txt_raw: txt_raw = txt_raw.replace("BIS", " BIS")
                txt_limpio = limpiar_texto_basico(txt_raw)
                if re.match(config.REGEX_UBICACION, txt_limpio): 
                    return txt_limpio, "EasyOCR"
        except: 
            pass

    # NIVEL 4: Tesseract
    if TESSERACT_HABILITADO:
        try:
            img_rec = img_crop[:, int(w_orig*0.35):]
            gray = cv2.cvtColor(img_rec, cv2.COLOR_BGR2GRAY)
            txt = pytesseract.image_to_string(gray, config='--psm 7').strip()
            txt_raw = txt.upper().strip()
            if "BIS" in txt_raw and " BIS" not in txt_raw: txt_raw = txt_raw.replace("BIS", " BIS")
            txt_limpio = limpiar_texto_basico(txt_raw)
            if re.match(config.REGEX_UBICACION, txt_limpio): 
                return txt_limpio, "Tesseract"
        except: 
            pass
            
    return None, "FALLO"
