import serial
import serial.tools.list_ports
import time
import csv
from datetime import datetime
from flask import Flask, render_template
import pandas as pd
import plotly.express as px
import plotly.io as pio
import threading

# シリアルポートの設定
def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        print(f"{port}: {desc} [{hwid}]")

list_serial_ports()
PORT = '/dev/tty.usbmodem1101'  # 使用するポートを指定
BAUD_RATE = 230400

# Flaskアプリケーションの作成と設定
app = Flask(__name__)

# 固定タイムスタンプを生成し、同じCSVファイルを使用
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
csv_file = f'output/{timestamp}.csv'
csv_columns = ['time', 'ch1', 'ch2', 'ch3', 'ch4']

# CSVファイルにヘッダーを書き込む関数（ファイルが存在しない場合にのみヘッダーを追加）
def write_header():
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        if file.tell() == 0:  # ファイルが空の場合にヘッダーを書き込む
            writer.writerow(csv_columns)

write_header()  # スクリプト実行時に一度だけヘッダーを書き込む

def init_serial():
    ser = None
    while ser is None:
        try:
            ser = serial.Serial(PORT, BAUD_RATE)
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)
    return ser

# シリアルポートの初期化
ser = init_serial()

# シリアルポートからデータを読み取り、ログに記録する関数
def read_serial_data():
    buffer = ""
    global ser
    while True:
        try:
            while ser.in_waiting > 0:
                buffer += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

            while len(buffer) >= 16:
                line = buffer[:16]
                buffer = buffer[16:]

                if len(line) == 16:
                    try:
                        value1 = int(line[0:3], 16)
                        value2 = int(line[3:6], 16)
                        value3 = int(line[6:9], 16)
                        value4 = int(line[9:12], 16)
                        count = int(line[12:16], 16)

                        v1 = value1 * 3.3 / 1023
                        v2 = value2 * 3.3 / 1023
                        v3 = value3 * 3.3 / 1023
                        v4 = value4 * 3.3 / 1023

                        data = [count, v1, v2, v3, v4]
                        print(data)

                        with open(csv_file, mode='a', newline='') as file:
                            writer = csv.writer(file)
                            writer.writerow(data)
                    except ValueError as e:
                        print(f"Error parsing line: {line} -> {e}")
                else:
                    print(f"Incomplete or invalid line received: {line}")
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            ser.close()
            ser = init_serial()
        except Exception as e:
            print(f"Unexpected error: {e}")

# シリアル読み取りをバックグラウンドで開始
threading.Thread(target=read_serial_data, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    df = pd.read_csv(csv_file)
    fig = px.line(df, x='time', y=['ch1', 'ch2', 'ch3', 'ch4'])
    graph_json = pio.to_json(fig)
    return graph_json

if __name__ == '__main__':
    app.run(debug=True)
