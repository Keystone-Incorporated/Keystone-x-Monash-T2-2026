import pandas as pd

df = pd.read_csv("Merged_Business_Data.csv", encoding="utf-8-sig")

target_n = 2000

df_2k = df.sample(
    n=target_n,
    replace=True,
    random_state=42
).reset_index(drop=True)

df_2k.to_csv(
    "Merged_Business_Data.csv",
    index=False,
    encoding="utf-8-sig"
)

print(len(df_2k))