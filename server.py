#!/usr/bin/env python3
"""EMG 4ch real-time visualization server.

Serial reader -> CSV writer + WebSocket broadcaster -> Browser frontend.
Includes experiment mode for structured silent speech data collection.
"""

import argparse
import asyncio
import csv
import json
import math
import os
import random
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import serial
from aiohttp import web
import websockets


def load_config(path):
    with open(path) as f:
        return json.load(f)


DEFAULT_CONFIG = {
    "serial_port": "/dev/tty.usbmodem101",
    "baud_rate": 115200,
    "http_port": 8080,
    "ws_port": 8765,
    "voltage_reference": 3.3,
    "adc_resolution": 1023,
    "num_channels": 4,
    "output_dir": "output",
}


class SerialReader:
    """Reads 4ch hex EMG data from serial port in a separate thread."""

    def __init__(self, config, data_queue, mock=False, port_override=None):
        self.config = config
        self.data_queue = data_queue
        self.mock = mock
        self.port = port_override or config["serial_port"]
        self.baud = config["baud_rate"]
        self.vref = config["voltage_reference"]
        self.adc_max = config["adc_resolution"]
        self.running = False
        self.thread = None
        self.start_time = None

    def start(self):
        self.running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _run(self):
        if self.mock:
            self._run_mock()
        else:
            self._run_serial()

    def _run_serial(self):
        try:
            ser = serial.Serial(self.port, self.baud, timeout=1)
            print(f"Serial port opened: {self.port} @ {self.baud} baud")
        except serial.SerialException as e:
            print(f"Failed to open serial port: {e}")
            self.running = False
            return

        sample_count = 0
        error_count = 0
        try:
            while self.running:
                line = ser.readline()
                if not line:
                    continue
                try:
                    text = line.strip().decode("utf-8")
                    if not text:
                        continue

                    # Auto-detect 3ch (9 hex chars) or 4ch (12 hex chars)
                    if len(text) >= 12:
                        raw1 = int(text[0:3], 16)
                        raw2 = int(text[3:6], 16)
                        raw3 = int(text[6:9], 16)
                        raw4 = int(text[9:12], 16)
                    elif len(text) >= 9:
                        raw1 = int(text[0:3], 16)
                        raw2 = int(text[3:6], 16)
                        raw3 = int(text[6:9], 16)
                        raw4 = 0
                    else:
                        error_count += 1
                        if error_count <= 5:
                            print(f"Short line ({len(text)} chars): {repr(text)}")
                        continue

                    t = time.time() - self.start_time
                    v1 = raw1 * self.vref / self.adc_max
                    v2 = raw2 * self.vref / self.adc_max
                    v3 = raw3 * self.vref / self.adc_max
                    v4 = raw4 * self.vref / self.adc_max

                    sample = (t, v1, v2, v3, v4)
                    self.data_queue.append(sample)

                    sample_count += 1
                    if sample_count == 1:
                        print(f"First sample received: {text} -> [{v1:.3f}, {v2:.3f}, {v3:.3f}, {v4:.3f}]V")
                    if sample_count % 1000 == 0:
                        print(f"Samples received: {sample_count}")
                except (ValueError, IndexError) as e:
                    error_count += 1
                    if error_count <= 5:
                        print(f"Parse error: {repr(text)} -> {e}")
                    continue
        finally:
            ser.close()
            print(f"Serial port closed (total samples: {sample_count}, errors: {error_count})")

    def _run_mock(self):
        """Generate mock EMG data simulating silent speech facial muscles."""
        print("Mock mode: generating synthetic facial EMG data (silent speech)")
        interval = 0.001  # 1ms = 1kHz

        # Speech cycle: ~3s utterance + ~1.5s rest
        cycle_period = 4.5
        utterance_duration = 3.0

        buccinator_bursts = [(0.05, 0.25, 0.7), (0.35, 0.20, 0.9), (0.60, 0.30, 0.6)]
        orbicularis_bursts = [(0.0, 0.15, 1.0), (0.30, 0.15, 0.8), (0.55, 0.20, 1.1), (0.80, 0.15, 0.7)]
        depressor_bursts = [(0.10, 0.20, 0.6), (0.45, 0.25, 0.8), (0.75, 0.20, 0.5)]
        mentalis_bursts = [(0.02, 0.18, 0.5), (0.25, 0.15, 0.7), (0.50, 0.20, 0.9), (0.78, 0.18, 0.6)]

        def envelope(t_in_utterance, bursts):
            env = 0.0
            for start_f, dur_f, peak in bursts:
                start = start_f * utterance_duration
                dur = dur_f * utterance_duration
                mid = start + dur / 2
                sigma = dur / 4
                env += peak * math.exp(-0.5 * ((t_in_utterance - mid) / sigma) ** 2)
            return env

        def emg_signal(env_val, baseline=0.15, noise_floor=0.05):
            activation_noise = random.gauss(0, 1) * env_val * 0.4
            base_noise = random.gauss(0, noise_floor)
            return baseline + abs(activation_noise) + abs(base_noise)

        while self.running:
            t = time.time() - self.start_time
            cycle_t = t % cycle_period

            if cycle_t < utterance_duration:
                env1 = envelope(cycle_t, buccinator_bursts)
                env2 = envelope(cycle_t, orbicularis_bursts)
                env3 = envelope(cycle_t, depressor_bursts)
                env4 = envelope(cycle_t, mentalis_bursts)
            else:
                env1 = env2 = env3 = env4 = 0.0

            v1 = emg_signal(env1, baseline=0.15, noise_floor=0.04)
            v2 = emg_signal(env2, baseline=0.12, noise_floor=0.04)
            v3 = emg_signal(env3, baseline=0.10, noise_floor=0.03)
            v4 = emg_signal(env4, baseline=0.13, noise_floor=0.04)

            v1 = max(0, min(3.3, v1))
            v2 = max(0, min(3.3, v2))
            v3 = max(0, min(3.3, v3))
            v4 = max(0, min(3.3, v4))

            sample = (t, v1, v2, v3, v4)
            self.data_queue.append(sample)
            time.sleep(interval)


class CSVWriter:
    """Writes EMG samples to CSV files in the output directory."""

    def __init__(self, config):
        self.output_dir = Path(config["output_dir"])
        self.output_dir.mkdir(exist_ok=True)
        self.file = None
        self.writer = None
        self.recording = False
        self.filename = None

    def start_recording(self):
        if self.recording:
            return self.filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.filename = f"{timestamp}.csv"
        filepath = self.output_dir / self.filename
        self.file = open(filepath, "w", newline="")
        self.writer = csv.writer(self.file, lineterminator="\n")
        self.writer.writerow(["time", "ch1", "ch2", "ch3", "ch4"])
        self.recording = True
        print(f"Recording started: {filepath}")
        return self.filename

    def stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        if self.file:
            self.file.close()
            self.file = None
            self.writer = None
        print(f"Recording stopped: {self.filename}")

    def write_samples(self, samples):
        if not self.recording or not self.writer:
            return
        for sample in samples:
            self.writer.writerow([f"{sample[0]:.4f}"] + [f"{v:.6f}" for v in sample[1:]])
        self.file.flush()

    def close(self):
        self.stop_recording()


class ExperimentManager:
    """Manages structured data collection experiments for silent speech."""

    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.experiment_id = None
        self.experiment_dir = None
        self.trial_buffer = []
        self.recording_trial = False
        self.current_word = None
        self.current_trial = None

    def create(self, words, trials_per_word, subject_id=""):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if subject_id:
            self.experiment_id = f"{subject_id}_{timestamp}"
        else:
            self.experiment_id = timestamp
        self.experiment_dir = self.output_dir / f"experiment_{self.experiment_id}"
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        (self.experiment_dir / "trials").mkdir(exist_ok=True)

        progress = {
            "experiment_id": self.experiment_id,
            "subject_id": subject_id,
            "created_at": datetime.now().isoformat(),
            "words": words,
            "trials_per_word": trials_per_word,
            "completed": {},
        }
        self._save_progress(progress)
        print(f"Experiment created: {self.experiment_dir} (subject: {subject_id})")
        return progress

    def resume(self, experiment_id):
        self.experiment_id = experiment_id
        self.experiment_dir = self.output_dir / f"experiment_{experiment_id}"
        if not self.experiment_dir.exists():
            return None
        progress = self._load_progress()
        print(f"Experiment resumed: {self.experiment_dir}")
        return progress

    def list_experiments(self):
        experiments = []
        for d in sorted(self.output_dir.glob("experiment_*")):
            pf = d / "progress.json"
            if pf.exists():
                try:
                    with open(pf) as f:
                        progress = json.load(f)
                    # Calculate total progress
                    total_trials = len(progress["words"]) * progress["trials_per_word"]
                    done_trials = sum(progress.get("completed", {}).values())
                    progress["total_trials"] = total_trials
                    progress["done_trials"] = done_trials
                    experiments.append(progress)
                except (json.JSONDecodeError, KeyError):
                    continue
        return experiments

    def start_trial(self, word, trial_num):
        self.trial_buffer = []
        self.recording_trial = True
        self.current_word = word
        self.current_trial = trial_num

    def add_samples(self, samples):
        if self.recording_trial:
            self.trial_buffer.extend(samples)

    def end_trial(self):
        if not self.recording_trial:
            return False
        self.recording_trial = False
        word = self.current_word
        trial = self.current_trial

        # Save trial CSV (backup if file already exists)
        filename = f"{word}_{trial:02d}.csv"
        filepath = self.experiment_dir / "trials" / filename
        if filepath.exists():
            backup = filepath.with_suffix(f".bak{int(time.time())}.csv")
            filepath.rename(backup)
            print(f"  Existing file backed up: {backup.name}")
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(["time", "ch1", "ch2", "ch3", "ch4"])
            if self.trial_buffer:
                t0 = self.trial_buffer[0][0]
                for s in self.trial_buffer:
                    writer.writerow(
                        [f"{s[0] - t0:.4f}"] + [f"{v:.6f}" for v in s[1:]]
                    )

        # Update progress
        progress = self._load_progress()
        if word not in progress["completed"]:
            progress["completed"][word] = 0
        progress["completed"][word] = max(progress["completed"][word], trial)
        self._save_progress(progress)

        self.trial_buffer = []
        print(f"  Trial saved: {filename} ({len(self.trial_buffer)} -> {filepath})")
        return True

    def cancel_trial(self):
        self.recording_trial = False
        self.trial_buffer = []

    def _save_progress(self, progress):
        with open(self.experiment_dir / "progress.json", "w") as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)

    def _load_progress(self):
        with open(self.experiment_dir / "progress.json") as f:
            return json.load(f)


class WebSocketHandler:
    """Manages WebSocket connections and broadcasts EMG data."""

    def __init__(self, data_queue, csv_writer, experiment_manager):
        self.data_queue = data_queue
        self.csv_writer = csv_writer
        self.experiment = experiment_manager
        self.clients = set()
        self.running = False

    async def handler(self, websocket):
        self.clients.add(websocket)
        remote = getattr(websocket, "remote_address", None)
        print(f"WebSocket client connected: {remote}")
        try:
            async for message in websocket:
                try:
                    cmd = json.loads(message)
                    action = cmd.get("action")
                    resp = await self._handle_command(action, cmd)
                    if resp:
                        await websocket.send(json.dumps(resp))
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"WebSocket handler error: {e}")
        finally:
            self.clients.discard(websocket)
            print(f"WebSocket client disconnected: {remote}")

    async def _handle_command(self, action, cmd):
        if action == "start_recording":
            filename = self.csv_writer.start_recording()
            return {"type": "recording_started", "filename": filename}

        elif action == "stop_recording":
            self.csv_writer.stop_recording()
            return {"type": "recording_stopped"}

        elif action == "list_experiments":
            experiments = self.experiment.list_experiments()
            return {"type": "experiment_list", "experiments": experiments}

        elif action == "create_experiment":
            words = cmd.get("words", [])
            trials_per_word = cmd.get("trials_per_word", 30)
            subject_id = cmd.get("subject_id", "")
            progress = self.experiment.create(words, trials_per_word, subject_id)
            return {"type": "experiment_ready", "progress": progress}

        elif action == "resume_experiment":
            experiment_id = cmd.get("experiment_id")
            progress = self.experiment.resume(experiment_id)
            if progress:
                return {"type": "experiment_ready", "progress": progress}
            else:
                return {"type": "experiment_error", "message": "Experiment not found"}

        elif action == "trial_start":
            word = cmd.get("word")
            trial = cmd.get("trial")
            self.experiment.start_trial(word, trial)
            return None

        elif action == "trial_end":
            self.experiment.end_trial()
            return None

        elif action == "trial_cancel":
            self.experiment.cancel_trial()
            return None

        return None

    async def broadcast_loop(self):
        """Send batched data to all clients at ~60Hz."""
        self.running = True
        while self.running:
            if self.data_queue and self.clients:
                # Drain the queue
                samples = []
                while self.data_queue:
                    samples.append(self.data_queue.popleft())

                # Write to manual CSV
                self.csv_writer.write_samples(samples)

                # Buffer for experiment trial
                self.experiment.add_samples(samples)

                # Send to WebSocket clients
                message = json.dumps({
                    "type": "data",
                    "samples": samples,
                })
                disconnected = set()
                for client in self.clients.copy():
                    try:
                        await client.send(message)
                    except Exception:
                        disconnected.add(client)
                self.clients -= disconnected

            await asyncio.sleep(0.016)  # ~60Hz

    def stop(self):
        self.running = False


async def run_http_server(port):
    """Serve the frontend directory via HTTP."""
    frontend_dir = Path(__file__).parent / "frontend"

    async def index_handler(request):
        return web.FileResponse(frontend_dir / "index.html")

    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_static("/", frontend_dir)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"HTTP server: http://localhost:{port}")
    return runner


async def main():
    parser = argparse.ArgumentParser(description="EMG 4ch real-time visualization server")
    parser.add_argument("--mock", action="store_true", help="Use mock data (no serial hardware)")
    parser.add_argument("--port", type=str, help="Serial port path (e.g. /dev/tty.usbmodemXXXX)")
    parser.add_argument("--config", type=str, default="config.json", help="Config file path")
    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if config_path.exists():
        config = {**DEFAULT_CONFIG, **load_config(config_path)}
        print(f"Config loaded from {config_path}")
    else:
        config = DEFAULT_CONFIG.copy()
        print("Using default config")

    data_queue = deque()
    csv_writer = CSVWriter(config)
    experiment_manager = ExperimentManager(config["output_dir"])

    # Start serial reader
    reader = SerialReader(config, data_queue, mock=args.mock, port_override=args.port)
    reader.start()

    # Start WebSocket handler
    ws_handler = WebSocketHandler(data_queue, csv_writer, experiment_manager)

    # Start HTTP server
    http_runner = await run_http_server(config["http_port"])

    # Start WebSocket server
    ws_server = await websockets.serve(ws_handler.handler, "0.0.0.0", config["ws_port"])
    print(f"WebSocket server: ws://localhost:{config['ws_port']}")

    # Start broadcast loop
    broadcast_task = asyncio.create_task(ws_handler.broadcast_loop())

    print("Server running. Press Ctrl+C to stop.")

    try:
        await asyncio.Future()  # Run forever
    except asyncio.CancelledError:
        pass
    finally:
        print("\nShutting down...")
        reader.stop()
        csv_writer.close()
        ws_handler.stop()
        broadcast_task.cancel()
        ws_server.close()
        await ws_server.wait_closed()
        await http_runner.cleanup()
        print("Server stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
