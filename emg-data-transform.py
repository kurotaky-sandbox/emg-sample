import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import csv

df = pd.read_csv('testdata/20200616-203813.csv')
df.columns = ["time", "voltage"]
print(df.head())

# 5000~10000 Alexa
# 15000~20000 Play
# 25000~30000 Music
#

with open('20200616-alexa.csv', 'w') as file:
    writer = csv.writer(file, lineterminator='\n')

    start_index = 5000
    for i in range(30):
        writer.writerow(df[start_index:start_index+100]['voltage'].tolist())
        start_index += 200
        print(start_index)
        if start_index >= 10000:
            break

with open('20200616-play.csv', 'w') as file:
    writer = csv.writer(file, lineterminator='\n')

    start_index = 15000
    for i in range(30):
        writer.writerow(df[start_index:start_index+100]['voltage'].tolist())
        start_index += 200
        print(start_index)
        if start_index >= 20000:
            break

with open('20200616-music.csv', 'w') as file:
    writer = csv.writer(file, lineterminator='\n')

    start_index = 25000
    for i in range(30):
        writer.writerow(df[start_index:start_index+100]['voltage'].tolist())
        start_index += 200
        print(start_index)
        if start_index >= 30000:
            break
