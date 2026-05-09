# 🚁 Manual de Uso: Inventario Dron

Bienvenido al sistema de Auditoría de Inventario con Drones. Este documento explica paso a paso cómo utilizar la herramienta de análisis y cómo corregir cualquier lectura fallida.

## 1. Preparación del Análisis
1. **Fotografías del Dron:** Asegúrate de colocar todas las fotografías tomadas por el dron en la carpeta `fotos_a_procesar`. Las imágenes deben estar en formato `.jpg`, `.jpeg` o `.png`.
2. **Archivo SAP Original:** Asegúrate de que el archivo `Audit Rot.xlsx` se encuentre en la misma carpeta raíz del programa. Este es el Excel extraído de tu sistema que contiene lo que el sistema *cree* que hay en el almacén.

## 2. Ejecutar el Procesamiento Automático
1. Abre tu consola (Símbolo del Sistema o PowerShell).
2. Navega a la carpeta del proyecto.
3. Activa tu entorno virtual si tienes uno (ej. `venv\Scripts\activate`).
4. Ejecuta el comando:
   ```powershell
   python main.py
   ```
5. Verás en la consola cómo se procesan las imágenes. Al finalizar, el programa indicará: `✅ Proceso completado exitosamente.`
6. Se generarán tres cosas automáticamente:
   - **Archivo Actualizado:** El Excel `Audit Rot.xlsx` (ubicado en la carpeta principal) se habrá actualizado en la columna `STATUS_APPSHEET` indicando si todo está OK, Vacío, etc.
   - **Reporte Detallado:** Un archivo `Reporte_Detallado_IA.xlsx` (ubicado en la carpeta principal) con el detalle de qué leyó en cada foto.
   - **Gráfico de Rendimiento:** Una imagen `metricas_resultado.png` (guardada en la carpeta principal del proyecto) que muestra de forma visual la cantidad de aciertos y errores.

## 3. Revisión Manual de Errores (Dashboard)
Es posible que algunas ubicaciones estén oscuras o tengan un código roto y la Inteligencia Artificial no logre leerlas (arrojando un estado distinto a "OK"). 

Para corregirlas manualmente:
1. En la consola, ejecuta:
   ```powershell
   python -m streamlit run app.py
   ```
2. Se abrirá automáticamente una pestaña en tu navegador web.
3. En la barra lateral izquierda, verás un menú desplegable con todas las Ubicaciones que fallaron.
4. Al seleccionar una, verás la imagen recortada correspondiente a esa ubicación con los cuadros dibujados por la IA. También verás claramente el **Estado Original** detectado por la IA (Ej: `Diferencia HU` o `SAP Vacío`).
5. Observa la imagen y decide:
   - **Si el estado detectado es correcto:** Presiona el botón rojo/primario **Confirmar Estado Actual**. Esto mantendrá el estado (Ej: `Diferencia HU`) en SAP tal como está, pero quitará la alerta de tu lista para pasar a la siguiente.
   - **Si puedes leer el número de palet (HU):** Escríbelo en la casilla "Ingresar HU Correcta" y presiona **Guardar HU**.
   - **Si la ubicación está vacía físicamente:** Haz clic en el botón que dice **Marcar como VACÍO**.
6. El sistema actualizará automáticamente el archivo de Excel SAP (si hubo un cambio) y avanzará a la siguiente alerta.
