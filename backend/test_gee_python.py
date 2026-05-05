import asyncio
import os
import sys

# Add the current directory to path
sys.path.append(os.path.abspath('.'))

from gee_client import init_gee, extract_metrics

async def test_gee():
    print("Testing GEE Connection...")
    if init_gee():
        # London coordinates
        polygon = {
            "type": "Polygon",
            "coordinates": [[
                [-0.1, 51.5],
                [-0.1, 51.51],
                [-0.08, 51.51],
                [-0.08, 51.5],
                [-0.1, 51.5]
            ]]
        }
        results = await extract_metrics(polygon)
        print("\nGEE Results:")
        for k, v in results.items():
            print(f"  {k}: {v}")
    else:
        print("GEE Initialization Failed.")

if __name__ == "__main__":
    asyncio.run(test_gee())
