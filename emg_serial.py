import serial
import numpy as np
from matplotlib import pyplot as plt

ser = serial.Serial('/dev/tty.usbmodem14201', 9600, timeout=None)

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

while True:
    try:
        ser.write("*".encode())
        data = ser.readline().strip().rsplit()
        t = np.append(t, (float(data[0])-tInt)/10**6)
        t = np.delete(t, 0)
        y = np.append(y, float(data[1])*5/1023)
        y = np.delete(y, 0)

        li.set_xdata(t)
        li.set_ydata(y)
        plt.xlim(min(t), max(t))
        plt.pause(.01)
    except KeyboardInterrupt:
        ser.close()
        break
