# 🚀 Instrucciones de Instalación (Nuevo Equipo)

Si has copiado la carpeta `Inventario Dron` a una nueva computadora, debes seguir estos pasos exactamente en el orden indicado para asegurar que el sistema funcione sin problemas de compatibilidad.

## 1. Requisitos Previos

Antes de configurar el entorno de Python, asegúrate de tener instalados los siguientes programas en el nuevo equipo:

1. **Python:** Se recomienda utilizar Python 3.10 o superior. Al instalarlo, asegúrate de marcar la casilla **"Add Python to PATH"**.
2. **Tesseract OCR:** 
   - Debes instalar el motor de reconocimiento óptico de caracteres de Tesseract.
   - Una vez instalado, debes ir al archivo `config.py` de este proyecto y actualizar la variable `RUTA_TESSERACT` con la ruta exacta donde se instaló (por defecto suele ser `C:\Program Files\Tesseract-OCR\tesseract.exe` o `C:\Users\<Usuario>\AppData\Local\Programs\Tesseract-OCR\tesseract.exe`).
3. **Microsoft Visual C++ Redistributable:** Las librerías de lectura de códigos de barras (`pyzbar` y `pylibdmtx`) requieren tener instaladas las bibliotecas de Visual C++ en Windows. Si no las tienes, el programa lanzará un error indicando que falta alguna `.dll`.

## 2. Creación del Entorno Virtual

Es **crítico** aislar la instalación de librerías para no romper otras aplicaciones.

1. Abre la terminal (Símbolo del Sistema o PowerShell).
2. Navega hasta la carpeta del proyecto:
   ```bash
   cd ruta\a\la\carpeta\Inventario Dron
   ```
3. Crea un nuevo entorno virtual (esto creará una carpeta llamada `venv`):
   ```bash
   python -m venv venv
   ```
4. Activa el entorno virtual:
   - En **Símbolo del Sistema (CMD)**:
     ```cmd
     venv\Scripts\activate
     ```
   - En **PowerShell**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   *(Sabrás que está activado porque aparecerá `(venv)` al inicio de la línea en la consola).*

## 3. Instalación de Dependencias (Crítico)

El archivo `requirements.txt` contiene las librerías con sus **versiones específicas**. Si omites este paso y dejas que Python instale versiones más recientes por su cuenta, es muy probable que haya conflictos (por ejemplo, con PyTorch, Ultralytics o PaddleOCR).

1. Con el entorno virtual **activado**, ejecuta el siguiente comando:
   ```bash
   pip install -r requirements.txt
   ```
2. Espera a que termine (puede tardar varios minutos dependiendo de la velocidad de internet, ya que librerías como PyTorch son pesadas).

## 4. Verificación y Puesta en Marcha

Una vez instalado todo:

1. Asegúrate de tener al menos una foto de prueba en la carpeta `fotos_a_procesar` y el archivo `Audit Rot.xlsx` en la carpeta raíz.
2. Ejecuta el sistema principal para verificar que los modelos de IA se carguen correctamente:
   ```bash
   python main.py
   ```
3. Prueba que el panel de revisión web funcione:
   ```bash
   streamlit run app.py
   ```

> [!WARNING]
> **Nota sobre PaddleOCR y Torch:** Si el nuevo equipo tiene una Tarjeta Gráfica NVIDIA y quieres usarla para acelerar el proceso, tendrás que desinstalar la versión actual de PyTorch e instalar la versión con soporte para CUDA (GPU) siguiendo las instrucciones de la página oficial de PyTorch, pero por ahora, la configuración instalada mediante `requirements.txt` está garantizada para funcionar en CPU de manera estable.
