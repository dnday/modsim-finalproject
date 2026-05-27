// ==========================================
// SPKLU p5.js Real-time Interactive Engine (Clean Theme)
// ==========================================

// Global state
let cars = [];
let chargers = [];
let queue = [];
let timeScale = 10; 
let nextSpawnDelay = 0;

// Stats
let statArrived = 0;
let statServed = 0;
let statBalked = 0;
let simClockSeconds = 0;
let totalWaitTime = 0;
let servedCountForAvg = 0;

// Base starting time: 06:00 AM (in seconds)
const STARTING_TIME_SECONDS = 6 * 3600;

// Params from UI
var param_c = 2;
var param_K = 10;
var param_lam = 5.0; // per hour
var param_mu = 2.0;  // per hour

// Graphics config
const CHARGER_W = 60;
const CHARGER_H = 80;
const CAR_W = 40;
const CAR_H = 70;

function setup() {
    let canvas = createCanvas(windowWidth, windowHeight);
    canvas.parent('canvas-container');
    
    bindControls();
    updateTheoreticalMetrics();
    updateChargers();
}

function bindControls() {
    const bindSlider = (idSlider, idVal, varName, callback) => {
        let el = document.getElementById(idSlider);
        let valEl = document.getElementById(idVal);
        el.addEventListener('input', (e) => {
            let val = parseFloat(e.target.value);
            valEl.innerText = val.toFixed(idSlider.includes('lam') || idSlider.includes('mu') ? 1 : 0);
            window[varName] = val;
            if(callback) callback();
        });
    };
    
    bindSlider('slider-c', 'val-c', 'param_c', () => {
        updateChargers();
        updateTheoreticalMetrics();
    });
    bindSlider('slider-k', 'val-k', 'param_K', updateTheoreticalMetrics);
    bindSlider('slider-lam', 'val-lam', 'param_lam', updateTheoreticalMetrics);
    bindSlider('slider-mu', 'val-mu', 'param_mu', () => {
        document.getElementById('val-mu-min').innerText = (60 / param_mu).toFixed(0);
        updateTheoreticalMetrics();
    });
    bindSlider('slider-speed', 'val-speed', 'timeScale', () => {
        document.getElementById('val-speed').innerText = timeScale + 'x';
    });
}

function windowResized() {
    resizeCanvas(windowWidth, windowHeight);
    updateChargers();
}

async function updateTheoreticalMetrics() {
    try {
        const response = await fetch('/api/metrics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                c: param_c,
                K: param_K,
                lambda_rate: param_lam,
                mu_rate: param_mu
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            document.getElementById('theo-rho').innerText = (data.rho * 100).toFixed(2) + '%';
            document.getElementById('theo-lq').innerText = data.Lq.toFixed(2);
            document.getElementById('theo-wq').innerText = data.Wq.toFixed(1) + ' min';
            document.getElementById('theo-pb').innerText = (data.Pb * 100).toFixed(2) + '%';
        }
    } catch (e) {
        console.error("API Error", e);
        document.getElementById('conn-status').innerText = "Offline (No API)";
        document.getElementById('conn-status').className = "text-red-500 font-medium";
    }
}

function randomExponential(rate) {
    return -Math.log(1.0 - Math.random()) / rate;
}

function updateChargers() {
    while(chargers.length < param_c) {
        chargers.push(new Charger(chargers.length));
    }
    while(chargers.length > param_c) {
        let removed = chargers.pop();
        if (removed.car) {
            removed.car.status = 'leaving';
        }
    }
    
    let spacing = 100;
    let totalW = param_c * spacing;
    let startX = width/2 - totalW/2 + spacing/2;
    for(let i=0; i<chargers.length; i++) {
        chargers[i].x = startX + i*spacing;
        chargers[i].y = height * 0.3;
    }
}

function draw() {
    background('#f8fafc'); // slate-50
    
    drawEnvironment();
    
    let dt = (deltaTime / 1000.0) * timeScale;
    let dtHours = dt / 3600.0;
    
    simClockSeconds += dt;
    updateLiveUI();

    if (nextSpawnDelay <= 0) {
        statArrived++;
        
        let systemSize = queue.length + chargers.filter(c => c.car != null).length;
        
        let newCar = new Car();
        cars.push(newCar);
        
        if (systemSize >= param_K) {
            newCar.status = 'balking';
            statBalked++;
        } else {
            newCar.status = 'arriving';
        }
        
        let nextArrivalHours = randomExponential(param_lam);
        nextSpawnDelay = nextArrivalHours * 3600;
    }
    nextSpawnDelay -= dt;
    
    updateSystem(dtHours);
    
    for(let c of chargers) c.draw();
    for(let c of cars) c.draw();
}

function drawEnvironment() {
    push();
    // Parking area
    fill('#f1f5f9'); // slate-100
    noStroke();
    rect(0, height*0.1, width, height*0.4);
    
    // Road
    fill('#e2e8f0'); // slate-200
    rect(0, height*0.6, width, height*0.4);
    
    // Road dashes
    stroke('#94a3b8'); // slate-400
    strokeWeight(4);
    for(let i=0; i<width; i+=60) {
        line(i, height*0.8, i+30, height*0.8);
    }
    pop();
}

function updateSystem(dtHours) {
    for (let i = cars.length - 1; i >= 0; i--) {
        let car = cars[i];
        
        if (car.status === 'arriving') {
            let emptyCharger = chargers.find(c => c.car === null);
            if (emptyCharger) {
                emptyCharger.car = car;
                car.status = 'charging';
                car.charger = emptyCharger;
                car.serviceTimeRemaining = randomExponential(param_mu);
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
                    let nextCar = queue.shift();
                    let emptyCharger = chargers.find(c => c.car === null);
                    if (emptyCharger) {
                        emptyCharger.car = nextCar;
                        nextCar.status = 'charging';
                        nextCar.charger = emptyCharger;
                        nextCar.serviceTimeRemaining = randomExponential(param_mu);
                    }
                }
            }
        }
        
        if (car.status === 'leaving' || car.status === 'balking') {
            car.y += 5; 
            if (car.y > height + 100) {
                cars.splice(i, 1);
            }
        }
        
        car.updateVisuals();
    }
}

// FORMAT TIME AS TIME OF DAY (HH:MM:SS)
function formatTimeOfDay(simSecs) {
    let totalSecs = STARTING_TIME_SECONDS + Math.floor(simSecs);
    let h = Math.floor(totalSecs / 3600) % 24;
    let m = Math.floor((totalSecs % 3600) / 60);
    let s = totalSecs % 60;
    return `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
}

function updateLiveUI() {
    document.getElementById('sim-clock').innerText = formatTimeOfDay(simClockSeconds);
    document.getElementById('stat-arrived').innerText = statArrived;
    document.getElementById('stat-served').innerText = statServed;
    document.getElementById('stat-balked').innerText = statBalked;
    
    let activeChargers = chargers.filter(c => c.car != null).length;
    let rho = activeChargers / param_c;
    document.getElementById('live-rho').innerText = (rho * 100).toFixed(2) + '%';
    document.getElementById('live-lq').innerText = queue.length.toFixed(2);
    
    let avgWait = servedCountForAvg > 0 ? (totalWaitTime / servedCountForAvg) * 60 : 0;
    document.getElementById('live-wq').innerText = avgWait.toFixed(1) + ' min';
    
    let pb = statArrived > 0 ? (statBalked / statArrived) : 0;
    document.getElementById('live-pb').innerText = (pb * 100).toFixed(2) + '%';
}

// ------------------------------------------
// Classes
// ------------------------------------------

class Charger {
    constructor(id) {
        this.id = id;
        this.x = 0;
        this.y = 0;
        this.car = null;
    }
    
    draw() {
        push();
        translate(this.x, this.y);
        
        // Base - Clean white
        fill('#ffffff');
        stroke('#cbd5e1'); // slate-300
        strokeWeight(2);
        rect(-CHARGER_W/2, -CHARGER_H/2, CHARGER_W, CHARGER_H, 4);
        
        // Screen
        fill('#f1f5f9'); // slate-100
        noStroke();
        rect(-CHARGER_W/2 + 10, -CHARGER_H/2 + 10, CHARGER_W - 20, CHARGER_H - 40, 2);
        
        // Status light
        if (this.car) {
            fill('#ef4444'); // red-500
            circle(0, CHARGER_H/2 - 15, 8);
            
            // Charging cable
            stroke('#64748b'); // slate-500
            strokeWeight(3);
            noFill();
            bezier(-CHARGER_W/2, 0, -CHARGER_W, 20, -CAR_W, 20, -CAR_W/2, 40);
        } else {
            fill('#22c55e'); // green-500
            circle(0, CHARGER_H/2 - 15, 8);
        }
        
        pop();
    }
}

class Car {
    constructor() {
        this.x = -100;
        this.y = height * 0.7;
        
        // Muted pastel colors for cars
        const hues = [
            '#93c5fd', // blue-300
            '#86efac', // green-300
            '#fca5a5', // red-300
            '#fcd34d', // amber-300
            '#d8b4fe', // purple-300
            '#cbd5e1'  // slate-300
        ];
        this.color = hues[Math.floor(Math.random() * hues.length)];
        
        this.status = 'spawning'; 
        this.charger = null;
        this.waitTime = 0;
        this.serviceTimeRemaining = 0;
    }
    
    updateVisuals() {
        let targetX = this.x;
        let targetY = this.y;
        
        if (this.status === 'arriving') {
            targetX = 100;
            targetY = height * 0.7;
        } else if (this.status === 'queueing') {
            let qIdx = queue.indexOf(this);
            targetX = width - 100 - (qIdx * (CAR_W + 15));
            targetY = height * 0.5;
        } else if (this.status === 'charging' && this.charger) {
            targetX = this.charger.x;
            targetY = this.charger.y + CHARGER_H/2 + CAR_H/2 + 15;
        } else if (this.status === 'balking') {
            targetX = width + 100;
            targetY = height * 0.7;
        } else if (this.status === 'leaving') {
            targetY = height + 100;
        }
        
        this.x = lerp(this.x, targetX, 0.1);
        this.y = lerp(this.y, targetY, 0.1);
    }
    
    draw() {
        push();
        translate(this.x, this.y);
        
        // Body
        fill(this.color);
        stroke('#64748b'); // slate-500
        strokeWeight(1);
        rect(-CAR_W/2, -CAR_H/2, CAR_W, CAR_H, 6);
        
        // Windows
        fill('#e2e8f0'); // slate-200
        noStroke();
        rect(-CAR_W/2 + 6, -CAR_H/2 + 12, CAR_W - 12, CAR_H - 24, 2);
        
        // Wait time
        if (this.status === 'queueing' || this.status === 'charging') {
            fill('#475569'); // slate-600
            textAlign(CENTER);
            textSize(10);
            text((this.waitTime * 60).toFixed(0) + 'm', 0, -CAR_H/2 - 6);
        }
        
        pop();
    }
}
