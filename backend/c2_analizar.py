#!/usr/bin/env python3
"""
🧪 Sistema de Análisis de Probetas con Selección Manual
Integra con ArUco y permite selección manual del área de líquido para mayor precisión.
"""

import cv2
import numpy as np
import os
import json
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sys



# Importar el detector ArUco existente
try:
    from a2_detectar_aruco import TablaAPIDetector
except ImportError:
    print("❌ No se puede importar a2_detectar_aruco.py")
    sys.exit(1)

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ResultadoProbetaManual:
    """Resultado del análisis manual de probeta."""
    tipo_test: str
    parametro_detectado: str
    valor_interpolado: float
    confianza: float
    color_promedio_rgb: Tuple[int, int, int]
    color_corregido_rgb: Tuple[int, int, int]
    valores_cercanos: List[Tuple[str, float, Tuple[int, int, int], float]]  # (param, valor, rgb, distancia)
    area_seleccionada: Tuple[int, int, int, int]
    pixeles_analizados: int
    interpolacion_aplicada: bool
    estadisticas_color: Dict

class CalibradorManual:
    """Calibrador usando datos reales de calibración con interpolación."""
    
    def __init__(self):
        # Se cargarán desde el Excel
        self.valores_por_tipo = {}
        self.colores_extraidos = {}  # Mantener para compatibilidad
        self.factores_correccion = {'r': 1.0, 'g': 1.0, 'b': 1.0}
        self.calibrado = False
        
    def cargar_datos_calibracion(self) -> bool:
        """Cargar datos de calibración desde Excel y organizar por tipo."""
        try:
            xlsx_path = "colores_proporcional.xlsx"
            if not os.path.exists(xlsx_path):
                logger.error(f"No se encuentra {xlsx_path}")
                return False
            
            df = pd.read_excel(xlsx_path)
            logger.info(f"📊 Cargando {len(df)} colores de calibración...")
            
            # Inicializar diccionario por tipo
            self.valores_por_tipo = {
                'ph': {},
                'high_ph': {},
                'ammonia': {},
                'nitrite': {},
                'nitrate': {}
            }
            
            # Procesar cada fila del Excel
            for _, row in df.iterrows():
                parametro = str(row['parametro']).strip()
                valor = row['valor']
                r, g, b = int(row['R']), int(row['G']), int(row['B'])
                
                # Normalizar nombre del parámetro y clasificar
                parametro_lower = parametro.lower()
                
                if parametro_lower == 'ph':
                    tipo = 'ph'
                elif parametro_lower.startswith('high_range') or 'high range' in parametro_lower:
                    tipo = 'high_ph'
                elif parametro_lower == 'ammonia':
                    tipo = 'ammonia'
                elif parametro_lower == 'nitrite':
                    tipo = 'nitrite'
                elif parametro_lower == 'nitrate':
                    tipo = 'nitrate'
                else:
                    logger.warning(f"Parámetro desconocido: {parametro}")
                    continue
                
                # Guardar en el diccionario organizado
                self.valores_por_tipo[tipo][valor] = (r, g, b)
                
                # También guardar en formato legacy para compatibilidad
                key = f"{tipo}_{valor}"
                self.colores_extraidos[key] = (r, g, b)
            
            # Mostrar resumen de lo cargado
            for tipo, valores in self.valores_por_tipo.items():
                if valores:
                    logger.info(f"  {tipo.upper()}: {len(valores)} valores cargados")
            
            # Como ahora usamos los valores RGB reales de la foto,
            # no necesitamos factores de corrección (ya están "corregidos")
            self.factores_correccion = {'r': 1.0, 'g': 1.0, 'b': 1.0}
            
            self.calibrado = True
            logger.info(f"✅ Calibración cargada desde Excel: {sum(len(v) for v in self.valores_por_tipo.values())} colores")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando calibración desde Excel: {e}")
            return False
    
    def _calcular_factores_correccion(self):
        """Como usamos valores RGB directos del Excel, no necesitamos corrección adicional."""
        # Los valores del Excel ya incluyen las características de tu cámara e iluminación
        # Por tanto, no aplicamos corrección adicional
        self.factores_correccion = {'r': 1.0, 'g': 1.0, 'b': 1.0}
        logger.info("🔧 Usando valores RGB directos del Excel (sin corrección adicional)")
    
    def corregir_color(self, color_rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Aplicar corrección de color."""
        if not self.calibrado:
            return color_rgb
        
        r, g, b = color_rgb
        r_corr = np.clip(int(r * self.factores_correccion['r']), 0, 255)
        g_corr = np.clip(int(g * self.factores_correccion['g']), 0, 255)
        b_corr = np.clip(int(b * self.factores_correccion['b']), 0, 255)
        
        return (r_corr, g_corr, b_corr)
    
    def calcular_distancia_color(self, color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> float:
        """Calcular distancia euclidiana entre colores."""
        r1, g1, b1 = color1
        r2, g2, b2 = color2
        return np.sqrt((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2)
    
    def encontrar_valores_cercanos(self, color_corregido: Tuple[int, int, int], 
                                 tipo_test: str) -> List[Tuple[str, float, Tuple[int, int, int], float]]:
        """Encontrar los colores más cercanos del tipo especificado."""
        if tipo_test not in self.valores_por_tipo:
            return []
        
        valores_tipo = self.valores_por_tipo[tipo_test]
        distancias = []
        
        for valor, color_ref in valores_tipo.items():
            distancia = self.calcular_distancia_color(color_corregido, color_ref)
            param_name = f"{tipo_test} {valor}"
            distancias.append((param_name, valor, color_ref, distancia))
        
        # Ordenar por distancia
        distancias.sort(key=lambda x: x[3])
        return distancias
    
    def interpolar_valor(self, color_corregido: Tuple[int, int, int], 
                        valores_cercanos: List[Tuple[str, float, Tuple[int, int, int], float]]) -> Tuple[float, bool]:
        """Interpolar valor entre los dos colores más cercanos."""
        if len(valores_cercanos) < 2:
            return valores_cercanos[0][1] if valores_cercanos else 0.0, False
        
        # Los dos más cercanos
        param1, valor1, color1, dist1 = valores_cercanos[0]
        param2, valor2, color2, dist2 = valores_cercanos[1]
        
        # Si el más cercano está muy cerca, usar directamente
        if dist1 < 10:  # Threshold de proximidad
            return valor1, False
        
        # Interpolación lineal basada en distancias
        # Peso inverso a la distancia
        peso1 = 1 / (dist1 + 0.1)  # +0.1 para evitar división por cero
        peso2 = 1 / (dist2 + 0.1)
        
        peso_total = peso1 + peso2
        valor_interpolado = (valor1 * peso1 + valor2 * peso2) / peso_total
        
        return valor_interpolado, True

class SelectorManualProbeta:
    """Selector manual de área de probeta basado en analizar_color2.py"""
    
    def __init__(self, img_rectificada: np.ndarray, calibrador: CalibradorManual):
        self.img_original = img_rectificada.copy()
        self.calibrador = calibrador
        
        # Parámetros de visualización
        self.max_width, self.max_height = 1000, 700
        self.calcular_escala()
        
        # Estado de interacción
        self.drawing = False
        self.start_pos = (0, 0)
        self.current_rect = None
        self.selection_made = False
        self.selected_area = None
        self.color_promedio = None
        
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
                
                # Mostrar rectángulo temporal
                img_temp = self.img_display.copy()
                cv2.rectangle(img_temp, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.imshow("Selecciona el área del líquido (ENTER para confirmar, ESC para salir)", img_temp)
                
        elif event == cv2.EVENT_LBUTTONUP:
            if not self.drawing:
                return
                
            self.drawing = False
            
            if self.current_rect is None:
                return
                
            x1, y1, x2, y2 = self.current_rect
            
            # Verificar tamaño mínimo
            if x2 - x1 < 10 or y2 - y1 < 10:
                print("⚠️ Selección muy pequeña, intenta de nuevo")
                return
            
            # Convertir a coordenadas originales
            x1_orig, y1_orig = self.display_to_original(x1, y1)
            x2_orig, y2_orig = self.display_to_original(x2, y2)
            
            # Extraer región y calcular color promedio
            region = self.img_original[y1_orig:y2_orig, x1_orig:x2_orig]
            
            if region.size == 0:
                print("⚠️ Región vacía, intenta de nuevo")
                return
            
            # Calcular color promedio (BGR -> RGB)
            mean_bgr = cv2.mean(region)
            self.color_promedio = (int(round(mean_bgr[2])), int(round(mean_bgr[1])), int(round(mean_bgr[0])))
            self.selected_area = (x1_orig, y1_orig, x2_orig, y2_orig)
            
            # Mostrar resultado en imagen
            img_result = self.img_display.copy()
            cv2.rectangle(img_result, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Mostrar color detectado
            cv2.putText(img_result, f"RGB: {self.color_promedio}", (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Patch de color
            cv2.rectangle(img_result, (x1, y2+5), (x1+60, y2+35), 
                         (self.color_promedio[2], self.color_promedio[1], self.color_promedio[0]), -1)
            
            cv2.imshow("Selecciona el área del líquido (ENTER para confirmar, ESC para salir)", img_result)
            
            print(f"🎨 Color promedio detectado: RGB{self.color_promedio}")
            print("📝 Presiona ENTER para confirmar la selección")
            
    def seleccionar_area(self) -> Optional[Tuple[Tuple[int, int, int, int], Tuple[int, int, int]]]:
        """Interfaz para seleccionar área manualmente."""
        cv2.namedWindow("Selecciona el área del líquido (ENTER para confirmar, ESC para salir)")
        cv2.setMouseCallback("Selecciona el área del líquido (ENTER para confirmar, ESC para salir)", self.on_mouse)
        
        print("👆 Instrucciones:")
        print("• Haz clic y arrastra para seleccionar el área del líquido en la probeta")
        print("• Presiona ENTER para confirmar la selección")
        print("• Presiona ESC para cancelar")
        
        while True:
            cv2.imshow("Selecciona el área del líquido (ENTER para confirmar, ESC para salir)", self.img_display)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                cv2.destroyAllWindows()
                return None
                
            elif key == 13:  # ENTER
                if self.selected_area is not None and self.color_promedio is not None:
                    cv2.destroyAllWindows()
                    return self.selected_area, self.color_promedio
                else:
                    print("⚠️ Primero debes hacer una selección")

def solicitar_tipo_test() -> Optional[str]:
    """Solicitar al usuario el tipo de test."""
    print("\n🧪 ¿Qué tipo de test estás analizando?")
    print("1. pH (6.0 - 7.6)")
    print("2. High Range pH (7.4 - 8.8)")  
    print("3. Ammonia (0 - 8.0 ppm)")
    print("4. Nitrite (0 - 5.0 ppm)")
    print("5. Nitrate (0 - 160 ppm)")
    
    tipos = {
        '1': 'ph',
        '2': 'high_ph', 
        '3': 'ammonia',
        '4': 'nitrite',
        '5': 'nitrate'
    }
    
    while True:
        try:
            opcion = input("Selecciona una opción (1-5): ").strip()
            if opcion in tipos:
                return tipos[opcion]
            else:
                print("❌ Opción inválida, intenta de nuevo")
        except KeyboardInterrupt:
            return None
####
def convertir(obj):
    if isinstance(obj, (np.integer)):
        return int(obj)
    if isinstance(obj, (np.floating)):
        return float(obj)
    if isinstance(obj, (np.ndarray)):
        return obj.tolist()
    return str(obj)  # fallback por si aparece algo raro
#####

def main():
    """Función principal del sistema manual."""
    print("🧪 Sistema de Análisis Manual de Probetas")
    print("=" * 50)
    
    # Cambiar al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Verificar archivos
    imagen_probeta = "probetanitrato2.jpg"
    if not os.path.exists(imagen_probeta):
        print(f"❌ No se encuentra: {imagen_probeta}")
        return
    
    # 1. Detección ArUco y rectificación
    print("\n🔍 Paso 1: Rectificando imagen...")
    detector_aruco = TablaAPIDetector(target_width=800, target_height=533)
    resultado_aruco = detector_aruco.procesar_imagen(imagen_probeta)
    
    if not resultado_aruco['exito']:
        print(f"❌ Error ArUco: {resultado_aruco['mensaje']}")
        return
    
    detector_aruco.guardar_resultados(resultado_aruco)
    # Gestionar nombres de archivos específicos para probetas
    try:
        # 1. Borrar tabla_rectificada.jpg si existe
        if os.path.exists("tabla_rectificada.jpg"):
            os.remove("tabla_rectificada.jpg")
            print("🗑️ Eliminada tabla_rectificada.jpg")

        # 2. Renombrar o crear probeta_rectificada.jpg
        if resultado_aruco['imagen_rectificada'] is not None:
            # Guardar directamente como probeta_rectificada.jpg (sobreescribe si existe)
            cv2.imwrite("probeta_rectificada.jpg", resultado_aruco['imagen_rectificada'])
            print("✅ Imagen guardada como: probeta_rectificada.jpg")
    except Exception as e:
        print(f"⚠️ Error gestionando archivos de imagen: {e}")
    img_rectificada = resultado_aruco['imagen_rectificada']
    print("✅ Imagen rectificada correctamente")
    
    # 2. Cargar calibración
    print("\n🔧 Paso 2: Cargando calibración...")
    calibrador = CalibradorManual()
    
    if not calibrador.cargar_datos_calibracion():
        print("❌ Error cargando calibración")
        return
    
    print("✅ Calibración cargada correctamente")
    
    # 3. Solicitar tipo de test
    tipo_test = solicitar_tipo_test()
    if tipo_test is None:
        print("❌ Operación cancelada")
        return
    
    # 4. Selección manual del área
    print(f"\n👆 Paso 3: Selección manual del área de líquido...")
    selector = SelectorManualProbeta(img_rectificada, calibrador)
    resultado_seleccion = selector.seleccionar_area()
    
    if resultado_seleccion is None:
        print("❌ Selección cancelada")
        return
    
    area_seleccionada, color_promedio = resultado_seleccion
    print(f"✅ Área seleccionada: {area_seleccionada}")
    print(f"🎨 Color promedio: RGB{color_promedio}")
    
    # 5. Análisis del color
    print(f"\n🔬 Paso 4: Analizando color para {tipo_test}...")
    
    # Aplicar corrección de color
    color_corregido = calibrador.corregir_color(color_promedio)
    print(f"🎨 Color corregido: RGB{color_corregido}")
    
    # Encontrar valores cercanos
    valores_cercanos = calibrador.encontrar_valores_cercanos(color_corregido, tipo_test)
    
    if not valores_cercanos:
        print(f"❌ No se encontraron valores de referencia para {tipo_test}")
        return
    
    # Interpolar valor
    valor_final, interpolado = calibrador.interpolar_valor(color_corregido, valores_cercanos)
    
    # Calcular confianza basada en distancia al más cercano
    distancia_minima = valores_cercanos[0][3]
    confianza = max(0.1, min(1.0, 1 - (distancia_minima / 100)))
    
    # Crear resultado
    x1, y1, x2, y2 = area_seleccionada
    pixeles_analizados = (x2 - x1) * (y2 - y1)
    
    resultado = ResultadoProbetaManual(
        tipo_test=tipo_test,
        parametro_detectado=valores_cercanos[0][0],
        valor_interpolado=valor_final,
        confianza=confianza,
        color_promedio_rgb=color_promedio,
        color_corregido_rgb=color_corregido,
        valores_cercanos=valores_cercanos[:3],  # Top 3
        area_seleccionada=area_seleccionada,
        pixeles_analizados=pixeles_analizados,
        interpolacion_aplicada=interpolado,
        estadisticas_color={
            'distancia_minima': distancia_minima,
            'valores_considerados': len(valores_cercanos)
        }
    )
    
    # 6. Mostrar resultados
    print(f"\n📊 RESULTADOS FINALES:")
    print(f"🧪 Tipo de test: {tipo_test.upper()}")
    print(f"📈 Valor {'interpolado' if interpolado else 'directo'}: {valor_final:.2f}")
    print(f"🎯 Parámetro más cercano: {valores_cercanos[0][0]}")
    print(f"📊 Confianza: {confianza:.3f}")
    print(f"🎨 Color detectado: RGB{color_corregido}")
    print(f"📏 Distancia al color más cercano: {distancia_minima:.1f}")
    print(f"🔍 Píxeles analizados: {pixeles_analizados}")
    
    if len(valores_cercanos) >= 2:
        print(f"\n🔍 Valores más cercanos:")
        for i, (param, valor, color_ref, dist) in enumerate(valores_cercanos[:3]):
            print(f"  {i+1}. {param}: distancia {dist:.1f}")
    
    # 7. Guardar resultados
    resultados_json = {
        'imagen_fuente': imagen_probeta,
        'tipo_test': tipo_test,
        'timestamp': str(pd.Timestamp.now()),
        'resultado': {
            'valor_final': valor_final,
            'parametro_cercano': valores_cercanos[0][0],
            'confianza': confianza,
            'interpolacion_aplicada': interpolado,
            'color_promedio_rgb': color_promedio,
            'color_corregido_rgb': color_corregido,
            'area_seleccionada': area_seleccionada,
            'pixeles_analizados': pixeles_analizados
        },
        'valores_cercanos': [
            {'parametro': v[0], 'valor': v[1], 'color_rgb': v[2], 'distancia': v[3]}
            for v in valores_cercanos[:3]
        ],
        'calibracion': calibrador.factores_correccion
    }
    
    json_path = f"resultado_manual_{tipo_test}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(resultados_json, f, indent=2, ensure_ascii=False, default=convertir)

    
    print(f"\n💾 Resultados guardados en: {json_path}")
    print(f"🎉 Análisis completado exitosamente!")

if __name__ == "__main__":
    main()