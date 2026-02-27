"use strict";

// ============================================================
// Ring Buffer
// ============================================================
class RingBuffer {
  constructor(capacity) {
    this.capacity = capacity;
    this.buffer = new Float32Array(capacity);
    this.head = 0;
    this.length = 0;
  }
  push(value) {
    this.buffer[this.head] = value;
    this.head = (this.head + 1) % this.capacity;
    if (this.length < this.capacity) this.length++;
  }
  get(index) {
    const start = (this.head - this.length + this.capacity) % this.capacity;
    return this.buffer[(start + index) % this.capacity];
  }
  latest() {
    if (this.length === 0) return 0;
    return this.buffer[(this.head - 1 + this.capacity) % this.capacity];
  }
}

// ============================================================
// Constants
// ============================================================
const BUFFER_SIZE = 3000;
const NUM_CHANNELS = 2;
const VOLTAGE_MIN = 0;
const VOLTAGE_MAX = 3.3;
const GRID_LINES = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0];
const CHANNEL_COLORS = ["#2980b9", "#e67e22"]; // EMG: blue, Pressure: orange
const RECONNECT_INTERVAL = 2000;

// ============================================================
// State
// ============================================================
const buffers = [new RingBuffer(BUFFER_SIZE), new RingBuffer(BUFFER_SIZE)];

let ws = null;
let sampleCount = 0;
let lastRateTime = performance.now();
let displayRate = 0;

// Recording state
let isRecording = false;
let recordingStartTime = null;

// Latest pressure extra values
let latestPressureRaw = 0;
let latestPressureForce = 0;

// ============================================================
// DOM Elements
// ============================================================
const statusEl = document.getElementById("connection-status");
const rateEl = document.getElementById("sample-rate");
const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const recordingStatusEl = document.getElementById("recording-status");
const elapsedTimeEl = document.getElementById("elapsed-time");

const voltageEmgEl = document.getElementById("voltage-emg");
const rawPressureEl = document.getElementById("raw-pressure");
const voltagePressureEl = document.getElementById("voltage-pressure");
const forcePressureEl = document.getElementById("force-pressure");

const canvasEmg = document.getElementById("chart-emg");
const canvasPressure = document.getElementById("chart-pressure");
const ctxEmg = canvasEmg.getContext("2d");
const ctxPressure = canvasPressure.getContext("2d");

const canvases = [canvasEmg, canvasPressure];
const contexts = [ctxEmg, ctxPressure];

// ============================================================
// Canvas Setup
// ============================================================
function resizeCanvas(canvas, ctx) {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);
}

function resizeAll() {
  for (let i = 0; i < NUM_CHANNELS; i++) {
    resizeCanvas(canvases[i], contexts[i]);
  }
}
window.addEventListener("resize", resizeAll);
resizeAll();

// ============================================================
// Helpers
// ============================================================
function formatElapsed(ms) {
  const totalMs = Math.floor(ms);
  const h = Math.floor(totalMs / 3600000);
  const m = Math.floor((totalMs % 3600000) / 60000);
  const s = Math.floor((totalMs % 60000) / 1000);
  const millis = totalMs % 1000;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(millis).padStart(3, "0")}`;
}

function wsSend(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(obj));
  }
}

// ============================================================
// WebSocket
// ============================================================
function connect() {
  const wsUrl = `ws://${location.hostname}:8766`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    statusEl.textContent = "Connected";
    statusEl.className = "status connected";
    btnStart.disabled = false;
  };

  ws.onclose = () => {
    statusEl.textContent = "Disconnected";
    statusEl.className = "status disconnected";
    btnStart.disabled = true;
    btnStop.disabled = true;
    ws = null;
    setTimeout(connect, RECONNECT_INTERVAL);
  };

  ws.onerror = () => {
    if (ws) ws.close();
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    handleMessage(msg);
  };
}

function handleMessage(msg) {
  if (msg.type === "data") {
    const samples = msg.samples;
    for (let s = 0; s < samples.length; s++) {
      const sample = samples[s];
      // sample: [time, emg_v, pressure_raw, pressure_v, pressure_force_n]
      buffers[0].push(sample[1]);       // EMG voltage
      buffers[1].push(sample[3]);       // Pressure voltage
      latestPressureRaw = sample[2];    // Pressure raw ADC
      latestPressureForce = sample[4];  // Pressure force (N)
      sampleCount++;
    }
  } else if (msg.type === "recording_started") {
    isRecording = true;
    recordingStartTime = performance.now();
    btnStart.disabled = true;
    btnStop.disabled = false;
    recordingStatusEl.textContent = `Rec: ${msg.filename}`;
    elapsedTimeEl.classList.add("active");
  } else if (msg.type === "recording_stopped") {
    isRecording = false;
    recordingStartTime = null;
    btnStart.disabled = false;
    btnStop.disabled = true;
    recordingStatusEl.textContent = "";
    elapsedTimeEl.classList.remove("active");
    elapsedTimeEl.textContent = "00:00:00.000";
  }
}

connect();

// ============================================================
// Recording Controls
// ============================================================
btnStart.addEventListener("click", () => {
  wsSend({ action: "start_recording" });
});
btnStop.addEventListener("click", () => {
  wsSend({ action: "stop_recording" });
});

// ============================================================
// Chart Rendering
// ============================================================
function drawChart(ctx, canvas, buffer, color) {
  const w = canvas.getBoundingClientRect().width;
  const h = canvas.getBoundingClientRect().height;
  const range = VOLTAGE_MAX - VOLTAGE_MIN;

  ctx.clearRect(0, 0, w, h);

  // Grid
  ctx.strokeStyle = "#c8c8c8";
  ctx.lineWidth = 0.5;
  ctx.font = "10px monospace";
  ctx.fillStyle = "#888";
  for (let gi = 0; gi < GRID_LINES.length; gi++) {
    const v = GRID_LINES[gi];
    const y = h - ((v - VOLTAGE_MIN) / range) * h;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
    ctx.fillText(`${v.toFixed(1)}V`, 2, y - 2);
  }

  if (buffer.length === 0) return;

  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  const len = buffer.length;
  const step = w / BUFFER_SIZE;
  for (let i = 0; i < len; i++) {
    const x = (BUFFER_SIZE - len + i) * step;
    const v = buffer.get(i);
    const y = h - ((v - VOLTAGE_MIN) / range) * h;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
}

// ============================================================
// Main Render Loop
// ============================================================
function render() {
  const now = performance.now();

  // Sample rate
  if (now - lastRateTime >= 500) {
    displayRate = Math.round(sampleCount / ((now - lastRateTime) / 1000));
    sampleCount = 0;
    lastRateTime = now;
    rateEl.textContent = `${displayRate} Hz`;
  }

  // Recording elapsed
  if (isRecording && recordingStartTime !== null) {
    elapsedTimeEl.textContent = formatElapsed(now - recordingStartTime);
  }

  // Voltage displays
  voltageEmgEl.textContent = `${buffers[0].latest().toFixed(3)} V`;
  rawPressureEl.textContent = `raw: ${latestPressureRaw}`;
  voltagePressureEl.textContent = `${buffers[1].latest().toFixed(3)} V`;
  forcePressureEl.textContent = `${latestPressureForce.toFixed(2)} N`;

  // Charts
  drawChart(ctxEmg, canvasEmg, buffers[0], CHANNEL_COLORS[0]);
  drawChart(ctxPressure, canvasPressure, buffers[1], CHANNEL_COLORS[1]);

  requestAnimationFrame(render);
}

requestAnimationFrame(render);
