# 🚁 Warehouse AI Inventory (Drones + IA)

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Computer%20Vision-yellow.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red.svg)

Un sistema de auditoría de inventarios logística automatizado que procesa imágenes de drones en alta resolución mediante Inteligencia Artificial para conciliar el inventario físico con bases de datos SAP ERP.

---

## 🚀 Características Principales

*   **Detección de Objetos (YOLOv8):** Identifica automáticamente la ubicación física (estantería) y la Unidad de Almacén (HU - Código de barras) en imágenes tomadas por drones en vuelo.
*   **OCR en Cascada:** Implementa una arquitectura resiliente de lectura (DataMatrix -> PaddleOCR -> EasyOCR -> Tesseract) para asegurar la máxima legibilidad de etiquetas en ángulos difíciles o con desenfoque de movimiento.
*   **Conciliación con SAP (Pandas):** Lee la base de datos logística y detecta discrepancias al instante (Ej: *"Físico Vacío pero SAP Ocupado"* o *"Diferencia de HU"*).
*   **Procesamiento Paralelo (Multi-threading):** Optimizado para correr en procesadores (CPU) utilizando `ThreadPoolExecutor` con bloqueos (`threading.Lock()`) seguros para el modelo YOLO, maximizando el uso de recursos sin requerir una tarjeta gráfica dedicada (GPU).
*   **Dashboard Interactivo (Streamlit):** Una aplicación web en tiempo real para la revisión humana (Poka-Yoke) donde los operadores pueden visualizar las discrepancias, ver los recortes de la IA y corregir los datos directamente.

## 🛠 Arquitectura del Proyecto

El proyecto está diseñado bajo un modelo modular:

- `main.py`: Orquestador principal que lanza los hilos de procesamiento.
- `core/vision.py`: Capa de inferencia visual (Redes neuronales).
- `core/ocr.py`: Cascada de extracción de texto.
- `core/matching.py`: Algoritmo de distancia euclidiana y lógica espacial para asociar un código de barras a su estantería correspondiente.
- `core/sap_sync.py`: Interfaz de lectura y escritura de Excel para la conciliación.
- `app.py`: Servidor Frontend (Dashboard).

---

## ⚙️ Instalación y Uso (Modo Demo)

Este repositorio contiene datos "Dummy" para proteger la confidencialidad. Para probarlo localmente:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/GinoVicoRamacciotti/Warehouse-AI-Inventory.git
   cd Warehouse-AI-Inventory
   ```

2. **Instalar dependencias:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
   *(Requiere tener Tesseract-OCR instalado en tu sistema).*

3. **Configuración inicial:**
   - Renombra `config.example.py` a `config.py`.
   - Modifica las rutas internas (como la de `tesseract.exe`) para que coincidan con tu sistema.
   - Pega 1 o 2 imágenes de prueba (JPG/PNG) en la carpeta `fotos_a_procesar`.
   - *(Los pesos pesados de los modelos `.pt` deben ser descargados desde la pestaña Releases y colocados en sus respectivas carpetas).*

4. **Ejecutar el Análisis IA:**
   ```bash
   python main.py
   ```
   *Esto generará un reporte de discrepancias comparado con la base falsa `Audit_Rot_Ejemplo.xlsx`.*

5. **Lanzar el Dashboard Operativo:**
   ```bash
   python -m streamlit run app.py
   ```
   *Abre `http://localhost:8501` en tu navegador para revisar las métricas interactivas y corregir los falsos positivos.*

---

## 📈 Dashboard y Métricas

El sistema no solo automatiza, sino que mide. En el dashboard web encontrarás:
- **KPIs Operativos:** Precisión global de lectura, total de escaneos, etc.
- **Fallos por Nivel/Calle:** Gráficos para detectar patrones de error en el almacén (ej: "Falta iluminación en el Nivel 3 de la Calle 54").
- **Historial de Evolución:** Registro histórico de cómo mejora la precisión del dron día tras día.

---
*Desarrollado por [Gino Vico Ramacciotti](https://github.com/GinoVicoRamacciotti)*
