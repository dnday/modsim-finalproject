// ==========================================
// SPKLU p5.js Real-time Simulation Engine
// Apple Glass Edition — 3D Sprite Version
// ==========================================

// --- Parameters ---
var simParams = {
    c: 2,
    K: 10,
    lam: 5.0,
    mu: 2.0,
    speed: 10
};

// --- State ---
var cars = [];
var chargers = [];
var queue = [];
var nextSpawnDelay = 0;
var simClockSeconds = 0;
var isPlaying = false;

// --- Counters ---
var statArrived = 0;
var statServed = 0;
var statBalked = 0;
var totalWaitTime = 0;
var servedCountForAvg = 0;

// --- Constants ---
var START_HOUR = 6;
var CHARGER_W = 60;
var CHARGER_H = 90;
var CAR_W = 60;
var CAR_H = 70;

// --- Sprite Images ---
var imgCar;
var imgCharger;

// ==========================================
// Preload (load images before setup)
// ==========================================

function preload() {
    imgCar = loadImage('assets/car.png');
    imgCharger = loadImage('assets/charger.png');
}

// ==========================================
// Setup & Resize
// ==========================================

function setup() {
    var container = document.getElementById('canvas-container');
    var canvas = createCanvas(container.offsetWidth, container.offsetHeight);
    canvas.parent('canvas-container');
    imageMode(CENTER);
    textFont('Inter');
    initSliders();
    updateChargerPositions();
    fetchTheoreticalMetrics();
}

function windowResized() {
    var container = document.getElementById('canvas-container');
    resizeCanvas(container.offsetWidth, container.offsetHeight);
    updateChargerPositions();
}

// ==========================================
// Slider Binding
// ==========================================

function initSliders() {
    function bind(sliderId, displayId, paramKey, opts) {
        var slider = document.getElementById(sliderId);
        var display = document.getElementById(displayId);
        if (!slider || !display) return;
        slider.addEventListener('input', function() {
            var val = parseFloat(slider.value);
            simParams[paramKey] = val;
            if (opts && opts.decimals !== undefined) {
                display.innerText = val.toFixed(opts.decimals);
            } else {
                display.innerText = val;
            }
            if (opts && opts.onChange) opts.onChange(val);
        });
    }

    bind('slider-c', 'val-c', 'c', {
        decimals: 0,
        onChange: function() { updateChargerPositions(); fetchTheoreticalMetrics(); }
    });
    bind('slider-k', 'val-k', 'K', { decimals: 0, onChange: fetchTheoreticalMetrics });
    bind('slider-lam', 'val-lam', 'lam', { decimals: 1, onChange: fetchTheoreticalMetrics });
    bind('slider-mu', 'val-mu', 'mu', {
        decimals: 1,
        onChange: function(val) {
            document.getElementById('val-mu-min').innerText = (60 / val).toFixed(0);
            fetchTheoreticalMetrics();
        }
    });
    bind('slider-speed', 'val-speed', 'speed', {
        decimals: 0,
        onChange: function(val) { document.getElementById('val-speed').innerText = val + '×'; }
    });

    // Play / Pause
    var playBtn = document.getElementById('btn-play');
    if (playBtn) {
        playBtn.addEventListener('click', function() {
            isPlaying = !isPlaying;
            if (isPlaying) {
                playBtn.innerText = '⏸ Pause';
                playBtn.classList.add('playing');
            } else {
                playBtn.innerText = '▶ Play';
                playBtn.classList.remove('playing');
            }
        });
    }

    // Reset
    var resetBtn = document.getElementById('btn-reset');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetSimulation);
    }
}

function resetSimulation() {
    cars = [];
    queue = [];
    nextSpawnDelay = 0;
    simClockSeconds = 0;
    statArrived = 0;
    statServed = 0;
    statBalked = 0;
    totalWaitTime = 0;
    servedCountForAvg = 0;
    for (var i = 0; i < chargers.length; i++) chargers[i].car = null;
    updateChargerPositions();
}

// ==========================================
// API
// ==========================================

function fetchTheoreticalMetrics() {
    fetch('/api/metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            c: simParams.c, K: simParams.K,
            lambda_rate: simParams.lam, mu_rate: simParams.mu
        })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        document.getElementById('theo-rho').innerText = (d.rho * 100).toFixed(2) + '%';
        document.getElementById('theo-lq').innerText = d.Lq.toFixed(2);
        document.getElementById('theo-wq').innerText = d.Wq.toFixed(1) + ' min';
        document.getElementById('theo-pb').innerText = (d.Pb * 100).toFixed(2) + '%';
        document.getElementById('conn-status').innerText = '● Online';
        document.getElementById('conn-status').style.color = '#34c759';
    })
    .catch(function() {
        document.getElementById('conn-status').innerText = '● Offline';
        document.getElementById('conn-status').style.color = '#ff3b30';
    });
}

// ==========================================
// Charger Management
// ==========================================

function updateChargerPositions() {
    var c = simParams.c;
    while (chargers.length < c) chargers.push({ id: chargers.length, x: 0, y: 0, car: null });
    while (chargers.length > c) {
        var rem = chargers.pop();
        if (rem.car) rem.car.status = 'leaving';
    }
    var spacing = 110;
    var totalW = c * spacing;
    var startX = width / 2 - totalW / 2 + spacing / 2;
    for (var i = 0; i < chargers.length; i++) {
        chargers[i].x = startX + i * spacing;
        chargers[i].y = height * 0.28;
    }
}

// ==========================================
// Draw Loop
// ==========================================

function draw() {
    // Background — match Apple's system gray 6
    background(242, 242, 247);

    drawScene();

    if (isPlaying) {
        var dt = (deltaTime / 1000.0) * simParams.speed;
        var dtHours = dt / 3600.0;
        simClockSeconds += dt;

        if (nextSpawnDelay <= 0) {
            spawnVehicle();
            nextSpawnDelay = randExp(simParams.lam) * 3600;
        }
        nextSpawnDelay -= dt;
        processVehicles(dtHours);
    }

    for (var i = 0; i < chargers.length; i++) drawCharger(chargers[i]);
    for (var j = 0; j < cars.length; j++) {
        if (isPlaying) updateCarVisual(cars[j]);
        drawCar(cars[j]);
    }

    updateHUD();

    if (!isPlaying) {
        // Frosted overlay
        fill(242, 242, 247, 180);
        noStroke();
        rect(0, 0, width, height);
        // Prompt
        fill(142, 142, 147);
        noStroke();
        textSize(15);
        textAlign(CENTER, CENTER);
        textStyle(NORMAL);
        text('Press ▶ Play to start simulation', width / 2, height / 2);
    }
}

// ==========================================
// Scene Drawing
// ==========================================

function drawScene() {
    noStroke();

    // Charging area
    fill(235, 235, 240);
    rect(0, 0, width, height * 0.56);

    // Area label
    fill(174, 174, 178);
    textSize(10);
    textAlign(CENTER);
    textStyle(BOLD);
    text('CHARGING AREA', width / 2, 18);
    textStyle(NORMAL);

    // Road
    fill(229, 229, 234);
    rect(0, height * 0.56, width, height * 0.44);

    // Road dashes
    stroke(199, 199, 204);
    strokeWeight(3);
    for (var x = 0; x < width; x += 48) {
        line(x, height * 0.77, x + 22, height * 0.77);
    }

    // Queue zone label
    noStroke();
    fill(174, 174, 178);
    textSize(10);
    textAlign(CENTER);
    text('QUEUE', width - 80, height * 0.42);
}

// ==========================================
// Charger Drawing
// ==========================================

function drawCharger(ch) {
    push();
    translate(ch.x, ch.y);

    // 3D charger sprite
    image(imgCharger, 0, 0, CHARGER_W, CHARGER_H);

    // Status dot overlay
    noStroke();
    if (ch.car) {
        fill(255, 59, 48, 200); // Red = busy
    } else {
        fill(52, 199, 89, 200); // Green = available
    }
    circle(0, CHARGER_H / 2 + 8, 10);

    // Label
    fill(142, 142, 147);
    textSize(10);
    textAlign(CENTER);
    textStyle(BOLD);
    text('C' + (ch.id + 1), 0, -CHARGER_H / 2 - 10);
    textStyle(NORMAL);

    pop();
}

// ==========================================
// Car Drawing
// ==========================================

function drawCar(car) {
    push();
    translate(car.x, car.y);

    // Slight color tint per car
    tint(car.color[0], car.color[1], car.color[2]);
    image(imgCar, 0, 0, CAR_W, CAR_H);
    noTint();

    // Wait label
    if (car.status === 'queueing') {
        // Background pill
        var label = (car.waitTime * 60).toFixed(0) + 'm';
        fill(0, 0, 0, 140);
        noStroke();
        rectMode(CENTER);
        rect(0, -CAR_H / 2 - 12, 30, 16, 8);
        rectMode(CORNER);
        // Text
        fill(255);
        textAlign(CENTER, CENTER);
        textSize(9);
        text(label, 0, -CAR_H / 2 - 12);
    }

    pop();
}

function updateCarVisual(car) {
    var tx = car.x;
    var ty = car.y;

    if (car.status === 'arriving') {
        tx = width * 0.12;
        ty = height * 0.72;
    } else if (car.status === 'queueing') {
        var idx = queue.indexOf(car);
        tx = width - 80 - (idx % 5) * (CAR_W + 8);
        ty = height * 0.44 + Math.floor(idx / 5) * (CAR_H + 4);
    } else if (car.status === 'charging' && car.charger) {
        tx = car.charger.x;
        ty = car.charger.y + CHARGER_H / 2 + CAR_H / 2 + 10;
    } else if (car.status === 'balking') {
        tx = width + 120;
        ty = height * 0.72;
    }

    car.x = lerp(car.x, tx, 0.1);
    car.y = lerp(car.y, ty, 0.1);
}

// ==========================================
// Spawning
// ==========================================

function spawnVehicle() {
    statArrived++;
    var systemSize = queue.length;
    for (var i = 0; i < chargers.length; i++) {
        if (chargers[i].car !== null) systemSize++;
    }
    var car = createCar();
    cars.push(car);
    if (systemSize >= simParams.K) {
        car.status = 'balking';
        statBalked++;
    } else {
        car.status = 'arriving';
    }
}

function createCar() {
    // Muted, sophisticated car colors (Apple palette feel)
    var colors = [
        [142, 142, 147],  // systemGray
        [174, 174, 178],  // systemGray2
        [199, 199, 204],  // systemGray3
        [162, 178, 194],  // steel blue
        [180, 196, 172],  // sage
        [196, 178, 168],  // warm taupe
        [168, 182, 200],  // slate
        [190, 180, 170],  // stone
    ];
    var c = colors[Math.floor(Math.random() * colors.length)];
    return {
        x: -80,
        y: height * 0.72,
        color: c,
        status: 'spawning',
        charger: null,
        waitTime: 0,
        serviceTimeRemaining: 0
    };
}

// ==========================================
// Vehicle Processing
// ==========================================

function processVehicles(dtHours) {
    for (var i = cars.length - 1; i >= 0; i--) {
        var car = cars[i];

        if (car.status === 'arriving') {
            var empty = null;
            for (var j = 0; j < chargers.length; j++) {
                if (chargers[j].car === null) { empty = chargers[j]; break; }
            }
            if (empty) {
                empty.car = car;
                car.status = 'charging';
                car.charger = empty;
                car.serviceTimeRemaining = randExp(simParams.mu);
            } else {
                car.status = 'queueing';
                queue.push(car);
            }
        }

        if (car.status === 'queueing') {
            car.waitTime += dtHours;
        }

        if (car.status === 'charging') {
            car.serviceTimeRemaining -= dtHours;
            if (car.serviceTimeRemaining <= 0) {
                car.status = 'leaving';
                car.charger.car = null;
                car.charger = null;
                statServed++;
                totalWaitTime += car.waitTime;
                servedCountForAvg++;

                if (queue.length > 0) {
                    var next = queue.shift();
                    var emptyC = null;
                    for (var k = 0; k < chargers.length; k++) {
                        if (chargers[k].car === null) { emptyC = chargers[k]; break; }
                    }
                    if (emptyC) {
                        emptyC.car = next;
                        next.status = 'charging';
                        next.charger = emptyC;
                        next.serviceTimeRemaining = randExp(simParams.mu);
                    }
                }
            }
        }

        if (car.status === 'leaving' || car.status === 'balking') {
            car.y += 4;
            if (car.y > height + 120) cars.splice(i, 1);
        }
    }
}

// ==========================================
// HUD
// ==========================================

function updateHUD() {
    document.getElementById('sim-clock').innerText = formatClock(simClockSeconds);
    document.getElementById('stat-arrived').innerText = statArrived;
    document.getElementById('stat-served').innerText = statServed;
    document.getElementById('stat-balked').innerText = statBalked;

    var busy = 0;
    for (var i = 0; i < chargers.length; i++) {
        if (chargers[i].car !== null) busy++;
    }
    document.getElementById('live-rho').innerText = ((busy / simParams.c) * 100).toFixed(2) + '%';
    document.getElementById('live-lq').innerText = queue.length.toFixed(2);
    var avgW = servedCountForAvg > 0 ? (totalWaitTime / servedCountForAvg) * 60 : 0;
    document.getElementById('live-wq').innerText = avgW.toFixed(1) + ' min';
    var pb = statArrived > 0 ? (statBalked / statArrived) : 0;
    document.getElementById('live-pb').innerText = (pb * 100).toFixed(2) + '%';
}

function formatClock(simSecs) {
    var total = (START_HOUR * 3600) + Math.floor(simSecs);
    var h = Math.floor(total / 3600) % 24;
    var m = Math.floor((total % 3600) / 60);
    var s = total % 60;
    return pad(h) + ':' + pad(m) + ':' + pad(s);
}

function pad(n) { return n < 10 ? '0' + n : '' + n; }
function randExp(rate) { return -Math.log(1.0 - Math.random()) / rate; }
