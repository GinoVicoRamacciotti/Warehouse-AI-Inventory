# 🚁 Warehouse AI Inventory Auditor

Sistema integral basado en Inteligencia Artificial y Visión por Computadora para automatizar la conciliación de inventarios físicos en almacenes logísticos de alta densidad, integrando los resultados directamente con SAP.

## 🎯 Objetivo
Eliminar las horas de carga manual y los errores humanos al cruzar el stock físico real (capturado mediante drones) contra los reportes del sistema ERP (SAP).

## ⚙️ ¿Cómo funciona?

1. **Captura:** Un dron recorre los pasillos tomando fotografías de alta resolución de las posiciones y estanterías.
2. **Detección y Lectura (IA):** El software procesa las imágenes masivamente usando modelos **YOLO** entrenados a medida para detectar las ubicaciones físicas y las etiquetas (Handling Units).
3. **Extracción de Datos:** Un sistema OCR redundante (Zbar, PaddleOCR y Tesseract) extrae el texto exacto de cada etiqueta.
4. **Matching Espacial:** Mediante cálculos de geometría analítica y distancia euclidiana, el script empareja lógicamente qué caja corresponde a qué ubicación en la estantería.
5. **Auditoría Automática:** El sistema cruza instantáneamente los datos leídos contra la base de datos de SAP y diagnostica el estado (Ej: *Físico Vacío / SAP Ocupado*, *Diferencia de HU*, *Match Perfecto*).
6. **Reporte:** Actualiza automáticamente la planilla Excel de control marcando las discrepancias.

## 🛠️ Tecnologías Utilizadas
* **Lenguaje:** Python 3.x
* **Computer Vision & IA:** Ultralytics (YOLOv8), PaddleOCR, OpenCV, PyTesseract, Pyzbar.
* **Análisis de Datos:** Pandas, Numpy, Openpyxl.

## 📸 Demostración Visual

**[¡ATENCIÓN! ARRASTRÁ TUS DOS FOTOS ACÁ]**
