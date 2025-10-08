#!/usr/bin/env python3
"""
API Flask para análisis de probetas con OpenCV
"""

from flask import Flask, request, jsonify
from typing import Tuple
from flask_cors import CORS
import cv2
import numpy as np
import base64
import os
from datetime import datetime, timedelta
import json
import logging

# Importar tus scripts adaptados
from a2_detectar_aruco import TablaAPIDetector
from b3_extractor import ExtractorProporcional
from c2_analizar import CalibradorManual, SelectorManualProbeta

import tempfile

# Directorio temporal compatible con Windows
TEMP_DIR = tempfile.gettempdir()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ✅ CORS CORREGIDO - PERMITE TODO
CORS(app)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Almacenamiento temporal de calibraciones (en memoria)
calibraciones_activas = {}

# Tiempo de expiración de calibración: 2 horas
EXPIRACION_CALIBRACION = timedelta(hours=2)

def limpiar_calibraciones_expiradas():
    """Elimina calibraciones que expiraron"""
    ahora = datetime.now()
    usuarios_expirados = [
        user for user, data in calibraciones_activas.items()
        if data['expires'] < ahora
    ]
    for user in usuarios_expirados:
        del calibraciones_activas[user]
        logger.info(f"Calibración expirada eliminada: {user}")

def base64_to_image(base64_string):
    """Convierte string base64 a imagen OpenCV"""
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        logger.error(f"Error convirtiendo base64 a imagen: {e}")
        return None

def image_to_base64(img):
    """Convierte imagen OpenCV a string base64"""
    try:
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{img_base64}"
    except Exception as e:
        logger.error(f"Error convirtiendo imagen a base64: {e}")
        return None

@app.route('/')
def home():
    """Endpoint de prueba"""
    return jsonify({
        'status': 'ok',
        'message': 'API Analizador de Probetas funcionando',
        'version': '1.0',
        'calibraciones_activas': len(calibraciones_activas)
    })

# ... (resto del código igual)
@app.route('/detectar_aruco', methods=['POST'])
def detectar_aruco():
    """PASO A2: Detectar ArUco y rectificar tabla"""
    try:
        data = request.get_json()
        
        if not data or 'imagen' not in data or 'user_code' not in data:
            return jsonify({'exito': False, 'mensaje': 'Faltan datos requeridos'}), 400
        
        user_code = data['user_code']
        logger.info(f"[{user_code}] Iniciando detección ArUco")
        
        img = base64_to_image(data['imagen'])
        if img is None:
            return jsonify({'exito': False, 'mensaje': 'Error al procesar imagen'}), 400
        
        temp_path = os.path.join(TEMP_DIR, f'{user_code}_tabla.jpg')
        cv2.imwrite(temp_path, img)
        
        detector = TablaAPIDetector(target_width=800, target_height=533)
        resultado = detector.procesar_imagen(temp_path)
        
        os.remove(temp_path)
        
        if not resultado['exito']:
            return jsonify({
                'exito': False,
                'mensaje': resultado['mensaje'],
                'imagen_marcadores': image_to_base64(resultado['imagen_marcadores']) if resultado['imagen_marcadores'] is not None else None
            })
        
        response = {
            'exito': True,
            'mensaje': 'Tabla rectificada correctamente',
            'imagen_rectificada': image_to_base64(resultado['imagen_rectificada']),
            'imagen_marcadores': image_to_base64(resultado['imagen_marcadores'])
        }
        
        logger.info(f"[{user_code}] ArUco detectado exitosamente")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error en detectar_aruco: {e}")
        return jsonify({'exito': False, 'mensaje': f'Error del servidor: {str(e)}'}), 500

@app.route('/extraer_colores', methods=['POST'])
def extraer_colores():
    """PASO B3: Extraer colores de tabla rectificada"""
    try:
        data = request.get_json()
        
        if not all(k in data for k in ['imagen_rectificada', 'bbox_tabla', 'user_code']):
            return jsonify({'exito': False, 'mensaje': 'Faltan datos requeridos'}), 400
        
        user_code = data['user_code']
        bbox_tabla = data.get('bbox_tabla')
        if not bbox_tabla or not isinstance(bbox_tabla, list):
            logger.error(f"bbox_tabla inválido: {bbox_tabla}")
            return jsonify({'exito': False, 'mensaje': 'bbox_tabla no recibido o inválido'}), 400
        bbox_tabla = tuple(bbox_tabla)
        
        logger.info(f"[{user_code}] Iniciando extracción de colores")
        
        img_tabla = base64_to_image(data['imagen_rectificada'])
        if img_tabla is None:
            return jsonify({'exito': False, 'mensaje': 'Error al procesar imagen'}), 400
        
        temp_tabla = os.path.join(TEMP_DIR, f'{user_code}_tabla_rect.jpg')
        cv2.imwrite(temp_tabla, img_tabla)
        
        extractor = ExtractorProporcional(
            tabla_rectificada_path=temp_tabla,
            referencia_path='referencia2.jpg'
        )
        
        resultado = extractor.procesar_extraccion_completa(bbox_tabla, directorio_salida=TEMP_DIR)
        
        os.remove(temp_tabla)
        
        if not resultado['exito']:
            return jsonify({'exito': False, 'mensaje': resultado['mensaje']})
        
        limpiar_calibraciones_expiradas()
        
        ahora = datetime.now()
        calibraciones_activas[user_code] = {
            'colores': resultado['colores_extraidos'],
            'timestamp': ahora,
            'expires': ahora + EXPIRACION_CALIBRACION,
            'estadisticas': resultado['estadisticas']
        }
        
        img_debug = None
        for archivo in resultado['archivos_generados']:
            if 'debug' in archivo:
                img_debug = cv2.imread(archivo)
                os.remove(archivo)
                break
        
        logger.info(f"[{user_code}] Colores extraídos: {len(resultado['colores_extraidos'])}")
        
        return jsonify({
            'exito': True,
            'mensaje': f"Extraídos {len(resultado['colores_extraidos'])} colores",
            'colores_extraidos': len(resultado['colores_extraidos']),
            'imagen_debug': image_to_base64(img_debug) if img_debug is not None else None,
            'expira_en': EXPIRACION_CALIBRACION.total_seconds()
        })
        
    except Exception as e:
        import traceback
        error_completo = traceback.format_exc()
        logger.error(f"Error en extraer_colores:\n{error_completo}")
        return jsonify({'exito': False, 'mensaje': f'Error del servidor: {str(e)}'}), 500

@app.route('/rectificar_probeta', methods=['POST'])
def rectificar_probeta():
    """PASO C2: Rectificar imagen de probeta usando ArUco"""
    try:
        data = request.get_json()
        if 'imagen_probeta' not in data or 'user_code' not in data:
            return jsonify({'exito': False, 'mensaje': 'Faltan datos'}), 400

        user_code = data['user_code']
        logger.info(f"[{user_code}] Rectificando probeta con ArUco")

        img = base64_to_image(data['imagen_probeta'])
        if img is None:
            return jsonify({'exito': False, 'mensaje': 'Error procesando imagen'}), 400

        # Guardar temporalmente
        temp_path = os.path.join(TEMP_DIR, f'{user_code}_probeta.jpg')
        cv2.imwrite(temp_path, img)
        
        # Usar detector ArUco (mismas dimensiones que tabla o ajustadas)
        detector = TablaAPIDetector(target_width=800, target_height=513)
        resultado = detector.procesar_imagen(temp_path)
        
        os.remove(temp_path)
        
        if not resultado['exito']:
            return jsonify({
                'exito': False,
                'mensaje': resultado['mensaje'],
                'imagen_marcadores': image_to_base64(resultado['imagen_marcadores']) if resultado['imagen_marcadores'] is not None else None
            })
        
        response = {
            'exito': True,
            'mensaje': 'Probeta rectificada correctamente',
            'imagen_rectificada': image_to_base64(resultado['imagen_rectificada']),
            'imagen_marcadores': image_to_base64(resultado['imagen_marcadores'])
        }
        
        logger.info(f"[{user_code}] Probeta rectificada con ArUco exitosamente")
        return jsonify(response)

    except Exception as e:
        import traceback
        logger.error(f"Error en rectificar_probeta:\n{traceback.format_exc()}")
        return jsonify({'exito': False, 'mensaje': f'Error del servidor: {str(e)}'}), 500
@app.route('/analizar_probeta', methods=['POST'])
def analizar_probeta():
    """PASO C2: Analizar probeta con calibración activa"""
    try:
        data = request.get_json()
        
        if not all(k in data for k in ['imagen_probeta', 'tipo_test', 'area_seleccionada', 'user_code']):
            return jsonify({'exito': False, 'mensaje': 'Faltan datos requeridos'}), 400
        
        user_code = data['user_code']
        tipo_test = data['tipo_test']
        area_seleccionada = tuple(data['area_seleccionada'])
        
        logger.info(f"[{user_code}] Analizando probeta tipo: {tipo_test}")
        
        limpiar_calibraciones_expiradas()
        
        if user_code not in calibraciones_activas:
            return jsonify({
                'exito': False,
                'mensaje': 'Calibración expirada o no encontrada. Vuelve a calibrar la tabla.'
            }), 400
        
        img_probeta = base64_to_image(data['imagen_probeta'])
        if img_probeta is None:
            return jsonify({'exito': False, 'mensaje': 'Error al procesar imagen de probeta'}), 400
        
        colores_calibracion = calibraciones_activas[user_code]['colores']
        
        # Crear diccionario de colores organizados por tipo
        valores_por_tipo = {}
        for color_obj in colores_calibracion:
            tipo_param = color_obj.parametro
            valor = color_obj.valor
            color_rgb = color_obj.color_rgb
            
            if tipo_param not in valores_por_tipo:
                valores_por_tipo[tipo_param] = {}
            valores_por_tipo[tipo_param][valor] = color_rgb
        
        # ✅ MAPEO CORREGIDO: frontend → nombre exacto en Excel
        mapeo_tipos = {
            'pH': 'pH',
            'high_ph': 'High_Range_pH',
            'ammonia': 'Ammonia',
            'nitrite': 'Nitrite',
            'nitrate': 'Nitrate'
        }
        
        tipo_calibracion = mapeo_tipos.get(tipo_test)
        
        # ✅ Búsqueda flexible si no encuentra exacto
        if not tipo_calibracion or tipo_calibracion not in valores_por_tipo:
            # Buscar variaciones (case-insensitive, con/sin espacios)
            for key in valores_por_tipo.keys():
                if tipo_test.lower().replace('_', ' ') in key.lower().replace('_', ' '):
                    tipo_calibracion = key
                    break
        
        if not tipo_calibracion or tipo_calibracion not in valores_por_tipo:
            logger.error(f"Tipos disponibles: {list(valores_por_tipo.keys())}")
            return jsonify({
                'exito': False,
                'mensaje': f'No hay datos de calibración para {tipo_test}. Tipos disponibles: {list(valores_por_tipo.keys())}'
            }), 400
        
        # Extraer color promedio del área seleccionada
        x, y, w, h = area_seleccionada
        
        img_h, img_w = img_probeta.shape[:2]
        if x < 0 or y < 0 or x + w > img_w or y + h > img_h or w < 5 or h < 5:
            return jsonify({
                'exito': False,
                'mensaje': f'Área seleccionada inválida: ({x},{y},{w},{h}) en imagen {img_w}x{img_h}'
            }), 400
        
        region = img_probeta[y:y+h, x:x+w]
        mean_bgr = cv2.mean(region)
        color_promedio_rgb = (int(round(mean_bgr[2])), int(round(mean_bgr[1])), int(round(mean_bgr[0])))
        
        logger.info(f"[{user_code}] Color promedio detectado: RGB{color_promedio_rgb}")
        
        # Encontrar valores cercanos
        valores_cercanos = []
        for valor, color_ref in valores_por_tipo[tipo_calibracion].items():
            distancia = calcular_distancia_color(color_promedio_rgb, color_ref)
            valores_cercanos.append({
                'parametro': f'{tipo_test} {float(valor)}',
                'valor': float(valor),
                'color_rgb': [int(color_ref[0]), int(color_ref[1]), int(color_ref[2])],
                'distancia': float(distancia)
            })
        
        valores_cercanos.sort(key=lambda x: x['distancia'])
        
        if not valores_cercanos:
            return jsonify({
                'exito': False,
                'mensaje': 'No se encontraron valores de referencia'
            }), 400
        
        # Interpolación simple
        valor_final = valores_cercanos[0]['valor']
        interpolado = False
        
        if len(valores_cercanos) >= 2:
            v1 = valores_cercanos[0]
            v2 = valores_cercanos[1]
            
            if v1['distancia'] > 10:
                peso1 = 1 / (v1['distancia'] + 0.1)
                peso2 = 1 / (v2['distancia'] + 0.1)
                peso_total = peso1 + peso2
                valor_final = (v1['valor'] * peso1 + v2['valor'] * peso2) / peso_total
                interpolado = True
        
        distancia_minima = valores_cercanos[0]['distancia']
        confianza = max(0.1, min(1.0, 1 - (distancia_minima / 100)))
        
        response = {
            'exito': True,
            'valor_final': float(valor_final),
            'parametro_cercano': valores_cercanos[0]['parametro'],
            'confianza': float(confianza),
            'interpolado': interpolado,
            'color_rgb': color_promedio_rgb,
            'valores_cercanos': valores_cercanos[:3]
        }
        
        logger.info(f"[{user_code}] Análisis completado: {valor_final:.2f} (confianza: {confianza:.2f})")
        return jsonify(response)
        
    except Exception as e:
        import traceback
        error_completo = traceback.format_exc()
        logger.error(f"Error en analizar_probeta:\n{error_completo}")
        return jsonify({'exito': False, 'mensaje': f'Error del servidor: {str(e)}'}), 500

def calcular_distancia_color(color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> float:
    """Calcular distancia euclidiana entre colores RGB."""
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    return float(np.sqrt((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2))

@app.route('/verificar_calibracion', methods=['POST'])
def verificar_calibracion():
    """Verifica si un usuario tiene calibración activa"""
    try:
        data = request.get_json()
        user_code = data.get('user_code')
        
        if not user_code:
            return jsonify({'exito': False, 'mensaje': 'Falta user_code'}), 400
        
        limpiar_calibraciones_expiradas()
        
        if user_code in calibraciones_activas:
            cal = calibraciones_activas[user_code]
            segundos_restantes = (cal['expires'] - datetime.now()).total_seconds()
            
            return jsonify({
                'activa': True,
                'expira_en_segundos': int(segundos_restantes),
                'colores_extraidos': len(cal['colores'])
            })
        else:
            return jsonify({'activa': False})
        
    except Exception as e:
        logger.error(f"Error en verificar_calibracion: {e}")
        return jsonify({'exito': False, 'mensaje': str(e)}), 500

if __name__ == '__main__':

    app.run(debug=True, host='0.0.0.0', port=5000)


