import shapefile
from shapely.geometry import shape
from shapely.ops import unary_union, transform
import pyproj
import os

def calculate_kba_overlap(site_geojson):
    """
    Calculates KBA Overlap percentage using local KBA_Datasets shapefile.
    Target: KBA_Datasets/KBA_Global_POL_SEP25.shp
    """
    # Dynamic path based on workspace structure
    shp_path = os.path.join(os.path.dirname(__file__), "..", "KBA_Datasets", "KBA_Global_POL_SEP25.shp")
    
    if not os.path.exists(shp_path):
        print(f"Warning: Local KBA shapefile not found at {shp_path}. Falling back to GEE.")
        return None

    try:
        # 1. Parse Site Geometry
        if site_geojson.get('type') == 'FeatureCollection' and len(site_geojson.get('features', [])) > 0:
            site_geom = shape(site_geojson['features'][0]['geometry'])
        elif site_geojson.get('geometry'):
            site_geom = shape(site_geojson['geometry'])
        else:
            site_geom = shape(site_geojson)
            
        # 2. Setup Projections (Equal Earth for accurate area)
        wgs84 = pyproj.CRS("EPSG:4326")
        equal_area = pyproj.CRS("EPSG:8857") # Equal Earth
        project = pyproj.Transformer.from_crs(wgs84, equal_area, always_xy=True).transform
        
        site_projected = transform(project, site_geom)
        site_area_km2 = site_projected.area / 1_000_000
        
        if site_area_km2 <= 0:
            return 0.0

        # 3. Stream through Shapefile with Bounding Box Filter
        site_bbox = site_geom.bounds # (minx, miny, maxx, maxy)
        intersection_pieces = []
        
        with shapefile.Reader(shp_path) as sf:
            # We use iterShapeRecords to minimize memory usage
            for shapedat in sf.iterShapeRecords():
                # Check bounding box intersection before full geometry check
                # shapedat.shape.bbox is [minx, miny, maxx, maxy]
                s_bbox = shapedat.shape.bbox
                if not (s_bbox[2] < site_bbox[0] or s_bbox[0] > site_bbox[2] or 
                        s_bbox[3] < site_bbox[1] or s_bbox[1] > site_bbox[3]):
                    
                    # Potential match
                    kba_geom = shape(shapedat.shape.__geo_interface__)
                    if site_geom.intersects(kba_geom):
                        intersection_pieces.append(site_geom.intersection(kba_geom))
        
        if not intersection_pieces:
            return 0.0
            
        # 4. Accurate Area Calculation (Dissolving Overlaps)
        union_intersection = unary_union(intersection_pieces)
        union_projected = transform(project, union_intersection)
        intersection_area_km2 = union_projected.area / 1_000_000
        
        overlap_pct = (intersection_area_km2 / site_area_km2) * 100
        return min(100.0, max(0.0, round(overlap_pct, 2)))

    except Exception as e:
        print(f"Local KBA Processing Error: {e}")
        return None
