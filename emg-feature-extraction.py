import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from tsfresh import extract_features

df = pd.read_csv('output/20200603-024110-a.csv')

df.columns = ["time", "value"]
df_extracted_features = extract_features(df, column_id="value")

print(df_extracted_features.head())
