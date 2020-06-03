import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# df = pd.read_csv('output/20200603-024110-a.csv')
df = pd.read_csv('output/20200603-024336-i.csv')

df.columns = ["time", "value"]
# print(df.head())

df.plot(x='time')
df.plot(y='value', subplots=True, sharex=True)

# 表示と終了
plt.show()
plt.close('all')
