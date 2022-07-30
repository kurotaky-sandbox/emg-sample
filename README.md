# EMG Sample
EMG is Electromyography.
Arduino send to serial port and processing with python programm, then plot sensor data.

## Usage
### Arduino sketch

1. MsTimer2.zip をダウンロード
2. 「スケッチ」→「ライブラリをインクルード」→「.ZIP形式のライブラリをインストール」をクリック
3. ダウンロードしたファイルを選択しインストール
```
open emg_sample/emg_sample.ino
```

### plotting data

Library install
```
pip install pyserial
pip install numpy
```

Run
```
python emg-serial.py
```
