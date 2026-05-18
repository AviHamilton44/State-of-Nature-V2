import ee
import logging

logger = logging.getLogger(__name__)

def extract_cpland(geometry, config=None):
    """
    Extracts cropland percentage for a given geometry using the custom GEE asset.
    Asset: projects/darukaa-earth-product/assets/biodiversity_India_PV_Binary_2025_Full_Mosaic
    """
    asset_id = "projects/darukaa-earth-product/assets/biodiversity_India_PV_Binary_2025_Full_Mosaic"
    
    try:
        # Load the asset
        img = ee.Image(asset_id)
        
        # Determine ee.Geometry
        try:
            from darukaa_reference.indicators import _to_ee
            eg = _to_ee(geometry)
        except Exception:
            if isinstance(geometry, dict):
                if geometry.get('type') == 'FeatureCollection':
                    eg = ee.FeatureCollection(geometry).geometry()
                elif geometry.get('type') == 'Feature':
                    eg = ee.Geometry(geometry['geometry'])
                else:
                    eg = ee.Geometry(geometry)
            else:
                if not isinstance(geometry, ee.Geometry):
                    try:
                        from shapely.geometry import mapping
                        from shapely.ops import transform as st
                        if hasattr(geometry, "has_z") and geometry.has_z:
                            geometry = st(lambda x, y, z=None: (x, y), geometry)
                        eg = ee.Geometry(mapping(geometry))
                    except ImportError:
                        eg = geometry
                else:
                    eg = geometry

        # Binary raster handling: 1 = Cropland, 0 = Non-cropland
        # Self mask non-cropland pixels
        cropland_mask = img.eq(1)
        cropland_img = img.updateMask(cropland_mask)
        
        # Use native scale
        try:
            scale = img.projection().nominalScale()
            if scale.getInfo() <= 0:
                scale = 30
        except Exception:
            scale = 30
            
        # Area calculation in hectares (1 hectare = 10,000 square meters)
        pixel_area_ha = ee.Image.pixelArea().divide(10000)
        
        # Total area
        total_area_dict = pixel_area_ha.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=eg,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True
        )
        
        # Cropland area
        cropland_area_dict = pixel_area_ha.updateMask(cropland_mask).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=eg,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True
        )
        
        import math
        
        total_area_val = total_area_dict.values().get(0)
        cropland_area_val = cropland_area_dict.values().get(0)
        
        # Safely extract and convert to float, catching any None values
        total_area_ha = total_area_val.getInfo()
        cropland_area_ha = cropland_area_val.getInfo()
        
        if total_area_ha is None or cropland_area_ha is None:
            return {"value": None, "pixels": None}
            
        total_area_ha = float(total_area_ha)
        cropland_area_ha = float(cropland_area_ha)
        
        # Check for NaN explicitly
        if math.isnan(total_area_ha) or total_area_ha <= 0:
            return {"value": None, "pixels": None}
        elif math.isnan(cropland_area_ha) or cropland_area_ha < 0:
            return {"value": None, "pixels": None}
        else:
            cropland_percent = (cropland_area_ha / total_area_ha) * 100.0
            
        # Final safety check on percentage
        if math.isnan(cropland_percent):
            return {"value": None, "pixels": None}

        logger.info(f"CPLAND computed: {cropland_percent:.2f}% (Cropland: {cropland_area_ha:.2f}ha / Total: {total_area_ha:.2f}ha)")

        return {
            "metric": "cpland",
            "value": cropland_percent,
            "unit": "%",
            "metadata": {
                "cropland_area_ha": cropland_area_ha,
                "total_area_ha": total_area_ha,
                "source": "Custom GEE Asset",
                "asset_id": asset_id
            },
            "pixels": None  # Maintain compatibility with legacy pipeline which expects pixels
        }

    except Exception as e:
        logger.error(f"Failed to extract CPLAND metric from {asset_id}: {str(e)}")
        # Do not raise exception, return None to gracefully exclude from score
        return {"value": None, "pixels": None}
