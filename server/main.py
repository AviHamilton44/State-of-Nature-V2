import os
import sys
import shutil
import ee
import json
import math
import geopandas as gpd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

# Add backend to path to import gee_client
sys.path.append(os.path.join(os.getcwd(), "..", "backend"))
from gee_client import init_gee, extract_metrics
from sector_data import get_sector_son_matrix

def sanitize_nan(data):
    """Recursively replace NaN values with None for JSON compliance."""
    if isinstance(data, dict):
        return {k: sanitize_nan(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_nan(x) for x in data]
    elif isinstance(data, float):
        return None if math.isnan(data) or math.isinf(data) else data
    return data

import logging
# Configure logging to show pipeline progress in console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from darukaa_reference.pipeline import Pipeline
from darukaa_reference.config import Config
from darukaa_reference.indicators import create_default_registry
from scoring import calculate_scorecard

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Darukaa Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    success = init_gee()
    if success:
        logger.info("GEE initialized successfully via backend/gee_client")
    else:
        logger.error("GEE initialization failed via backend/gee_client")

# Initialize Pipeline Registry
REGISTRY = create_default_registry()

def get_pipeline_config(year: int):
    return Config(
        gee_project="gaurav-singh-007",
        bii_gee_asset="projects/gaurav-singh-007/assets/bii-2020_v2-1-1",
        hmi_hard_ceiling=0.10,
        elevation_band_m=300.0,
        min_reference_pixels=5,
        ndvi_year=year,
        lst_year=year,
        output_dir="./output"
    )

@app.post("/api/run-pipeline")
async def run_pipeline(
    file: UploadFile = File(...),
    year: int = Form(...)
):
    temp_file_path = f"temp_{file.filename}"
    
    try:
        # Save uploaded file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Load Geometry for return
        gdf = gpd.read_file(temp_file_path)
        if gdf.empty:
            raise HTTPException(status_code=400, detail="Invalid or empty spatial file")
        
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
            
        from shapely.geometry import mapping
        geometry = mapping(gdf.geometry.iloc[0])
        
        # 2. Configure and Run Pipeline
        logger.info(f"RUNNING: Darukaa Pipeline for {file.filename} (Year: {year})...")
        config = get_pipeline_config(year)
        pipeline = Pipeline(config, REGISTRY)
        
        report = pipeline.run(temp_file_path)
        
        # 3. Calculate Scorecard using updated scoring logic
        scorecard = report.get("scorecard", [])
        if not scorecard:
            raise Exception("Pipeline returned empty scorecard")
            
        scoring_results = calculate_scorecard(scorecard, REGISTRY)
        
        # 4. Final Response
        result = {
            "status": "success",
            "scoring": scoring_results,
            "geojson": geometry,
            "metadata": {
                "filename": file.filename,
                "year": year
            }
        }

        return JSONResponse(content=sanitize_nan(result))
        
    except Exception as e:
        import traceback
        logger.error(f"PIPELINE ERROR: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/api/sector-son-matrix")
async def sector_son_matrix():
    return get_sector_son_matrix()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
