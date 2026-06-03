import pandas as pd
from pathlib import Path

# ------------------------------------------------------------
# Folder where your exported OpenDSS monitor CSV files are stored
# ------------------------------------------------------------
exports_folder = Path(r"C:\EPRI_Ckt7_DER_Project\Exports")

# ------------------------------------------------------------
# RFI to OpenDSS line mapping
# RFI20 final = Line.255389
# ------------------------------------------------------------
rfi_line_map = {
    "RFI1": "Line.215299",
    "RFI2": "Line.298366",
    "RFI3": "Line.157115",
    "RFI4": "Line.157152",
    "RFI5": "Line.157168",
    "RFI6": "Line.175038",
    "RFI7": "Line.255473",
    "RFI8": "Line.175060",
    "RFI9": "Line.175064",
    "RFI10": "Line.175085",
    "RFI11": "Line.175087",
    "RFI12": "Line.182907",
    "RFI13": "Line.182915",
    "RFI14": "Line.157127",
    "RFI15": "Line.318388",
    "RFI16": "Line.175042",
    "RFI17": "Line.262345",
    "RFI18": "Line.174952",
    "RFI19": "Line.175054",
    "RFI20": "Line.255389",
}

def find_monitor_file(rfi_id):
    """
    Finds the exact OpenDSS monitor export file for each RFI.
    Example:
        RFI1  -> ckt7_Mon_rfi1_1.csv
        RFI10 -> ckt7_Mon_rfi10_1.csv
    """
    rfi_number = rfi_id.replace("RFI", "")

    exact_name = f"ckt7_Mon_rfi{rfi_number}_1.csv"
    file_path = exports_folder / exact_name

    if not file_path.exists():
        raise FileNotFoundError(f"Could not find exact file: {file_path}")

    return file_path


rows = []

for rfi_id, line_name in rfi_line_map.items():
    file_path = find_monitor_file(rfi_id)

    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()

    row = df.iloc[0]

    i1 = float(row["I1"])
    i2 = float(row["I2"])
    i3 = float(row["I3"])

    max_normal_current = max(i1, i2, i3)

    if rfi_id == "RFI20":
        pickup_threshold = 25.0
        threshold_rule = "Manual 25 A"
    else:
        pickup_threshold = 2 * max_normal_current
        threshold_rule = "2x max normal phase current"

    rows.append({
        "RFI_ID": rfi_id,
        "Line": line_name,
        "I1_normal_A": i1,
        "I2_normal_A": i2,
        "I3_normal_A": i3,
        "Max_normal_current_A": max_normal_current,
        "Pickup_threshold_A": pickup_threshold,
        "Threshold_rule": threshold_rule,
        "Source_file": file_path.name
    })

threshold_df = pd.DataFrame(rows)

threshold_df["RFI_Number"] = threshold_df["RFI_ID"].str.replace("RFI", "").astype(int)
threshold_df = threshold_df.sort_values("RFI_Number").drop(columns=["RFI_Number"])

output_file = exports_folder / "rfi_thresholds_2x_with_RFI20_25A.csv"
threshold_df.to_csv(output_file, index=False)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

print("Threshold table created successfully.")
print(f"Saved to: {output_file}")
print()
print(threshold_df)