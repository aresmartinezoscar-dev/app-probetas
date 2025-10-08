#!/usr/bin/env python3
"""
🔍 Detección y Rectificación Robusta de Tabla API con ArUco
Versión mejorada con validaciones, logging y manejo de errores.
MEJORA: Muestra marcadores detectados parcialmente cuando no se encuentran todos.
"""

import cv2
import numpy as np
import os
import json
from pathlib import Path
import logging
from typing import Dict, Tuple, Optional, List

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TablaAPIDetector:
    def __init__(self, target_width: int = 800, target_height: int = 533):
        """
        Inicializar detector de tabla API.
        
        Args:
            target_width: Ancho objetivo de la tabla rectificada
            target_height: Alto objetivo de la tabla rectificada
        """
        self.target_width = target_width
        self.target_height = target_height
        
        # Configurar ArUco
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.parameters = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.parameters)
        
        # IDs esperados para cada esquina (ajustado según tu configuración real)
        self.expected_ids = {
            3: "superior_izquierda",    # ID 3 está en superior izquierda
            0: "superior_derecha",      # ID 0 está en superior derecha
            1: "inferior_izquierda",    # ID 1 está en inferior izquierda
            2: "inferior_derecha"       # ID 2 está en inferior derecha
        }
        
    def detectar_marcadores(self, img: np.ndarray) -> Tuple[Optional[Dict], bool, str]:
        """
        Detectar y validar marcadores ArUco.
        
        Returns:
            Tuple[marcadores_info, exito, mensaje]
        """
        try:
            # Detectar marcadores
            corners, ids, _ = self.detector.detectMarkers(img)
            
            if ids is None or len(ids) == 0:
                return None, False, "No se detectaron marcadores ArUco"
            
            # Crear diccionario de TODOS los marcadores detectados
            self.marcadores_detectados_todos = {}
            marcadores_validos = {}
            
            for i, marker_id in enumerate(ids.flatten()):
                info_marcador = {
                    'corners': corners[i][0],
                    'centro': np.mean(corners[i][0], axis=0),
                    'posicion': self.expected_ids.get(marker_id, f"desconocido_id_{marker_id}")
                }
                
                # Guardar TODOS los marcadores detectados
                self.marcadores_detectados_todos[marker_id] = info_marcador
                
                # Solo agregar a válidos si está en los IDs esperados
                if marker_id in self.expected_ids:
                    marcadores_validos[marker_id] = info_marcador
            
            # Verificar si tenemos todos los marcadores necesarios
            expected_ids = set(self.expected_ids.keys())
            detected_valid_ids = set(marcadores_validos.keys())
            
            if len(marcadores_validos) < 4:
                missing = expected_ids - detected_valid_ids
                found = detected_valid_ids
                extra = set(self.marcadores_detectados_todos.keys()) - expected_ids
                
                mensaje = f"Solo se detectaron {len(marcadores_validos)}/4 marcadores ArUco\n"
                mensaje += f"✅ Encontrados: {[f'ID_{id_}({self.expected_ids[id_]})' for id_ in sorted(found)]}\n"
                mensaje += f"❌ Faltan: {[f'ID_{id_}({self.expected_ids[id_]})' for id_ in sorted(missing)]}"
                
                if extra:
                    mensaje += f"\n⚠️ Marcadores extra detectados: {sorted(extra)}"
                
                return None, False, mensaje
            
            # Validar que tenemos exactamente los IDs esperados
            if not expected_ids.issubset(detected_valid_ids):
                missing = expected_ids - detected_valid_ids
                return None, False, f"Faltan marcadores con IDs: {missing}"
            
            # Validar geometría de los marcadores
            if not self._validar_geometria(marcadores_validos):
                return None, False, "La geometría de los marcadores no es válida"
            
            logger.info(f"✅ Detectados correctamente {len(marcadores_validos)} marcadores ArUco")
            return marcadores_validos, True, "Marcadores detectados correctamente"
            
        except Exception as e:
            logger.error(f"Error en detección de marcadores: {e}")
            return None, False, f"Error en detección: {str(e)}"
    
    def _validar_geometria(self, marcadores: Dict) -> bool:
        """
        Validar que los marcadores forman un cuadrilátero válido.
        """
        try:
            # Extraer centros
            centros = {id_: info['centro'] for id_, info in marcadores.items()}
            
            # Verificar que forman un cuadrilátero aproximadamente rectangular
            # Superior izq (ID 3) -> Superior der (ID 0) (debe ir hacia la derecha)
            if centros[0][0] <= centros[3][0]:  # sup_der.x <= sup_izq.x
                logger.warning("⚠️ Marcadores superiores mal orientados")
                return False
                
            # Superior izq (ID 3) -> Inferior izq (ID 1) (debe ir hacia abajo)  
            if centros[1][1] <= centros[3][1]:  # inf_izq.y <= sup_izq.y
                logger.warning("⚠️ Marcadores izquierdos mal orientados")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validando geometría: {e}")
            return False
    
    def dibujar_marcadores_detallados(self, img: np.ndarray, marcadores_todos: Dict) -> np.ndarray:
        """
        Dibujar TODOS los marcadores detectados con información detallada.
        """
        img_resultado = img.copy()
        
        if not marcadores_todos:
            return img_resultado
            
        try:
            for marker_id, info in marcadores_todos.items():
                corners = info['corners'].reshape(1, -1, 2).astype(np.int32)
                centro = info['centro'].astype(int)
                
                # Color según si es válido o no
                if marker_id in self.expected_ids:
                    color = (0, 255, 0)  # Verde para válidos
                    status = "✅ VÁLIDO"
                else:
                    color = (0, 165, 255)  # Naranja para extra/no esperados
                    status = "⚠️ EXTRA"
                
                # Dibujar contorno del marcador
                cv2.polylines(img_resultado, corners, True, color, 3)
                
                # Dibujar centro
                cv2.circle(img_resultado, tuple(centro), 8, color, -1)
                
                # Texto con ID y estado
                texto_id = f"ID: {marker_id}"
                texto_pos = info['posicion']
                texto_status = status
                
                # Posición del texto (arriba del marcador)
                pos_texto = (centro[0] - 60, centro[1] - 30)
                
                # Fondo para el texto
                cv2.rectangle(img_resultado, 
                            (pos_texto[0] - 5, pos_texto[1] - 45),
                            (pos_texto[0] + 200, pos_texto[1] + 10),
                            (255, 255, 255), -1)
                cv2.rectangle(img_resultado, 
                            (pos_texto[0] - 5, pos_texto[1] - 45),
                            (pos_texto[0] + 200, pos_texto[1] + 10),
                            (0, 0, 0), 2)
                
                # Escribir textos
                cv2.putText(img_resultado, texto_id, pos_texto, 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                cv2.putText(img_resultado, texto_pos, 
                           (pos_texto[0], pos_texto[1] + 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                cv2.putText(img_resultado, texto_status, 
                           (pos_texto[0], pos_texto[1] + 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Agregar leyenda en la esquina superior izquierda
            leyenda_y = 30
            cv2.rectangle(img_resultado, (10, 10), (350, leyenda_y + 60), (255, 255, 255), -1)
            cv2.rectangle(img_resultado, (10, 10), (350, leyenda_y + 60), (0, 0, 0), 2)
            
            cv2.putText(img_resultado, f"Marcadores detectados: {len(marcadores_todos)}", 
                       (15, leyenda_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            
            validos = sum(1 for id_ in marcadores_todos.keys() if id_ in self.expected_ids)
            cv2.putText(img_resultado, f"Validos: {validos}/4 | Extra: {len(marcadores_todos) - validos}", 
                       (15, leyenda_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
        except Exception as e:
            logger.error(f"Error dibujando marcadores: {e}")
            
        return img_resultado
    
    def extraer_puntos_esquinas(self, marcadores: Dict) -> np.ndarray:
        """
        Extraer puntos de esquinas para transformación de perspectiva.
        Usa la esquina más externa de cada marcador.
        """
        # Para cada marcador, seleccionar la esquina más externa
        esquinas = []
        
        # Superior izquierda (esquina 0 del marcador 3)
        esquinas.append(marcadores[3]['corners'][0])
        
        # Superior derecha (esquina 1 del marcador 0)  
        esquinas.append(marcadores[0]['corners'][1])
        
        # Inferior derecha (esquina 2 del marcador 2)
        esquinas.append(marcadores[2]['corners'][2])
        
        # Inferior izquierda (esquina 3 del marcador 1)
        esquinas.append(marcadores[1]['corners'][3])
        
        return np.array(esquinas, dtype="float32")
    
    def rectificar_tabla(self, img: np.ndarray, pts_src: np.ndarray) -> Tuple[Optional[np.ndarray], np.ndarray]:
        """
        Rectificar perspectiva de la tabla.
        
        Returns:
            Tuple[imagen_rectificada, matriz_homografia]
        """
        try:
            # Puntos destino (rectángulo perfecto)
            pts_dst = np.array([
                [0, 0],
                [self.target_width - 1, 0],
                [self.target_width - 1, self.target_height - 1],
                [0, self.target_height - 1]
            ], dtype="float32")
            
            # Calcular homografía
            M = cv2.getPerspectiveTransform(pts_src, pts_dst)
            
            # Aplicar transformación
            tabla_rectificada = cv2.warpPerspective(
                img, M, (self.target_width, self.target_height)
            )
            
            logger.info(f"✅ Tabla rectificada a {self.target_width}x{self.target_height}")
            return tabla_rectificada, M
            
        except Exception as e:
            logger.error(f"Error rectificando tabla: {e}")
            return None, None
    
    def procesar_imagen(self, ruta_imagen: str) -> Dict:
        """
        Proceso completo: detectar, validar y rectificar.
        
        Returns:
            Dict con resultados del procesamiento
        """
        resultado = {
            'exito': False,
            'mensaje': '',
            'imagen_original': None,
            'imagen_marcadores': None,
            'imagen_rectificada': None,
            'marcadores': None,
            'homografia': None
        }
        
        # Inicializar variable para todos los marcadores detectados
        self.marcadores_detectados_todos = {}
        
        try:
            # Cargar imagen
            if not os.path.exists(ruta_imagen):
                resultado['mensaje'] = f"No se encuentra la imagen: {ruta_imagen}"
                return resultado
                
            img = cv2.imread(ruta_imagen)
            if img is None:
                resultado['mensaje'] = f"No se pudo cargar la imagen: {ruta_imagen}"
                return resultado
                
            resultado['imagen_original'] = img.copy()
            logger.info(f"📸 Imagen cargada: {img.shape[1]}x{img.shape[0]}")
            
            # Detectar marcadores
            marcadores, exito, mensaje = self.detectar_marcadores(img)
            if not exito:
                resultado['mensaje'] = mensaje
                
                # NUEVA FUNCIONALIDAD: Mostrar marcadores parciales si los hay
                if hasattr(self, 'marcadores_detectados_todos') and self.marcadores_detectados_todos:
                    img_marcadores_parciales = self.dibujar_marcadores_detallados(img, self.marcadores_detectados_todos)
                    resultado['imagen_marcadores'] = img_marcadores_parciales
                    logger.info(f"📋 Mostrando {len(self.marcadores_detectados_todos)} marcadores detectados parcialmente")
                
                return resultado
            
            resultado['marcadores'] = marcadores
            
            # Dibujar marcadores para visualización (método original)
            corners_list = [marcadores[id_]['corners'].reshape(1, -1, 2) for id_ in sorted(marcadores.keys())]
            ids_array = np.array([[id_] for id_ in sorted(marcadores.keys())])
            
            img_marcadores = cv2.aruco.drawDetectedMarkers(img.copy(), corners_list, ids_array)
            resultado['imagen_marcadores'] = img_marcadores
            
            # Extraer puntos para rectificación
            pts_src = self.extraer_puntos_esquinas(marcadores)
            
            # Rectificar tabla
            tabla_rectificada, homografia = self.rectificar_tabla(img, pts_src)
            if tabla_rectificada is None:
                resultado['mensaje'] = "Error en rectificación de perspectiva"
                return resultado
                
            resultado['imagen_rectificada'] = tabla_rectificada
            resultado['homografia'] = homografia
            resultado['exito'] = True
            resultado['mensaje'] = "Procesamiento completado exitosamente"
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error procesando imagen: {e}")
            resultado['mensaje'] = f"Error inesperado: {str(e)}"
            return resultado
    
    def mostrar_resultados(self, resultado: Dict, escala: float = 0.4):
        """
        Mostrar resultados del procesamiento.
        """
        if not resultado['exito']:
            print(f"❌ {resultado['mensaje']}")
        else:
            print(f"✅ {resultado['mensaje']}")
        
        # Función auxiliar para redimensionar
        def redimensionar(img, escala):
            if img is None:
                return None
            width = int(img.shape[1] * escala)
            height = int(img.shape[0] * escala)
            return cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
        
        # Mostrar imágenes
        if resultado['imagen_marcadores'] is not None:
            img_show = redimensionar(resultado['imagen_marcadores'], escala)
            titulo = "🎯 Marcadores Detectados"
            if not resultado['exito'] and hasattr(self, 'marcadores_detectados_todos'):
                titulo += " (PARCIALES - Ver detalles)"
            cv2.imshow(titulo, img_show)
            
        if resultado['imagen_rectificada'] is not None:
            img_show = redimensionar(resultado['imagen_rectificada'], escala * 1.5)
            cv2.imshow("📋 Tabla Rectificada", img_show)
        
        # Información de marcadores
        if resultado['marcadores']:
            print("\n🔍 Marcadores detectados:")
            for id_, info in resultado['marcadores'].items():
                centro = info['centro']
                print(f"  ID {id_} ({info['posicion']}): centro en ({centro[0]:.1f}, {centro[1]:.1f})")
        elif hasattr(self, 'marcadores_detectados_todos') and self.marcadores_detectados_todos:
            print("\n🔍 Marcadores detectados (parciales):")
            for id_, info in self.marcadores_detectados_todos.items():
                centro = info['centro']
                estado = "✅ VÁLIDO" if id_ in self.expected_ids else "⚠️ EXTRA"
                print(f"  ID {id_} ({info['posicion']}) {estado}: centro en ({centro[0]:.1f}, {centro[1]:.1f})")
    
    def guardar_resultados(self, resultado: Dict, directorio_salida: str = "."):
        """
        Guardar imágenes y metadatos de resultado.
        """
        if not resultado['exito'] and resultado['imagen_marcadores'] is None:
            logger.warning("No hay resultados para guardar")
            return
            
        try:
            Path(directorio_salida).mkdir(exist_ok=True)
            
            # Guardar imagen rectificada (solo si fue exitoso)
            if resultado['imagen_rectificada'] is not None:
                ruta_rectificada = os.path.join(directorio_salida, "tabla_rectificada.jpg")
                cv2.imwrite(ruta_rectificada, resultado['imagen_rectificada'])
                logger.info(f"💾 Tabla rectificada guardada: {ruta_rectificada}")
            
            # Guardar imagen con marcadores (siempre que haya)
            if resultado['imagen_marcadores'] is not None:
                ruta_marcadores = os.path.join(directorio_salida, "tabla_con_marcadores.jpg")
                cv2.imwrite(ruta_marcadores, resultado['imagen_marcadores'])
                logger.info(f"💾 Imagen con marcadores guardada: {ruta_marcadores}")
            
            # Guardar metadatos
            metadatos = {
                'exito': resultado['exito'],
                'mensaje': resultado['mensaje'],
                'dimensiones_rectificada': [self.target_width, self.target_height],
                'marcadores': {}
            }
            
            if resultado['marcadores']:
                for id_, info in resultado['marcadores'].items():
                    metadatos['marcadores'][str(id_)] = {
                        'posicion': info['posicion'],
                        'centro': info['centro'].tolist()
                    }
            elif hasattr(self, 'marcadores_detectados_todos') and self.marcadores_detectados_todos:
                # Incluir información de marcadores parciales
                metadatos['marcadores_detectados_parciales'] = {}
                for id_, info in self.marcadores_detectados_todos.items():
                    metadatos['marcadores_detectados_parciales'][str(id_)] = {
                        'posicion': info['posicion'],
                        'centro': info['centro'].tolist(),
                        'es_valido': id_ in self.expected_ids
                    }
            
            ruta_metadatos = os.path.join(directorio_salida, "deteccion_metadatos.json")
            with open(ruta_metadatos, 'w', encoding='utf-8') as f:
                json.dump(metadatos, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Metadatos guardados: {ruta_metadatos}")
                
        except Exception as e:
            logger.error(f"Error guardando resultados: {e}")

def main():
    """Función principal para ejecutar el detector."""
    
    # Cambiar al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"📂 Directorio de trabajo: {os.getcwd()}")
    
    # Crear detector
    detector = TablaAPIDetector(target_width=800, target_height=533)
    
    # Procesar imagen
    ruta_imagen = "tabla_con_aruco3.jpg"
    resultado = detector.procesar_imagen(ruta_imagen)
    
    # Mostrar resultados
    detector.mostrar_resultados(resultado)
    
    # Guardar resultados
    detector.guardar_resultados(resultado)
    
    # Esperar tecla para cerrar
    if resultado['exito'] or resultado['imagen_marcadores'] is not None:
        print("\n✨ Presiona cualquier tecla para continuar...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()