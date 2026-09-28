import pandas as pd

INPUT_FILE = "Merged_Business_Data.csv"
OUTPUT_FILE = "Merged_Business_Data.csv"

target_n = 100000  #  60000 or 100000

df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")

expanded = df.sample(
    n=target_n,
    replace=True,
    random_state=42
).reset_index(drop=True)

expanded.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print(f"Original rows: {len(df)}")
print(f"Expanded rows: {len(expanded)}")