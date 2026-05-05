import ee
import json
from pathlib import Path

def test_assets():
    key_path = Path("gee-key.json")
    if not key_path.exists():
        print("gee-key.json not found.")
        return

    try:
        with open(key_path, 'r') as f:
            credentials = json.load(f)
        auth = ee.ServiceAccountCredentials(credentials['client_email'], key_data=json.dumps(credentials))
        ee.Initialize(auth)
        
        assets = [
            "projects/darukaa-earth130226/assets/RedList_Bird_IUCN_Category",
            "projects/darukaa-earth130226/assets/RedList_Mammals_Terrestrial",
            "projects/darukaa-earth130226/assets/KBA_Global_POL_SEP25"
        ]
        
        for asset in assets:
            try:
                info = ee.FeatureCollection(asset).limit(1).getInfo()
                print(f"Asset OK: {asset}")
                print(f"Columns: {list(info['columns'].keys()) if 'columns' in info else 'No columns info'}")
            except Exception as e:
                print(f"Asset FAILED: {asset} - {e}")
                
    except Exception as e:
        print(f"Initialization Error: {e}")

if __name__ == "__main__":
    test_assets()
