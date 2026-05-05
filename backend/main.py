import time
import math
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gee_client import init_gee, extract_metrics
from sector_data import get_sector_son_matrix
from spatial_utils import calculate_kba_overlap

app = FastAPI(title="State of Nature API (Python)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

site_data: Dict[str, Dict[str, Any]] = {}

@app.on_event("startup")
def startup_event():
    init_gee()

@app.get("/")
async def root():
    return {"message": "State of Nature API running"}

class SiteUpload(BaseModel):
    geometry: Dict[str, Any]
    filename: str

# ------------------------------
# Upload
# ------------------------------
@app.post("/api/sites/upload")
async def upload_site(upload: SiteUpload):
    site_id = f"site_{int(time.time()*1000)}"
    site_data[site_id] = {"geometry": upload.geometry}
    return {"site_id": site_id}

# ------------------------------
# Generate Metrics
# ------------------------------
@app.post("/api/sites/{id}/generate-metrics")
async def generate_metrics(id: str):

    if id not in site_data:
        raise HTTPException(status_code=404, detail="Site not found")

    geometry = site_data[id]["geometry"]
    gee = await extract_metrics(geometry)

    # Calculate Local KBA Overlap (Overwrite)
    local_kba = calculate_kba_overlap(geometry)
    if local_kba is not None:
        gee["kba_overlap"] = local_kba
        print(f"DEBUG: Local KBA Overlap applied: {local_kba}%")

    # ------------------------------
    # NORMALIZATION HELPERS
    # ------------------------------
    def clamp01(x): return max(0.0, min(1.0, x))

    # ------------------------------
    # RAW VALUES
    # ------------------------------
    ghm = gee.get("ghm", 0)
    ndvi = gee.get("ndvi_median", 0)
    lst_day = gee.get("lst_day", 0)
    lst_night = gee.get("lst_night", 0)
    light = gee.get("light_pollution", 0)
    forest_loss = gee.get("forest_loss_rate", 0) * 100
    aridity = gee.get("aridity_index", 0)
    natural_dw = gee.get("natural_habitat_dw", 0)
    natural_lc = gee.get("natural_lc_modis", 0)
    dist = gee.get("distance_to_urban", 10000)
    npp = gee.get("npp", 0)
    bii = gee.get("bii", 0.8)

    # NEW METRICS (ADDED)
    flII_raw = gee.get("flii", None)
    pdf_raw = gee.get("pdf", None)
    kba = gee.get("kba_overlap", None)
    species_richness = gee.get("species_richness", None)
    threatened_species = gee.get("threatened_species", None)
    ceri = gee.get("ceri", None)
    star_t = gee.get("star_t", None)
    star_r = gee.get("star_r", None)
    habitat_viability = gee.get("habitat_viability", None)

    # ------------------------------
    # NORMALIZED METRICS (0–1)
    # ------------------------------

    # Extent
    forest_loss_norm = 1 - clamp01(forest_loss / 100)

    # Condition
    aridity_norm = clamp01(aridity / 2)
    lst_day_norm = clamp01((lst_day - 15) / (45 - 15))
    lst_night_norm = clamp01((lst_night - 10) / (35 - 10))

    # Light
    light_norm = 1 - clamp01(light / 50)

    # HDI
    hdi_norm = clamp01(dist / 1500)

    # EII
    eii_structural = 1 - ghm
    eii_compositional = bii
    eii_functional = clamp01(npp / 2)
    eii_overall = min(eii_structural, eii_compositional, eii_functional)

    # FLII
    if flII_raw is not None:
        flii_norm = clamp01(flII_raw / 10)
    else:
        pressure = clamp01((light/60 + ghm)/2)
        flii_norm = 1 - pressure

    # PDF
    if pdf_raw is not None:
        pdf_norm = 1 - clamp01(pdf_raw)
    else:
        lc = round(gee.get("modis_lc_type", 0))
        pdf_val = 0
        if lc == 12: pdf_val = 0.30
        elif lc == 13: pdf_val = 0.50
        elif lc == 10: pdf_val = 0.05
        elif lc == 7: pdf_val = 0.20
        elif 0 < lc <= 5: pdf_val = 0.10
        pdf_norm = 1 - pdf_val
    
    # Biodiversity
    species_richness = gee.get("species_richness", 0)
    threatened_species = gee.get("threatened_species", 0)
    srr = gee.get("srr", 0)
    kba = gee.get("kba_overlap", 0)
    ceri = gee.get("ceri", 0.5)
    star_t = gee.get("star_t", 0.5)
    star_r = gee.get("star_r", 0.5)
    hvi = gee.get("hvi", 0.5)

    # ------------------------------
    # NORMALIZED METRICS (0–1)
    # ------------------------------

    # Extent
    forest_loss_norm = 1 - clamp01(forest_loss / 100)
    kba_norm = clamp01(kba / 100)

    # Condition
    aridity_norm = clamp01(aridity / 2)
    lst_day_norm = clamp01((lst_day - 15) / (45 - 15))
    lst_night_norm = clamp01((lst_night - 10) / (35 - 10))
    light_norm = 1 - clamp01(light / 50)
    hdi_norm = clamp01(dist / 1500)

    # EII
    eii_structural = 1 - ghm
    eii_compositional = bii
    eii_functional = clamp01(npp / 2)
    eii_overall = min(eii_structural, eii_compositional, eii_functional)

    # ------------------------------
    # METRICS STRUCTURE
    # ------------------------------
    metrics = {

        "Pillar-1: Ecosystem Extent": {
            "Natural Habitat Extent": natural_dw,
            "Natural Land Cover %": natural_lc,
            "Habitat Loss Rate": forest_loss_norm,
            "Connectivity (CPLAND)": "Coming soon",
            "KBA Overlap": kba_norm
        },

        "Pillar-2: Ecosystem Condition": {
            "NDVI": ndvi,
            "Habitat Health Index": ndvi * 0.9,
            "FLII": flii_norm,
            "EII Overall": eii_overall,
            "EII Structural": eii_structural,
            "EII Compositional": eii_compositional,
            "EII Functional": eii_functional,
            "BII": bii,
            "PDF": pdf_norm,
            "Aridity Index": aridity_norm,
            "Water Stress": "Coming soon",
            "Water Quality": "Coming soon",
            "Acoustic Index": "Coming soon",
            "Taxonomic Dissimilarity": "Coming soon"
        },

        "Pillar-3: Population": {
            "Species Richness": species_richness,
            "Endemic / Small Range": srr,
            "KBA / IBA Overlap": kba_norm,
            "Habitat Viability Index": clamp01(hvi),
            "IUCN Conservation Value": 1 - ceri
        },

        "Pillar-4: Extinction Risk": {
            "Threatened Species": threatened_species,
            "CERI": ceri,
            "STAR_T": clamp01(star_t),
            "STAR_R": clamp01(star_r)
        },

        "Pillar-5: Pressure": {
            "GHM": 1 - ghm,
            "Light Pollution": light_norm,
            "HDI": hdi_norm,
            "Day LST": lst_day,
            "Night LST": lst_night,
            "Urban Heat Island": "Coming soon",
            "Acoustic Disturbance": "Coming soon"
        }
    }

    site_data[id]["metrics"] = metrics
    return {"data": metrics}


# ------------------------------
# SoN CALCULATION (PRD v2.0)
# ------------------------------
@app.get("/api/sites/{id}/son-summary")
async def son_summary(id: str):
    if id not in site_data or "metrics" not in site_data[id]:
        raise HTTPException(status_code=404, detail="Run analysis first")

    data = site_data[id]["metrics"]

    # 1. Define Dimension Mapping
    DIM_MAP = {
        1: ["Natural Habitat Extent", "Natural Land Cover %", "Habitat Loss Rate"],
        2: ["NDVI", "FLII", "EII Overall", "BII", "PDF", "Aridity Index"],
        3: ["Species Richness", "Habitat Viability Index"],
        4: ["Threatened Species", "CERI", "STAR_T", "STAR_R"]
    }

    # 2. Extract values and convert 0-1 metrics to 1-5 concern levels (5 is best)
    # Note: frontend metrics are already 0-1 normalized
    dim_scores = {}
    for dim_num, indicators in DIM_MAP.items():
        values = []
        # Check all pillars in 'metrics' as some dimensions span multiple pillars
        for pillar_name, pillar_metrics in data.items():
            for name, val in pillar_metrics.items():
                if name in indicators and isinstance(val, (int, float)):
                    # Convert 0-1 to 1-5 (5 is best)
                    concern_numeric = 1 + (val * 4)
                    concern_numeric = max(1.0, min(5.0, concern_numeric))
                    values.append(concern_numeric)
        
        dim_scores[dim_num] = sum(values) / len(values) if values else None

    # 3. Apply SoN PRD v2.0 Formula
    valid_dims = {d: s for d, s in dim_scores.items() if s is not None}
    n_valid = len(valid_dims)

    if n_valid >= 1:
        total = sum(valid_dims.values())
        # SoN Score: (Sigma - n) / (n * 4) * 10
        son = ((total - n_valid) / (n_valid * 4)) * 10
        son = max(0, min(10, son))
    else:
        son = None

    # 4. Extract Pressure Score (Pillar 5)
    pressure_avg = None
    p5 = data.get("Pillar-5: Pressure", {})
    p5_vals = []
    
    # helper for LST re-normalization inside summary
    def normalize_lst(val, is_day):
        low = 15 if is_day else 10
        high = 45 if is_day else 35
        v = (val - low) / (high - low)
        return max(0.0, min(1.0, v))

    for name, val in p5.items():
        if isinstance(val, (int, float)):
            if name == "Day LST":
                p5_vals.append(normalize_lst(val, True))
            elif name == "Night LST":
                p5_vals.append(normalize_lst(val, False))
            else:
                p5_vals.append(val)

    if p5_vals:
        # Pressure Score is 0-10 based on normalized pressure (Higher = Worse)
        pressure_avg = (sum(p5_vals) / len(p5_vals)) * 10

    return {
        "SoN Score": round(son, 2) if son is not None else None,
        "Extent": round(dim_scores.get(1), 2) if dim_scores.get(1) else None,
        "Condition": round(dim_scores.get(2), 2) if dim_scores.get(2) else None,
        "Population": round(dim_scores.get(3), 2) if dim_scores.get(3) else None,
        "Extinction": round(dim_scores.get(4), 2) if dim_scores.get(4) else None,
        "Pressure Score": round(pressure_avg, 2) if pressure_avg is not None else None,
        "metrics": data
    }

@app.get("/api/sector-son-matrix")
async def sector_son_matrix():
    return get_sector_son_matrix()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)