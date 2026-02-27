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
const NUM_CHANNELS = 4;
const VOLTAGE_MIN = 0;
const VOLTAGE_MAX = 3.3;
const GRID_LINES = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0];
const CHANNEL_COLORS = ["#2980b9", "#c0392b", "#27ae60", "#8e44ad"];
const RECONNECT_INTERVAL = 2000;

const EXPERIMENT_WORDS = [
  "on", "off", "turn", "start", "stop", "yes", "no", "up", "down", "show",
  "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
  "play", "add", "create", "move", "open", "next", "set", "cancel", "lock", "call",
];
const TRIALS_PER_WORD = 30;
const SPEAK_DURATION = 1000;  // ms
const REST_DURATION = 1000;   // ms
const PREPARE_COUNTDOWN = 3;   // seconds countdown before each word
const COUNTDOWN_FROM = 3;     // seconds

// ============================================================
// State
// ============================================================
const buffers = [];
for (let i = 0; i < NUM_CHANNELS; i++) {
  buffers.push(new RingBuffer(BUFFER_SIZE));
}

let ws = null;
let sampleCount = 0;
let lastRateTime = performance.now();
let displayRate = 0;
let pendingAutoResume = false;

// Manual recording state
let isRecording = false;
let recordingStartTime = null;

// Experiment state
const exp = {
  active: false,
  paused: false,
  words: [],
  trialsPerWord: TRIALS_PER_WORD,
  wordIndex: 0,
  trial: 1,
  phase: "idle", // idle | countdown | prepare | speak | rest | completed | paused
  timer: null,
  completed: {},
  experimentId: null,
};

// ============================================================
// DOM Elements
// ============================================================
const statusEl = document.getElementById("connection-status");
const rateEl = document.getElementById("sample-rate");

// Manual recording
const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const recordingStatusEl = document.getElementById("recording-status");
const elapsedTimeEl = document.getElementById("elapsed-time");

// Experiment setup
const experimentSetupEl = document.getElementById("experiment-setup");
const btnNewExperiment = document.getElementById("btn-new-experiment");
const experimentListEl = document.getElementById("experiment-list");
const subjectIdInput = document.getElementById("subject-id");

// Experiment running
const experimentRunningEl = document.getElementById("experiment-running");
const expSubjectLabelEl = document.getElementById("exp-subject-label");
const expWordProgressEl = document.getElementById("exp-word-progress");
const expTrialProgressEl = document.getElementById("exp-trial-progress");
const expCueEl = document.getElementById("exp-cue");
const expPhaseEl = document.getElementById("exp-phase");
const expWordEl = document.getElementById("exp-word");
const expCountdownEl = document.getElementById("exp-countdown");
const btnPause = document.getElementById("btn-pause");
const btnSkipWord = document.getElementById("btn-skip-word");
const btnEndExperiment = document.getElementById("btn-end-experiment");
const expTotalProgressEl = document.getElementById("exp-total-progress");

// Charts
const voltageEls = [];
const canvases = [];
const contexts = [];
for (let i = 0; i < NUM_CHANNELS; i++) {
  const ch = i + 1;
  voltageEls.push(document.getElementById(`voltage-ch${ch}`));
  const canvas = document.getElementById(`chart-ch${ch}`);
  canvases.push(canvas);
  contexts.push(canvas.getContext("2d"));
}

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
// localStorage helpers
// ============================================================
const LS_KEY_EXPERIMENT = "emg_active_experiment_id";
const LS_KEY_SUBJECT = "emg_subject_id";

function saveActiveExperiment(experimentId) {
  localStorage.setItem(LS_KEY_EXPERIMENT, experimentId);
}

function clearActiveExperiment() {
  localStorage.removeItem(LS_KEY_EXPERIMENT);
}

function getSavedExperimentId() {
  return localStorage.getItem(LS_KEY_EXPERIMENT);
}

function saveSubjectId(id) {
  localStorage.setItem(LS_KEY_SUBJECT, id);
}

function getSavedSubjectId() {
  return localStorage.getItem(LS_KEY_SUBJECT) || "";
}

// Restore subject ID from localStorage
subjectIdInput.value = getSavedSubjectId();

// ============================================================
// WebSocket
// ============================================================
function connect() {
  const wsUrl = `ws://${location.hostname}:8765`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    statusEl.textContent = "Connected";
    statusEl.className = "status connected";
    btnStart.disabled = false;
    btnNewExperiment.disabled = false;

    // Auto-resume if there was an active experiment
    const savedId = getSavedExperimentId();
    if (savedId && !exp.active) {
      pendingAutoResume = true;
      wsSend({ action: "resume_experiment", experiment_id: savedId });
    } else {
      wsSend({ action: "list_experiments" });
    }
  };

  ws.onclose = () => {
    statusEl.textContent = "Disconnected";
    statusEl.className = "status disconnected";
    btnStart.disabled = true;
    btnStop.disabled = true;
    btnNewExperiment.disabled = true;
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
      for (let ch = 0; ch < NUM_CHANNELS; ch++) {
        buffers[ch].push(sample[ch + 1]);
      }
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
  } else if (msg.type === "experiment_list") {
    renderExperimentList(msg.experiments);
  } else if (msg.type === "experiment_ready") {
    const wasAutoResume = pendingAutoResume;
    pendingAutoResume = false;
    onExperimentReady(msg.progress, wasAutoResume);
  } else if (msg.type === "experiment_error") {
    // Saved experiment not found on server, clear localStorage
    pendingAutoResume = false;
    clearActiveExperiment();
    wsSend({ action: "list_experiments" });
  }
}

connect();

// ============================================================
// Manual Recording Controls
// ============================================================
btnStart.addEventListener("click", () => {
  wsSend({ action: "start_recording" });
});
btnStop.addEventListener("click", () => {
  wsSend({ action: "stop_recording" });
});

// ============================================================
// Experiment: Setup & List
// ============================================================
function renderExperimentList(experiments) {
  experimentListEl.innerHTML = "";
  // Show only incomplete experiments
  const incomplete = experiments.filter((e) => e.done_trials < e.total_trials);
  for (const e of incomplete) {
    const div = document.createElement("div");
    div.className = "exp-list-item";
    const pct = Math.round((e.done_trials / e.total_trials) * 100);
    const subLabel = e.subject_id ? `Subject: ${e.subject_id} | ` : "";
    div.innerHTML = `
      <div class="exp-info">
        <strong>${subLabel}${e.experiment_id}</strong><br>
        ${e.done_trials}/${e.total_trials} trials (${pct}%)
      </div>
    `;
    const btn = document.createElement("button");
    btn.textContent = "Resume";
    btn.addEventListener("click", () => {
      wsSend({ action: "resume_experiment", experiment_id: e.experiment_id });
    });
    div.appendChild(btn);
    experimentListEl.appendChild(div);
  }
}

btnNewExperiment.addEventListener("click", () => {
  const subjectId = subjectIdInput.value.trim();
  if (!subjectId) {
    subjectIdInput.focus();
    subjectIdInput.style.borderColor = "#e74c3c";
    return;
  }
  subjectIdInput.style.borderColor = "";
  saveSubjectId(subjectId);
  wsSend({
    action: "create_experiment",
    words: EXPERIMENT_WORDS,
    trials_per_word: TRIALS_PER_WORD,
    subject_id: subjectId,
  });
});

function onExperimentReady(progress, autoResumed) {
  exp.active = true;
  exp.paused = false;
  exp.words = progress.words;
  exp.trialsPerWord = progress.trials_per_word;
  exp.completed = progress.completed || {};
  exp.experimentId = progress.experiment_id;
  exp.subjectId = progress.subject_id || "";

  // Persist to localStorage for reload recovery
  saveActiveExperiment(exp.experimentId);

  // Show subject label
  expSubjectLabelEl.textContent = exp.subjectId
    ? `Subject: ${exp.subjectId}  |  ${exp.experimentId}`
    : exp.experimentId;

  // Find first incomplete word
  exp.wordIndex = 0;
  for (let i = 0; i < exp.words.length; i++) {
    const done = exp.completed[exp.words[i]] || 0;
    if (done < exp.trialsPerWord) {
      exp.wordIndex = i;
      exp.trial = done + 1;
      break;
    }
    if (i === exp.words.length - 1) {
      // All done
      exp.phase = "completed";
      clearActiveExperiment();
      showExperimentUI();
      updateExpDisplay();
      return;
    }
  }

  showExperimentUI();

  if (autoResumed) {
    // Reload recovery: show paused state, wait for user to press Resume
    exp.paused = true;
    exp.phase = "paused";
    btnPause.textContent = "Resume";
    updateExpDisplay();
  } else {
    startCountdown();
  }
}

function showExperimentUI() {
  experimentSetupEl.style.display = "none";
  experimentRunningEl.style.display = "flex";
}

function hideExperimentUI() {
  experimentSetupEl.style.display = "flex";
  experimentRunningEl.style.display = "none";
  // Refresh list
  wsSend({ action: "list_experiments" });
}

// ============================================================
// Experiment: Protocol State Machine
// ============================================================
function clearExpTimer() {
  if (exp.timer) {
    clearTimeout(exp.timer);
    exp.timer = null;
  }
}

function startCountdown() {
  exp.phase = "countdown";
  let count = COUNTDOWN_FROM;
  updateExpDisplay(count);

  function tick() {
    if (exp.paused) return;
    count--;
    if (count <= 0) {
      startPrepare();
    } else {
      updateExpDisplay(count);
      exp.timer = setTimeout(tick, 1000);
    }
  }
  exp.timer = setTimeout(tick, 1000);
}

function startPrepare() {
  exp.phase = "prepare";
  let count = PREPARE_COUNTDOWN;
  updateExpDisplay(count);

  function tick() {
    if (exp.paused) return;
    count--;
    if (count <= 0) {
      startSpeak();
    } else {
      updateExpDisplay(count);
      exp.timer = setTimeout(tick, 1000);
    }
  }
  exp.timer = setTimeout(tick, 1000);
}

function startSpeak() {
  exp.phase = "speak";
  updateExpDisplay();

  // Tell server to start buffering trial data
  const word = exp.words[exp.wordIndex];
  wsSend({ action: "trial_start", word: word, trial: exp.trial });

  exp.timer = setTimeout(() => {
    if (!exp.paused) endSpeak();
  }, SPEAK_DURATION);
}

function endSpeak() {
  // Tell server to save the trial
  wsSend({ action: "trial_end" });

  exp.phase = "rest";
  updateExpDisplay();

  exp.timer = setTimeout(() => {
    if (!exp.paused) advanceTrial();
  }, REST_DURATION);
}

function advanceTrial() {
  const word = exp.words[exp.wordIndex];

  // Update local completed tracking
  exp.completed[word] = exp.trial;

  exp.trial++;
  if (exp.trial > exp.trialsPerWord) {
    // Word finished, move to next
    exp.wordIndex++;
    exp.trial = 1;

    // Skip already-completed words
    while (exp.wordIndex < exp.words.length) {
      const w = exp.words[exp.wordIndex];
      const done = exp.completed[w] || 0;
      if (done < exp.trialsPerWord) {
        exp.trial = done + 1;
        break;
      }
      exp.wordIndex++;
    }

    if (exp.wordIndex >= exp.words.length) {
      exp.phase = "completed";
      clearActiveExperiment();
      updateExpDisplay();
      return;
    }

    // Prepare for next word
    startPrepare();
  } else {
    // Next trial of same word
    startSpeak();
  }
}

function updateExpDisplay(countdownVal) {
  const word = exp.words[exp.wordIndex] || "";
  const totalWords = exp.words.length;
  const totalDone = Object.values(exp.completed).reduce((a, b) => a + b, 0);
  const totalTrials = totalWords * exp.trialsPerWord;

  expWordProgressEl.textContent = `Word ${exp.wordIndex + 1}/${totalWords}`;
  expTrialProgressEl.textContent = `Trial ${exp.trial}/${exp.trialsPerWord}`;
  expTotalProgressEl.textContent = `Total: ${totalDone}/${totalTrials} (${Math.round(totalDone / totalTrials * 100)}%)`;

  // Reset classes
  expCueEl.className = "experiment-cue";
  expPhaseEl.className = "exp-phase";
  expWordEl.textContent = "";
  expCountdownEl.textContent = "";
  expPhaseEl.textContent = "";

  switch (exp.phase) {
    case "countdown":
      expCueEl.classList.add("countdown");
      expPhaseEl.textContent = "Starting...";
      expCountdownEl.textContent = countdownVal || "";
      break;
    case "prepare":
      expCueEl.classList.add("prepare");
      expPhaseEl.textContent = "Next Word";
      expPhaseEl.classList.add("prepare");
      expWordEl.textContent = word;
      expCountdownEl.textContent = countdownVal || "";
      break;
    case "speak":
      expCueEl.classList.add("speak");
      expPhaseEl.textContent = "Speak";
      expPhaseEl.classList.add("speak");
      expWordEl.textContent = word;
      break;
    case "rest":
      expCueEl.classList.add("rest");
      expPhaseEl.textContent = "Rest";
      expPhaseEl.classList.add("rest");
      expWordEl.textContent = word;
      break;
    case "completed":
      expCueEl.classList.add("rest");
      expPhaseEl.textContent = "Complete!";
      expWordEl.textContent = "";
      expCountdownEl.textContent = "";
      expTotalProgressEl.textContent = `All ${totalTrials} trials completed!`;
      break;
    case "paused":
      expCueEl.classList.add("rest");
      expPhaseEl.textContent = "Paused";
      expPhaseEl.classList.add("rest");
      expWordEl.textContent = word;
      break;
  }
}

// ============================================================
// Experiment: Pause / Resume / Skip
// ============================================================
btnPause.addEventListener("click", () => {
  if (!exp.active) return;

  if (exp.paused) {
    // Resume
    exp.paused = false;
    btnPause.textContent = "Pause";

    // If we were mid-trial (speak phase), cancel that trial and restart it
    if (exp.phase === "speak") {
      wsSend({ action: "trial_cancel" });
    }
    // Restart from current position
    startPrepare();
  } else {
    // Pause
    exp.paused = true;
    clearExpTimer();
    btnPause.textContent = "Resume";

    // If we're in speak phase, cancel the current trial
    if (exp.phase === "speak") {
      wsSend({ action: "trial_cancel" });
    }

    exp.phase = "paused";
    updateExpDisplay();
  }
});

btnSkipWord.addEventListener("click", () => {
  if (!exp.active || exp.phase === "completed") return;

  clearExpTimer();
  if (exp.phase === "speak") {
    wsSend({ action: "trial_cancel" });
  }

  // Move to next word
  exp.wordIndex++;
  exp.trial = 1;

  // Skip already-completed words
  while (exp.wordIndex < exp.words.length) {
    const w = exp.words[exp.wordIndex];
    const done = exp.completed[w] || 0;
    if (done < exp.trialsPerWord) {
      exp.trial = done + 1;
      break;
    }
    exp.wordIndex++;
  }

  if (exp.wordIndex >= exp.words.length) {
    exp.phase = "completed";
    updateExpDisplay();
    return;
  }

  if (exp.paused) {
    exp.phase = "paused";
    updateExpDisplay();
  } else {
    startPrepare();
  }
});

btnEndExperiment.addEventListener("click", () => {
  if (!exp.active) return;
  if (!confirm("End this experiment and return to setup?\n(Progress is saved. You can resume later from the list.)")) {
    return;
  }

  clearExpTimer();
  if (exp.phase === "speak") {
    wsSend({ action: "trial_cancel" });
  }

  exp.active = false;
  exp.paused = false;
  exp.phase = "idle";
  btnPause.textContent = "Pause";
  clearActiveExperiment();
  hideExperimentUI();
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

  // Manual recording elapsed
  if (isRecording && recordingStartTime !== null) {
    elapsedTimeEl.textContent = formatElapsed(now - recordingStartTime);
  }

  // Voltage displays
  for (let i = 0; i < NUM_CHANNELS; i++) {
    voltageEls[i].textContent = `${buffers[i].latest().toFixed(3)} V`;
  }

  // Charts
  for (let i = 0; i < NUM_CHANNELS; i++) {
    drawChart(contexts[i], canvases[i], buffers[i], CHANNEL_COLORS[i]);
  }

  requestAnimationFrame(render);
}

requestAnimationFrame(render);
