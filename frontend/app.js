// NO usar imports ES6, cargar Firebase desde CDN
const API_URL = "https://danieldon.pythonanywhere.com";

// Esperar a que Firebase esté cargado
let database;

// Inicializar Firebase cuando esté disponible
function inicializarFirebase() {
    const firebaseConfig = {
        apiKey: "AIzaSyCpmluGnCG1NgWloj5Rra6IrFIXpI1jt9I",
        authDomain: "app-identificador-colores.firebaseapp.com",
        databaseURL: "https://app-identificador-colores-default-rtdb.firebaseio.com",
        projectId: "app-identificador-colores",
        storageBucket: "app-identificador-colores.firebasestorage.app",
        messagingSenderId: "270910920015",
        appId: "1:270910920015:web:4f89f480e217a9d6c1a13a"
    };

    firebase.initializeApp(firebaseConfig);
    database = firebase.database();
}

// Estado global
const estado = {
    userCode: localStorage.getItem('userCode') || null,
    tipoTestSeleccionado: null,
    imagenTablaRectificada: null,
    imagenTablaOriginal: null,
    imagenProbeta: null,
    imagenProbetaRectificada: null,
    calibracionActiva: false,
    resultadoAnalisis: null,
    seleccionCanvas: {
        dibujando: false,
        startX: 0,
        startY: 0,
        rect: null,
        escala: 1
    },
    seleccionProbeta: {
        activo: false,
        inicio: null,
        rect: null,
        escala: 1
    }
};

// Esperar a que el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM cargado');

    if (estado.userCode) {
        console.log('Usuario guardado:', estado.userCode);
        mostrarPantalla('pantalla-principal');
        document.getElementById('nombre-usuario').textContent = estado.userCode;
        verificarCalibracionActiva();
    } else {
        console.log('Sin usuario, mostrando pantalla de código');
        mostrarPantalla('pantalla-codigo');
    }

    inicializarEventListeners();
    try {
        inicializarFirebase();
        console.log('Firebase inicializado');
    } catch (e) {
        console.error('No se pudo inicializar Firebase:', e);
    }
});

function inicializarEventListeners() {
    console.log('Inicializando event listeners');

    const btnGuardarCodigo = document.getElementById('btn-guardar-codigo');
    if (!btnGuardarCodigo) {
        console.error('No se encuentra #btn-guardar-codigo en el DOM');
        return;
    }

    btnGuardarCodigo.addEventListener('click', guardarCodigoUsuario);
    document.getElementById('btn-cambiar-usuario').addEventListener('click', cambiarUsuario);

    // ✅ CALIBRACIÓN - Tabla
    document.getElementById('btn-capturar-tabla').addEventListener('click', () => {
        document.getElementById('input-foto-tabla').click();
    });
    document.getElementById('input-foto-tabla').addEventListener('change', manejarFotoTabla);
    document.getElementById('btn-procesar-tabla').addEventListener('click', procesarTablaAruco);
    document.getElementById('btn-seleccionar-area').addEventListener('click', abrirSeleccionArea);
    document.getElementById('btn-cancelar-seleccion').addEventListener('click', cerrarSeleccionArea);
    document.getElementById('btn-confirmar-seleccion').addEventListener('click', confirmarSeleccionArea);
    document.getElementById('btn-ir-analisis').addEventListener('click', irAAnalisis);

    // ✅ ANÁLISIS - Selección de tipo de test
    document.querySelectorAll('.btn-test').forEach(btn => {
        btn.addEventListener('click', (e) => seleccionarTipoTest(e, btn.dataset.tipo));
    });

    // ✅ ANÁLISIS - Captura de probeta (SOLO UN LISTENER POR INPUT)
    // Botón cámara abre input-foto-probeta
    document.getElementById('btn-capturar-probeta').addEventListener('click', () => {
        document.getElementById('input-foto-probeta').click();
    });

    // Botón galería abre input-probeta
    document.getElementById('btn-subir-probeta').addEventListener('click', () => {
        document.getElementById('input-probeta').click();
    });

    // Listener para input-foto-probeta (CÁMARA)
    document.getElementById('input-foto-probeta').addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            leerYRectificarProbeta(file);
        }
    });

    // Listener para input-probeta (GALERÍA)
    document.getElementById('input-probeta').addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            leerYRectificarProbeta(file);
        }
    });

    // ✅ ANÁLISIS - Procesar probeta
    document.getElementById('btn-procesar-probeta').addEventListener('click', () => {
        if (!estado.tipoTestSeleccionado) {
            alert("Primero selecciona un tipo de test.");
            return;
        }
        abrirSeleccionProbeta();
    });

    // ✅ MODAL PROBETA - Confirmar/Cancelar selección
    document.getElementById('btn-cancelar-seleccion-probeta').addEventListener('click', cerrarSeleccionProbeta);
    document.getElementById('btn-confirmar-seleccion-probeta').addEventListener('click', () => {
        if (!estado.seleccionProbeta.rect) {
            alert("Selecciona un área primero.");
            return;
        }
        const rect = estado.seleccionProbeta.rect;
        cerrarSeleccionProbeta();
        procesarProbetaConArea(rect);
    });

    // ✅ ACCIONES - Nueva probeta y guardar
    document.getElementById('btn-nueva-probeta').addEventListener('click', nuevaProbeta);
    document.getElementById('btn-guardar-medicion').addEventListener('click', abrirModalGuardar);

    // ✅ MODALES
    document.getElementById('btn-confirmar-guardar').addEventListener('click', guardarMedicion);
    document.getElementById('btn-cancelar-guardar').addEventListener('click', cerrarModalGuardar);
    document.getElementById('btn-historico').addEventListener('click', abrirHistorico);
    document.getElementById('btn-cerrar-historico').addEventListener('click', cerrarHistorico);
    document.getElementById('btn-recalibrar').addEventListener('click', recalibrar);

    // ✅ FILTROS HISTÓRICO
    document.querySelectorAll('.btn-filtro').forEach(btn => {
        btn.addEventListener('click', () => filtrarHistorico(btn.dataset.filtro));
    });

    // ✅ CANVAS TABLA - Eventos mouse y touch
    const canvas = document.getElementById('canvas-seleccion');
    canvas.addEventListener('mousedown', iniciarSeleccion);
    canvas.addEventListener('mousemove', dibujarSeleccion);
    canvas.addEventListener('mouseup', finalizarSeleccion);
    canvas.addEventListener('touchstart', iniciarSeleccionTouch);
    canvas.addEventListener('touchmove', dibujarSeleccionTouch);
    canvas.addEventListener('touchend', finalizarSeleccion);
}

function mostrarPantalla(idPantalla) {
    console.log('Mostrando pantalla:', idPantalla);
    document.querySelectorAll('.pantalla').forEach(p => p.classList.remove('activa'));
    document.getElementById(idPantalla).classList.add('activa');
}

function mostrarSeccion(idSeccion) {
    document.querySelectorAll('.seccion').forEach(s => {
        s.classList.remove('activa');
        s.classList.add('oculto');
    });

    const target = document.getElementById(idSeccion);
    target.classList.add('activa');
    target.classList.remove('oculto');

    document.querySelectorAll('.paso').forEach(p => p.classList.remove('activo'));
    if (idSeccion === 'seccion-calibracion') {
        document.querySelector('[data-paso="1"]').classList.add('activo');
    } else if (idSeccion === 'seccion-analisis') {
        document.querySelector('[data-paso="2"]').classList.add('activo');
    }
}

function mostrarLoading(texto = 'Procesando...') {
    document.getElementById('loading-texto').textContent = texto;
    document.getElementById('loading').classList.remove('oculto');
}

function ocultarLoading() {
    document.getElementById('loading').classList.add('oculto');
}

function guardarCodigoUsuario() {
    console.log('Guardando código de usuario');
    const input = document.getElementById('input-codigo');
    const codigo = input.value.trim().toUpperCase();

    if (!codigo) {
        alert('Por favor ingresa un código de usuario');
        return;
    }

    if (codigo.length < 5) {
        alert('El código debe tener al menos 5 caracteres');
        return;
    }

    estado.userCode = codigo;
    localStorage.setItem('userCode', codigo);
    document.getElementById('nombre-usuario').textContent = codigo;

    mostrarPantalla('pantalla-principal');
    verificarCalibracionActiva();
}

function cambiarUsuario() {
    if (confirm('¿Cerrar sesión? Se perderá la calibración actual')) {
        localStorage.removeItem('userCode');
        estado.userCode = null;
        estado.calibracionActiva = false;
        mostrarPantalla('pantalla-codigo');
        document.getElementById('input-codigo').value = '';
    }
}

async function verificarCalibracionActiva() {
    try {
        const response = await fetch(`${API_URL}/verificar_calibracion`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_code: estado.userCode })
        });

        const data = await response.json();

        if (data.activa) {
            estado.calibracionActiva = true;
            actualizarEstadoCalibracion(true, data.expira_en_segundos);
        } else {
            estado.calibracionActiva = false;
            actualizarEstadoCalibracion(false);
        }
    } catch (error) {
        console.error('Error verificando calibración:', error);
    }
}

function actualizarEstadoCalibracion(activa, segundosRestantes = 0) {
    const div = document.getElementById('estado-calibracion');
    const texto = document.getElementById('texto-calibracion');

    if (activa) {
        const minutos = Math.floor(segundosRestantes / 60);
        div.className = 'alerta alerta-exito';
        texto.textContent = `Calibración activa (expira en ${minutos} minutos)`;
        div.classList.remove('oculto');
    } else {
        div.className = 'alerta alerta-advertencia';
        texto.textContent = 'Sin calibración activa. Calibra la tabla primero.';
        div.classList.remove('oculto');
    }
}

// ========== PASO 1: CALIBRACIÓN ==========
function manejarFotoTabla(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        const img = document.getElementById('img-preview-tabla');
        img.src = e.target.result;
        document.getElementById('preview-tabla').classList.remove('oculto');
        estado.imagenTablaOriginal = e.target.result;
    };
    reader.readAsDataURL(file);
}

async function procesarTablaAruco() {
    if (!estado.imagenTablaOriginal) {
        alert('No hay imagen para procesar');
        return;
    }

    mostrarLoading('Detectando marcadores ArUco...');

    try {
        const response = await fetch(`${API_URL}/detectar_aruco`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                imagen: estado.imagenTablaOriginal,
                user_code: estado.userCode
            })
        });

        const data = await response.json();

        if (!data.exito) {
            alert(`Error: ${data.mensaje}`);
            if (data.imagen_marcadores) {
                document.getElementById('img-tabla-rectificada').src = data.imagen_marcadores;
                document.getElementById('resultado-aruco').classList.remove('oculto');
                document.getElementById('btn-seleccionar-area').disabled = true;
            }
            ocultarLoading();
            return;
        }

        estado.imagenTablaRectificada = data.imagen_rectificada;
        document.getElementById('img-tabla-rectificada').src = data.imagen_rectificada;
        document.getElementById('resultado-aruco').classList.remove('oculto');
        document.getElementById('btn-seleccionar-area').disabled = false;

    } catch (error) {
        console.error('Error procesando tabla:', error);
        alert('Error de conexión con el servidor');
    } finally {
        ocultarLoading();
    }
}

function abrirSeleccionArea() {
    const modal = document.getElementById('modal-seleccion');
    const canvas = document.getElementById('canvas-seleccion');
    const ctx = canvas.getContext('2d');

    const img = new Image();
    img.onload = () => {
        const maxWidth = window.innerWidth - 80;
        const maxHeight = window.innerHeight - 200;

        let width = img.width;
        let height = img.height;

        if (width > maxWidth) {
            height *= maxWidth / width;
            width = maxWidth;
        }

        if (height > maxHeight) {
            width *= maxHeight / height;
            height = maxHeight;
        }

        canvas.width = width;
        canvas.height = height;

        ctx.drawImage(img, 0, 0, width, height);

        estado.seleccionCanvas.escala = width / img.width;
        estado.seleccionCanvas.imgOriginalWidth = img.width;
        estado.seleccionCanvas.imgOriginalHeight = img.height;

        console.log('Canvas preparado. Escala:', estado.seleccionCanvas.escala);
    };
    img.src = estado.imagenTablaRectificada;

    modal.classList.remove('oculto');
}

function cerrarSeleccionArea() {
    document.getElementById('modal-seleccion').classList.add('oculto');
    estado.seleccionCanvas.rect = null;
}

function iniciarSeleccion(e) {
    const canvas = document.getElementById('canvas-seleccion');
    const rect = canvas.getBoundingClientRect();

    estado.seleccionCanvas.dibujando = true;
    estado.seleccionCanvas.startX = e.clientX - rect.left;
    estado.seleccionCanvas.startY = e.clientY - rect.top;
}

function iniciarSeleccionTouch(e) {
    e.preventDefault();
    const canvas = document.getElementById('canvas-seleccion');
    const rect = canvas.getBoundingClientRect();
    const touch = e.touches[0];

    estado.seleccionCanvas.dibujando = true;
    estado.seleccionCanvas.startX = touch.clientX - rect.left;
    estado.seleccionCanvas.startY = touch.clientY - rect.top;
}

function dibujarSeleccion(e) {
    if (!estado.seleccionCanvas.dibujando) return;

    const canvas = document.getElementById('canvas-seleccion');
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();

    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    const img = new Image();
    img.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 3;
        ctx.strokeRect(
            estado.seleccionCanvas.startX,
            estado.seleccionCanvas.startY,
            currentX - estado.seleccionCanvas.startX,
            currentY - estado.seleccionCanvas.startY
        );

        ctx.fillStyle = '#10b981';
        ctx.fillRect(estado.seleccionCanvas.startX, estado.seleccionCanvas.startY - 25, 120, 20);
        ctx.fillStyle = 'white';
        ctx.font = '12px Arial';
        const w = Math.abs(currentX - estado.seleccionCanvas.startX);
        const h = Math.abs(currentY - estado.seleccionCanvas.startY);
        ctx.fillText(`${Math.round(w)} x ${Math.round(h)} px`, estado.seleccionCanvas.startX + 5, estado.seleccionCanvas.startY - 10);
    };
    img.src = estado.imagenTablaRectificada;
}

function dibujarSeleccionTouch(e) {
    e.preventDefault();
    if (!estado.seleccionCanvas.dibujando) return;

    const canvas = document.getElementById('canvas-seleccion');
    const rect = canvas.getBoundingClientRect();
    const touch = e.touches[0];

    const fakeEvent = {
        clientX: touch.clientX,
        clientY: touch.clientY
    };

    dibujarSeleccion(fakeEvent);
}

function finalizarSeleccion(e) {
    if (!estado.seleccionCanvas.dibujando) return;

    const canvas = document.getElementById('canvas-seleccion');
    const rect = canvas.getBoundingClientRect();

    let currentX, currentY;

    if (e.type === 'touchend') {
        const touch = e.changedTouches[0];
        currentX = touch.clientX - rect.left;
        currentY = touch.clientY - rect.top;
    } else {
        currentX = e.clientX - rect.left;
        currentY = e.clientY - rect.top;
    }

    const x = Math.min(estado.seleccionCanvas.startX, currentX);
    const y = Math.min(estado.seleccionCanvas.startY, currentY);
    const w = Math.abs(currentX - estado.seleccionCanvas.startX);
    const h = Math.abs(currentY - estado.seleccionCanvas.startY);

    if (w < 10 || h < 10) {
        alert('Selección muy pequeña, intenta de nuevo');
        estado.seleccionCanvas.dibujando = false;
        return;
    }

    const escala = estado.seleccionCanvas.escala || 1;
    const rectOriginal = [
        Math.round(x / escala),
        Math.round(y / escala),
        Math.round(w / escala),
        Math.round(h / escala)
    ];

    estado.seleccionCanvas.rect = rectOriginal;
    estado.seleccionCanvas.dibujando = false;

    document.getElementById('btn-confirmar-seleccion').textContent = `✓ Confirmar (${w}x${h} px)`;
    document.getElementById('btn-confirmar-seleccion').disabled = false;
}

async function confirmarSeleccionArea() {
    if (!estado.seleccionCanvas.rect) {
        alert('Primero selecciona un área');
        return;
    }

    const rect = estado.seleccionCanvas.rect;

    cerrarSeleccionArea();
    mostrarLoading('Extrayendo colores de la tabla...');

    try {
        const response = await fetch(`${API_URL}/extraer_colores`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                imagen_rectificada: estado.imagenTablaRectificada,
                bbox_tabla: rect,
                user_code: estado.userCode
            })
        });

        const data = await response.json();

        if (!data.exito) {
            alert(`Error: ${data.mensaje}`);
            ocultarLoading();
            return;
        }

        document.getElementById('info-colores').textContent =
            `${data.colores_extraidos} colores extraídos correctamente. Calibración válida por ${Math.floor(data.expira_en / 60)} minutos.`;

        if (data.imagen_debug) {
            document.getElementById('img-debug-colores').src = data.imagen_debug;
        }

        document.getElementById('resultado-colores').classList.remove('oculto');
        estado.calibracionActiva = true;
        actualizarEstadoCalibracion(true, data.expira_en);

    } catch (error) {
        console.error('Error extrayendo colores:', error);
        alert('Error de conexión con el servidor');
    } finally {
        ocultarLoading();
    }
}

function irAAnalisis() {
    mostrarSeccion('seccion-analisis');
    window.scrollTo(0, 0);
}

// ========== PASO 2: ANÁLISIS ==========
function seleccionarTipoTest(e, tipo) {
    estado.tipoTestSeleccionado = tipo;

    document.querySelectorAll('.btn-test').forEach(btn => {
        btn.classList.remove('seleccionado');
    });
    e.currentTarget.classList.add('seleccionado');

    const nombres = {
        'pH': 'pH (6.0-7.6)',
        'high_ph': 'High Range pH (7.4-8.8)',
        'ammonia': 'Amonio (0-8 ppm)',
        'nitrite': 'Nitrito (0-5 ppm)',
        'nitrate': 'Nitrato (0-160 ppm)'
    };

    document.getElementById('nombre-test').textContent = nombres[tipo] || tipo;
    document.getElementById('tipo-seleccionado').classList.remove('oculto');
    
    // ✅ Habilitar ambos botones de captura
    document.getElementById('btn-capturar-probeta').disabled = false;
    document.getElementById('btn-subir-probeta').disabled = false;
}

async function leerYRectificarProbeta(file) {
    const reader = new FileReader();
    reader.onload = async function (ev) {
        const base64Img = ev.target.result;

        mostrarLoading("Detectando ArUco en probeta...");

        try {
            const response = await fetch(`${API_URL}/rectificar_probeta`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    imagen_probeta: base64Img,
                    user_code: estado.userCode
                })
            });

            const data = await response.json();

            if (!data.exito) {
                alert(`Error: ${data.mensaje}`);
                
                // Si hay imagen de marcadores, mostrarla como debug
                if (data.imagen_marcadores) {
                    document.getElementById("img-preview-probeta").src = data.imagen_marcadores;
                    document.getElementById('preview-probeta').classList.remove('oculto');
                }
                
                ocultarLoading();
                return;
            }

            estado.imagenProbeta = base64Img;
            estado.imagenProbetaRectificada = data.imagen_rectificada;

            document.getElementById("img-preview-probeta").src = estado.imagenProbetaRectificada;
            document.getElementById('preview-probeta').classList.remove('oculto');
            document.getElementById('btn-procesar-probeta').disabled = false;

        } catch (err) {
            console.error("Error al rectificar probeta:", err);
            alert("Error de conexión con el servidor");
        } finally {
            ocultarLoading();
        }
    };
    reader.readAsDataURL(file);
}

// // Estado del zoom
// const estadoZoom = {
//     escala: 1,
//     minEscala: 1,
//     maxEscala: 4,
//     offsetX: 0,
//     offsetY: 0,
//     arrastrando: false,
//     ultimoX: 0,
//     ultimoY: 0,
//     // Para pinch
//     distanciaInicial: 0,
//     escalaInicial: 1
// };

function resetearZoom() {
    estadoZoom.escala = 1;
    estadoZoom.offsetX = 0;
    estadoZoom.offsetY = 0;
}

function aplicarZoom(canvas, ctx, imagenSrc, escala, offsetX, offsetY) {
    const img = new Image();
    img.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.save();
        
        // Aplicar transformación
        ctx.translate(offsetX, offsetY);
        ctx.scale(escala, escala);
        
        // Dibujar imagen
        ctx.drawImage(img, 0, 0, canvas.width / escala, canvas.height / escala);
        
        ctx.restore();
    };
    img.src = imagenSrc;
}

function obtenerDistancia(touch1, touch2) {
    const dx = touch1.clientX - touch2.clientX;
    const dy = touch1.clientY - touch2.clientY;
    return Math.sqrt(dx * dx + dy * dy);
}

// Estado del zoom simplificado
const estadoZoomProbeta = {
    modoZoom: false, // true = seleccionando área para zoom
    zoomeado: false,
    regionZoom: null
};

function abrirSeleccionProbeta() {
    if (!estado.imagenProbetaRectificada) {
        alert('No hay imagen de probeta rectificada');
        return;
    }

    estadoZoomProbeta.modoZoom = false;
    estadoZoomProbeta.zoomeado = false;
    estadoZoomProbeta.regionZoom = null;

    const modal = document.getElementById('modal-seleccion-probeta');
    const canvas = document.getElementById('canvas-seleccion-probeta');
    const ctx = canvas.getContext('2d');

    modal.classList.remove('oculto');

    const img = new Image();
    img.onload = () => {
        const maxWidth = window.innerWidth - 80;
        const maxHeight = window.innerHeight - 300;

        let width = img.width;
        let height = img.height;

        if (width > maxWidth) {
            height *= maxWidth / width;
            width = maxWidth;
        }
        if (height > maxHeight) {
            width *= maxHeight / height;
            height = maxHeight;
        }

        canvas.width = width;
        canvas.height = height;
        ctx.drawImage(img, 0, 0, width, height);

        estado.seleccionProbeta.escala = width / img.width;
        estado.seleccionProbeta.imgOriginalWidth = img.width;
        estado.seleccionProbeta.imgOriginalHeight = img.height;

        console.log('Canvas probeta preparado. Escala:', estado.seleccionProbeta.escala);
    };
    img.src = estado.imagenProbetaRectificada;

    let dibujando = false;
    let startX = 0;
    let startY = 0;

    document.getElementById('btn-confirmar-seleccion-probeta').disabled = true;
    
    // Resetear botón de zoom
    const btnZoom = document.getElementById('btn-zoom-probeta');
    btnZoom.classList.remove('activo');
    btnZoom.textContent = '🔍 Ampliar Zona';

    const pos = (evt) => {
        const r = canvas.getBoundingClientRect();
        const x = (evt.clientX ?? evt.touches[0].clientX) - r.left;
        const y = (evt.clientY ?? evt.touches[0].clientY) - r.top;
        return { x, y };
    };

    const redibujarImagen = (region = null) => {
    const imgObj = new Image();
    imgObj.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (region) {
            // Region en coordenadas del canvas, convertir a coordenadas de imagen original
            const [canvasX, canvasY, canvasW, canvasH] = region;
            
            // Calcular coordenadas en imagen original
            const escalaCanvas = canvas.width / imgObj.width;
            const imgX = canvasX / escalaCanvas;
            const imgY = canvasY / escalaCanvas;
            const imgW = canvasW / escalaCanvas;
            const imgH = canvasH / escalaCanvas;
            
            // Dibujar región ampliada desde la imagen original
            ctx.drawImage(imgObj, imgX, imgY, imgW, imgH, 0, 0, canvas.width, canvas.height);
        } else {
            // Dibujar imagen completa
            ctx.drawImage(imgObj, 0, 0, canvas.width, canvas.height);
        }
    };
    imgObj.src = estado.imagenProbetaRectificada;
};

    const drawFrame = (x1, y1, x2, y2, color = '#ef4444') => {
        // Primero redibujar imagen base (con o sin zoom)
        if (estadoZoomProbeta.zoomeado && estadoZoomProbeta.regionZoom) {
            redibujarImagen(estadoZoomProbeta.regionZoom);
        } else {
            const imgObj = new Image();
            imgObj.onload = () => {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(imgObj, 0, 0, canvas.width, canvas.height);

                // Después dibujar el rectángulo
                dibujarRectanguloSeleccion(x1, y1, x2, y2, color);
            };
            imgObj.src = estado.imagenProbetaRectificada;
            return;
        }

        // Si ya hay zoom, solo dibujar rectángulo
        dibujarRectanguloSeleccion(x1, y1, x2, y2, color);
    };

const dibujarRectanguloSeleccion = (x1, y1, x2, y2, color) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    ctx.fillStyle = color;
    ctx.fillRect(x1, Math.max(0, y1 - 25), 120, 20);
    ctx.fillStyle = 'white';
    ctx.font = '12px Arial';
    const w = Math.abs(x2 - x1);
    const h = Math.abs(y2 - y1);
    ctx.fillText(`${Math.round(w)} x ${Math.round(h)} px`, x1 + 5, Math.max(12, y1 - 10));
};

    const start = (evt) => {
        evt.preventDefault();
        dibujando = true;
        const p = pos(evt);
        startX = p.x;
        startY = p.y;
    };

    const move = (evt) => {
        if (!dibujando) return;
        evt.preventDefault();
        const p = pos(evt);
        
        const color = estadoZoomProbeta.modoZoom ? '#10b981' : '#ef4444';
        drawFrame(startX, startY, p.x, p.y, color);
    };

    const end = (evt) => {
        if (!dibujando) return;
        evt.preventDefault();
        dibujando = false;

        const p = pos(evt.type === 'touchend' ?
            { clientX: startX, clientY: startY } : evt);

        const x = Math.min(startX, p.x);
        const y = Math.min(startY, p.y);
        const w = Math.abs(p.x - startX);
        const h = Math.abs(p.y - startY);

        if (w < 10 || h < 10) {
            alert('Selección muy pequeña');
            return;
        }

        if (estadoZoomProbeta.modoZoom) {
            // Aplicar zoom a esta región
            estadoZoomProbeta.regionZoom = [x, y, w, h];
            estadoZoomProbeta.zoomeado = true;
            estadoZoomProbeta.modoZoom = false;

            redibujarImagen([x, y, w, h]);

            const btnZoom = document.getElementById('btn-zoom-probeta');
            btnZoom.classList.remove('activo');
            btnZoom.textContent = '↺ Restablecer Zoom';

            console.log('Zoom aplicado a región:', [x, y, w, h]);
        } else {
            // Guardar selección de área de probeta
            let finalX = x;
            let finalY = y;
            let finalW = w;
            let finalH = h;

            if (estadoZoomProbeta.zoomeado && estadoZoomProbeta.regionZoom) {
                // La región de zoom está en coordenadas del canvas
                // Convertir a coordenadas de imagen original
                const [zoomCanvasX, zoomCanvasY, zoomCanvasW, zoomCanvasH] = estadoZoomProbeta.regionZoom;

                // Calcular escala canvas -> imagen original
                const imgObj = new Image();
                imgObj.src = estado.imagenProbetaRectificada;

                // Esperar a que cargue para obtener dimensiones reales
                const escalaCanvas = canvas.width / estado.seleccionProbeta.imgOriginalWidth;

                // Convertir región de zoom a coordenadas de imagen original
                const zoomImgX = zoomCanvasX / escalaCanvas;
                const zoomImgY = zoomCanvasY / escalaCanvas;
                const zoomImgW = zoomCanvasW / escalaCanvas;
                const zoomImgH = zoomCanvasH / escalaCanvas;

                // La selección actual (x, y, w, h) es relativa al canvas zoomeado
                // Convertir a coordenadas dentro de la región de zoom original
                const ratioX = x / canvas.width;
                const ratioY = y / canvas.height;
                const ratioW = w / canvas.width;
                const ratioH = h / canvas.height;

                // Aplicar estos ratios a la región de zoom en imagen original
                finalX = (zoomImgX + ratioX * zoomImgW) * escalaCanvas;
                finalY = (zoomImgY + ratioY * zoomImgH) * escalaCanvas;
                finalW = ratioW * zoomImgW * escalaCanvas;
                finalH = ratioH * zoomImgH * escalaCanvas;

                console.log('Conversión de coordenadas:');
                console.log('  Canvas selección:', [x, y, w, h]);
                console.log('  Zoom región canvas:', [zoomCanvasX, zoomCanvasY, zoomCanvasW, zoomCanvasH]);
                console.log('  Zoom región img original:', [zoomImgX, zoomImgY, zoomImgW, zoomImgH]);
                console.log('  Ratios:', [ratioX, ratioY, ratioW, ratioH]);
                console.log('  Final canvas coords:', [finalX, finalY, finalW, finalH]);
            }

            const escala = estado.seleccionProbeta.escala || 1;
            estado.seleccionProbeta.rect = [
                Math.round(finalX / escala),
                Math.round(finalY / escala),
                Math.round(finalW / escala),
                Math.round(finalH / escala)
            ];
            console.log('Área de probeta para backend (img rectificada):', estado.seleccionProbeta.rect);
            document.getElementById('btn-confirmar-seleccion-probeta').disabled = false;
        }
    };

    canvas.onmousedown = start;
    canvas.onmousemove = move;
    canvas.onmouseup = end;
    canvas.ontouchstart = start;
    canvas.ontouchmove = move;
    canvas.ontouchend = end;
    
    // Botón de zoom
    document.getElementById('btn-zoom-probeta').onclick = () => {
        if (estadoZoomProbeta.zoomeado) {
            // Restablecer zoom
            estadoZoomProbeta.zoomeado = false;
            estadoZoomProbeta.regionZoom = null;
            estadoZoomProbeta.modoZoom = false;
            redibujarImagen();
            
            const btnZoom = document.getElementById('btn-zoom-probeta');
            btnZoom.classList.remove('activo');
            btnZoom.textContent = '🔍 Ampliar Zona';
        } else {
            // Activar modo zoom
            estadoZoomProbeta.modoZoom = !estadoZoomProbeta.modoZoom;
            const btnZoom = document.getElementById('btn-zoom-probeta');
            
            if (estadoZoomProbeta.modoZoom) {
                btnZoom.classList.add('activo');
                btnZoom.textContent = '🔍 Selecciona zona...';
                canvas.style.cursor = 'zoom-in';
            } else {
                btnZoom.classList.remove('activo');
                btnZoom.textContent = '🔍 Ampliar Zona';
                canvas.style.cursor = 'crosshair';
            }
        }
    };
}

function cerrarSeleccionProbeta() {
    document.getElementById('modal-seleccion-probeta').classList.add('oculto');
}

async function procesarProbetaConArea(area) {
    mostrarLoading("Analizando probeta...");

    try {
        const response = await fetch(`${API_URL}/analizar_probeta`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                imagen_probeta: estado.imagenProbetaRectificada,  // ✅ CAMBIO: usar rectificada
                tipo_test: estado.tipoTestSeleccionado,
                area_seleccionada: area,
                user_code: estado.userCode
            })
        });

        const data = await response.json();

        if (!data.exito) {
            alert(`Error: ${data.mensaje}`);
            ocultarLoading();
            return;
        }

        mostrarResultadoAnalisis(data);

        document.getElementById("resultado-analisis").classList.remove("oculto");
        document.getElementById("valor-detectado").textContent = data.valor_final.toFixed(2);
        document.getElementById("parametro-cercano").textContent = data.parametro_cercano;
        document.getElementById("confianza-valor").textContent = `${Math.round(data.confianza * 100)}%`;
        document.getElementById("interpolado-valor").textContent = data.interpolado ? "Sí" : "No";
        document.getElementById("color-rgb-texto").textContent = `RGB(${data.color_rgb.join(", ")})`;

        const colorBox = document.getElementById("muestra-color-box");
        colorBox.style.backgroundColor = `rgb(${data.color_rgb.join(",")})`;

        const lista = document.getElementById("lista-valores-cercanos");
        lista.innerHTML = "";
        data.valores_cercanos.forEach(v => {
            const div = document.createElement("div");
            div.classList.add("item-valor-cercano");
            div.textContent = `${v.parametro} (distancia: ${v.distancia.toFixed(2)})`;
            lista.appendChild(div);
        });

    } catch (error) {
        console.error("Error analizando probeta:", error);
        alert("Error de conexión con el servidor");
    } finally {
        ocultarLoading();
    }
}

function mostrarResultadoAnalisis(data) {
    document.getElementById('valor-detectado').textContent = data.valor_final.toFixed(2);
    document.getElementById('parametro-cercano').textContent = data.parametro_cercano;
    document.getElementById('confianza-valor').textContent = `${(data.confianza * 100).toFixed(1)}%`;
    document.getElementById('interpolado-valor').textContent = data.interpolado ? 'Sí' : 'No';

    const [r, g, b] = data.color_rgb;
    document.getElementById('muestra-color-box').style.backgroundColor = `rgb(${r}, ${g}, ${b})`;
    document.getElementById('color-rgb-texto').textContent = `RGB(${r}, ${g}, ${b})`;

    const listaValores = document.getElementById('lista-valores-cercanos');
    listaValores.innerHTML = data.valores_cercanos.map(v => `
        <div class="valor-cercano-item">
            <span>${v.parametro}: ${v.valor}</span>
            <span>Distancia: ${v.distancia.toFixed(1)}</span>
        </div>
    `).join('');

    const unidades = {
        'pH': '',
        'high_ph': '',
        'ammonia': 'ppm',
        'nitrite': 'ppm',
        'nitrate': 'ppm'
    };
    document.getElementById('unidad-valor').textContent = unidades[estado.tipoTestSeleccionado] || '';

    document.getElementById('resultado-analisis').classList.remove('oculto');

    document.getElementById('select-tipo-guardar').value = estado.tipoTestSeleccionado;
    document.getElementById('input-valor-guardar').value = data.valor_final.toFixed(2);
}

function nuevaProbeta() {
    document.getElementById('preview-probeta').classList.add('oculto');
    document.getElementById('resultado-analisis').classList.add('oculto');
    document.getElementById('input-foto-probeta').value = '';
    document.getElementById('input-probeta').value = '';
    estado.imagenProbeta = null;
    estado.imagenProbetaRectificada = null;
    estado.resultadoAnalisis = null;
}

// ========== MODALES Y GUARDADO ==========
function abrirModalGuardar() {
    document.getElementById('modal-guardar').classList.remove('oculto');
}

function cerrarModalGuardar() {
    document.getElementById('modal-guardar').classList.add('oculto');
}

async function guardarMedicion() {
    const tipo = document.getElementById('select-tipo-guardar').value;
    const valor = parseFloat(document.getElementById('input-valor-guardar').value);

    if (isNaN(valor)) {
        alert('Ingresa un valor válido');
        return;
    }

    mostrarLoading('Guardando medición...');

    try {
        const medicionRef = firebase.database().ref(`usuarios/${estado.userCode}/mediciones`);
        const nuevaMedicion = {
            tipo: tipo,
            valor: valor,
            fecha: new Date().toISOString(),
            timestamp: Date.now()
        };

        await medicionRef.push(nuevaMedicion);
        await limpiarMedicionesAntiguas();

        alert('Medición guardada correctamente');
        cerrarModalGuardar();

    } catch (error) {
        console.error('Error guardando medición:', error);
        alert('Error al guardar en Firebase');
    } finally {
        ocultarLoading();
    }
}

async function limpiarMedicionesAntiguas() {
    try {
        const medicionesRef = firebase.database().ref(`usuarios/${estado.userCode}/mediciones`).orderByChild('timestamp');
        const snapshot = await medicionesRef.once('value');

        const mediciones = [];
        snapshot.forEach(child => {
            mediciones.push({ key: child.key, ...child.val() });
        });

        if (mediciones.length > 30) {
            mediciones.sort((a, b) => a.timestamp - b.timestamp);
            const paraEliminar = mediciones.slice(0, mediciones.length - 30);

            for (const med of paraEliminar) {
                await firebase.database().ref(`usuarios/${estado.userCode}/mediciones/${med.key}`).remove();
            }
        }
    } catch (error) {
        console.error('Error limpiando mediciones:', error);
    }
}

async function abrirHistorico() {
    document.getElementById('modal-historico').classList.remove('oculto');
    
    // Activar botón "Todas"
    document.querySelectorAll('.btn-filtro').forEach(btn => {
        btn.classList.remove('activo');
        if (btn.dataset.filtro === 'todas') {
            btn.classList.add('activo');
        }
    });
    
    await cargarHistorico('todas');
}   

function cerrarHistorico() {
    document.getElementById('modal-historico').classList.add('oculto');
    
    // Limpiar canvas
    const canvas = document.getElementById('canvas-grafica');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
}

async function verificarEstructuraFirebase() {
    try {
        const ref = firebase.database().ref(`usuarios/${estado.userCode}`);
        const snapshot = await ref.once('value');
        console.log('Estructura completa Firebase:', snapshot.val());
        
        const medicionesRef = firebase.database().ref(`usuarios/${estado.userCode}/mediciones`);
        const snapshotMediciones = await medicionesRef.once('value');
        console.log('Mediciones:', snapshotMediciones.val());
        console.log('Número de mediciones:', snapshotMediciones.numChildren());
    } catch (error) {
        console.error('Error verificando Firebase:', error);
    }
}

async function cargarHistorico(filtro) {
    mostrarLoading('Cargando histórico...');

    try {
        console.log('Cargando histórico para usuario:', estado.userCode);
        
        const medicionesRef = firebase.database()
            .ref(`usuarios/${estado.userCode}/mediciones`)
            .orderByChild('timestamp')
            .limitToLast(30);
        
        const snapshot = await medicionesRef.once('value');
        
        console.log('Snapshot recibido:', snapshot.exists());
        
        if (!snapshot.exists()) {
            console.log('No hay mediciones guardadas');
            mostrarGrafica([]);
            mostrarListaMediciones([]);
            ocultarLoading();
            return;
        }

        const mediciones = [];
        snapshot.forEach(child => {
            const data = child.val();
            console.log('Medición leída:', data);
            mediciones.push(data);
        });

        console.log('Total mediciones cargadas:', mediciones.length);

        // Ordenar por timestamp descendente (más recientes primero)
        mediciones.sort((a, b) => b.timestamp - a.timestamp);

        // Aplicar filtro
        let medicionesFiltradas = mediciones;
        if (filtro !== 'todas') {
            medicionesFiltradas = mediciones.filter(m => {
                // Normalizar comparación (por si hay inconsistencias)
                const tipoMedicion = m.tipo.toLowerCase().replace(/_/g, '');
                const tipoFiltro = filtro.toLowerCase().replace(/_/g, '');
                return tipoMedicion === tipoFiltro;
            });
        }

        console.log('Mediciones después de filtrar:', medicionesFiltradas.length);

        if (medicionesFiltradas.length === 0) {
            mostrarGrafica([]);
            document.getElementById('lista-mediciones').innerHTML = 
                '<p class="texto-info">No hay mediciones para este filtro</p>';
        } else {
            mostrarGrafica(medicionesFiltradas);
            mostrarListaMediciones(medicionesFiltradas);
        }

    } catch (error) {
        console.error('Error completo cargando histórico:', error);
        console.error('Stack:', error.stack);
        alert(`Error al cargar datos: ${error.message}`);
        
        // Mostrar interfaz vacía en caso de error
        mostrarGrafica([]);
        document.getElementById('lista-mediciones').innerHTML = 
            '<p class="texto-info">Error al cargar mediciones</p>';
    } finally {
        ocultarLoading();
    }
}

function filtrarHistorico(filtro) {
    document.querySelectorAll('.btn-filtro').forEach(btn => {
        btn.classList.remove('activo');
    });
    event.target.classList.add('activo');

    cargarHistorico(filtro);
}

function mostrarGrafica(mediciones) {
    const canvas = document.getElementById('canvas-grafica');
    
    if (!canvas) {
        console.error('Canvas de gráfica no encontrado');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    // Limpiar canvas completamente
    canvas.width = canvas.offsetWidth;
    canvas.height = 300;
    
    if (mediciones.length === 0) {
        ctx.fillStyle = '#64748b';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No hay datos para mostrar', canvas.width / 2, canvas.height / 2);
        return;
    }

    // Agrupar por tipo
    const porTipo = {};
    mediciones.forEach(m => {
        const tipo = m.tipo;
        if (!porTipo[tipo]) porTipo[tipo] = [];
        porTipo[tipo].push(m);
    });

    console.log('Datos agrupados por tipo:', Object.keys(porTipo));

    const colores = {
        'pH': '#2563eb',
        'high_ph': '#ef4444',
        'ammonia': '#10b981',
        'nitrite': '#f59e0b',
        'nitrate': '#8b5cf6'
    };

    // Configuración de la gráfica
    const padding = 50;
    const graphWidth = canvas.width - padding * 2;
    const graphHeight = canvas.height - padding * 2;
    
    // Encontrar valores mínimos y máximos
    let minValor = Infinity;
    let maxValor = -Infinity;
    let totalPuntos = 0;
    
    Object.values(porTipo).forEach(datos => {
        datos.forEach(m => {
            const val = parseFloat(m.valor);
            if (val < minValor) minValor = val;
            if (val > maxValor) maxValor = val;
            totalPuntos++;
        });
    });
    
    // Ajustar rango
    const rangoValor = maxValor - minValor;
    minValor = Math.max(0, minValor - rangoValor * 0.1);
    maxValor = maxValor + rangoValor * 0.1;
    
    // Dibujar ejes
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();
    
    // Etiquetas del eje Y
    ctx.fillStyle = '#64748b';
    ctx.font = '12px Arial';
    ctx.textAlign = 'right';
    
    const pasos = 5;
    for (let i = 0; i <= pasos; i++) {
        const valor = minValor + (maxValor - minValor) * (i / pasos);
        const y = canvas.height - padding - (graphHeight * i / pasos);
        ctx.fillText(valor.toFixed(1), padding - 10, y + 4);
        
        // Líneas guía horizontales
        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(canvas.width - padding, y);
        ctx.stroke();
    }
    
    // Dibujar líneas por tipo
    let offsetX = 0;
    const tiposArray = Object.keys(porTipo);
    
    tiposArray.forEach((tipo, tipoIndex) => {
        const datos = porTipo[tipo].sort((a, b) => a.timestamp - b.timestamp);
        const color = colores[tipo] || '#64748b';
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.beginPath();
        
        datos.forEach((m, index) => {
            const x = padding + (graphWidth * (offsetX + index) / totalPuntos);
            const valorNorm = (parseFloat(m.valor) - minValor) / (maxValor - minValor);
            const y = canvas.height - padding - (graphHeight * valorNorm);
            
            if (index === 0 && tipoIndex === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
            
            // Dibujar punto
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(x, y, 5, 0, Math.PI * 2);
            ctx.fill();
        });
        
        ctx.stroke();
        offsetX += datos.length;
    });
    
    // Leyenda
    ctx.font = '14px Arial';
    ctx.textAlign = 'left';
    let legendX = padding;
    const legendY = 20;
    
    const nombres = {
        'pH': 'pH',
        'high_ph': 'High pH',
        'ammonia': 'Amonio',
        'nitrite': 'Nitrito',
        'nitrate': 'Nitrato'
    };
    
    tiposArray.forEach((tipo, index) => {
        const color = colores[tipo] || '#64748b';
        const nombre = nombres[tipo] || tipo;
        
        // Cuadrado de color
        ctx.fillStyle = color;
        ctx.fillRect(legendX, legendY - 10, 15, 15);
        
        // Texto
        ctx.fillStyle = '#1e293b';
        ctx.fillText(nombre, legendX + 20, legendY + 2);
        
        legendX += ctx.measureText(nombre).width + 40;
    });
    
    console.log('Gráfica dibujada manualmente');
}

function mostrarListaMediciones(mediciones) {
    const lista = document.getElementById('lista-mediciones');

    if (mediciones.length === 0) {
        lista.innerHTML = '<p class="texto-info">No hay mediciones registradas</p>';
        return;
    }

    lista.innerHTML = mediciones.map(m => {
        const fecha = new Date(m.fecha);
        const fechaTexto = fecha.toLocaleDateString('es-CO', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        const nombres = {
            'pH': 'pH',
            'high_ph': 'High pH',
            'ammonia': 'Amonio',
            'nitrite': 'Nitrito',
            'nitrate': 'Nitrato'
        };

        return `
            <div class="medicion-item">
                <div class="medicion-info">
                    <div class="medicion-tipo">${nombres[m.tipo]}</div>
                    <div class="medicion-fecha">${fechaTexto}</div>
                </div>
                <div class="medicion-valor">${m.valor}</div>
            </div>
        `;
    }).join('');
}

function recalibrar() {
    if (confirm('¿Recalibrar tabla? Se perderá la calibración actual')) {
        estado.calibracionActiva = false;
        estado.imagenTablaRectificada = null;
        estado.imagenTablaOriginal = null;

        document.getElementById('preview-tabla').classList.add('oculto');
        document.getElementById('resultado-aruco').classList.add('oculto');
        document.getElementById('resultado-colores').classList.add('oculto');
        document.getElementById('input-foto-tabla').value = '';

        mostrarSeccion('seccion-calibracion');
        actualizarEstadoCalibracion(false);
    }

}

