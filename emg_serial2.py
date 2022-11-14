import serial
import numpy as np
import csv
from datetime import datetime

ser = serial.Serial('/dev/tty.usbmodem1101', 115200, timeout=None)
ser.write("*".encode())
data = ser.readline().strip().decode('utf-8').split(',')
print(data)
tInt = float(data[0])
filename = datetime.now().strftime("%Y%m%d-%H%M%S")
f = open('output/%s.csv' % filename, 'w')

while True:
    try:
        ser.write("*".encode())
        data = ser.readline().strip().decode('utf-8').split(',')
        time = data[0]
        voltage = data[1]
        voltage2 = data[2]
        voltage3 = data[3]
        print(time, voltage, voltage2, voltage3)
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow([time, voltage, voltage2, voltage3])
    except KeyboardInterrupt:  # Ctr + C
        ser.close()
        f.close()
        break
