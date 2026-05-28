// ==========================================
// SPKLU p5.js Real-time Simulation Engine
// ==========================================

// --- Simulation Parameters (mutable via sliders) ---
var simParams = {
    c: 2,        // number of chargers
    K: 10,       // system capacity
    lam: 5.0,    // arrival rate (vehicles/hour)
    mu: 2.0,     // service rate (vehicles/hour per charger)
    speed: 10    // time multiplier
};

// --- State ---
var cars = [];
var chargers = [];
var queue = [];
var nextSpawnDelay = 0;
var simClockSeconds = 0;

// --- Counters ---
var statArrived = 0;
var statServed = 0;
var statBalked = 0;
var totalWaitTime = 0;
var servedCountForAvg = 0;

// --- Constants ---
var START_HOUR = 6; // 06:00 AM
var CHARGER_W = 56;
var CHARGER_H = 72;
var CAR_W = 36;
var CAR_H = 60;

// ==========================================
// p5.js Lifecycle
// ==========================================

function setup() {
    var container = document.getElementById('canvas-container');
    var canvas = createCanvas(container.offsetWidth, container.offsetHeight);
    canvas.parent('canvas-container');

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
// Slider Binding (direct, no window[] hack)
// ==========================================

function initSliders() {
    // Helper: bind a slider to simParams and update display
    function bind(sliderId, displayId, paramKey, opts) {
        var slider = document.getElementById(sliderId);
        var display = document.getElementById(displayId);
        if (!slider || !display) return;

        slider.addEventListener('input', function() {
            var val = parseFloat(slider.value);
            simParams[paramKey] = val;

            // Format display
            if (opts && opts.decimals !== undefined) {
                display.innerText = val.toFixed(opts.decimals);
            } else {
                display.innerText = val;
            }

            // Extra callbacks
            if (opts && opts.onChange) opts.onChange(val);
        });
    }

    bind('slider-c', 'val-c', 'c', {
        decimals: 0,
        onChange: function() {
            updateChargerPositions();
            fetchTheoreticalMetrics();
        }
    });

    bind('slider-k', 'val-k', 'K', {
        decimals: 0,
        onChange: fetchTheoreticalMetrics
    });

    bind('slider-lam', 'val-lam', 'lam', {
        decimals: 1,
        onChange: fetchTheoreticalMetrics
    });

    bind('slider-mu', 'val-mu', 'mu', {
        decimals: 1,
        onChange: function(val) {
            document.getElementById('val-mu-min').innerText = (60 / val).toFixed(0);
            fetchTheoreticalMetrics();
        }
    });

    bind('slider-speed', 'val-speed', 'speed', {
        decimals: 0,
        onChange: function(val) {
            document.getElementById('val-speed').innerText = val + '×';
        }
    });

    // Reset button
    var resetBtn = document.getElementById('btn-reset');
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            resetSimulation();
        });
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

    // Reset charger occupancy
    for (var i = 0; i < chargers.length; i++) {
        chargers[i].car = null;
    }
    updateChargerPositions();
}

// ==========================================
// Theoretical Metrics (FastAPI)
// ==========================================

function fetchTheoreticalMetrics() {
    fetch('/api/metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            c: simParams.c,
            K: simParams.K,
            lambda_rate: simParams.lam,
            mu_rate: simParams.mu
        })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        document.getElementById('theo-rho').innerText = (data.rho * 100).toFixed(2) + '%';
        document.getElementById('theo-lq').innerText = data.Lq.toFixed(2);
        document.getElementById('theo-wq').innerText = data.Wq.toFixed(1) + ' min';
        document.getElementById('theo-pb').innerText = (data.Pb * 100).toFixed(2) + '%';
        document.getElementById('conn-status').innerText = '● Online';
        document.getElementById('conn-status').style.color = '#16a34a';
    })
    .catch(function() {
        document.getElementById('conn-status').innerText = '● Offline';
        document.getElementById('conn-status').style.color = '#dc2626';
    });
}

// ==========================================
// Charger Management
// ==========================================

function updateChargerPositions() {
    var c = simParams.c;

    // Add/remove chargers
    while (chargers.length < c) {
        chargers.push({ id: chargers.length, x: 0, y: 0, car: null });
    }
    while (chargers.length > c) {
        var removed = chargers.pop();
        if (removed.car) removed.car.status = 'leaving';
    }

    // Position them evenly
    var spacing = 100;
    var totalW = c * spacing;
    var startX = width / 2 - totalW / 2 + spacing / 2;
    for (var i = 0; i < chargers.length; i++) {
        chargers[i].x = startX + i * spacing;
        chargers[i].y = height * 0.28;
    }
}

// ==========================================
// Main Draw Loop
// ==========================================

function draw() {
    background(245); // light gray

    drawScene();

    var dt = (deltaTime / 1000.0) * simParams.speed; // sim seconds per frame
    var dtHours = dt / 3600.0;

    simClockSeconds += dt;

    // --- Spawn Logic (Poisson arrivals) ---
    if (nextSpawnDelay <= 0) {
        spawnVehicle();
        nextSpawnDelay = randExp(simParams.lam) * 3600; // hours -> seconds
    }
    nextSpawnDelay -= dt;

    // --- Update vehicles ---
    processVehicles(dtHours);

    // --- Draw chargers ---
    for (var i = 0; i < chargers.length; i++) {
        drawCharger(chargers[i]);
    }

    // --- Draw cars ---
    for (var j = 0; j < cars.length; j++) {
        updateCarVisual(cars[j]);
        drawCar(cars[j]);
    }

    // --- Update HUD ---
    updateHUD();
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
    var colors = ['#7c9cba', '#8fad8f', '#c4937a', '#b8a9c4', '#a0aab4', '#c2b280'];
    return {
        x: -80,
        y: height * 0.72,
        color: colors[Math.floor(Math.random() * colors.length)],
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
            // Try to find an empty charger
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
                // Finish service
                car.status = 'leaving';
                car.charger.car = null;
                car.charger = null;
                statServed++;
                totalWaitTime += car.waitTime;
                servedCountForAvg++;

                // Pull next from queue
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
            if (car.y > height + 120) {
                cars.splice(i, 1);
            }
        }
    }
}

// ==========================================
// Drawing Functions
// ==========================================

function drawScene() {
    // Charging area background
    noStroke();
    fill(238);
    rect(0, 0, width, height * 0.58);

    // Road
    fill(220);
    rect(0, height * 0.58, width, height * 0.42);

    // Road center line
    stroke(190);
    strokeWeight(3);
    for (var x = 0; x < width; x += 50) {
        line(x, height * 0.78, x + 25, height * 0.78);
    }

    // Labels
    noStroke();
    fill(180);
    textSize(11);
    textAlign(CENTER);
    text('CHARGING AREA', width / 2, 20);
    text('QUEUE', width - 80, height * 0.50);

    // Queue zone indicator
    stroke(200);
    strokeWeight(1);
    noFill();
    var qzoneX = width - 160;
    var qzoneY = height * 0.42;
    rect(qzoneX, qzoneY, 140, height * 0.14, 4);
}

function drawCharger(ch) {
    push();
    translate(ch.x, ch.y);

    // Charger body
    fill(255);
    stroke(200);
    strokeWeight(1.5);
    rect(-CHARGER_W / 2, -CHARGER_H / 2, CHARGER_W, CHARGER_H, 4);

    // Screen
    noStroke();
    fill(240);
    rect(-CHARGER_W / 2 + 8, -CHARGER_H / 2 + 8, CHARGER_W - 16, CHARGER_H - 32, 2);

    // Status indicator
    if (ch.car) {
        fill('#dc2626');
    } else {
        fill('#16a34a');
    }
    circle(0, CHARGER_H / 2 - 12, 8);

    // Label
    fill(160);
    noStroke();
    textSize(9);
    textAlign(CENTER);
    text('C' + (ch.id + 1), 0, -CHARGER_H / 2 - 6);

    pop();
}

function drawCar(car) {
    push();
    translate(car.x, car.y);

    // Body
    fill(car.color);
    stroke(150);
    strokeWeight(1);
    rect(-CAR_W / 2, -CAR_H / 2, CAR_W, CAR_H, 5);

    // Windshield
    noStroke();
    fill(220);
    rect(-CAR_W / 2 + 5, -CAR_H / 2 + 8, CAR_W - 10, 14, 2);

    // Rear window
    rect(-CAR_W / 2 + 5, CAR_H / 2 - 20, CAR_W - 10, 12, 2);

    // Wait time label
    if (car.status === 'queueing') {
        fill(100);
        textAlign(CENTER);
        textSize(9);
        text((car.waitTime * 60).toFixed(0) + 'm', 0, -CAR_H / 2 - 8);
    }

    pop();
}

function updateCarVisual(car) {
    var tx = car.x;
    var ty = car.y;

    if (car.status === 'arriving') {
        tx = width * 0.15;
        ty = height * 0.72;
    } else if (car.status === 'queueing') {
        var idx = queue.indexOf(car);
        tx = width - 90 - (idx % 5) * (CAR_W + 8);
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
// HUD Updates
// ==========================================

function updateHUD() {
    document.getElementById('sim-clock').innerText = formatClock(simClockSeconds);
    document.getElementById('stat-arrived').innerText = statArrived;
    document.getElementById('stat-served').innerText = statServed;
    document.getElementById('stat-balked').innerText = statBalked;

    // Live rho
    var busy = 0;
    for (var i = 0; i < chargers.length; i++) {
        if (chargers[i].car !== null) busy++;
    }
    var rho = busy / simParams.c;
    document.getElementById('live-rho').innerText = (rho * 100).toFixed(2) + '%';

    // Live Lq
    document.getElementById('live-lq').innerText = queue.length.toFixed(2);

    // Live Wq
    var avgW = servedCountForAvg > 0 ? (totalWaitTime / servedCountForAvg) * 60 : 0;
    document.getElementById('live-wq').innerText = avgW.toFixed(1) + ' min';

    // Live Pb
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

function pad(n) {
    return n < 10 ? '0' + n : '' + n;
}

// ==========================================
// Utilities
// ==========================================

function randExp(rate) {
    return -Math.log(1.0 - Math.random()) / rate;
}
