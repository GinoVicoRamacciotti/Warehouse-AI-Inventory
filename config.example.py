import os

# =========================================================
# ⚙️ CONFIGURACIÓN GENERAL (EJEMPLO PÚBLICO)
# =========================================================

# --- RUTAS DE MODELOS Y EJECUTABLES ---
# Descarga los pesos de YOLO desde la pestaña "Releases" de GitHub
MODELO_YOLO_PATH = r"runs\detect\train_v2_highres2\weights\best.pt" 

# Reemplaza con la ruta donde instalaste Tesseract OCR en tu PC
RUTA_TESSERACT = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Descarga el modelo custom de PaddleOCR desde "Releases"
RUTA_BASE_IA = r'modelo_ocr_custom'

# --- ARCHIVOS DE EXCEL ---
# Archivo de ejemplo proveído en el repo
ARCHIVO_SAP = "ejemplo_datos_falsos/Audit_Rot_Ejemplo.xlsx"
NOMBRE_HOJA = "Planilla de control"
ARCHIVO_REPORTE_DETALLADO = "Reporte_Detallado_IA.xlsx"
ARCHIVO_RELACIONES = "Reporte_Links.xlsx"

# --- CARPETAS ---
CARPETA_FOTOS = "fotos_a_procesar"
CARPETA_DEBUG = "debug_recortes"
CARPETA_FALLOS = "debug_fallos_lectura"
CARPETA_METRICAS = "metricas_historico"

ARCHIVO_HISTORICO = os.path.join(CARPETA_METRICAS, "historico_runs.xlsx")
ARCHIVO_CORRECCIONES = os.path.join(CARPETA_METRICAS, "correcciones_manuales.xlsx")

# --- PARÁMETROS DE IA Y VISIÓN ---
YOLO_INPUT_SIZE = 3840 
REGEX_UBICACION = r"^[0-9]{2}[A-Z][0-9][A-Z](\sBIS)?$"
UMBRALES_CLASE = {0: 0.15, 2: 0.40} 
RADIO_MAX_CANTIDAD = 3500 
TOLERANCIA_COLUMNA_X = 5000
MAPA_CLASES_CORREGIDO = {0: "barcode", 1: "cantidad", 2: "ubicacion"}
CONF_GLOBAL = 0.10

# --- COLUMNAS EXCEL SAP ---
COL_UBICACION = "Ubicación"      
COL_HU = "Unidad almacén"        
COL_STATUS_OUTPUT = "STATUS_APPSHEET"  
COL_CANTIDAD_OUTPUT = "CANT_IA"        

# --- COLORES BGR PARA DIBUJO ---
COLOR_UBI = (0, 100, 0)      # Verde
COLOR_BAR = (255, 0, 0)      # Azul
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)

# --- PARÁMETROS DE PARALELIZACIÓN ---
MAX_WORKERS = 2

for c in [CARPETA_DEBUG, CARPETA_FALLOS, CARPETA_FOTOS, CARPETA_METRICAS]:
    if not os.path.exists(c):
        os.makedirs(c)
