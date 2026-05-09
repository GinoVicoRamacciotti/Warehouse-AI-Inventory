# 🛠️ Manual Técnico: Arquitectura y Mantenimiento

Este documento describe la arquitectura técnica del sistema **Inventario Dron** tras su refactorización a una estructura modular, facilitando su mantenimiento y escalabilidad.

## 1. Estructura del Proyecto

El código está dividido en responsabilidades claras dentro de la carpeta `core/`:

- `config.py`: **Punto central de configuración**. Contiene rutas de archivos, colores, umbrales de detección y parámetros de rendimiento (`MAX_WORKERS`). Si necesitas cambiar un excel o la ruta de un modelo, házlo aquí.
- `main.py`: **Orquestador**. Se encarga de inicializar los modelos, leer las fotos, instanciar el `ThreadPoolExecutor` para paralelización, y llamar a los distintos módulos para procesar cada imagen. También genera los logs y gráficos.
- `app.py`: **Dashboard Web**. Aplicación de Streamlit que lee los reportes generados y permite interacción humana en el bucle para corregir las inferencias fallidas y re-inyectarlas en SAP.
- `core/vision.py`: **Capa de Visión (YOLO)**. Maneja el redimensionamiento de las imágenes, la inferencia de YOLO y el dibujado de las "bounding boxes" para el debug.
- `core/ocr.py`: **Capa de Lectura**. Inicializa PaddleOCR, Tesseract y las librerías de códigos de barras/DataMatrix. Contiene la lógica en cascada (Nivel 1 a Nivel 3) para intentar leer texto de los recortes generados por visión.
- `core/sap_sync.py`: **Capa de Integración**. Lee los Excels originales usando Pandas y OpenPyXL, determina la lógica de estados de inventario (OK, Diferencia HU, etc.) y guarda los reportes resultantes y modifica la planilla `Audit Rot.xlsx`.
- `core/matching.py`: **Lógica de Negocio Espacial**. Contiene los algoritmos para decidir, dadas unas coordenadas X/Y de una ubicación y un código de barras, cuáles hacen par (matching) priorizando el mapa esperado de SAP y limitando las distancias y niveles verticales.

## 2. Paralelización e Hilos (`ThreadPoolExecutor`)

Dado que el entorno de ejecución no cuenta con GPU dedicada, se implementó `ThreadPoolExecutor` en lugar de multiprocesamiento pesado para evitar saturar la memoria RAM.
- **Rendimiento:** Puedes ajustar la variable `MAX_WORKERS` en `config.py`. Para una CPU estándar integrada, un valor de `2` a `4` es recomendado. Valores muy altos causarán _thrashing_ de memoria ya que PaddleOCR y Torch consumen RAM al inferir simultáneamente.
- **Seguridad de Hilos:** YOLO (vía PyTorch) es seguro en hilos si se usa el mismo modelo instanciado. Para PaddleOCR se recomienda instanciarlo globalmente una sola vez mediante `init_paddle()` antes de abrir el pool de hilos.

## 3. Manejo de Errores y Logging

- Todo el proceso de `main.py` utiliza la librería estándar `logging`.
- Los errores (excepciones de lectura, archivos faltantes) no detienen la ejecución global; en su lugar, se registran en el archivo `audit_process.log`. 
- Revisa el archivo `audit_process.log` periódicamente para identificar patrones de fallos, tiempos de ejecución (se miden en segundos por imagen) y excepciones de memoria.

## 4. Agregar Nuevas Capacidades de OCR

Si deseas agregar un nuevo motor OCR (ej. EasyOCR o una API de Cloud Vision):
1. Ve al archivo `core/ocr.py`.
2. Agrega la lógica de inicialización en la parte superior.
3. Modifica la función `leer_ubicacion_con_diagnostico(img_crop, debug_name)`. Agrega un "NIVEL 4" o intercálalo donde estimes conveniente (antes o después de Tesseract).

## 5. Mantenimiento del Dashboard (Streamlit)

- El dashboard corre bajo el paradigma reactivo de Streamlit. Al usar `st.cache_data` leemos el Excel una sola vez. Cuando se realiza una actualización manual en la base de datos (Excel), llamamos a `st.cache_data.clear()` para forzar a Streamlit a volver a leer el Excel actualizado en la siguiente recarga de la página.
