#!/usr/bin/env python3
"""
🎨 Extractor de Colores por Mapeo Proporcional con Selección Manual
Permite al usuario seleccionar manualmente el área de la tabla antes del mapeo.
"""

import cv2
import numpy as np
import os
from openpyxl import Workbook
import json
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ColorInfo:
    """Información de un color de referencia."""
    parametro: str
    valor: float
    posicion_foto: Tuple[int, int, int, int]
    posicion_ref: Tuple[int, int, int, int]
    color_bgr: Tuple[int, int, int]
    color_rgb: Tuple[int, int, int]
    color_lab: Tuple[float, float, float]
    confianza: float
    puntos_muestreados: int

class SelectorTablaManual:
    """Selector manual del área de la tabla."""
    
    def __init__(self, img_rectificada: np.ndarray):
        self.img_original = img_rectificada.copy()
        
        # Parámetros de visualización
        self.max_width, self.max_height = 1200, 800
        self.calcular_escala()
        
        # Estado de interacción
        self.drawing = False
        self.start_pos = (0, 0)
        self.current_rect = None
        self.selection_made = False
        self.selected_area = None
        
        # Crear imagen de visualización
        self.img_display = cv2.resize(self.img_original, (self.display_w, self.display_h), 
                                    interpolation=cv2.INTER_AREA)
        
    def calcular_escala(self):
        """Calcular escala para ajustar imagen a ventana."""
        orig_h, orig_w = self.img_original.shape[:2]
        scale_w = min(1.0, self.max_width / orig_w)
        scale_h = min(1.0, self.max_height / orig_h)
        self.scale = min(scale_w, scale_h)
        
        self.display_w = int(round(orig_w * self.scale))
        self.display_h = int(round(orig_h * self.scale))
        
    def display_to_original(self, x_disp: int, y_disp: int) -> Tuple[int, int]:
        """Convertir coordenadas de display a originales."""
        x_orig = int(round(x_disp / self.scale))
        y_orig = int(round(y_disp / self.scale))
        
        # Clamp a límites
        h, w = self.img_original.shape[:2]
        x_orig = max(0, min(w-1, x_orig))
        y_orig = max(0, min(h-1, y_orig))
        
        return x_orig, y_orig
    
    def on_mouse(self, event, x, y, flags, param):
        """Callback del mouse para selección."""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_pos = (x, y)
            self.current_rect = None
            
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                x1, y1 = self.start_pos
                x2, y2 = x, y
                
                # Ordenar coordenadas
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                
                self.current_rect = (x1, y1, x2, y2)
                
                # Mostrar rectángulo temporal en tiempo real
                img_temp = self.img_display.copy()
                cv2.rectangle(img_temp, (x1, y1), (x2, y2), (0, 255, 0), 3)
                
                # Mostrar dimensiones
                width_px = x2 - x1
                height_px = y2 - y1
                cv2.putText(img_temp, f"{width_px}x{height_px} px", 
                           (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.6, (0, 255, 0), 2)
                
                cv2.imshow("Selecciona la TABLA completa (ENTER=confirmar, ESC=cancelar)", img_temp)
                
        elif event == cv2.EVENT_LBUTTONUP:
            if not self.drawing:
                return
                
            self.drawing = False
            
            if self.current_rect is None:
                return
                
            x1, y1, x2, y2 = self.current_rect
            
            # Verificar tamaño mínimo
            if x2 - x1 < 50 or y2 - y1 < 50:
                print("⚠️ Selección muy pequeña, intenta de nuevo")
                return
            
            # Convertir a coordenadas originales
            x1_orig, y1_orig = self.display_to_original(x1, y1)
            x2_orig, y2_orig = self.display_to_original(x2, y2)
            
            # Guardar área seleccionada como (x, y, w, h)
            self.selected_area = (x1_orig, y1_orig, x2_orig - x1_orig, y2_orig - y1_orig)
            
            # Mostrar resultado en imagen
            img_result = self.img_display.copy()
            cv2.rectangle(img_result, (x1, y1), (x2, y2), (0, 255, 0), 3)
            
            # Mostrar dimensiones finales
            cv2.putText(img_result, f"Tabla: {x2-x1}x{y2-y1} px", 
                       (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0, 255, 0), 2)
            cv2.putText(img_result, "TABLA SELECCIONADA", 
                       (x1, y2+25), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0, 255, 0), 2)
            
            cv2.imshow("Selecciona la TABLA completa (ENTER=confirmar, ESC=cancelar)", img_result)
            
            print(f"✅ Tabla seleccionada: {self.selected_area}")
            print("📝 Presiona ENTER para confirmar la selección")
            
    def seleccionar_tabla(self) -> Optional[Tuple[int, int, int, int]]:
        """Interfaz para seleccionar tabla manualmente."""
        window_name = "Selecciona la TABLA completa (ENTER=confirmar, ESC=cancelar)"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self.on_mouse)
        
        print("\n👆 Instrucciones:")
        print("• Haz clic y arrastra para seleccionar toda el área de la tabla")
        print("• Asegúrate de incluir todos los rectángulos de colores")
        print("• Presiona ENTER para confirmar la selección")
        print("• Presiona ESC para cancelar")
        
        while True:
            cv2.imshow(window_name, self.img_display)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                cv2.destroyAllWindows()
                return None
                
            elif key == 13:  # ENTER
                if self.selected_area is not None:
                    cv2.destroyAllWindows()
                    return self.selected_area
                else:
                    print("⚠️ Primero debes hacer una selección")

class ExtractorProporcional:
    def __init__(self, 
                 tabla_rectificada_path: str = "tabla_rectificada.jpg",
                 referencia_path: str = "referencia2.jpg"):
        """Inicializar extractor proporcional."""
        self.tabla_path = tabla_rectificada_path
        self.referencia_path = referencia_path
        
        # Configuración de parámetros
        self.parametros_config = {
            'pH': {
                'valores': [6.0, 6.4, 6.6, 6.8, 7.0, 7.2, 7.6],
                'posicion_columna': 0,
                'nombre_completo': 'pH'
            },
            'High_Range_pH': {
                'valores': [7.4, 7.8, 8.0, 8.2, 8.4, 8.8],
                'posicion_columna': 1,
                'nombre_completo': 'High Range pH'
            },
            'Ammonia': {
                'valores': [0, 0.25, 0.50, 1.0, 2.0, 4.0, 8.0],
                'posicion_columna': 2,
                'nombre_completo': 'Ammonia (NH₃/NH₄⁺) ppm'
            },
            'Nitrite': {
                'valores': [0, 0.25, 0.50, 1.0, 2.0, 5.0],
                'posicion_columna': 3,
                'nombre_completo': 'Nitrite (NO₂⁻) ppm'
            },
            'Nitrate': {
                'valores': [0, 5, 10, 20, 40, 80, 160],
                'posicion_columna': 4,
                'nombre_completo': 'Nitrate (NO₃⁻) ppm'
            }
        }
        
        # Parámetros de sampling
        self.puntos_por_rectangulo = 5
        self.radio_sampling = 0.3
        
    def cargar_imagenes(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Cargar imagen tabla y referencia."""
        try:
            # Cargar tabla rectificada
            if not os.path.exists(self.tabla_path):
                logger.error(f"No se encuentra {self.tabla_path}")
                return None, None
            
            tabla = cv2.imread(self.tabla_path)
            if tabla is None:
                logger.error(f"No se pudo cargar {self.tabla_path}")
                return None, None
            
            # Cargar referencia
            if not os.path.exists(self.referencia_path):
                logger.error(f"No se encuentra {self.referencia_path}")
                return None, None
            
            referencia = cv2.imread(self.referencia_path)
            if referencia is None:
                logger.error(f"No se pudo cargar {self.referencia_path}")
                return None, None
            
            logger.info(f"📸 Tabla cargada: {tabla.shape[1]}x{tabla.shape[0]}")
            logger.info(f"📋 Referencia cargada: {referencia.shape[1]}x{referencia.shape[0]}")
            
            return tabla, referencia
            
        except Exception as e:
            logger.error(f"Error cargando imágenes: {e}")
            return None, None
    
    def detectar_tabla_en_referencia(self, img_ref: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Detectar la tabla en la imagen de referencia."""
        try:
            if len(img_ref.shape) == 3:
                gray = cv2.cvtColor(img_ref, cv2.COLOR_BGR2GRAY)
            else:
                gray = img_ref.copy()
            
            _, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            
            contornos, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contornos:
                h, w = gray.shape
                bbox_ref = (0, 0, w, h)
            else:
                contorno_mayor = max(contornos, key=cv2.contourArea)
                bbox_ref = cv2.boundingRect(contorno_mayor)
            
            logger.info(f"📋 Tabla detectada en referencia: {bbox_ref}")
            return bbox_ref
            
        except Exception as e:
            logger.error(f"Error detectando tabla en referencia: {e}")
            return None
    
    def extraer_rectangulos_referencia(self, img_ref: np.ndarray, bbox_ref: Tuple[int, int, int, int]) -> Dict[str, List[Tuple[int, int, int, int]]]:
        """Extraer posiciones de rectángulos negros de la imagen de referencia."""
        try:
            x_ref, y_ref, w_ref, h_ref = bbox_ref
            
            roi_ref = img_ref[y_ref:y_ref+h_ref, x_ref:x_ref+w_ref]
            
            if len(roi_ref.shape) == 3:
                gray_ref = cv2.cvtColor(roi_ref, cv2.COLOR_BGR2GRAY)
            else:
                gray_ref = roi_ref.copy()
            
            _, mask_negros = cv2.threshold(gray_ref, 127, 255, cv2.THRESH_BINARY_INV)
            
            kernel = np.ones((3, 3), np.uint8)
            mask_negros = cv2.morphologyEx(mask_negros, cv2.MORPH_CLOSE, kernel)
            
            contornos, _ = cv2.findContours(mask_negros, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            rectangulos = []
            for contorno in contornos:
                area = cv2.contourArea(contorno)
                if area < 100:
                    continue
                
                x, y, w, h = cv2.boundingRect(contorno)
                rectangulos.append((x_ref + x, y_ref + y, w, h))
            
            rectangulos.sort(key=lambda r: (r[1], r[0]))
            
            logger.info(f"📋 Encontrados {len(rectangulos)} rectángulos en referencia")
            
            rectangulos_organizados = self._organizar_rectangulos(rectangulos)
            
            return rectangulos_organizados
            
        except Exception as e:
            logger.error(f"Error extrayendo rectángulos de referencia: {e}")
            return {}
    
    def _organizar_rectangulos(self, rectangulos: List[Tuple[int, int, int, int]]) -> Dict[str, List[Tuple[int, int, int, int]]]:
        """Organizar rectángulos por parámetros según su posición."""
        try:
            if not rectangulos:
                return {}
            
            rectangulos.sort(key=lambda r: r[0])
            
            x_positions = [r[0] for r in rectangulos]
            x_min, x_max = min(x_positions), max(x_positions)
            ancho_total = x_max - x_min
            
            columnas = {i: [] for i in range(5)}
            
            for rect in rectangulos:
                x, y, w, h = rect
                pos_relativa = (x - x_min) / ancho_total if ancho_total > 0 else 0
                col_idx = min(4, int(pos_relativa * 5))
                columnas[col_idx].append(rect)
            
            rectangulos_organizados = {}
            
            for i, (param, config) in enumerate(self.parametros_config.items()):
                if i < 5 and i in columnas:
                    rects_columna = sorted(columnas[i], key=lambda r: r[1])
                    rectangulos_organizados[param] = rects_columna[:len(config['valores'])]
                else:
                    rectangulos_organizados[param] = []
            
            return rectangulos_organizados
            
        except Exception as e:
            logger.error(f"Error organizando rectángulos: {e}")
            return {}
    
    def mapear_coordenadas(self, bbox_foto: Tuple[int, int, int, int], 
                          bbox_ref: Tuple[int, int, int, int],
                          rect_ref: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Mapear coordenadas desde referencia a foto usando proporcionalidad."""
        try:
            x_foto, y_foto, w_foto, h_foto = bbox_foto
            x_ref, y_ref, w_ref, h_ref = bbox_ref
            rx, ry, rw, rh = rect_ref
            
            escala_x = w_foto / w_ref if w_ref > 0 else 1
            escala_y = h_foto / h_ref if h_ref > 0 else 1
            
            x_mapeado = x_foto + int((rx - x_ref) * escala_x)
            y_mapeado = y_foto + int((ry - y_ref) * escala_y)
            w_mapeado = int(rw * escala_x)
            h_mapeado = int(rh * escala_y)
            
            return (x_mapeado, y_mapeado, w_mapeado, h_mapeado)
            
        except Exception as e:
            logger.error(f"Error mapeando coordenadas: {e}")
            return rect_ref
    
    def extraer_color_con_sampling(self, img: np.ndarray, rect: Tuple[int, int, int, int]) -> Tuple[Optional[Dict], float]:
        """Extraer color usando múltiples puntos de muestreo."""
        try:
            x, y, w, h = rect
            
            img_h, img_w = img.shape[:2]
            if x < 0 or y < 0 or x + w > img_w or y + h > img_h:
                logger.warning(f"Rectángulo fuera de límites: {rect}")
                return None, 0.0
            
            if w < 10 or h < 10:
                logger.warning(f"Rectángulo muy pequeño: {rect}")
                return None, 0.0
            
            centro_x = x + w // 2
            centro_y = y + h // 2
            radio_x = int(w * self.radio_sampling)
            radio_y = int(h * self.radio_sampling)
            
            puntos_muestreo = []
            puntos_muestreo.append((centro_x, centro_y))
            
            if self.puntos_por_rectangulo > 1:
                for i in range(self.puntos_por_rectangulo - 1):
                    angulo = (2 * np.pi * i) / (self.puntos_por_rectangulo - 1)
                    px = centro_x + int(radio_x * np.cos(angulo))
                    py = centro_y + int(radio_y * np.sin(angulo))
                    
                    if x <= px < x + w and y <= py < y + h:
                        puntos_muestreo.append((px, py))
            
            if not puntos_muestreo:
                return None, 0.0
            
            colores_bgr = []
            colores_rgb = []
            colores_lab = []
            
            for px, py in puntos_muestreo:
                pixel_bgr = img[py, px]
                pixel_rgb = cv2.cvtColor(pixel_bgr.reshape(1, 1, 3), cv2.COLOR_BGR2RGB)[0, 0]
                pixel_lab = cv2.cvtColor(pixel_bgr.reshape(1, 1, 3), cv2.COLOR_BGR2LAB)[0, 0]
                
                colores_bgr.append(pixel_bgr)
                colores_rgb.append(pixel_rgb)
                colores_lab.append(pixel_lab)
            
            color_bgr_promedio = np.mean(colores_bgr, axis=0).astype(int)
            color_rgb_promedio = np.mean(colores_rgb, axis=0).astype(int)
            color_lab_promedio = np.mean(colores_lab, axis=0)
            
            std_rgb = np.std(colores_rgb, axis=0)
            uniformidad = np.mean(std_rgb)
            confianza = max(0.1, min(1.0, 1 - (uniformidad / 50)))
            
            return {
                'bgr': tuple(color_bgr_promedio),
                'rgb': tuple(color_rgb_promedio),
                'lab': tuple(color_lab_promedio.astype(float)),
                'uniformidad': uniformidad,
                'puntos_muestreados': len(puntos_muestreo)
            }, confianza
            
        except Exception as e:
            logger.error(f"Error extrayendo color con sampling: {e}")
            return None, 0.0
    
    def procesar_extraccion_completa(self, bbox_foto_manual: Tuple[int, int, int, int], 
                                    directorio_salida: str = ".") -> Dict:
        """Proceso completo de extracción proporcional con tabla seleccionada manualmente."""
        resultado = {
            'exito': False,
            'mensaje': '',
            'tabla_foto': None,
            'tabla_referencia': None,
            'colores_extraidos': [],
            'estadisticas': {},
            'archivos_generados': []
        }
        
        try:
            Path(directorio_salida).mkdir(exist_ok=True)
            
            # Cargar imágenes
            img_tabla, img_ref = self.cargar_imagenes()
            if img_tabla is None or img_ref is None:
                resultado['mensaje'] = "No se pudieron cargar las imágenes"
                return resultado
            
            # Usar bbox manual
            bbox_foto = bbox_foto_manual
            resultado['tabla_foto'] = bbox_foto
            logger.info(f"✅ Usando tabla seleccionada manualmente: {bbox_foto}")
            
            # Detectar tabla en referencia
            bbox_ref = self.detectar_tabla_en_referencia(img_ref)
            if bbox_ref is None:
                resultado['mensaje'] = "No se pudo detectar la tabla en la referencia"
                return resultado
            
            resultado['tabla_referencia'] = bbox_ref
            
            # Extraer rectángulos de referencia
            rectangulos_ref = self.extraer_rectangulos_referencia(img_ref, bbox_ref)
            if not rectangulos_ref:
                resultado['mensaje'] = "No se pudieron extraer rectángulos de la referencia"
                return resultado
            
            logger.info(f"🎨 Iniciando extracción de colores con mapeo proporcional")
            
            # Extraer colores
            colores_extraidos = []
            
            for parametro, rects_ref in rectangulos_ref.items():
                config = self.parametros_config[parametro]
                logger.info(f"   📋 Procesando {parametro}: {len(rects_ref)} rectángulos")
                
                for i, rect_ref in enumerate(rects_ref):
                    if i >= len(config['valores']):
                        break
                    
                    valor = config['valores'][i]
                    
                    rect_foto = self.mapear_coordenadas(bbox_foto, bbox_ref, rect_ref)
                    
                    color_info, confianza = self.extraer_color_con_sampling(img_tabla, rect_foto)
                    
                    if color_info is not None:
                        color_obj = ColorInfo(
                            parametro=parametro,
                            valor=valor,
                            posicion_foto=rect_foto,
                            posicion_ref=rect_ref,
                            color_bgr=color_info['bgr'],
                            color_rgb=color_info['rgb'],
                            color_lab=color_info['lab'],
                            confianza=confianza,
                            puntos_muestreados=color_info['puntos_muestreados']
                        )
                        colores_extraidos.append(color_obj)
                        
                        logger.debug(f"     ✓ {valor}: RGB{color_info['rgb']} (conf: {confianza:.3f})")
                    else:
                        logger.warning(f"     ⚠️ Error extrayendo {parametro} = {valor}")
            
            if not colores_extraidos:
                resultado['mensaje'] = "No se pudieron extraer colores"
                return resultado
            
            resultado['colores_extraidos'] = colores_extraidos
            
            # Generar estadísticas
            stats = self._generar_estadisticas(colores_extraidos, bbox_foto, bbox_ref)
            resultado['estadisticas'] = stats
            
            # Generar imagen de debug
            debug_img = self._generar_imagen_debug(img_tabla, bbox_foto, colores_extraidos)
            ruta_debug = os.path.join(directorio_salida, "extraccion_proporcional_debug.jpg")
            cv2.imwrite(ruta_debug, debug_img)
            resultado['archivos_generados'].append(ruta_debug)
            
            # Generar Excel simplificado
            ruta_xlsx = os.path.join(directorio_salida, "colores_proporcional.xlsx")
            self._generar_excel_simplificado(colores_extraidos, ruta_xlsx)
            resultado['archivos_generados'].append(ruta_xlsx)
            
            # Guardar metadatos
            ruta_meta = os.path.join(directorio_salida, "proporcional_metadatos.json")
            self._guardar_metadatos(resultado, ruta_meta)
            resultado['archivos_generados'].append(ruta_meta)
            
            resultado['exito'] = True
            resultado['mensaje'] = f"Extracción completada: {len(colores_extraidos)} colores extraídos"
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error en extracción completa: {e}")
            resultado['mensaje'] = f"Error inesperado: {str(e)}"
            return resultado
    
    def _generar_estadisticas(self, colores: List[ColorInfo], bbox_foto: Tuple[int, int, int, int], 
                             bbox_ref: Tuple[int, int, int, int]) -> Dict:
        """Generar estadísticas detalladas."""
        if not colores:
            return {}
        
        stats = {
            'mapeo': {
                'tabla_foto': bbox_foto,
                'tabla_referencia': bbox_ref,
                'escala_x': bbox_foto[2] / bbox_ref[2] if bbox_ref[2] > 0 else 1,
                'escala_y': bbox_foto[3] / bbox_ref[3] if bbox_ref[3] > 0 else 1
            },
            'colores': {
                'total_extraidos': len(colores),
                'total_esperados': sum(len(config['valores']) for config in self.parametros_config.values()),
                'porcentaje_exito': (len(colores) / sum(len(config['valores']) for config in self.parametros_config.values())) * 100,
                'confianza_promedio': np.mean([c.confianza for c in colores]),
                'confianza_minima': np.min([c.confianza for c in colores]),
                'confianza_maxima': np.max([c.confianza for c in colores]),
                'puntos_promedio': np.mean([c.puntos_muestreados for c in colores])
            },
            'por_parametro': {}
        }
        
        for param, config in self.parametros_config.items():
            colores_param = [c for c in colores if c.parametro == param]
            esperados = len(config['valores'])
            detectados = len(colores_param)
            
            stats['por_parametro'][param] = {
                'esperados': esperados,
                'detectados': detectados,
                'porcentaje_exito': (detectados / esperados) * 100 if esperados > 0 else 0,
                'confianza_promedio': np.mean([c.confianza for c in colores_param]) if colores_param else 0,
                'valores_detectados': sorted([c.valor for c in colores_param])
            }
        
        return stats
    
    def _generar_imagen_debug(self, img: np.ndarray, bbox_foto: Tuple[int, int, int, int], 
                             colores: List[ColorInfo]) -> np.ndarray:
        """Generar imagen de debug con visualizaciones."""
        debug_img = img.copy()
        
        x, y, w, h = bbox_foto
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 3)
        cv2.putText(debug_img, "TABLA SELECCIONADA", (x, y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        colores_param = {
            'pH': (0, 255, 0),
            'High_Range_pH': (255, 0, 0),
            'Ammonia': (0, 165, 255),
            'Nitrite': (255, 0, 255),
            'Nitrate': (0, 255, 255)
        }
        
        for color in colores:
            x, y, w, h = color.posicion_foto
            param_color = colores_param.get(color.parametro, (255, 255, 255))
            
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), param_color, 2)
            
            texto = f"{color.valor}"
            font_scale = 0.4
            cv2.putText(debug_img, texto, (x + 2, y + h - 2), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, param_color, 1)
            
            centro_x = x + w // 2
            centro_y = y + h // 2
            cv2.circle(debug_img, (centro_x, centro_y), 3, param_color, -1)
        
        return debug_img
    
    def _generar_excel_simplificado(self, colores: List[ColorInfo], ruta_xlsx: str):
        """Generar Excel (XLSX) simplificado con solo las columnas necesarias: parametro, valor, R, G, B."""
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Colores"

            fieldnames = ['parametro', 'valor', 'R', 'G', 'B']
        
            ws.append(fieldnames)

            for color in colores:
                fila = [
                    color.parametro,
                    color.valor,
                    color.color_rgb[0],
                    color.color_rgb[1],
                    color.color_rgb[2]
                ]
                ws.append(fila)

            wb.save(ruta_xlsx)
            logger.info(f"💾 Excel simplificado generado: {ruta_xlsx}")

        except Exception as e:
            logger.error(f"Error generando Excel simplificado: {e}")
    
    def _guardar_metadatos(self, resultado: Dict, ruta_meta: str):
        """Guardar metadatos del procesamiento."""
        try:
            metadatos = {
                'version': 'proporcional_manual_1.0',
                'algoritmo': 'mapeo_proporcional_con_seleccion_manual',
                'exito': resultado['exito'],
                'mensaje': resultado['mensaje'],
                'estadisticas': resultado['estadisticas'],
                'configuracion': {
                    'puntos_por_rectangulo': self.puntos_por_rectangulo,
                    'radio_sampling': self.radio_sampling
                },
                'parametros_config': self.parametros_config,
                'archivos_fuente': {
                    'tabla': self.tabla_path,
                    'referencia': self.referencia_path
                }
            }
            
            with open(ruta_meta, 'w', encoding='utf-8') as f:
                json.dump(metadatos, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Metadatos guardados: {ruta_meta}")
            
        except Exception as e:
            logger.error(f"Error guardando metadatos: {e}")

def main():
    """Función principal."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"📂 Directorio de trabajo: {os.getcwd()}")
    
    # Verificar archivos necesarios
    archivos_necesarios = ["tabla_rectificada.jpg", "referencia2.jpg"]
    faltantes = [f for f in archivos_necesarios if not os.path.exists(f)]
    
    if faltantes:
        print(f"❌ Archivos faltantes: {', '.join(faltantes)}")
        print("   • tabla_rectificada.jpg: Ejecuta detectar_aruco_mejorado.py")
        print("   • referencia2.jpg: Imagen de referencia en B&N")
        return
    
    # Cargar imagen rectificada
    img_tabla = cv2.imread("tabla_rectificada.jpg")
    if img_tabla is None:
        print("❌ No se pudo cargar tabla_rectificada.jpg")
        return
    
    print("\n" + "="*60)
    print("🎨 EXTRACTOR DE COLORES CON SELECCIÓN MANUAL")
    print("="*60)
    
    # Paso 1: Selección manual de la tabla
    print("\n📍 PASO 1: Selección manual del área de la tabla")
    print("-" * 60)
    
    selector = SelectorTablaManual(img_tabla)
    bbox_tabla = selector.seleccionar_tabla()
    
    if bbox_tabla is None:
        print("\n❌ Selección cancelada por el usuario")
        return
    
    print(f"\n✅ Tabla seleccionada: x={bbox_tabla[0]}, y={bbox_tabla[1]}, w={bbox_tabla[2]}, h={bbox_tabla[3]}")
    
    # Paso 2: Extracción de colores
    print("\n🎨 PASO 2: Extracción de colores con mapeo proporcional")
    print("-" * 60)
    
    extractor = ExtractorProporcional()
    resultado = extractor.procesar_extraccion_completa(bbox_tabla)
    
    # Mostrar resultados
    if resultado['exito']:
        print(f"\n✅ {resultado['mensaje']}")
        stats = resultado['estadisticas']
        
        print(f"\n📊 Mapeo realizado:")
        print(f"   • Tabla en foto (manual): {stats['mapeo']['tabla_foto']}")
        print(f"   • Tabla en referencia: {stats['mapeo']['tabla_referencia']}")
        print(f"   • Escala X: {stats['mapeo']['escala_x']:.3f}")
        print(f"   • Escala Y: {stats['mapeo']['escala_y']:.3f}")
        
        print(f"\n📈 Resultados:")
        print(f"   • Colores extraídos: {stats['colores']['total_extraidos']}/{stats['colores']['total_esperados']} ({stats['colores']['porcentaje_exito']:.1f}%)")
        print(f"   • Confianza promedio: {stats['colores']['confianza_promedio']:.3f}")
        print(f"   • Puntos de muestreo promedio: {stats['colores']['puntos_promedio']:.1f}")
        
        print(f"\n📋 Por parámetro:")
        for param, info in stats['por_parametro'].items():
            nombre = extractor.parametros_config[param]['nombre_completo']
            print(f"   • {nombre}: {info['detectados']}/{info['esperados']} ({info['porcentaje_exito']:.1f}%) - conf: {info['confianza_promedio']:.3f}")
        
        print(f"\n💾 Archivos generados:")
        for archivo in resultado['archivos_generados']:
            print(f"   • {os.path.basename(archivo)}")
        
        print(f"\n🎯 Excel simplificado: parametro, valor, R, G, B")
        
        # Mostrar imagen de debug
        try:
            debug_path = next(f for f in resultado['archivos_generados'] if 'debug' in f)
            img_debug = cv2.imread(debug_path)
            if img_debug is not None:
                scale = 0.7
                width = int(img_debug.shape[1] * scale)
                height = int(img_debug.shape[0] * scale)
                img_show = cv2.resize(img_debug, (width, height), interpolation=cv2.INTER_AREA)
                cv2.imshow("🎯 Extracción Proporcional - Resultados", img_show)
                print(f"\n👁️ Presiona cualquier tecla para continuar...")
                cv2.waitKey(0)
                cv2.destroyAllWindows()
        except:
            pass
            
        print("\n" + "="*60)
        print("🎉 PROCESO COMPLETADO EXITOSAMENTE")
        print("="*60)
    else:
        print(f"\n❌ {resultado['mensaje']}")
        
        print(f"\n💡 Posibles soluciones:")
        print(f"   1. Selecciona toda el área de la tabla incluyendo todos los colores")
        print(f"   2. Verifica que referencia2.jpg sea correcta")
        print(f"   3. Asegúrate de que tabla_rectificada.jpg tenga buena calidad")

if __name__ == "__main__":
    main()