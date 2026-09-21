import pandas as pd

df = pd.read_csv("Merged_Business_Data.csv", encoding="utf-8-sig")

target_n = 60000

df_nk = df.sample(
    n=target_n,
    replace=True,
    random_state=42
).reset_index(drop=True)

df_nk.to_csv(
    "Merged_Business_Data.csv",
    index=False,
    encoding="utf-8-sig"
)

print(len(df_nk))