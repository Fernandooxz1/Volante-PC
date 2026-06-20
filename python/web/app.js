// ==========================================================================
// MODO NATIVO (PyWebView) - Detección y Comunicación
// ==========================================================================
let nativeMode = false;
let pyApi = null;
let telemetryPollTimer = null;
let logPollTimer = null;

// ==========================================================================
// CONFIGURACIÓN Y VARIABLES DE ESTADO
// ==========================================================================
let socket = null;
let reconnectInterval = 2000;
let isConnected = false;
let isEmulating = false;

let config = {
    sensitivity: 0.25,
    slope: 0.65,
    anti_deadzone: 0.0,
    deadzone: 0.23,
    filter: 0.55,
    steer_target: "Left Stick X",
    accel_target: "Right Trigger (RT)",
    brake_target: "Left Trigger (LT)",
    btn_d2_target: "Ninguno",
    steer_min: 0,
    steer_center: 512,
    steer_max: 1023,
    invert_steer: false,
    invert_accel: false,
    invert_brake: false,
    accel_min: 0,
    accel_max: 1023,
    brake_min: 0,
    brake_max: 1023,
    btn_map_p2: "Ninguno",
    btn_map_p3: "Ninguno",
    btn_map_p4: "Ninguno",
    btn_map_p5: "Ninguno",
    btn_map_p6: "Ninguno",
    btn_map_p7: "Ninguno",
    btn_map_p8: "Ninguno",
    btn_map_p9: "Ninguno",
    btn_map_p10: "Ninguno",
    btn_map_p11: "Ninguno",
    preset_cycle_btn: "Ninguno",
    active_preset: "Personalizado",
    previous_preset: "Personalizado"
};

// Presets de Juego (Espejo de python para consistencia local y velocidad)
const PRESETS = {
    "Personalizado": null // Se mantiene el estado actual
};

// Opciones de Mapeo para botones digitales
const MAP_OPTIONS = {
    "Button Start": "Xbox Start",
    "Button Back": "Xbox Back",
    "Button A": "Xbox A",
    "Button B": "Xbox B",
    "Button X": "Xbox X",
    "Button Y": "Xbox Y",
    "Button LB (Left Shoulder)": "Xbox LB (Traba Izq)",
    "Button RB (Right Shoulder)": "Xbox RB (Traba Der)",
    "Button L3 (Left Click)": "Xbox L3 (Stick Izq Click)",
    "Button R3 (Right Click)": "Xbox R3 (Stick Der Click)",
    "D-Pad UP": "Cruceta Arriba",
    "D-Pad DOWN": "Cruceta Abajo",
    "D-Pad LEFT": "Cruceta Izquierda",
    "D-Pad RIGHT": "Cruceta Derecha",
    "Ninguno": "Ninguno (Desactivado)"
};

// Últimos valores de Telemetría recibidos
let currentTelemetry = {
    raw: { steer: 512, accel: 0, brake: 0, btn_d2: 0 },
    mapped: { steer: 512, accel: 0, brake: 0, btn_d2: 0 },
    virtual: { steer_deg: 0 } // Calculado localmente para el volante
};

// Referencias a Elementos DOM
const dom = {
    portSelect: document.getElementById('port-select'),
    btnRefresh: document.getElementById('btn-refresh'),
    btnConnect: document.getElementById('btn-connect'),
    statusBadge: document.getElementById('status-badge'),
    
    // Gauges
    steeringWheel: document.getElementById('steering-wheel'),
    steerAngleDisplay: document.getElementById('steer-angle-display'),
    rawSteer: document.getElementById('raw-steer'),
    mappedSteer: document.getElementById('mapped-steer'),
    
    // Pedals
    throttleFill: document.getElementById('throttle-fill'),
    throttleDisplay: document.getElementById('throttle-display'),
    rawAccel: document.getElementById('raw-accel'),
    throttleDzMarker: document.getElementById('throttle-dz-marker'),
    
    brakeFill: document.getElementById('brake-fill'),
    brakeDisplay: document.getElementById('brake-display'),
    rawBrake: document.getElementById('raw-brake'),
    brakeDzMarker: document.getElementById('brake-dz-marker'),
    
    // Buttons status pills
    btnPills: [
        document.getElementById('btn-p2-pill'),
        document.getElementById('btn-p3-pill'),
        document.getElementById('btn-p4-pill'),
        document.getElementById('btn-p5-pill'),
        document.getElementById('btn-p6-pill'),
        document.getElementById('btn-p7-pill'),
        document.getElementById('btn-p8-pill'),
        document.getElementById('btn-p9-pill'),
        document.getElementById('btn-p10-pill'),
        document.getElementById('btn-p11-pill'),
        document.getElementById('btn-p12-pill')
    ],
    
    // Button mapping dropdowns
    mapSelects: [
        document.getElementById('map-p2'),
        document.getElementById('map-p3'),
        document.getElementById('map-p4'),
        document.getElementById('map-p5'),
        document.getElementById('map-p6'),
        document.getElementById('map-p7'),
        document.getElementById('map-p8'),
        document.getElementById('map-p9'),
        document.getElementById('map-p10'),
        document.getElementById('map-p11'),
        document.getElementById('map-p12')
    ],
    
    // Tuning
    presetSelect: document.getElementById('preset-select'),
    sliderSens: document.getElementById('slider-sens'),
    sliderSlope: document.getElementById('slider-slope'),
    sliderAntiDz: document.getElementById('slider-anti-dz'),
    sliderDz: document.getElementById('slider-dz'),
    sliderFilter: document.getElementById('slider-filter'),
    
    valSens: document.getElementById('val-sens'),
    valSlope: document.getElementById('val-slope'),
    valAntiDz: document.getElementById('val-anti-dz'),
    valDz: document.getElementById('val-dz'),
    valFilter: document.getElementById('val-filter'),
    
    // Canvas
    curveCanvas: document.getElementById('curve-canvas'),
    
    // Hardware Calibration
    btnCalLeft: document.getElementById('btn-cal-left'),
    btnCalCenter: document.getElementById('btn-cal-center'),
    btnCalRight: document.getElementById('btn-cal-right'),
    btnCalReset: document.getElementById('btn-cal-reset'),
    lblCalMin: document.getElementById('lbl-cal-min'),
    lblCalCenter: document.getElementById('lbl-cal-center'),
    lblCalMax: document.getElementById('lbl-cal-max'),
    checkInvertSteer: document.getElementById('check-invert-steer'),
    checkInvertAccel: document.getElementById('check-invert-accel'),
    checkInvertBrake: document.getElementById('check-invert-brake'),
    
    // Pedals Hardware Calibration
    btnCalAccelMin: document.getElementById('btn-cal-accel-min'),
    btnCalAccelMax: document.getElementById('btn-cal-accel-max'),
    btnCalBrakeMin: document.getElementById('btn-cal-brake-min'),
    btnCalBrakeMax: document.getElementById('btn-cal-brake-max'),
    btnPedalReset: document.getElementById('btn-pedal-reset'),
    lblCalAccelMin: document.getElementById('lbl-cal-accel-min'),
    lblCalAccelMax: document.getElementById('lbl-cal-accel-max'),
    lblCalBrakeMin: document.getElementById('lbl-cal-brake-min'),
    lblCalBrakeMax: document.getElementById('lbl-cal-brake-max'),
    
    // Logs & Status Footer
    consoleOutput: document.getElementById('console-output'),
    btnClearLog: document.getElementById('btn-clear-log'),
    wsDot: document.getElementById('ws-dot'),
    wsStatusText: document.getElementById('ws-status-text'),
    arduinoPortText: document.getElementById('arduino-port-text')
};

// Canvas 2D Context
const ctx = dom.curveCanvas.getContext('2d');

// ==========================================================================
// WEBSOCKET: CONEXIÓN & COMUNICACIÓN
// ==========================================================================
function connectWebSocket() {
    const urlParams = new URLSearchParams(window.location.search);
    const wsPort = urlParams.get('ws_port') || '8765';
    
    log(`Conectando con el servidor backend (ws://localhost:${wsPort})...`, "info");
    dom.wsStatusText.innerText = "WebSocket: Conectando...";
    dom.wsDot.className = "dot yellow";

    socket = new WebSocket(`ws://localhost:${wsPort}`);

    socket.onopen = function() {
        isConnected = true;
        log("¡Conexión WebSocket establecida con éxito!", "success");
        dom.wsStatusText.innerText = "WebSocket: Conectado";
        dom.wsDot.className = "dot green";
        
        // Solicitar inicialización y escaneo de puertos
        sendMessage("command", "get_status");
        sendMessage("command", "refresh_ports");
    };

    socket.onmessage = function(event) {
        try {
            const message = JSON.parse(event.data);
            handleServerMessage(message);
        } catch (e) {
            console.error("Error decodificando mensaje:", e);
        }
    };

    socket.onerror = function(error) {
        console.error("Error de WebSocket:", error);
    };

    socket.onclose = function() {
        isConnected = false;
        isEmulating = false;
        log("Se cerró la conexión con el servidor. Reintentando...", "warn");
        dom.wsStatusText.innerText = "WebSocket: Desconectado";
        dom.wsDot.className = "dot red";
        dom.statusBadge.innerText = "DESCONECTADO";
        dom.statusBadge.className = "badge";
        dom.arduinoPortText.innerText = "Ninguno";
        
        // Reset botones de UI
        updateEmulationUIState(false);
        
        setTimeout(connectWebSocket, reconnectInterval);
    };
}

function sendMessage(type, data, value = null) {
    if (nativeMode) {
        nativeSendMessage(type, data, value);
        return;
    }
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type, data, value }));
    }
}

async function nativeSendMessage(type, data, value) {
    try {
        let result;
        if (type === "command") {
            switch (data) {
                case "get_status":
                    result = await pyApi.get_status();
                    break;
                case "refresh_ports":
                    result = await pyApi.refresh_ports();
                    break;
                case "select_port":
                    await pyApi.select_port(value);
                    return;
                case "start":
                    result = await pyApi.start_emulation(value);
                    break;
                case "stop":
                    result = await pyApi.stop_emulation();
                    break;
                case "install_driver":
                    result = await pyApi.run_driver_installer();
                    break;
                case "trigger_dpad":
                    await pyApi.trigger_dpad(value);
                    return;
            }
        } else if (type === "config") {
            result = await pyApi.update_config(JSON.stringify(data));
        }
        if (result) {
            handleServerMessage(JSON.parse(result));
        }
    } catch (e) {
        console.error("Error en comunicación nativa:", e);
    }
}

function initNativeMode() {
    nativeMode = true;
    pyApi = window.pywebview.api;
    
    log("Modo aplicación nativa detectado (PyWebView).", "success");
    dom.wsStatusText.innerText = "App Nativa: Conectado";
    dom.wsDot.className = "dot green";
    isConnected = true;
    
    // Solicitar estado inicial
    sendMessage("command", "get_status");
    sendMessage("command", "refresh_ports");
    
    // Iniciar polling de telemetría (60 FPS)
    telemetryPollTimer = setInterval(async () => {
        if (!nativeMode || !isEmulating) return;
        try {
            const data = await pyApi.get_telemetry();
            if (data) {
                const telemetry = JSON.parse(data);
                if (telemetry) {
                    updateTelemetry(telemetry);
                }
            }
        } catch (e) { /* silenciar errores de polling */ }
    }, 16);
    
    // Iniciar polling de logs (5 veces por segundo)
    logPollTimer = setInterval(async () => {
        if (!nativeMode) return;
        try {
            const data = await pyApi.get_logs();
            if (data) {
                const logs = JSON.parse(data);
                if (logs && logs.length > 0) {
                    logs.forEach(l => log(l.text, l.level));
                }
            }
        } catch (e) { /* silenciar errores de polling */ }
    }, 200);
    
    // Polling de estado periódico (para detectar cambios de preset por botón físico)
    setInterval(async () => {
        if (!nativeMode) return;
        try {
            const result = await pyApi.get_status();
            if (result) {
                const msg = JSON.parse(result);
                // Solo actualizar config si cambió el preset activo
                if (msg.data && msg.data.config && msg.data.config.active_preset !== config.active_preset) {
                    handleServerMessage(msg);
                }
                // Actualizar estado de emulación
                if (msg.data && msg.data.emulating !== isEmulating) {
                    handleServerMessage(msg);
                }
            }
        } catch (e) { /* silenciar */ }
    }, 1000);
}

// ==========================================================================
// CONTROLADOR DE MENSAJES DEL SERVIDOR
// ==========================================================================
function handleServerMessage(msg) {
    switch(msg.type) {
        case "status":
            // Actualizar estado general
            isEmulating = msg.data.emulating;
            updateEmulationUIState(isEmulating);
            
            // Cargar puertos y seleccionar el puerto actual
            updatePortsList(msg.data.ports, msg.data.current_port);
            
            // Sincronizar estado del driver
            if (msg.data && msg.data.hasOwnProperty("gamepad_ok")) {
                toggleDriverWarningBanner(!msg.data.gamepad_ok);
            }
            
            // Sincronizar configuración actual con la del backend
            if (msg.data.config) {
                config = msg.data.config;
                populatePresetsDropdown();
                syncSlidersWithConfig();
                drawCurve();
            }
            break;
            
        case "ports":
            updatePortsList(msg.data.ports, msg.data.current_port);
            break;
            
        case "telemetry":
            updateTelemetry(msg.data);
            break;
            
        case "log":
            log(msg.data.text, msg.data.level);
            break;
            
        default:
            console.warn("Mensaje desconocido del servidor:", msg);
    }
}

function toggleDriverWarningBanner(show) {
    const banner = document.getElementById("driver-warning-banner");
    if (banner) {
        banner.style.display = show ? "flex" : "none";
    }
}

// ==========================================================================
// RENDERIZADO Y ACTUALIZACIÓN EN VIVO (TELEMETRÍA)
// ==========================================================================
function updateTelemetry(data) {
    currentTelemetry.raw = data.raw;
    currentTelemetry.mapped = data.mapped;
    
    // --- 1. ACTUALIZAR VOLANTE ---
    // En el backend, steer mapeado va de 0 a 1023 (donde 512 es centro)
    // Queremos girar visualmente el volante entre -90 y +90 grados.
    const angle = ((data.mapped.steer - 512) / 512) * 90; // Rango -90° a +90°
    dom.steeringWheel.style.transform = `rotate(${angle}deg)`;
    dom.steerAngleDisplay.innerText = `${Math.round(angle)}°`;
    
    dom.rawSteer.innerText = data.raw.steer;
    dom.mappedSteer.innerText = data.mapped.steer;

    // --- 2. ACTUALIZAR PEDALES ---
    // Acelerador
    const throttlePct = Math.round((data.mapped.accel / 1023) * 100);
    dom.throttleFill.style.height = `${throttlePct}%`;
    dom.throttleDisplay.innerText = `${throttlePct}%`;
    dom.rawAccel.innerText = data.raw.accel;
    
    // Freno
    const brakePct = Math.round((data.mapped.brake / 1023) * 100);
    dom.brakeFill.style.height = `${brakePct}%`;
    dom.brakeDisplay.innerText = `${brakePct}%`;
    dom.rawBrake.innerText = data.raw.brake;
    
    // --- 3. ACTUALIZAR ESTADO DE LOS BOTONES ---
    if (data.mapped.buttons && data.mapped.buttons.length >= 10) {
        for (let i = 0; i < data.mapped.buttons.length; i++) {
            const pill = dom.btnPills[i];
            if (pill) {
                if (data.mapped.buttons[i] === 1) {
                    pill.classList.add("pressed");
                } else {
                    pill.classList.remove("pressed");
                }
            }
        }
    }

    // --- 4. DIBUJAR PUNTO EN EL GRÁFICO DE CURVA ---
    // Dibujar la curva y el cursor dinámico
    drawCurve();
}

function updatePortsList(ports, currentPort) {
    dom.portSelect.innerHTML = "";
    if (!ports || ports.length === 0) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.innerText = "No se hallaron puertos";
        dom.portSelect.appendChild(opt);
        dom.arduinoPortText.innerText = "Ninguno";
        return;
    }

    ports.forEach(port => {
        const opt = document.createElement("option");
        opt.value = port;
        opt.innerText = port;
        if (port === currentPort) {
            opt.selected = true;
        }
        dom.portSelect.appendChild(opt);
    });

    if (currentPort) {
        dom.arduinoPortText.innerText = currentPort;
    }
}

function updateEmulationUIState(emulating) {
    isEmulating = emulating;
    if (emulating) {
        dom.btnConnect.innerHTML = `<span class="icon">■</span><span class="text">Detener Emulación</span>`;
        dom.btnConnect.className = "btn btn-primary btn-stop";
        dom.statusBadge.innerText = "EMULANDO";
        dom.statusBadge.className = "badge connected";
        dom.portSelect.disabled = true;
        dom.btnRefresh.disabled = true;
    } else {
        dom.btnConnect.innerHTML = `<span class="icon">●</span><span class="text">Iniciar Emulación</span>`;
        dom.btnConnect.className = "btn btn-primary btn-start";
        dom.statusBadge.innerText = "CONEXIÓN LISTA";
        dom.statusBadge.className = "badge";
        dom.portSelect.disabled = false;
        dom.btnRefresh.disabled = false;
    }
}

// ==========================================================================
// DIBUJO DE LA CURVA DE CALIBRACIÓN (CANVAS)
// ==========================================================================
function getMappedSteerValue(x, sensitivity, slope, antiDeadzone) {
    // x va de -1.0 a 1.0 (Entrada normalizada)
    // 1. Aplicar Exponencial: x_expo = sign(x) * (|x| ^ slope)
    let abs_x_raw = Math.abs(x);
    let sign_x_raw = Math.sign(x);
    let x_expo = abs_x_raw === 0 ? 0.0 : sign_x_raw * Math.pow(abs_x_raw, slope);

    // Aplicar sensibilidad
    let x_sloped = x_expo * sensitivity;
    x_sloped = Math.max(-1.0, Math.min(1.0, x_sloped));

    // 2. Aplicar Anti-Zona Muerta
    let abs_x = Math.abs(x_sloped);
    let sign_x = Math.sign(x_sloped);
    const REST_DEADZONE = 0.01;
    let x_final = 0.0;

    if (abs_x > REST_DEADZONE) {
        let scaled = (abs_x - REST_DEADZONE) / (1.0 - REST_DEADZONE);
        let x_final_magnitude = antiDeadzone + (1.0 - antiDeadzone) * scaled;
        x_final = sign_x * x_final_magnitude;
    }

    return Math.max(-1.0, Math.min(1.0, x_final));
}

function drawCurve() {
    const width = dom.curveCanvas.clientWidth;
    const height = dom.curveCanvas.clientHeight;
    
    // Limpiar canvas
    ctx.clearRect(0, 0, width, height);

    // Fondo
    ctx.fillStyle = "#090c10";
    ctx.fillRect(0, 0, width, height);

    // Dibujar rejilla (Grid)
    ctx.strokeStyle = "rgba(255, 255, 255, 0.03)";
    ctx.lineWidth = 1;
    
    // Líneas verticales
    const gridCols = 8;
    for (let i = 1; i < gridCols; i++) {
        const x = (width / gridCols) * i;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }
    
    // Líneas horizontales
    const gridRows = 4;
    for (let i = 1; i < gridRows; i++) {
        const y = (height / gridRows) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    // Dibujar Ejes Centrales (X e Y)
    ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
    ctx.lineWidth = 1.5;
    
    // Eje X central
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();
    
    // Eje Y central
    ctx.beginPath();
    ctx.moveTo(width / 2, 0);
    ctx.lineTo(width / 2, height);
    ctx.stroke();

    // Dibujar Curva Matemática de Calibración
    ctx.strokeStyle = "#00f2fe";
    ctx.lineWidth = 3;
    ctx.shadowBlur = 8;
    ctx.shadowColor = "rgba(0, 242, 254, 0.5)";
    
    ctx.beginPath();
    for (let px = 0; px <= width; px++) {
        // Mapear pixel X [0, width] a valor normalizado [-1.0, 1.0]
        const xVal = (px / width) * 2.0 - 1.0;
        
        // Calcular salida Y normalizada [-1.0, 1.0]
        const yVal = getMappedSteerValue(xVal, config.sensitivity, config.slope, config.anti_deadzone);
        
        // Mapear salida normalizada Y [-1.0, 1.0] a pixel Y [height, 0] (Invertido en pantalla)
        const py = height - ((yVal + 1.0) / 2.0) * height;
        
        if (px === 0) {
            ctx.moveTo(px, py);
        } else {
            ctx.lineTo(px, py);
        }
    }
    ctx.stroke();
    
    // Reset de sombras
    ctx.shadowBlur = 0;

    // Dibujar indicador en tiempo real de la posición del volante
    // currentTelemetry.raw.steer va de 0 a 1023. Lo normalizamos a [-1, 1] usando límites calibrados.
    let currentRawX = 0.0;
    const steer = currentTelemetry.raw.steer;
    const sMin = config.steer_min !== undefined ? config.steer_min : 0;
    const sCenter = config.steer_center !== undefined ? config.steer_center : 512;
    const sMax = config.steer_max !== undefined ? config.steer_max : 1023;

    if (steer < sCenter) {
        const denom = sCenter - sMin;
        currentRawX = denom > 0 ? (steer - sCenter) / denom : 0.0;
        currentRawX = Math.max(-1.0, Math.min(0.0, currentRawX));
    } else {
        const denom = sMax - sCenter;
        currentRawX = denom > 0 ? (steer - sCenter) / denom : 0.0;
        currentRawX = Math.max(0.0, Math.min(1.0, currentRawX));
    }

    const currentMappedY = getMappedSteerValue(currentRawX, config.sensitivity, config.slope, config.anti_deadzone);

    // Mapear a pixeles en pantalla
    const markerX = ((currentRawX + 1.0) / 2.0) * width;
    const markerY = height - ((currentMappedY + 1.0) / 2.0) * height;

    // Dibujar Punto de posición
    ctx.fillStyle = "#ff3366";
    ctx.shadowBlur = 12;
    ctx.shadowColor = "rgba(255, 51, 102, 0.8)";
    ctx.beginPath();
    ctx.arc(markerX, markerY, 6, 0, 2 * Math.PI);
    ctx.fill();
    ctx.shadowBlur = 0;
}

// ==========================================================================
// MANEJO DE CONTROLES: SLIDERS & PRESETS
// ==========================================================================
function populatePresetsDropdown() {
    const select = dom.presetSelect;
    if (!select) return;
    
    // Guardar el valor seleccionado actual
    const currentVal = config.active_preset || "Personalizado";
    
    // Limpiar
    select.innerHTML = "";
    
    // Añadir presets por defecto
    for (const name in PRESETS) {
        if (name === "Personalizado") continue;
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name.split(" (")[0]; // Nombre simplificado
        select.appendChild(opt);
    }
    
    // Añadir presets personalizados
    if (config.custom_presets) {
        for (const name in config.custom_presets) {
            const opt = document.createElement("option");
            opt.value = name;
            opt.textContent = name;
            select.appendChild(opt);
        }
    }
    
    // Añadir "Personalizado" al final
    const optPers = document.createElement("option");
    optPers.value = "Personalizado";
    optPers.textContent = "Personalizado";
    select.appendChild(optPers);
    
    // Restaurar valor seleccionado
    select.value = currentVal;
    
    // Mostrar/ocultar botón de eliminar si es un preset personalizado
    const btnDelete = document.getElementById("btn-delete-preset");
    if (btnDelete) {
        if (config.custom_presets && config.custom_presets[currentVal] !== undefined) {
            btnDelete.style.display = "inline-block";
        } else {
            btnDelete.style.display = "none";
        }
    }
}

function getShortMappingLabel(mappingValue) {
    const map = {
        "Button Start": "Start",
        "Button Back": "Back",
        "Button A": "A",
        "Button B": "B",
        "Button X": "X",
        "Button Y": "Y",
        "Button LB (Left Shoulder)": "LB",
        "Button RB (Right Shoulder)": "RB",
        "Button L3 (Left Click)": "L3",
        "Button R3 (Right Click)": "R3",
        "D-Pad UP": "Pad Arriba",
        "D-Pad DOWN": "Pad Abajo",
        "D-Pad LEFT": "Pad Izq",
        "D-Pad RIGHT": "Pad Der",
        "Ninguno": "None"
    };
    return map[mappingValue] || mappingValue || "None";
}

function syncSlidersWithConfig() {
    dom.sliderSens.value = config.sensitivity;
    dom.sliderSlope.value = config.slope;
    dom.sliderAntiDz.value = config.anti_deadzone;
    dom.sliderDz.value = config.deadzone;
    dom.sliderFilter.value = config.filter;

    dom.valSens.innerText = `${Math.round(config.sensitivity * 100)}%`;
    dom.valSlope.innerText = `${config.slope.toFixed(2)}x`;
    dom.valAntiDz.innerText = `${Math.round(config.anti_deadzone * 100)}%`;
    dom.valDz.innerText = `${Math.round(config.deadzone * 100)}%`;
    dom.valFilter.innerText = `${Math.round(config.filter * 100)}%`;

    // Actualizar valores de calibración de hardware en la UI
    dom.lblCalMin.innerText = config.steer_min !== undefined ? config.steer_min : 0;
    dom.lblCalCenter.innerText = config.steer_center !== undefined ? config.steer_center : 512;
    dom.lblCalMax.innerText = config.steer_max !== undefined ? config.steer_max : 1023;

    // Actualizar marcadores de zona muerta en las barras de pedales
    const dzPercent = config.deadzone * 100;
    dom.throttleDzMarker.style.bottom = `${dzPercent}%`;
    dom.brakeDzMarker.style.bottom = `${dzPercent}%`;

    // Actualizar mapeos de botones en la UI
    if (dom.mapSelects && dom.mapSelects.length >= 10) {
        const p2 = config.btn_map_p2 !== undefined ? config.btn_map_p2 : "Ninguno";
        const p3 = config.btn_map_p3 !== undefined ? config.btn_map_p3 : "Ninguno";
        const p4 = config.btn_map_p4 !== undefined ? config.btn_map_p4 : "Ninguno";
        const p5 = config.btn_map_p5 !== undefined ? config.btn_map_p5 : "Ninguno";
        const p6 = config.btn_map_p6 !== undefined ? config.btn_map_p6 : "Ninguno";
        const p7 = config.btn_map_p7 !== undefined ? config.btn_map_p7 : "Ninguno";
        const p8 = config.btn_map_p8 !== undefined ? config.btn_map_p8 : "Ninguno";
        const p9 = config.btn_map_p9 !== undefined ? config.btn_map_p9 : "Ninguno";
        const p10 = config.btn_map_p10 !== undefined ? config.btn_map_p10 : "Ninguno";
        const p11 = config.btn_map_p11 !== undefined ? config.btn_map_p11 : "Ninguno";
        const p12 = config.btn_map_p12 !== undefined ? config.btn_map_p12 : "Ninguno";

        if (dom.mapSelects[0]) dom.mapSelects[0].value = p2;
        if (dom.mapSelects[1]) dom.mapSelects[1].value = p3;
        if (dom.mapSelects[2]) dom.mapSelects[2].value = p4;
        if (dom.mapSelects[3]) dom.mapSelects[3].value = p5;
        if (dom.mapSelects[4]) dom.mapSelects[4].value = p6;
        if (dom.mapSelects[5]) dom.mapSelects[5].value = p7;
        if (dom.mapSelects[6]) dom.mapSelects[6].value = p8;
        if (dom.mapSelects[7]) dom.mapSelects[7].value = p9;
        if (dom.mapSelects[8]) dom.mapSelects[8].value = p10;
        if (dom.mapSelects[9]) dom.mapSelects[9].value = p11;
        if (dom.mapSelects[10]) dom.mapSelects[10].value = p12;

        // Actualizar etiquetas en las píldoras del HUD
        if (document.getElementById("btn-p2-mapping")) document.getElementById("btn-p2-mapping").innerText = getShortMappingLabel(p2);
        if (document.getElementById("btn-p3-mapping")) document.getElementById("btn-p3-mapping").innerText = getShortMappingLabel(p3);
        if (document.getElementById("btn-p4-mapping")) document.getElementById("btn-p4-mapping").innerText = getShortMappingLabel(p4);
        if (document.getElementById("btn-p5-mapping")) document.getElementById("btn-p5-mapping").innerText = getShortMappingLabel(p5);
        if (document.getElementById("btn-p6-mapping")) document.getElementById("btn-p6-mapping").innerText = getShortMappingLabel(p6);
        if (document.getElementById("btn-p7-mapping")) document.getElementById("btn-p7-mapping").innerText = getShortMappingLabel(p7);
        if (document.getElementById("btn-p8-mapping")) document.getElementById("btn-p8-mapping").innerText = getShortMappingLabel(p8);
        if (document.getElementById("btn-p9-mapping")) document.getElementById("btn-p9-mapping").innerText = getShortMappingLabel(p9);
        if (document.getElementById("btn-p10-mapping")) document.getElementById("btn-p10-mapping").innerText = getShortMappingLabel(p10);
        if (document.getElementById("btn-p11-mapping")) document.getElementById("btn-p11-mapping").innerText = getShortMappingLabel(p11);
        if (document.getElementById("btn-p12-mapping")) document.getElementById("btn-p12-mapping").innerText = getShortMappingLabel(p12);
    }
    
    // Sincronizar el select de alternar presets
    const cycleBtnSelect = document.getElementById("preset-cycle-btn");
    if (cycleBtnSelect) {
        cycleBtnSelect.value = config.preset_cycle_btn !== undefined ? config.preset_cycle_btn : "Ninguno";
    }
    
    // Sincronizar selector de preset
    if (dom.presetSelect) {
        dom.presetSelect.value = config.active_preset !== undefined ? config.active_preset : "Personalizado";
    }

    // Sincronizar checkboxes de inversión
    if (dom.checkInvertSteer) dom.checkInvertSteer.checked = config.invert_steer || false;
    if (dom.checkInvertAccel) dom.checkInvertAccel.checked = config.invert_accel || false;
    if (dom.checkInvertBrake) dom.checkInvertBrake.checked = config.invert_brake || false;

    // Sincronizar límites de calibración de pedales en la UI
    if (dom.lblCalAccelMin) dom.lblCalAccelMin.innerText = config.accel_min !== undefined ? config.accel_min : 0;
    if (dom.lblCalAccelMax) dom.lblCalAccelMax.innerText = config.accel_max !== undefined ? config.accel_max : 1023;
    if (dom.lblCalBrakeMin) dom.lblCalBrakeMin.innerText = config.brake_min !== undefined ? config.brake_min : 0;
    if (dom.lblCalBrakeMax) dom.lblCalBrakeMax.innerText = config.brake_max !== undefined ? config.brake_max : 1023;

    // Actualizar los dropdowns personalizados
    if (typeof updateCustomSelects === 'function') {
        updateCustomSelects();
    }
}

function handleSliderChange(key, value, displayElement, suffix = "") {
    config[key] = parseFloat(value);
    displayElement.innerText = suffix === "%" ? `${Math.round(config[key] * 100)}%` : `${config[key].toFixed(2)}${suffix}`;
    
    // Si cambiamos un slider manualmente, el preset cambia a Personalizado
    if (config.active_preset !== "Personalizado") {
        config.previous_preset = config.active_preset;
    }
    config.active_preset = "Personalizado";
    if (dom.presetSelect) {
        dom.presetSelect.value = "Personalizado";
    }
    
    const btnDelete = document.getElementById("btn-delete-preset");
    if (btnDelete) {
        btnDelete.style.display = "none";
    }
    
    // Actualizar marcadores de pedales si es necesario
    if (key === 'deadzone') {
        const dzPercent = config.deadzone * 100;
        dom.throttleDzMarker.style.bottom = `${dzPercent}%`;
        dom.brakeDzMarker.style.bottom = `${dzPercent}%`;
    }

    // Enviar nueva configuración al servidor
    sendMessage("config", config);
    drawCurve();
}

function loadPreset(presetName) {
    let preset = PRESETS[presetName];
    if (!preset && config.custom_presets) {
        preset = config.custom_presets[presetName];
    }
    
    if (preset) {
        // Guardar actual como anterior antes de cambiar
        if (config.active_preset !== presetName) {
            config.previous_preset = config.active_preset;
        }
        
        // Copiar valores del preset a config
        config.sensitivity = preset.sensitivity;
        config.slope = preset.slope;
        config.anti_deadzone = preset.anti_deadzone;
        config.deadzone = preset.deadzone;
        config.filter = preset.filter;
        
        // Copiar targets y mapeos si existen en el preset
        if (preset.steer_target !== undefined) config.steer_target = preset.steer_target;
        if (preset.accel_target !== undefined) config.accel_target = preset.accel_target;
        if (preset.brake_target !== undefined) config.brake_target = preset.brake_target;
        
        for (let i = 2; i <= 11; i++) {
            const key = `btn_map_p${i}`;
            if (preset[key] !== undefined) {
                config[key] = preset[key];
            }
        }
        if (preset.preset_cycle_btn !== undefined) {
            config.preset_cycle_btn = preset.preset_cycle_btn;
        }
        
        config.active_preset = presetName;
        
        syncSlidersWithConfig();
        drawCurve();
        log(`Preset cargado: ${presetName}`, "info");
    } else if (presetName === "Personalizado") {
        if (config.active_preset !== "Personalizado") {
            config.previous_preset = config.active_preset;
        }
        config.active_preset = "Personalizado";
        log("Preset cambiado a Personalizado", "info");
    }
    
    // Actualizar visibilidad del botón de eliminar preset
    const btnDelete = document.getElementById("btn-delete-preset");
    if (btnDelete) {
        if (config.custom_presets && config.custom_presets[presetName] !== undefined) {
            btnDelete.style.display = "inline-block";
        } else {
            btnDelete.style.display = "none";
        }
    }

    // Enviar configuración al servidor
    sendMessage("config", config);
    drawCurve();
}

// ==========================================================================
// CONSOLA LOGS DE REGISTRO
// ==========================================================================
function log(text, level = "info") {
    const time = new Date().toLocaleTimeString();
    const line = document.createElement("div");
    line.className = `log-line log-${level}`;
    line.innerText = `[${time}] ${text}`;
    
    dom.consoleOutput.appendChild(line);
    
    // Limitar logs a un máximo de 100 líneas
    while (dom.consoleOutput.childNodes.length > 100) {
        dom.consoleOutput.removeChild(dom.consoleOutput.firstChild);
    }
    
    // Auto-scroll
    dom.consoleOutput.scrollTop = dom.consoleOutput.scrollHeight;
}

// ==========================================================================
// EVENT LISTENERS & INICIALIZACIÓN
// ==========================================================================
function setupEventListeners() {
    // Botón instalar driver
    const btnInstallDriver = document.getElementById('btn-install-driver');
    if (btnInstallDriver) {
        btnInstallDriver.addEventListener('click', () => {
            log("Iniciando instalador de ViGEmBus...", "info");
            sendMessage("command", "install_driver");
        });
    }

    // Botones Conexión
    dom.btnRefresh.addEventListener('click', () => {
        log("Escaneando puertos serie disponibles...", "info");
        sendMessage("command", "refresh_ports");
    });

    dom.btnConnect.addEventListener('click', () => {
        if (!isEmulating) {
            const selectedPort = dom.portSelect.value;
            if (!selectedPort) {
                log("Error: Selecciona un puerto serie válido.", "error");
                return;
            }
            sendMessage("command", "start", selectedPort);
        } else {
            sendMessage("command", "stop");
        }
    });

    dom.portSelect.addEventListener('change', () => {
        const selectedPort = dom.portSelect.value;
        if (selectedPort) {
            sendMessage("command", "select_port", selectedPort);
        }
    });

    // Preset selector
    dom.presetSelect.addEventListener('change', (e) => {
        loadPreset(e.target.value);
    });

    // Guardar preset
    const btnSave = document.getElementById("btn-save-preset");
    if (btnSave) {
        btnSave.addEventListener('click', () => {
            const presetName = prompt("Introduce un nombre para el nuevo preset:");
            if (!presetName) return;
            const trimmedName = presetName.trim();
            if (trimmedName === "" || trimmedName === "Personalizado") {
                alert("Nombre de preset no válido.");
                return;
            }
            
            if (config.custom_presets && config.custom_presets[trimmedName] !== undefined) {
                if (!confirm(`El preset "${trimmedName}" ya existe. ¿Deseas sobrescribirlo con los ajustes actuales?`)) {
                    return;
                }
            }
            
            if (!config.custom_presets) {
                config.custom_presets = {};
            }
            
            // Guardar valores actuales (ejes y botones)
            config.custom_presets[trimmedName] = {
                sensitivity: config.sensitivity,
                slope: config.slope,
                anti_deadzone: config.anti_deadzone,
                deadzone: config.deadzone,
                filter: config.filter,
                steer_target: config.steer_target || "Left Stick X",
                accel_target: config.accel_target || "Right Trigger (RT)",
                brake_target: config.brake_target || "Left Trigger (LT)",
                btn_map_p2: config.btn_map_p2 || "Ninguno",
                btn_map_p3: config.btn_map_p3 || "Ninguno",
                btn_map_p4: config.btn_map_p4 || "Ninguno",
                btn_map_p5: config.btn_map_p5 || "Ninguno",
                btn_map_p6: config.btn_map_p6 || "Ninguno",
                btn_map_p7: config.btn_map_p7 || "Ninguno",
                btn_map_p8: config.btn_map_p8 || "Ninguno",
                btn_map_p9: config.btn_map_p9 || "Ninguno",
                btn_map_p10: config.btn_map_p10 || "Ninguno",
                btn_map_p11: config.btn_map_p11 || "Ninguno",
                preset_cycle_btn: config.preset_cycle_btn || "Ninguno"
            };
            config.active_preset = trimmedName;
            
            populatePresetsDropdown();
            log(`Preset guardado como: ${trimmedName}`, "success");
            
            sendMessage("config", config);
        });
    }

    // Eliminar preset
    const btnDelete = document.getElementById("btn-delete-preset");
    if (btnDelete) {
        btnDelete.addEventListener('click', () => {
            const currentPreset = dom.presetSelect.value;
            if (config.custom_presets && config.custom_presets[currentPreset] !== undefined) {
                if (confirm(`¿Estás seguro de que quieres eliminar el preset "${currentPreset}"?`)) {
                    delete config.custom_presets[currentPreset];
                    config.active_preset = "Personalizado";
                    
                    populatePresetsDropdown();
                    log(`Preset eliminado: ${currentPreset}`, "info");
                    
                    sendMessage("config", config);
                }
            }
        });
    }

    // Sliders
    dom.sliderSens.addEventListener('input', (e) => {
        handleSliderChange('sensitivity', e.target.value, dom.valSens, "%");
    });
    dom.sliderSlope.addEventListener('input', (e) => {
        handleSliderChange('slope', e.target.value, dom.valSlope, "x");
    });
    dom.sliderAntiDz.addEventListener('input', (e) => {
        handleSliderChange('anti_deadzone', e.target.value, dom.valAntiDz, "%");
    });
    dom.sliderDz.addEventListener('input', (e) => {
        handleSliderChange('deadzone', e.target.value, dom.valDz, "%");
    });
    dom.sliderFilter.addEventListener('input', (e) => {
        handleSliderChange('filter', e.target.value, dom.valFilter, "%");
    });

    // Calibración de Hardware
    dom.btnCalLeft.addEventListener('click', () => {
        config.steer_min = currentTelemetry.raw.steer;
        dom.lblCalMin.innerText = config.steer_min;
        log(`Calibración: Límite izquierdo (Mín) establecido a ${config.steer_min}`, "success");
        sendMessage("config", config);
        drawCurve();
    });

    dom.btnCalCenter.addEventListener('click', () => {
        config.steer_center = currentTelemetry.raw.steer;
        dom.lblCalCenter.innerText = config.steer_center;
        log(`Calibración: Centro establecido a ${config.steer_center}`, "success");
        sendMessage("config", config);
        drawCurve();
    });

    dom.btnCalRight.addEventListener('click', () => {
        config.steer_max = currentTelemetry.raw.steer;
        dom.lblCalMax.innerText = config.steer_max;
        log(`Calibración: Límite derecho (Máx) establecido a ${config.steer_max}`, "success");
        sendMessage("config", config);
        drawCurve();
    });

    dom.btnCalReset.addEventListener('click', () => {
        config.steer_min = 0;
        config.steer_center = 512;
        config.steer_max = 1023;
        dom.lblCalMin.innerText = "0";
        dom.lblCalCenter.innerText = "512";
        dom.lblCalMax.innerText = "1023";
        log(`Calibración de límites de dirección restablecida a valores por defecto (0, 512, 1023)`, "info");
        sendMessage("config", config);
        drawCurve();
    });

    // Calibración de Pedales (Hardware)
    if (dom.btnCalAccelMin) {
        dom.btnCalAccelMin.addEventListener('click', () => {
            config.accel_min = currentTelemetry.raw.accel;
            dom.lblCalAccelMin.innerText = config.accel_min;
            log(`Calibración Pedales: Acelerador Suelto (Mín) establecido a ${config.accel_min}`, "success");
            sendMessage("config", config);
        });
    }

    if (dom.btnCalAccelMax) {
        dom.btnCalAccelMax.addEventListener('click', () => {
            config.accel_max = currentTelemetry.raw.accel;
            dom.lblCalAccelMax.innerText = config.accel_max;
            log(`Calibración Pedales: Acelerador A Fondo (Máx) establecido a ${config.accel_max}`, "success");
            sendMessage("config", config);
        });
    }

    if (dom.btnCalBrakeMin) {
        dom.btnCalBrakeMin.addEventListener('click', () => {
            config.brake_min = currentTelemetry.raw.brake;
            dom.lblCalBrakeMin.innerText = config.brake_min;
            log(`Calibración Pedales: Freno Suelto (Mín) establecido a ${config.brake_min}`, "success");
            sendMessage("config", config);
        });
    }

    if (dom.btnCalBrakeMax) {
        dom.btnCalBrakeMax.addEventListener('click', () => {
            config.brake_max = currentTelemetry.raw.brake;
            dom.lblCalBrakeMax.innerText = config.brake_max;
            log(`Calibración Pedales: Freno A Fondo (Máx) establecido a ${config.brake_max}`, "success");
            sendMessage("config", config);
        });
    }

    if (dom.btnPedalReset) {
        dom.btnPedalReset.addEventListener('click', () => {
            config.accel_min = 0;
            config.accel_max = 1023;
            config.brake_min = 0;
            config.brake_max = 1023;
            dom.lblCalAccelMin.innerText = "0";
            dom.lblCalAccelMax.innerText = "1023";
            dom.lblCalBrakeMin.innerText = "0";
            dom.lblCalBrakeMax.innerText = "1023";
            log("Calibración de límites de pedales restablecida a valores por defecto (0, 1023)", "info");
            sendMessage("config", config);
        });
    }

    // Event listeners para mapeos de botones
    if (dom.mapSelects && dom.mapSelects.length >= 10) {
        dom.mapSelects.forEach((select, index) => {
            select.addEventListener('change', (e) => {
                const key = `btn_map_p${index + 2}`;
                config[key] = e.target.value;
                if (config.active_preset !== "Personalizado") {
                    config.previous_preset = config.active_preset;
                }
                config.active_preset = "Personalizado";
                dom.presetSelect.value = "Personalizado";
                
                // Actualizar etiqueta del HUD inmediatamente
                const mappingLabel = document.getElementById(`btn-p${index + 2}-mapping`);
                if (mappingLabel) {
                    mappingLabel.innerText = getShortMappingLabel(e.target.value);
                }
                
                sendMessage("config", config);
                log(`Mapeo de Pin D${index + 2} actualizado a: ${MAP_OPTIONS[e.target.value]}`, "info");
            });
        });
    }

    // Event listeners para Cruceta Virtual (Mapeo)
    const btnDpadUp = document.getElementById('btn-dpad-up');
    const btnDpadDown = document.getElementById('btn-dpad-down');
    const btnDpadLeft = document.getElementById('btn-dpad-left');
    const btnDpadRight = document.getElementById('btn-dpad-right');

    if (btnDpadUp) {
        btnDpadUp.addEventListener('click', () => {
            sendMessage("command", "trigger_dpad", "D-Pad UP");
            log("Simulando Cruceta Arriba (D-Pad UP) para mapeo...", "info");
        });
    }
    if (btnDpadDown) {
        btnDpadDown.addEventListener('click', () => {
            sendMessage("command", "trigger_dpad", "D-Pad DOWN");
            log("Simulando Cruceta Abajo (D-Pad DOWN) para mapeo...", "info");
        });
    }
    if (btnDpadLeft) {
        btnDpadLeft.addEventListener('click', () => {
            sendMessage("command", "trigger_dpad", "D-Pad LEFT");
            log("Simulando Cruceta Izquierda (D-Pad LEFT) para mapeo...", "info");
        });
    }
    if (btnDpadRight) {
        btnDpadRight.addEventListener('click', () => {
            sendMessage("command", "trigger_dpad", "D-Pad RIGHT");
            log("Simulando Cruceta Derecha (D-Pad RIGHT) para mapeo...", "info");
        });
    }

    const cycleBtnSelect = document.getElementById('preset-cycle-btn');
    if (cycleBtnSelect) {
        cycleBtnSelect.addEventListener('change', (e) => {
            config.preset_cycle_btn = e.target.value;
            sendMessage("config", config);
            log(`Botón de alternar presets configurado a: ${e.target.value}`, "info");
        });
    }

    // Event listeners para inversión de ejes
    const handleCheckboxChange = (key, checked, label) => {
        config[key] = checked;
        if (config.active_preset !== "Personalizado") {
            config.previous_preset = config.active_preset;
        }
        config.active_preset = "Personalizado";
        if (dom.presetSelect) {
            dom.presetSelect.value = "Personalizado";
        }
        sendMessage("config", config);
        log(`${label} ${checked ? 'activado' : 'desactivado'}`, "info");
    };

    if (dom.checkInvertSteer) {
        dom.checkInvertSteer.addEventListener('change', (e) => {
            handleCheckboxChange('invert_steer', e.target.checked, "Invertir Volante");
        });
    }
    if (dom.checkInvertAccel) {
        dom.checkInvertAccel.addEventListener('change', (e) => {
            handleCheckboxChange('invert_accel', e.target.checked, "Invertir Acelerador");
        });
    }
    if (dom.checkInvertBrake) {
        dom.checkInvertBrake.addEventListener('change', (e) => {
            handleCheckboxChange('invert_brake', e.target.checked, "Invertir Freno");
        });
    }

    // Limpiar Consola
    dom.btnClearLog.addEventListener('click', () => {
        dom.consoleOutput.innerHTML = "";
        log("Registro de consola limpiado.", "info");
    });
}

// Inicialización
function init() {
    // 1. Popular selectores de botones dinámicamente antes de sincronizar
    if (dom.mapSelects && dom.mapSelects.length >= 10) {
        dom.mapSelects.forEach((select) => {
            select.innerHTML = "";
            for (const [val, label] of Object.entries(MAP_OPTIONS)) {
                const opt = document.createElement("option");
                opt.value = val;
                opt.innerText = label;
                select.appendChild(opt);
            }
        });
    }

    setupEventListeners();
    // Detectar modo nativo (PyWebView) o web (WebSocket)
    if (window.pywebview && window.pywebview.api) {
        initNativeMode();
    } else {
        // Esperar evento pywebviewready o caer a WebSocket
        let nativeTimeout = setTimeout(() => {
            if (!nativeMode) {
                connectWebSocket();
            }
        }, 600);
        
        window.addEventListener('pywebviewready', () => {
            clearTimeout(nativeTimeout);
            if (!nativeMode) {
                initNativeMode();
            }
        });
    }
    
    // Ajustar dimensiones del Canvas por el escalado de retina
    const dpr = window.devicePixelRatio || 1;
    dom.curveCanvas.width = dom.curveCanvas.clientWidth * dpr;
    dom.curveCanvas.height = dom.curveCanvas.clientHeight * dpr;
    ctx.scale(dpr, dpr);
    
    populatePresetsDropdown();
    syncSlidersWithConfig();
    drawCurve();
    
    // Escuchar cambios de tamaño de ventana para redibujar el canvas
    window.addEventListener('resize', () => {
        dom.curveCanvas.width = dom.curveCanvas.clientWidth * dpr;
        dom.curveCanvas.height = dom.curveCanvas.clientHeight * dpr;
        ctx.scale(dpr, dpr);
        drawCurve();
    });

    // Convertir todos los selectores de botones a custom selects para evitar problemas de visualización en PyWebView
    document.querySelectorAll('.select-sm').forEach(convertToCustomSelect);
}

// --- Custom Dropdown Logic for PyWebView GTK clipping fix ---
function convertToCustomSelect(selectElement) {
    if (selectElement.style.display === 'none') return; // Evitar doble conversión
    
    selectElement.style.display = 'none';

    const wrapper = document.createElement('div');
    wrapper.className = 'custom-select-wrapper';
    selectElement.parentNode.insertBefore(wrapper, selectElement.nextSibling);

    const trigger = document.createElement('div');
    trigger.className = 'custom-select-trigger';
    const triggerText = document.createElement('span');
    triggerText.innerText = selectElement.options[selectElement.selectedIndex]?.text || '';
    trigger.appendChild(triggerText);
    
    const arrow = document.createElement('span');
    arrow.className = 'custom-select-arrow';
    arrow.innerHTML = '▼';
    trigger.appendChild(arrow);
    
    wrapper.appendChild(trigger);

    const dropdown = document.createElement('div');
    dropdown.className = 'custom-select-options';
    
    function rebuildOptions() {
        dropdown.innerHTML = '';
        Array.from(selectElement.options).forEach((option) => {
            const optDiv = document.createElement('div');
            optDiv.className = 'custom-select-option';
            if (option.value === selectElement.value) {
                optDiv.classList.add('selected');
            }
            optDiv.innerText = option.text;
            optDiv.dataset.value = option.value;

            optDiv.addEventListener('click', (e) => {
                e.stopPropagation();
                selectElement.value = option.value;
                triggerText.innerText = option.text;
                
                // Disparar evento change en el select original
                const event = new Event('change', { bubbles: true });
                selectElement.dispatchEvent(event);
                
                closeDropdown();
            });
            dropdown.appendChild(optDiv);
        });
    }

    rebuildOptions();
    wrapper.appendChild(dropdown);

    function toggleDropdown(e) {
        e.stopPropagation();
        const isOpen = dropdown.classList.contains('show');
        closeAllCustomDropdowns();
        if (!isOpen) {
            dropdown.classList.add('show');
            trigger.classList.add('active');
            const selectedOpt = dropdown.querySelector('.custom-select-option.selected');
            if (selectedOpt) {
                selectedOpt.scrollIntoView({ block: 'nearest' });
            }
        }
    }

    function closeDropdown() {
        dropdown.classList.remove('show');
        trigger.classList.remove('active');
    }

    trigger.addEventListener('click', toggleDropdown);

    selectElement.customSelect = {
        update: () => {
            rebuildOptions();
            triggerText.innerText = selectElement.options[selectElement.selectedIndex]?.text || '';
        }
    };
}

function closeAllCustomDropdowns() {
    document.querySelectorAll('.custom-select-options.show').forEach((dropdown) => {
        dropdown.classList.remove('show');
    });
    document.querySelectorAll('.custom-select-trigger.active').forEach((trigger) => {
        trigger.classList.remove('active');
    });
}

document.addEventListener('click', closeAllCustomDropdowns);

function updateCustomSelects() {
    document.querySelectorAll('.select-sm').forEach((selectElement) => {
        if (selectElement.customSelect) {
            selectElement.customSelect.update();
        }
    });
}

window.onload = init;
