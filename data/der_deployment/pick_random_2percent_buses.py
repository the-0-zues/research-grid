import random
import csv
from pathlib import Path
from collections import defaultdict

# --------------------------------------------------
# SETTINGS
# --------------------------------------------------
INPUT_FILE = Path("ckt7_VLN_Node.Txt")
RANDOM_SEED = 42
PERCENT_TO_SELECT = 0.02

# --------------------------------------------------
# FIND ALL THREE-PHASE 12.47 kV BUSES
# --------------------------------------------------
bus_nodes = defaultdict(set)
current_bus = None

with INPUT_FILE.open("r", encoding="utf-8") as file:
    for line in file:
        tokens = line.split()

        if not tokens:
            continue

        # Case 1: Continuation line for the current bus
        # Example:
        # -          2       6.9716 ... 12.470
        if tokens[0] == "-" and current_bus is not None:
            node = tokens[1]

            if node in {"1", "2", "3"} and "12.470" in tokens:
                bus_nodes[current_bus].add(node)

        # Case 2: New bus line
        else:
            bus_name = tokens[0]
            current_bus = bus_name

            # Find the node number somewhere near the start of the row
            node = None
            for token in tokens[1:4]:
                if token in {"1", "2", "3"}:
                    node = token
                    break

            if node in {"1", "2", "3"} and "12.470" in tokens:
                bus_nodes[current_bus].add(node)

# --------------------------------------------------
# KEEP ONLY TRUE THREE-PHASE 12.47 kV BUSES
# --------------------------------------------------
three_phase_buses = sorted([
    bus for bus, nodes in bus_nodes.items()
    if nodes == {"1", "2", "3"}
])

# --------------------------------------------------
# RANDOMLY SELECT 2%
# --------------------------------------------------
num_buses_total = len(three_phase_buses)
num_to_select = round(num_buses_total * PERCENT_TO_SELECT)

random.seed(RANDOM_SEED)
selected_buses = random.sample(three_phase_buses, num_to_select)

# --------------------------------------------------
# PRINT RESULTS
# --------------------------------------------------
print(f"Total three-phase 12.47 kV buses found: {num_buses_total}")
print(f"2% of {num_buses_total} buses = {num_to_select} buses")
print()
print("Randomly selected DG candidate buses:")

for bus in selected_buses:
    print(bus)

# --------------------------------------------------
# SAVE RESULTS TO CSV
# --------------------------------------------------
output_file = Path("selected_dg_buses_2percent.csv")

with output_file.open("w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Selected_DG_Bus"])

    for bus in selected_buses:
        writer.writerow([bus])

print()
print(f"Selected buses saved to: {output_file}")