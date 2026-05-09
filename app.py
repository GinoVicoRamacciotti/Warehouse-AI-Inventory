import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
from datetime import datetime

import importlib
import config
importlib.reload(config)
from core import sap_sync

st.set_page_config(page_title="Dashboard Inventario", layout="wide")

st.write("DEBUG INFO CONFIG FILE:", config.__file__)

st.title("🚁 Revisión Manual de Inventario Dron")

def cargar_datos():
    if not os.path.exists(config.ARCHIVO_REPORTE_DETALLADO):
        return pd.DataFrame()
    return pd.read_excel(config.ARCHIVO_REPORTE_DETALLADO)

def registrar_correccion(ubicacion, old_status, new_status, accion):
    archivo = config.ARCHIVO_CORRECCIONES
    registro = pd.DataFrame([{
        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Ubicacion": ubicacion,
        "Estado_Original": old_status,
        "Nuevo_Estado": new_status,
        "Accion": accion
    }])
    if os.path.exists(archivo):
        df = pd.read_excel(archivo)
        df = pd.concat([df, registro], ignore_index=True)
    else:
        df = registro
    df.to_excel(archivo, index=False)

tab1, tab2, tab3 = st.tabs(["🔍 Revisión Manual", "📊 Métricas de la Corrida Actual", "📈 Histórico y Evolución"])

df_reporte = cargar_datos()

# ==========================================
# PESTAÑA 1: REVISIÓN MANUAL
# ==========================================
with tab1:
    if df_reporte.empty:
        st.info("No hay reporte detallado disponible. Ejecuta el análisis primero (`python main.py`).")
    else:
        # Filtrar estados que NO son OK
        df_errores = df_reporte[df_reporte['Status'] != 'OK']

        if df_errores.empty:
            st.success("¡Todo está OK! No hay errores para revisar en la corrida actual.")
        else:
            st.sidebar.header("Ubicaciones a Revisar")
            opciones = df_errores.apply(lambda x: f"{x['Ubicacion']} ({x['Status']})", axis=1).tolist()
            seleccion = st.sidebar.selectbox("Selecciona una ubicación:", opciones)

            if seleccion:
                idx = opciones.index(seleccion)
                fila = df_errores.iloc[idx]
                
                st.subheader(f"📍 Ubicación: {fila['Ubicacion']}")
                st.write(f"**Estado Original:** {fila['Status']}")
                st.write(f"**Imagen Original:** {fila['Imagen']}")
                
                # Cargar Imagen Debug
                img_path = os.path.join(config.CARPETA_DEBUG, f"AUDIT_{fila['Imagen']}")
                if os.path.exists(img_path):
                    img = Image.open(img_path)
                    st.image(img, caption=f"Debug Visual: {fila['Imagen']}", use_container_width=True)
                else:
                    st.warning("Imagen de debug no encontrada.")
                
                st.markdown("---")
                st.subheader("Corrección Manual")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    nuevo_hu = st.text_input("Ingresar HU Correcta:", placeholder="Ej: 123456")
                    if st.button("Guardar HU"):
                        if nuevo_hu:
                            df_sap, _ = sap_sync.cargar_sap()
                            nuevo_estado = sap_sync.determinar_estado(fila['Ubicacion'], nuevo_hu, df_sap)
                            sap_sync.actualizar_excel_sap({fila['Ubicacion']: {"status": nuevo_estado}})
                            
                            registrar_correccion(fila['Ubicacion'], fila['Status'], nuevo_estado, "INGRESO MANUAL HU")
                            
                            df_reporte_actual = cargar_datos()
                            idx_rep = df_reporte_actual[df_reporte_actual['Ubicacion'] == fila['Ubicacion']].index
                            if not idx_rep.empty:
                                df_reporte_actual.loc[idx_rep, 'Status'] = 'OK'
                                df_reporte_actual.to_excel(config.ARCHIVO_REPORTE_DETALLADO, index=False)
                            
                            st.rerun()
                        else:
                            st.error("Debes ingresar un código HU.")
                            
                with col2:
                    st.write("¿La ubicación está físicamente vacía?")
                    if st.button("Marcar como VACÍO"):
                        df_sap, _ = sap_sync.cargar_sap()
                        nuevo_estado = sap_sync.determinar_estado(fila['Ubicacion'], "VACIO", df_sap)
                        sap_sync.actualizar_excel_sap({fila['Ubicacion']: {"status": nuevo_estado}})
                        
                        registrar_correccion(fila['Ubicacion'], fila['Status'], nuevo_estado, "MARCADO VACIO")
                        
                        df_reporte_actual = cargar_datos()
                        idx_rep = df_reporte_actual[df_reporte_actual['Ubicacion'] == fila['Ubicacion']].index
                        if not idx_rep.empty:
                            df_reporte_actual.loc[idx_rep, 'Status'] = 'OK'
                            df_reporte_actual.to_excel(config.ARCHIVO_REPORTE_DETALLADO, index=False)
                        st.rerun()

                with col3:
                    st.write("¿El estado detectado es correcto?")
                    if st.button("Confirmar Estado Actual", type="primary"):
                        registrar_correccion(fila['Ubicacion'], fila['Status'], fila['Status'], "CONFIRMADO CORRECTO")
                        
                        df_reporte_actual = cargar_datos()
                        idx_rep = df_reporte_actual[df_reporte_actual['Ubicacion'] == fila['Ubicacion']].index
                        if not idx_rep.empty:
                            df_reporte_actual.loc[idx_rep, 'Status'] = 'OK'
                            df_reporte_actual.to_excel(config.ARCHIVO_REPORTE_DETALLADO, index=False)
                            
                        st.success("Estado confirmado y descartado de la lista.")
                        st.rerun()

# ==========================================
# PESTAÑA 2: MÉTRICAS DE LA CORRIDA ACTUAL
# ==========================================
with tab2:
    st.header("Métricas Operativas - Corrida Actual")
    if not df_reporte.empty:
        # Extracción de Nivel y Calle
        df_reporte['Calle'] = df_reporte['Ubicacion'].astype(str).apply(lambda x: x[:2] if len(x)>1 and x[:2].isdigit() else 'Desconocido')
        df_reporte['Nivel'] = df_reporte['Ubicacion'].astype(str).apply(lambda x: x[3] if len(x)>3 and x[3].isdigit() else 'Desconocido')
        
        # Filtro Global
        calles_disponibles = sorted([c for c in df_reporte['Calle'].unique() if c != 'Desconocido'])
        calles_seleccionadas = st.multiselect("Filtro por Calles (dejar vacío para ver todas):", calles_disponibles)
        
        if calles_seleccionadas:
            df_filtrado = df_reporte[df_reporte['Calle'].isin(calles_seleccionadas)].copy()
        else:
            df_filtrado = df_reporte.copy()
            
        total = len(df_filtrado)
        oks = len(df_filtrado[df_filtrado['Status'] == 'OK'])
        errores = total - oks
        
        if total == 0:
            st.warning("No hay datos para la calle seleccionada.")
        else:
            # Tarjetas (KPIs)
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Total Escaneadas", total)
            kpi2.metric("Precisión (OK)", f"{(oks/total*100):.1f}%")
            kpi3.metric("Requieren Revisión", errores)
            
            conf_ubi = df_filtrado['Conf_YOLO_Ubi'].mean() if 'Conf_YOLO_Ubi' in df_filtrado.columns else 0
            kpi4.metric("Confianza Media YOLO", f"{(conf_ubi*100):.1f}%")

            st.markdown("---")
            
            col_graf1, col_graf2, col_graf3 = st.columns(3)
            
            df_errores_puro = df_filtrado[df_filtrado['Status'] != 'OK'].copy()
            
            with col_graf1:
                st.subheader("Distribución")
                fig1, ax1 = plt.subplots(figsize=(5, 4))
                conteo_status = df_filtrado['Status'].value_counts()
                if not conteo_status.empty:
                    ax1.pie(conteo_status.values, labels=conteo_status.index, autopct='%1.1f%%', startangle=90, colors=sns.color_palette("pastel"))
                    ax1.axis('equal')
                    st.pyplot(fig1)
                else:
                    st.info("No hay datos para graficar.")
                
            with col_graf2:
                st.subheader("Fallos por Nivel")
                if not df_errores_puro.empty:
                    fig2, ax2 = plt.subplots(figsize=(5, 4))
                    sns.countplot(data=df_errores_puro, x='Nivel', ax=ax2, palette="Blues_r", order=sorted(df_errores_puro['Nivel'].unique()))
                    ax2.set_ylabel("Fallos")
                    st.pyplot(fig2)
                else:
                    st.success("No hay errores.")
                    
            with col_graf3:
                st.subheader("Fallos por Calle")
                if not df_errores_puro.empty:
                    fig3, ax3 = plt.subplots(figsize=(5, 4))
                    sns.countplot(data=df_errores_puro, x='Calle', ax=ax3, palette="Reds_r", order=sorted(df_errores_puro['Calle'].unique()))
                    ax3.set_ylabel("Fallos")
                    plt.xticks(rotation=45)
                    st.pyplot(fig3)
                else:
                    st.success("No hay errores.")
                    
            # Gráfico de métodos de OCR
            if os.path.exists(config.ARCHIVO_RELACIONES):
                df_links = pd.read_excel(config.ARCHIVO_RELACIONES)
                if not df_links.empty and 'Metodo_Ubi' in df_links.columns:
                    # Filtramos los links para que coincidan con la calle seleccionada
                    df_links = df_links[df_links['Ubicacion'].isin(df_filtrado['Ubicacion'])]
                    if not df_links.empty:
                        st.markdown("---")
                        st.subheader("Rendimiento de los Métodos de Lectura (Ubicaciones)")
                        metodos = df_links['Metodo_Ubi'].value_counts()
                        st.bar_chart(metodos)
    else:
        st.info("Ejecuta el análisis primero para ver métricas.")

# ==========================================
# PESTAÑA 3: MÉTRICAS HISTÓRICAS
# ==========================================
with tab3:
    st.header("Histórico de Precisión y Correcciones")
    
    col_hist1, col_hist2 = st.columns(2)
    
    with col_hist1:
        st.subheader("Evolución de Precisión (OK)")
        if os.path.exists(config.ARCHIVO_HISTORICO):
            df_hist = pd.read_excel(config.ARCHIVO_HISTORICO)
            if not df_hist.empty:
                df_hist['Fecha'] = pd.to_datetime(df_hist['Fecha'])
                fig_hist, ax_hist = plt.subplots(figsize=(8, 4))
                sns.lineplot(data=df_hist, x='Fecha', y='Porcentaje_Precisión', marker="o", ax=ax_hist)
                ax_hist.set_ylim(0, 105)
                ax_hist.set_ylabel("% OK")
                plt.xticks(rotation=45)
                st.pyplot(fig_hist)
            else:
                st.info("Archivo histórico vacío.")
        else:
            st.info("Aún no hay registros históricos. Corre `main.py` para empezar a registrar.")
            
    with col_hist2:
        st.subheader("Intervenciones Manuales (Poka-yoke Humano)")
        if os.path.exists(config.ARCHIVO_CORRECCIONES):
            df_corr = pd.read_excel(config.ARCHIVO_CORRECCIONES)
            if not df_corr.empty:
                acciones = df_corr['Accion'].value_counts()
                st.write("**Total de intervenciones manuales realizadas:**", len(df_corr))
                st.bar_chart(acciones)
                with st.expander("Ver detalle de correcciones"):
                    st.dataframe(df_corr)
            else:
                st.info("Archivo de correcciones vacío.")
        else:
            st.info("Aún no hay correcciones manuales guardadas.")
