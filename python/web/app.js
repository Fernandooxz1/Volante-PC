// ==========================================================================
// CONFIGURACIÓN Y VARIABLES DE ESTADO
// ==========================================================================
let socket = null;
let reconnectInterval = 2000;
let isConnected = false;
let isEmulating = false;

// Estado de Ajustes (Calibración)
let config = {
    sensitivity: 0.25,
    slope: 0.65,
    anti_deadzone: 0.0,
    deadzone: 0.23,
    filter: 0.55,
    steer_target: "Left Stick X",
    accel_target: "Right Trigger (RT)",
    brake_target: "Left Trigger (LT)",
    btn_d2_target: "Button Start",
    steer_min: 0,
    steer_center: 512,
    steer_max: 1023,
    btn_map_p2: "Button Start",
    btn_map_p3: "Button A",
    btn_map_p4: "Button B",
    btn_map_p5: "Button X",
    btn_map_p6: "Button Y",
    btn_map_p7: "Button LB (Left Shoulder)",
    btn_map_p8: "Button RB (Right Shoulder)",
    btn_map_p9: "Button Back"
};

// Presets de Juego (Espejo de python para consistencia local y velocidad)
const PRESETS = {
    "F1 Series (F1 23/24) / Modern Racing": {
        sensitivity: 0.25,
        slope: 0.65,
        anti_deadzone: 0.0,
        deadzone: 0.23,
        filter: 0.55
    },
    "Gran Turismo 4 (PS2 / PCSX2)": {
        sensitivity: 0.40,
        slope: 0.80,
        anti_deadzone: 0.15,
        deadzone: 0.10,
        filter: 0.40
    },
    "Need for Speed Underground / PS2 Classic": {
        sensitivity: 0.50,
        slope: 1.00,
        anti_deadzone: 0.25,
        deadzone: 0.15,
        filter: 0.30
    },
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
    gamepadStatus: document.getElementById('gamepad-status'),
    
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
        document.getElementById('btn-p9-pill')
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
        document.getElementById('map-p9')
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
    log("Conectando con el servidor backend (ws://localhost:8765)...", "info");
    dom.wsStatusText.innerText = "WebSocket: Conectando...";
    dom.wsDot.className = "dot yellow";

    socket = new WebSocket("ws://localhost:8765");

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
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type, data, value }));
    }
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
    
    // --- 3. ACTUALIZAR ESTADO DE LOS 9 BOTONES ---
    if (data.mapped.buttons && data.mapped.buttons.length === 9) {
        for (let i = 0; i < 9; i++) {
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
    // 1. Aplicar pendiente y sensibilidad
    let x_sloped = x * slope * sensitivity;
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
    const width = dom.curveCanvas.width;
    const height = dom.curveCanvas.height;
    
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
            opt.textContent = `⭐ ${name}`;
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
    if (dom.mapSelects && dom.mapSelects.length === 8) {
        const p2 = config.btn_map_p2 !== undefined ? config.btn_map_p2 : "Button Start";
        const p3 = config.btn_map_p3 !== undefined ? config.btn_map_p3 : "Button A";
        const p4 = config.btn_map_p4 !== undefined ? config.btn_map_p4 : "Button B";
        const p5 = config.btn_map_p5 !== undefined ? config.btn_map_p5 : "Button X";
        const p6 = config.btn_map_p6 !== undefined ? config.btn_map_p6 : "Button Y";
        const p7 = config.btn_map_p7 !== undefined ? config.btn_map_p7 : "Button LB (Left Shoulder)";
        const p8 = config.btn_map_p8 !== undefined ? config.btn_map_p8 : "Button RB (Right Shoulder)";
        const p9 = config.btn_map_p9 !== undefined ? config.btn_map_p9 : "Button Back";

        dom.mapSelects[0].value = p2;
        dom.mapSelects[1].value = p3;
        dom.mapSelects[2].value = p4;
        dom.mapSelects[3].value = p5;
        dom.mapSelects[4].value = p6;
        dom.mapSelects[5].value = p7;
        dom.mapSelects[6].value = p8;
        dom.mapSelects[7].value = p9;

        // Actualizar etiquetas en las píldoras del HUD
        document.getElementById("btn-p2-mapping").innerText = getShortMappingLabel(p2);
        document.getElementById("btn-p3-mapping").innerText = getShortMappingLabel(p3);
        document.getElementById("btn-p4-mapping").innerText = getShortMappingLabel(p4);
        document.getElementById("btn-p5-mapping").innerText = getShortMappingLabel(p5);
        document.getElementById("btn-p6-mapping").innerText = getShortMappingLabel(p6);
        document.getElementById("btn-p7-mapping").innerText = getShortMappingLabel(p7);
        document.getElementById("btn-p8-mapping").innerText = getShortMappingLabel(p8);
        document.getElementById("btn-p9-mapping").innerText = getShortMappingLabel(p9);
    }
    
    // Sincronizar selector de preset
    if (dom.presetSelect) {
        dom.presetSelect.value = config.active_preset !== undefined ? config.active_preset : "Personalizado";
    }
}

function handleSliderChange(key, value, displayElement, suffix = "") {
    config[key] = parseFloat(value);
    displayElement.innerText = suffix === "%" ? `${Math.round(config[key] * 100)}%` : `${config[key].toFixed(2)}${suffix}`;
    
    // Si cambiamos un slider manualmente, el preset cambia a Personalizado
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
        // Copiar valores del preset a config
        config.sensitivity = preset.sensitivity;
        config.slope = preset.slope;
        config.anti_deadzone = preset.anti_deadzone;
        config.deadzone = preset.deadzone;
        config.filter = preset.filter;
        config.active_preset = presetName;
        
        syncSlidersWithConfig();
        drawCurve();
        log(`Preset cargado: ${presetName}`, "info");
    } else if (presetName === "Personalizado") {
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
            if (PRESETS[trimmedName] !== undefined) {
                alert("No puedes sobrescribir los presets por defecto.");
                return;
            }
            
            if (!config.custom_presets) {
                config.custom_presets = {};
            }
            
            // Guardar valores actuales
            config.custom_presets[trimmedName] = {
                sensitivity: config.sensitivity,
                slope: config.slope,
                anti_deadzone: config.anti_deadzone,
                deadzone: config.deadzone,
                filter: config.filter
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

    // Event listeners para mapeos de botones
    if (dom.mapSelects && dom.mapSelects.length === 8) {
        dom.mapSelects.forEach((select, index) => {
            select.addEventListener('change', (e) => {
                const key = `btn_map_p${index + 2}`;
                config[key] = e.target.value;
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

    // Limpiar Consola
    dom.btnClearLog.addEventListener('click', () => {
        dom.consoleOutput.innerHTML = "";
        log("Registro de consola limpiado.", "info");
    });
}

// Inicialización
function init() {
    // 1. Popular selectores de botones dinámicamente antes de sincronizar
    if (dom.mapSelects && dom.mapSelects.length === 8) {
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
    connectWebSocket();
    
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
}

window.onload = init;
