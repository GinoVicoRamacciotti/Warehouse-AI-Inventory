import os
import cv2
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt

import config
from core import vision, ocr, sap_sync, matching

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("audit_process.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Parches de seguridad
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

def procesar_imagen(img_name, df_sap, sap_hu_map):
    """
    Función que procesa una sola imagen. Será ejecutada por los workers.
    """
    try:
        t_start = time.time()
        img_path = os.path.join(config.CARPETA_FOTOS, img_name)
        img_full = cv2.imread(img_path)
        if img_full is None: 
            return None
            
        img_debug = img_full.copy()
        h_full_img, w_full_img = img_full.shape[:2]
        centro_img = {'cx': w_full_img // 2, 'cy': h_full_img // 2}

        # 1. Detección con YOLO
        elementos = vision.detectar_elementos(img_full)
        
        ubicaciones = []
        hus = []
        
        # 2. Lectura OCR/Códigos
        for i, elem in enumerate(elementos):
            texto_final = "NO_LEIDO"
            metodo_final = "N/A"
            color = (0,0,0)
            
            if elem['cls'] == 0: # HU
                color = config.COLOR_BAR
                val, met = ocr.leer_barcode_super(elem['crop'])
                if val: 
                    texto_final, metodo_final = val, met
                hus.append({'texto': texto_final, 'metodo': metodo_final, 'cx': elem['cx'], 'cy': elem['cy'], 'usado': False, 'conf': elem['conf']})
                
            elif elem['cls'] == 2: # Ubicacion
                color = config.COLOR_UBI
                val, met = ocr.leer_ubicacion_con_diagnostico(elem['crop'], f"{img_name}_{i}")
                if val: 
                    texto_final, metodo_final = val, met
                ubicaciones.append({'texto': texto_final, 'metodo': metodo_final, 'cx': elem['cx'], 'cy': elem['cy'], 'usado': False, 'conf': elem['conf']})

            vision.dibujar_debug(img_debug, elem, texto_final, color)

        # 3. Matching Lógico
        res_foto, registros, relaciones = matching.realizar_matching(
            ubicaciones, hus, sap_hu_map, df_sap, img_name, centro_img
        )
        
        # Dibujar líneas de relación en debug
        for rel in relaciones:
            cv2.line(img_debug, (rel['cx1'], rel['cy1']), (rel['cx2'], rel['cy2']), (255, 0, 255), 5)
            
        # 4. Guardar Debug
        cv2.imwrite(os.path.join(config.CARPETA_DEBUG, f"AUDIT_{img_name}"), cv2.resize(img_debug, (0,0), fx=0.4, fy=0.4))
        
        t_end = time.time()
        logging.info(f"✅ {img_name} procesada en {t_end - t_start:.2f}s")
        
        return {
            "resultados_foto": res_foto,
            "registros": registros,
            "relaciones": relaciones
        }
        
    except Exception as e:
        logging.error(f"[ERROR] Error procesando {img_name}: {e}")
        return None

def generar_grafico_metricas(registros_globales):
    """
    Genera un gráfico simple sobre los estados resultantes del análisis.
    """
    if not registros_globales:
        return
        
    estados = [r['Status'] for r in registros_globales]
    from collections import Counter
    conteo = Counter(estados)
    
    labels = list(conteo.keys())
    valores = list(conteo.values())
    
    plt.figure(figsize=(10, 6))
    plt.bar(labels, valores, color=['green' if 'OK' in l else 'orange' if 'Vacío' in l else 'red' for l in labels])
    plt.xticks(rotation=45, ha='right')
    plt.title('Métricas de Procesamiento de Inventario')
    plt.ylabel('Cantidad de Ubicaciones')
    plt.tight_layout()
    plt.savefig('metricas_resultado.png')
    logging.info("📊 Gráfico de métricas guardado como 'metricas_resultado.png'.")

def guardar_metricas_historicas(registros_globales):
    """
    Calcula KPIs globales y los guarda como una nueva fila en el Excel histórico.
    """
    if not registros_globales:
        return
        
    import pandas as pd
    from datetime import datetime
    import numpy as np
    
    df = pd.DataFrame(registros_globales)
    
    total = len(df)
    total_ok = len(df[df['Status'] == 'OK'])
    pct_ok = round((total_ok / total) * 100, 2) if total > 0 else 0
    total_errores = total - total_ok
    
    conf_ubi_avg = round(df['Conf_YOLO_Ubi'].mean(), 3) if 'Conf_YOLO_Ubi' in df.columns else 0
    
    # Confianza HU solo de las que no son VACIO (es decir, Tipo MATCH)
    df_hus = df[df['Tipo'] == 'MATCH']
    conf_hu_avg = round(df_hus['Conf_YOLO_HU'].mean(), 3) if 'Conf_YOLO_HU' in df_hus.columns and not df_hus.empty else 0
    
    nuevo_registro = pd.DataFrame([{
        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Total_Ubicaciones": total,
        "Total_OK": total_ok,
        "Total_Errores": total_errores,
        "Porcentaje_Precisión": pct_ok,
        "Promedio_Confianza_Ubi": conf_ubi_avg,
        "Promedio_Confianza_HU": conf_hu_avg
    }])
    
    # Si existe el histórico, lo leemos y anexamos. Si no, lo creamos.
    if os.path.exists(config.ARCHIVO_HISTORICO):
        try:
            df_hist = pd.read_excel(config.ARCHIVO_HISTORICO)
            df_hist = pd.concat([df_hist, nuevo_registro], ignore_index=True)
        except Exception as e:
            logging.error(f"[ERROR] No se pudo leer histórico: {e}")
            df_hist = nuevo_registro
    else:
        df_hist = nuevo_registro
        
    df_hist.to_excel(config.ARCHIVO_HISTORICO, index=False)
    logging.info(f"📈 Métricas históricas actualizadas en {config.ARCHIVO_HISTORICO}")

def procesar_inventario():
    logging.info("🚀 Iniciando proceso de auditoría...")
    
    # Pre-cargar modelos en el hilo principal para evitar problemas
    ocr.init_paddle()
    ocr.init_easyocr()
    vision.get_yolo_model()
    
    # Cargar SAP
    df_sap, sap_hu_map = sap_sync.cargar_sap()
    if df_sap is None: return

    imagenes = sorted([f for f in os.listdir(config.CARPETA_FOTOS) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    
    resultados_finales = {}
    registros_globales = []
    reporte_relaciones = []

    logging.info(f"⚡ Iniciando paralelización con {config.MAX_WORKERS} workers para {len(imagenes)} imágenes.")
    
    # Ejecución Paralela
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        futuros = {executor.submit(procesar_imagen, img_name, df_sap, sap_hu_map): img_name for img_name in imagenes}
        
        for futuro in as_completed(futuros):
            res = futuro.result()
            if res:
                resultados_finales.update(res['resultados_foto'])
                registros_globales.extend(res['registros'])
                reporte_relaciones.extend(res['relaciones'])

    # Sincronización final y reportes
    sap_sync.guardar_reportes_temporales(registros_globales, reporte_relaciones)
    sap_sync.actualizar_excel_sap(resultados_finales)
    
    # Generar gráficos
    generar_grafico_metricas(registros_globales)
    guardar_metricas_historicas(registros_globales)
    logging.info("✅ Proceso completado exitosamente.")

if __name__ == "__main__":
    procesar_inventario()