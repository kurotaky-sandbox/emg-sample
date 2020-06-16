import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# df = pd.read_csv('output/20200603-024110-a.csv')
df = pd.read_csv('output/20200616-203813.csv')

df.columns = ["time", "voltage"]
# print(df.head())

df.plot(x='time')
df.plot(y='voltage', subplots=True, sharex=True)

plt.xlabel("time[sec]")
plt.ylabel("voltage[V]")

# 表示と終了
plt.show()
plt.close('all')
