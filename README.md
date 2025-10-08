# 🧪 Analizador de Probetas - App Móvil

Aplicación móvil para análisis de calidad de agua mediante detección de colores en probetas API.

## 🚀 Características

- Calibración automática con marcadores ArUco
- Análisis de pH, Amonio, Nitrito y Nitrato
- Histórico de mediciones en Firebase
- Interfaz móvil optimizada

## 📱 Instalación

### Opción 1: Instalar APK

1. Descarga el APK desde [Releases](../../releases)
2. Instala en tu dispositivo Android
3. Abre la app y comienza a usar

### Opción 2: Usar como Web App (PWA)

1. Visita: `https://tu-app.onrender.com`
2. En Chrome: Menú → "Añadir a pantalla de inicio"
3. La app se instalará como aplicación nativa

## 🛠️ Desarrollo Local

### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend

Abre `frontend/index.html` en tu navegador o usa un servidor local:

```bash
cd frontend
python -m http.server 8080
```

## 📦 Despliegue

### Backend en Render

1. Conecta tu repositorio de GitHub
2. Selecciona Python
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn --chdir backend main:app`

### Frontend en GitHub Pages

1. Settings → Pages
2. Source: `main` branch, `/frontend` folder

## 🔧 Configuración

Actualiza la URL del backend en `frontend/app.js`:

```javascript
const API_URL = "https://tu-backend.onrender.com";
```

## 📄 Licencia

MIT License - 2024
