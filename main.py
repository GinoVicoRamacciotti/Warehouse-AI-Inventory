import cv2
import os
import re
import time
import pandas as pd
import numpy as np
import pytesseract
import ssl
from ultralytics import YOLO
from pyzbar.pyzbar import decode as decode_barcode
from pylibdmtx.pylibdmtx import decode as decode_dmtx
from openpyxl import load_workbook
import logging

# --- PARCHE DE SEGURIDAD Y MODO OFFLINE ---
ssl._create_default_https_context = ssl._create_unverified_context
os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

# =========================================================
# ⚙️ CONFIGURACIÓN GENERAL
# =========================================================
MODELO_YOLO_PATH = r"runs\detect\train_v2_highres2\weights\best.pt" 
RUTA_TESSERACT = r'C:\Users\Vicog\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
RUTA_BASE_IA = r'C:\Proyectos\Inventario Dron\modelo_ocr_custom'

# Archivos
ARCHIVO_SAP = "Audit Rot.xlsx"
NOMBRE_HOJA = "Planilla de control"
ARCHIVO_REPORTE_DETALLADO = "Reporte_Detallado_IA.xlsx"
ARCHIVO_RELACIONES = "Reporte_Links.xlsx"
CARPETA_FOTOS = "fotos_a_procesar"
CARPETA_DEBUG = "debug_recortes"
CARPETA_FALLOS = "debug_fallos_lectura"

# Parámetros
YOLO_INPUT_SIZE = 3840 
REGEX_UBICACION = r"^[0-9]{2}[A-Z][0-9][A-Z](\sBIS)?$"
UMBRALES_CLASE = {0: 0.15, 2: 0.40} 
RADIO_MAX_CANTIDAD = 3500 
TOLERANCIA_COLUMNA_X = 5000
MAPA_CLASES_CORREGIDO = {0: "barcode", 1: "cantidad", 2: "ubicacion"}
CONF_GLOBAL = 0.10

# Columnas Excel SAP
COL_UBICACION = "Ubicación"      
COL_HU = "Unidad almacén"        
COL_STATUS_OUTPUT = "STATUS_APPSHEET"  
COL_CANTIDAD_OUTPUT = "CANT_IA"        

# Colores BGR
COLOR_UBI = (0, 100, 0)      # Verde
COLOR_BAR = (255, 0, 0)      # Azul (BGR)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)

# =========================================================
# 🧠 CARGA DE IA CUSTOM (TU BLOQUE FUNCIONAL)
# =========================================================
PADDLE_DISPONIBLE = False
try:
    from paddleocr import PaddleOCR
    logging.getLogger("ppocr").setLevel(logging.ERROR)
    
    paddle_reader = PaddleOCR(
        det_model_dir=os.path.join(RUTA_BASE_IA, 'det_v3'),
        cls_model_dir=os.path.join(RUTA_BASE_IA, 'cls_v2'),
        rec_model_dir=os.path.join(RUTA_BASE_IA, 'modelo_final_real', 'mi_modelo_final'),
        rec_char_dict_path=os.path.join(RUTA_BASE_IA, 'modelo_final_real', 'mi_modelo_final', 'en_dict.txt'),
        use_angle_cls=True,
        ocr_version='PP-OCRv3',
        lang='en',
        show_log=False,
        use_gpu=False
    )
    PADDLE_DISPONIBLE = True
    print("✅ IA CUSTOM CARGADA EXITOSAMENTE")
except Exception as e:
    print(f"❌ Error cargando IA: {e}")

if os.path.exists(RUTA_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = RUTA_TESSERACT
    TESSERACT_HABILITADO = True
else:
    TESSERACT_HABILITADO = False

for c in [CARPETA_DEBUG, CARPETA_FALLOS]:
    if not os.path.exists(c): os.makedirs(c)

# =========================================================
# 🛠️ FUNCIONES DE APOYO
# =========================================================

def limpiar_texto_basico(txt):
    return re.sub(r'[^A-Z0-9 ]', '', str(txt).strip().upper())

def obtener_nivel(texto_ubicacion):
    try:
        if not re.match(REGEX_UBICACION, texto_ubicacion): return None
        return int(texto_ubicacion[3])
    except: return None

def distancia_euclidiana(p1, p2):
    return ((p1['cx'] - p2['cx'])**2 + (p1['cy'] - p2['cy'])**2)**0.5

def agregar_padding(img, pixels):
    return cv2.copyMakeBorder(img, pixels, pixels, pixels, pixels, cv2.BORDER_CONSTANT, value=[255, 255, 255])

# --- MOTORES DE LECTURA ---

def leer_barcode_super(img_crop):
    img_padded = agregar_padding(img_crop, 50)
    try:
        res = decode_barcode(img_padded)
        if res: return res[0].data.decode("utf-8").strip(), "Scanner-Zbar"
    except: pass
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
            if re.match(REGEX_UBICACION, txt): return txt, "DataMatrix"
    except: pass

    # NIVEL 2: IA CUSTOM
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
                        if re.match(REGEX_UBICACION, txt_final): return txt_final, f"IA-{nombre}"
            except: pass

    # NIVEL 3: Tesseract
    if TESSERACT_HABILITADO:
        try:
            img_rec = img_crop[:, int(w_orig*0.35):]
            gray = cv2.cvtColor(img_rec, cv2.COLOR_BGR2GRAY)
            txt = pytesseract.image_to_string(gray, config='--psm 7').strip()
            txt_raw = txt.upper().strip()
            if "BIS" in txt_raw and " BIS" not in txt_raw: txt_raw = txt_raw.replace("BIS", " BIS")
            txt_limpio = limpiar_texto_basico(txt_raw)
            if re.match(REGEX_UBICACION, txt_limpio): return txt_limpio, "Tesseract"
        except: pass
    return None, "FALLO"

def determinar_estado(ubi_fisica, hu_fisica, df_sap):
    if ubi_fisica == "NO_LEIDO": return "ERROR VISUAL: ILEGIBLE"
    fila = df_sap[df_sap[COL_UBICACION] == ubi_fisica]
    if fila.empty: return f"ERROR: No existe en SAP"
    sap_hu = str(fila.iloc[0][COL_HU]).strip().replace(".0", "")
    sap_vacio = (sap_hu in ["nan", "", "None", "NaN", "<< vacías >>"])
    if hu_fisica == "VACIO": return "OK" if sap_vacio else "A - Físico Vacío / SAP Ocupado"
    if hu_fisica == "NO_LEIDO": return "E - HU Ilegible"
    if not sap_vacio:
        if sap_hu.endswith(str(hu_fisica)[-6:]): return "OK"
        else: return "C - Diferencia HU"
    return "B - Físico Ocupado / SAP Vacío"

# =========================================================
# 🚀 PROCESAMIENTO
# =========================================================

def procesar_inventario():
    print(f"📂 Cargando SAP...")
    try:
        df_sap = pd.read_excel(ARCHIVO_SAP, sheet_name=NOMBRE_HOJA, dtype=str)
        df_sap.columns = [c.strip() for c in df_sap.columns]
        df_sap[COL_UBICACION] = df_sap[COL_UBICACION].astype(str).str.strip().str.upper()

        sap_hu_map = {}
        for _, row in df_sap.iterrows():
            hu_val = str(row[COL_HU]).strip().replace(".0", "")
            ubi_val = str(row[COL_UBICACION]).strip().upper()
            if hu_val and hu_val not in ["nan", "None", "", "<< vacías >>"]:
                sap_hu_map[hu_val] = ubi_val
        
        print(f"✅ Mapa de SAP cargado: {len(sap_hu_map)} HUs encontradas.")

    except Exception as e: 
        print(f"❌ Error SAP: {e}"); return

    model = YOLO(MODELO_YOLO_PATH)
    imagenes = sorted([f for f in os.listdir(CARPETA_FOTOS) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    
    resultados_finales, registros_globales, reporte_relaciones = {}, [], []

    for img_name in imagenes:
        t_start = time.time()
        img_full = cv2.imread(os.path.join(CARPETA_FOTOS, img_name))
        if img_full is None: continue
        img_debug = img_full.copy()
        h_full_img, w_full_img = img_full.shape[:2]
        centro_img = {'cx': w_full_img // 2, 'cy': h_full_img // 2}

        scale = YOLO_INPUT_SIZE / max(img_full.shape[:2])
        img_resized = cv2.resize(img_full, (int(img_full.shape[1]*scale), int(img_full.shape[0]*scale)))
        results = model.predict(img_resized, conf=CONF_GLOBAL, verbose=False)[0]
        
        ubicaciones, hus = [], []

        if results.boxes:
            for i, (box, cls_id, conf) in enumerate(zip(results.boxes.xyxy.cpu().numpy(), results.boxes.cls.cpu().numpy(), results.boxes.conf.cpu().numpy())):
                cls_idx = int(cls_id)
                if cls_idx == 1: continue 
                if float(conf) < UMBRALES_CLASE.get(cls_idx, 0.10): continue
                
                x1, y1, x2, y2 = (box/scale).astype(int)
                x1, y1, x2, y2 = max(0,x1), max(0,y1), min(img_full.shape[1],x2), min(img_full.shape[0],y2)
                crop = img_full[y1:y2, x1:x2]; cx, cy = (x1+x2)//2, (y1+y2)//2
                
                texto_final, metodo_final, color = "NO_LEIDO", "N/A", (0,0,0)
                etiqueta_vis = MAPA_CLASES_CORREGIDO[cls_idx]

                if cls_idx == 0: # HU
                    color = COLOR_BAR
                    val, met = leer_barcode_super(crop)
                    if val: texto_final, metodo_final = val, met
                    hus.append({'texto': texto_final, 'metodo': metodo_final, 'cx': cx, 'cy': cy, 'usado': False, 'conf': float(conf)})
                elif cls_idx == 2: # Ubicacion
                    color = COLOR_UBI
                    val, met = leer_ubicacion_con_diagnostico(crop, f"{img_name}_{i}")
                    if val: texto_final, metodo_final = val, met
                    ubicaciones.append({'texto': texto_final, 'metodo': metodo_final, 'cx': cx, 'cy': cy, 'usado': False, 'conf': float(conf)})

                cv2.rectangle(img_debug, (x1, y1), (x2, y2), color, 8)
                lbl_yolo = f"{etiqueta_vis} {float(conf):.2f}"
                (w1, h1), _ = cv2.getTextSize(lbl_yolo, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
                cv2.rectangle(img_debug, (x1, y1 - h1 - 15), (x1 + w1 + 10, y1), color, -1)
                cv2.putText(img_debug, lbl_yolo, (x1 + 5, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLOR_WHITE, 3)
                if texto_final != "NO_LEIDO":
                    lbl_read = f"READ: {texto_final}"
                    (w2, h2), _ = cv2.getTextSize(lbl_read, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
                    pos_x = max(x1 + w1 + 20, x2 - w2)
                    if pos_x + w2 > img_full.shape[1]: pos_x = img_full.shape[1] - w2 - 10
                    cv2.rectangle(img_debug, (pos_x - 5, y1 - h2 - 15), (pos_x + w2 + 5, y1), COLOR_WHITE, -1)
                    cv2.putText(img_debug, lbl_read, (pos_x, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLOR_BLACK, 3)

        # --- MATCHING GLOBAL ---
        hus_ok = [x for x in hus if x['texto'] != "NO_LEIDO"]
        ubis_ok = [x for x in ubicaciones if x['texto'] != "NO_LEIDO"]
        candidatos = []
        for u in ubis_ok:
            nivel = obtener_nivel(u['texto'])
            for h in hus_ok:
                if abs(h['cx'] - u['cx']) > TOLERANCIA_COLUMNA_X: continue
                dist_y = h['cy'] - u['cy']
                if (nivel == 1 and dist_y < 0) or (nivel and nivel > 1 and dist_y > 0): continue
                score = 5000 if sap_hu_map.get(h['texto']) == u['texto'] else 0
                score -= distancia_euclidiana(h, u)
                candidatos.append({'u': u, 'h': h, 'score': score})

        candidatos.sort(key=lambda x: x['score'], reverse=True)
        match_encontrado_en_foto = False
        for c in candidatos:
            if not c['u']['usado'] and not c['h']['usado']:
                c['u']['usado'] = True; c['h']['usado'] = True
                match_encontrado_en_foto = True
                status = determinar_estado(c['u']['texto'], c['h']['texto'], df_sap)
                resultados_finales[c['u']['texto']] = {"status": status}
                registros_globales.append({"Imagen": img_name, "Tipo": "MATCH", "Ubicacion": c['u']['texto'], "HU": c['h']['texto'], "Status": status})
                reporte_relaciones.append({"Imagen": img_name, "Ubicacion": c['u']['texto'], "HU": c['h']['texto'], "Distancia": round(distancia_euclidiana(c['h'], c['u']), 1), "Metodo_Ubi": c['u']['metodo']})
                cv2.line(img_debug, (c['u']['cx'], c['u']['cy']), (c['h']['cx'], c['h']['cy']), (255, 0, 255), 5)

        # --- LÓGICA DE FILTRADO PARA UBICACIONES VACÍAS (HUÉRFANOS) ---
        # Si ya vinculamos una HU a una ubicación en esta foto, descartamos el resto.
        # Si no hubo ningún MATCH, elegimos solo una ubicación vacía.
        if not match_encontrado_en_foto:
            ubis_validas_libres = [u for u in ubicaciones if not u['usado'] and u['texto'] != "NO_LEIDO"]
            if ubis_validas_libres:
                # Criterio de elección: 
                # 1. Prioridad: ¿Cuál de estas figura vacía en SAP?
                # 2. Desempate: ¿Cuál está más cerca del centro de la imagen?
                def evaluar_prioridad_vacia(ubi):
                    fila = df_sap[df_sap[COL_UBICACION] == ubi['texto']]
                    vacia_en_sap = 0
                    if not fila.empty:
                        hu_sap = str(fila.iloc[0][COL_HU]).strip().replace(".0", "")
                        if hu_sap in ["nan", "", "None", "NaN", "<< vacías >>"]:
                            vacia_en_sap = 1
                    # Retornamos tupla para ordenar (SAP vacía primero, luego menor distancia al centro)
                    dist_centro = distancia_euclidiana(ubi, centro_img)
                    return (vacia_en_sap, -dist_centro)

                ubis_validas_libres.sort(key=evaluar_prioridad_vacia, reverse=True)
                u_elegida = ubis_validas_libres[0]
                
                status = determinar_estado(u_elegida['texto'], "VACIO", df_sap)
                resultados_finales[u_elegida['texto']] = {"status": status}
                registros_globales.append({"Imagen": img_name, "Tipo": "UBI SOLA", "Ubicacion": u_elegida['texto'], "HU": "VACIO", "Status": status})

        cv2.imwrite(os.path.join(CARPETA_DEBUG, f"AUDIT_{img_name}"), cv2.resize(img_debug, (0,0), fx=0.4, fy=0.4))
        print(f"✅ {img_name} procesada.")

    if registros_globales: pd.DataFrame(registros_globales).to_excel(ARCHIVO_REPORTE_DETALLADO, index=False)
    if reporte_relaciones: pd.DataFrame(reporte_relaciones).to_excel(ARCHIVO_RELACIONES, index=False)
    
    try:
        wb = load_workbook(ARCHIVO_SAP); ws = wb[NOMBRE_HOJA]
        headers = {cell.value.strip(): cell.col_idx for cell in ws[1] if cell.value}
        count = 0
        for row in ws.iter_rows(min_row=2):
            val_cell = row[headers[COL_UBICACION]-1].value
            if not val_cell: continue
            val = str(val_cell).strip().upper()
            if val in resultados_finales:
                res = resultados_finales[val]
                ws.cell(row=row[0].row, column=headers[COL_STATUS_OUTPUT], value=res['status'])
                count += 1
        wb.save(ARCHIVO_SAP); print(f"✅ SAP Actualizado: {count} filas.")
    except Exception as e: print(f"❌ Error SAP final: {e}")

if __name__ == "__main__":
    procesar_inventario()