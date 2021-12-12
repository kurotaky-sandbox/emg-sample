import serial
import numpy as np
import csv
from datetime import datetime
from matplotlib import pyplot as plt

ser = serial.Serial('/dev/tty.usbmodem14101', 115200, timeout=None)

t = np.zeros(100)
y = np.zeros(100)

plt.ion()
plt.figure()
li, = plt.plot(t, y)
plt.ylim(0, 5)
plt.xlabel("time[s]")
plt.ylabel("Voltage[V]")

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
        t = np.append(t, time)
        t = np.delete(t, 0)
        voltage = float(data[1]) # * 5.0 / 1023
        y = np.append(y, voltage)
        y = np.delete(y, 0)

        #writer = csv.writer(f, lineterminator='\n')
        #writer.writerow([time, voltage])

        li.set_xdata(t)
        li.set_ydata(y)
        plt.xlim(min(t), max(t))
        plt.pause(0.001) # 0.001sec
    except KeyboardInterrupt:
        ser.close()
        f.close()
        break
