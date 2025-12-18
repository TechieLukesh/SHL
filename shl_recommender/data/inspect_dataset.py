import pandas as pd

fn = "data/dataset.xlsx"
xls = pd.ExcelFile(fn)
print("Sheets:", xls.sheet_names)
for sheet in xls.sheet_names:
    df = pd.read_excel(fn, sheet_name=sheet)
    print(f"--- Sheet: {sheet} ---")
    print(df.head(10))
