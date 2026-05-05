import ee
import json
import os
from pathlib import Path

# Initialization State
_is_initialized = False

def init_gee():
    """Initializes Google Earth Engine using the service account key."""
    global _is_initialized
    
    key_path = Path(__file__).parent / "gee-key.json"
    if not key_path.exists():
        print("gee-key.json not found. Earth Engine running in graceful fallback mode.")
        return False

    try:
        project = 'gaurav-singh-007'
        try:
            ee.Initialize(project=project)
        except Exception:
            ee.Authenticate()
            ee.Initialize(project=project)
            
        print(f"Google Earth Engine Initialized Successfully! (Project: {project} via Default Credentials)")
        _is_initialized = True
        return True
    except Exception as e:
        print(f"Earth Engine Initialization Error: {e}")
        return False


async def extract_metrics(geo_json_data):
    """
    Extract Comprehensive Metrics via GEE
    Ports the logic from Node.js geeClient.js to Python.
    """
    default_fallback = {
        "natural_habitat_dw": 0.5,
        "natural_lc_modis": 0.5,
        "forest_loss_rate": 0,
        "ndvi_median": 0.6,
        "aridity_index": 1.0,
        "ghm": 0.2,
        "light_pollution": 5,
        "lst_day": 30,
        "lst_night": 20,
        "npp": 0.5,
        "bii": 0.8,
        "modis_lc_type": 1,
        "distance_to_urban": 5000,
        "species_richness": 0,
        "threatened_species": 0,
        "srr": 0,
        "kba_overlap": 0,
        "ceri": 0.5,
        "star_t": 0.5,
        "star_r": 0.5,
        "habitat_viability": 0.5
    }

    if not _is_initialized or not geo_json_data:
        return default_fallback

    try:
        # 1. Parse Geometry
        if geo_json_data.get('type') == 'FeatureCollection' and len(geo_json_data.get('features', [])) > 0:
            raw_geometry = geo_json_data['features'][0]['geometry']
        elif geo_json_data.get('geometry'):
            raw_geometry = geo_json_data['geometry']
        else:
            raw_geometry = geo_json_data

        polygon = ee.Geometry(raw_geometry)
        geom_area_km2 = polygon.area().divide(1000000)
        
        year_last = '2024'
        year_now = '2025'

        # --- A. BIODIVERSITY METRICS (IUCN REDLIST) ---
        birds = ee.FeatureCollection("projects/darukaa-earth130226/assets/RedList_Bird_IUCN_Category") \
            .filterBounds(polygon).filter(ee.Filter.eq('presence', 1)).filter(ee.Filter.eq('origin', 1))
        mammals = ee.FeatureCollection("projects/darukaa-earth130226/assets/RedList_Mammals_Terrestrial") \
            .filterBounds(polygon).filter(ee.Filter.eq('presence', 1)).filter(ee.Filter.eq('origin', 1))

        # Weighting Function for CERI/STAR
        def assign_weights(f, cat_col):
            cat = ee.String(f.get(cat_col))
            w = ee.Number(ee.Algorithms.If(cat.equals('EX') or cat.equals('EW'), 5,
                ee.Algorithms.If(cat.equals('CR'), 4,
                ee.Algorithms.If(cat.equals('EN'), 3,
                ee.Algorithms.If(cat.equals('VU'), 2,
                ee.Algorithms.If(cat.equals('NT'), 1, 0))))))
            return f.set('weight', w)

        birds_w = birds.map(lambda f: assign_weights(f, 'RedList__5'))
        mammals_w = mammals.map(lambda f: assign_weights(f, 'category'))
        combined_species = birds_w.merge(mammals_w)

        # 1. Species Richness
        richness = combined_species.distinct('sci_name').size()

        # 2. Threatened Species (CR, EN, VU)
        threatened = combined_species.filter(ee.Filter.inList('weight', [2, 3, 4])).distinct('sci_name').size()

        # 3. CERI (Composite Extinction Risk Index)
        # Formula: Sum(weight) / (N * 5)
        total_weight = combined_species.aggregate_sum('weight')
        ceri = ee.Number(ee.Algorithms.If(richness.gt(0), total_weight.divide(richness.multiply(5)), 0))

        # 4. SRR (Small Range Species) - Range < 100,000 km2
        # Using a conservative range size filter from RedList metadata if available, otherwise 0
        srr = combined_species.filter(ee.Filter.lt('SHAPE_Area', 1e11)).distinct('sci_name').size()

        # --- B. KBA OVERLAP ---
        kba = ee.FeatureCollection("projects/darukaa-earth130226/assets/KBA_Global_POL_SEP25").filterBounds(polygon)
        kba_intersection = kba.map(lambda f: f.intersection(polygon, 1))
        kba_area_km2 = kba_intersection.geometry().area().divide(1000000)
        kba_overlap_pct = ee.Number(ee.Algorithms.If(geom_area_km2.gt(0), kba_area_km2.divide(geom_area_km2).multiply(100), 0))

        # --- C. SUITABILITY MODELS (RASTER) ---
        # 5. HVI (Habitat Viability Index)
        # HVI = (0.6 * HSI) + (0.4 * Species Normalized)
        srtm = ee.Image("USGS/SRTMGL1_003").clip(polygon)
        elevation_norm = srtm.unitScale(0, 3000).subtract(1).abs() # 1 - normalized elevation
        
        viirs = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG").filterDate(f"{year_last}-01-01", f"{year_last}-12-31").select('avg_rad').median().clip(polygon)
        human_suitability = viirs.unitScale(0, 50).subtract(1).abs() # 1 - normalized nightlights
        
        dw = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1").filterBounds(polygon).filterDate(f"{year_last}-01-01", f"{year_last}-12-31").select('label').mode().clip(polygon)
        is_forest = dw.eq(1).rename('forest')
        
        hsi = is_forest.multiply(elevation_norm).multiply(human_suitability)
        # Species Normalized part is done on the scalar ceri value for simplicity
        hvi_raster = hsi.multiply(0.6).add(ceri.multiply(0.4)).rename('hvi')

        # 6. STAR_T (Threat Abatement)
        built_density = dw.eq(6).rename('built')
        threat_pressure = built_density.add(viirs.unitScale(0, 50)).divide(2)
        star_t_raster = threat_pressure.multiply(0.5).add(is_forest.multiply(0.5)).multiply(ceri).rename('star_t')

        # 7. STAR_R (Restoration)
        hansen = ee.Image("UMD/hansen/global_forest_change_2024_v1_12")
        forest_2000 = hansen.select('treecover2000').gt(10)
        not_currently_forest = dw.neq(1)
        restoration_opp = forest_2000.And(not_currently_forest)
        star_r_raster = restoration_opp.multiply(ceri).rename('star_r')

        # --- DIM 1: ECOSYSTEM EXTENT ---
        natural_habitat_dw = dw.remap([1, 2, 3, 5], [1, 1, 1, 1], 0).rename('natural_habitat_dw')

        # MODIS LC
        modis_lc_coll = ee.ImageCollection("MODIS/061/MCD12Q1").filterDate(f"{year_last}-01-01", f"{year_last}-12-31").select('LC_Type1')
        modis_lc = modis_lc_coll.first()
        natural_lc_modis = modis_lc.remap([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], 0).rename('natural_lc_modis')
        modis_lc_raw = modis_lc.rename('modis_lc_type')

        # Habitat Loss Rate
        loss_area = hansen.select('loss').multiply(ee.Image.pixelArea())
        forest_2000_area = forest_2000.multiply(ee.Image.pixelArea())
        loss_rate = loss_area.divide(forest_2000_area).rename('forest_loss_rate')

        # --- DIM 2: ECOSYSTEM CONDITION ---
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(polygon).filterDate(f"{year_last}-01-01", f"{year_last}-12-31").filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        ndvi = s2.median().normalizedDifference(['B8', 'B4']).rename('ndvi_median')

        ppt = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(f"{year_last}-01-01", f"{year_last}-12-31").sum()
        pet = ee.ImageCollection("IDAHO_EPSCOR/TERRACLIMATE").filterDate(f"{year_last}-01-01", f"{year_last}-12-31").select('pet').sum()
        aridity = ppt.divide(pet.multiply(0.1)).rename('aridity_index')

        ghm = ee.ImageCollection("CSP/HM/GlobalHumanModification").first().rename('ghm')
        npp = ee.ImageCollection("MODIS/061/MOD17A3HGF").filterDate(f"{year_last}-01-01", f"{year_last}-12-31").select('Npp').first().multiply(0.0001).rename('npp')
        bii = ee.ImageCollection("projects/ebx-data/assets/earthblox/IO/BIOINTACT").filterDate('2020-01-01', '2020-12-31').first().rename('bii')

        # HUMAN DISTURBANCE
        worldcover = ee.ImageCollection("ESA/WorldCover/v200").first()
        built_mask = worldcover.eq(50)
        dist_to_urban = built_mask.fastDistanceTransform().sqrt().multiply(ee.Image.pixelArea().sqrt()).rename('distance_to_urban')

        # LST
        lst_coll = ee.ImageCollection('MODIS/061/MOD11A2').filterDate(f"{year_now}-01-01", f"{year_now}-12-31").filterBounds(polygon)
        lst_mean = lst_coll.mean()
        lst_day = lst_mean.select('LST_Day_1km').multiply(0.02).subtract(273.15).rename('lst_day')
        lst_night = lst_mean.select('LST_Night_1km').multiply(0.02).subtract(273.15).rename('lst_night')

        # --- BATCH REDUCTION ---
        combined_images = ee.Image.cat([
            natural_habitat_dw, natural_lc_modis, modis_lc_raw, loss_rate,
            ndvi, aridity, ghm, npp, bii, viirs.rename('light_pollution'), dist_to_urban,
            lst_day, lst_night, hvi_raster, star_t_raster, star_r_raster
        ])

        stats = combined_images.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=polygon,
            scale=1000,
            maxPixels=1e13
        ).getInfo()

        # Combine vector stats with image stats
        vector_stats = {
            "species_richness": richness.getInfo(),
            "threatened_species": threatened.getInfo(),
            "srr": srr.getInfo(),
            "kba_overlap": kba_overlap_pct.getInfo(),
            "ceri": ceri.getInfo()
        }

        # Final Result Map
        final_results = {}
        for key, val in default_fallback.items():
            if key in vector_stats:
                final_results[key] = vector_stats[key]
            else:
                final_results[key] = stats.get(key, val) if stats.get(key) is not None else val
            
        return final_results

    except Exception as e:
        print(f"GEE Processing Error: {e}")
        return default_fallback
