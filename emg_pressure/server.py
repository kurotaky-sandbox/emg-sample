#!/usr/bin/env python3
"""EMG 1ch + FSR pressure sensor real-time visualization server.

Serial reader -> CSV writer + WebSocket broadcaster -> Browser frontend.
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
    "http_port": 8081,
    "ws_port": 8766,
    "voltage_reference": 3.3,
    "adc_resolution": 1023,
    "num_channels": 2,
    "output_dir": "output",
    "fsr_vcc": 3.3,
    "fsr_reference_resistor": 10000,
}


def voltage_to_force(v, vcc, r_ref):
    """Convert FSR voltage to approximate force in Newtons.

    Assumes pullup voltage divider circuit:
      Vcc --- R_ref --- analog pin --- FSR --- GND
      V_out = Vcc * R_FSR / (R_FSR + R_ref)

    From this: R_FSR = R_ref * V / (Vcc - V)
    When force is applied, R_FSR decreases, V decreases.
    Conductance (1/R_FSR) is roughly proportional to applied force.
    Uses a simplified linear conductance model for FSR 402.
    """
    if vcc - v < 0.01:
        # V ≈ Vcc: no pressure (R_FSR very high)
        return 0.0
    if v < 0.01:
        # V ≈ 0: maximum pressure (R_FSR ≈ 0)
        v = 0.01
    r_fsr = r_ref * v / (vcc - v)
    if r_fsr < 1.0:
        r_fsr = 1.0
    conductance_us = 1_000_000.0 / r_fsr  # microsiemens
    force_n = conductance_us / 80.0  # approximate scaling for FSR 402
    return force_n


class SerialReader:
    """Reads 2ch hex data (EMG + FSR) from serial port in a separate thread."""

    def __init__(self, config, data_queue, mock=False, port_override=None):
        self.config = config
        self.data_queue = data_queue
        self.mock = mock
        self.port = port_override or config["serial_port"]
        self.baud = config["baud_rate"]
        self.vref = config["voltage_reference"]
        self.adc_max = config["adc_resolution"]
        self.fsr_vcc = config["fsr_vcc"]
        self.fsr_r_ref = config["fsr_reference_resistor"]
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

                    # Expect 6 hex chars: 3 for EMG + 3 for FSR
                    if len(text) >= 6:
                        raw_emg = int(text[0:3], 16)
                        raw_pressure = int(text[3:6], 16)
                    else:
                        error_count += 1
                        if error_count <= 5:
                            print(f"Short line ({len(text)} chars): {repr(text)}")
                        continue

                    t = time.time() - self.start_time
                    v_emg = raw_emg * self.vref / self.adc_max
                    v_pressure = raw_pressure * self.vref / self.adc_max
                    force_n = voltage_to_force(v_pressure, self.fsr_vcc, self.fsr_r_ref)

                    # (time, emg_v, pressure_raw, pressure_v, pressure_force_n)
                    sample = (t, v_emg, raw_pressure, v_pressure, force_n)
                    self.data_queue.append(sample)

                    sample_count += 1
                    if sample_count == 1:
                        print(f"First sample: {text} -> [EMG={v_emg:.3f}V, Pressure={v_pressure:.3f}V / {force_n:.2f}N (raw={raw_pressure})]")
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
        """Generate mock EMG + FSR pressure data."""
        print("Mock mode: generating synthetic EMG + pressure data")
        interval = 0.001  # 1ms = 1kHz

        while self.running:
            t = time.time() - self.start_time

            # EMG: baseline noise with periodic bursts
            emg_burst = 0.0
            cycle = t % 4.0  # 4s cycle
            if 1.0 < cycle < 2.5:
                # Muscle activation burst
                phase = (cycle - 1.0) / 1.5
                emg_burst = 0.8 * math.sin(phase * math.pi)
            emg_noise = random.gauss(0, 1) * (0.05 + emg_burst * 0.4)
            v_emg = max(0, min(3.3, 0.15 + abs(emg_noise)))

            # FSR pressure (pullup circuit): pressing makes voltage DROP
            # No pressure: V ≈ Vcc (3.3V), Max pressure: V → 0V
            pressure_cycle = t % 6.0  # 6s cycle
            if pressure_cycle < 3.0:
                # Pressing: voltage ramps down from ~3.2V to ~0.5V
                v_pressure = 3.2 - (pressure_cycle / 3.0) * 2.7
            else:
                # Releasing: voltage ramps back up
                v_pressure = 0.5 + ((pressure_cycle - 3.0) / 3.0) * 2.7
            v_pressure += random.gauss(0, 0.03)
            v_pressure = max(0, min(3.3, v_pressure))

            raw_pressure = int(v_pressure * self.adc_max / self.vref)
            raw_pressure = max(0, min(self.adc_max, raw_pressure))
            force_n = voltage_to_force(v_pressure, self.fsr_vcc, self.fsr_r_ref)

            # (time, emg_v, pressure_raw, pressure_v, pressure_force_n)
            sample = (t, v_emg, raw_pressure, v_pressure, force_n)
            self.data_queue.append(sample)
            time.sleep(interval)


class CSVWriter:
    """Writes EMG + pressure samples to CSV files."""

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
        self.writer.writerow(["time", "emg_voltage", "pressure_raw", "pressure_voltage", "pressure_force_n"])
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
            # sample: (time, emg_v, pressure_raw, pressure_v, pressure_force_n)
            t, emg_v, p_raw, p_v, p_force = sample
            self.writer.writerow([f"{t:.4f}", f"{emg_v:.6f}", int(p_raw), f"{p_v:.6f}", f"{p_force:.4f}"])
        self.file.flush()

    def close(self):
        self.stop_recording()


class WebSocketHandler:
    """Manages WebSocket connections and broadcasts sensor data."""

    def __init__(self, data_queue, csv_writer):
        self.data_queue = data_queue
        self.csv_writer = csv_writer
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

                # Write to CSV
                self.csv_writer.write_samples(samples)

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
    parser = argparse.ArgumentParser(description="EMG + Pressure sensor real-time server")
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

    # Start serial reader
    reader = SerialReader(config, data_queue, mock=args.mock, port_override=args.port)
    reader.start()

    # Start WebSocket handler
    ws_handler = WebSocketHandler(data_queue, csv_writer)

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
