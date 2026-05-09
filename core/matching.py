from core.ocr import obtener_nivel
import config

def distancia_euclidiana(p1, p2):
    return ((p1['cx'] - p2['cx'])**2 + (p1['cy'] - p2['cy'])**2)**0.5

def evaluar_prioridad_vacia(ubi, df_sap, centro_img):
    """Criterio de ordenación para ubicaciones huérfanas."""
    from core.sap_sync import config as sap_config
    fila = df_sap[df_sap[sap_config.COL_UBICACION] == ubi['texto']]
    vacia_en_sap = 0
    if not fila.empty:
        hu_sap = str(fila.iloc[0][sap_config.COL_HU]).strip().replace(".0", "")
        if hu_sap in ["nan", "", "None", "NaN", "<< vacías >>"]:
            vacia_en_sap = 1
    dist_centro = distancia_euclidiana(ubi, centro_img)
    return (vacia_en_sap, -dist_centro)

def realizar_matching(ubicaciones, hus, sap_hu_map, df_sap, img_name, centro_img):
    """
    Implementa la lógica global de emparejamiento entre Ubicaciones y HUs detectadas.
    Retorna la lista de matches encontrados, registros y relaciones para reporte.
    """
    from core.sap_sync import determinar_estado
    
    hus_ok = [x for x in hus if x['texto'] != "NO_LEIDO"]
    ubis_ok = [x for x in ubicaciones if x['texto'] != "NO_LEIDO"]
    candidatos = []
    
    for u in ubis_ok:
        nivel = obtener_nivel(u['texto'])
        for h in hus_ok:
            if abs(h['cx'] - u['cx']) > config.TOLERANCIA_COLUMNA_X: 
                continue
            dist_y = h['cy'] - u['cy']
            if (nivel == 1 and dist_y < 0) or (nivel and nivel > 1 and dist_y > 0): 
                continue
                
            score = 5000 if sap_hu_map.get(h['texto']) == u['texto'] else 0
            score -= distancia_euclidiana(h, u)
            candidatos.append({'u': u, 'h': h, 'score': score})

    candidatos.sort(key=lambda x: x['score'], reverse=True)
    
    resultados_foto = {}
    registros = []
    relaciones = []
    match_encontrado_en_foto = False
    
    # Procesar Candidatos de Mayor a Menor Score
    for c in candidatos:
        if not c['u']['usado'] and not c['h']['usado']:
            c['u']['usado'] = True
            c['h']['usado'] = True
            match_encontrado_en_foto = True
            
            status = determinar_estado(c['u']['texto'], c['h']['texto'], df_sap)
            resultados_foto[c['u']['texto']] = {"status": status}
            
            registros.append({
                "Imagen": img_name, 
                "Tipo": "MATCH", 
                "Ubicacion": c['u']['texto'], 
                "HU": c['h']['texto'], 
                "Status": status,
                "Conf_YOLO_Ubi": round(float(c['u'].get('conf', 0)), 2),
                "Conf_YOLO_HU": round(float(c['h'].get('conf', 0)), 2)
            })
            
            relaciones.append({
                "Imagen": img_name, 
                "Ubicacion": c['u']['texto'], 
                "HU": c['h']['texto'], 
                "Distancia": round(distancia_euclidiana(c['h'], c['u']), 1), 
                "Metodo_Ubi": c['u']['metodo'],
                "Conf_YOLO_Ubi": round(float(c['u'].get('conf', 0)), 2),
                "Conf_YOLO_HU": round(float(c['h'].get('conf', 0)), 2),
                # Data para dibujar
                "cx1": c['u']['cx'], "cy1": c['u']['cy'],
                "cx2": c['h']['cx'], "cy2": c['h']['cy']
            })

    # Lógica de Filtrado para Ubicaciones Vacías (Huérfanos)
    if not match_encontrado_en_foto:
        ubis_validas_libres = [u for u in ubicaciones if not u['usado'] and u['texto'] != "NO_LEIDO"]
        if ubis_validas_libres:
            ubis_validas_libres.sort(key=lambda u: evaluar_prioridad_vacia(u, df_sap, centro_img), reverse=True)
            u_elegida = ubis_validas_libres[0]
            
            status = determinar_estado(u_elegida['texto'], "VACIO", df_sap)
            resultados_foto[u_elegida['texto']] = {"status": status}
            
            registros.append({
                "Imagen": img_name, 
                "Tipo": "UBI SOLA", 
                "Ubicacion": u_elegida['texto'], 
                "HU": "VACIO", 
                "Status": status,
                "Conf_YOLO_Ubi": round(float(u_elegida.get('conf', 0)), 2),
                "Conf_YOLO_HU": 0.0
            })

    return resultados_foto, registros, relaciones
