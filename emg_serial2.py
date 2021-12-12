import serial
import numpy as np
import csv
from datetime import datetime

ser = serial.Serial('/dev/tty.usbmodem14101', 115200, timeout=None)
ser.write("*".encode())
data = ser.readline().strip().rsplit()
tInt = float(data[0])
filename = datetime.now().strftime("%Y%m%d-%H%M%S")
f = open('output/%s.csv' % filename, 'w')

while True:
    try:
        ser.write("*".encode())
        data = ser.readline().strip().rsplit()
        time = (float(data[0]) - tInt) # / 10**6
        voltage = float(data[1])
        #voltage2 = float(data[2])
        #print(time, voltage, voltage2)
        print(time, voltage)
        writer = csv.writer(f, lineterminator='\n')
        #writer.writerow([time, voltage, voltage2])
        writer.writerow([time, voltage])
    except KeyboardInterrupt:  # Ctr + C
        ser.close()
        f.close()
        break
