import json
from spatial_utils import calculate_kba_overlap

# A sample geometry that might overlap with a KBA (using dummy.json's area or similar)
with open('../server/dummy.json', 'r') as f:
    dummy_geo = json.load(f)

print("Starting Local KBA Overlap Calculation Test...")
overlap = calculate_kba_overlap(dummy_geo)
print(f"Result: {overlap}%")

if overlap is not None:
    print("SUCCESS: Local KBA processing is working.")
else:
    print("FAILED: Local KBA processing returned None.")
