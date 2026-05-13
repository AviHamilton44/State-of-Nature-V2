import numpy as np
import pandas as pd

# Protocol A: Published literature thresholds (applied to raw site value)
PROTOCOL_A = {
    # ── Ecosystem Condition ──
    "bii":  {"breaks": [0.20, 0.40, 0.60, 0.80], "scores": [5, 4, 3, 2, 1], "higher_is_better": True},
    "flii": {"breaks": [2.0,  4.0,  6.0,  8.0],  "scores": [5, 4, 3, 2, 1], "higher_is_better": True},
    "msa":  {"breaks": [0.20, 0.40, 0.60, 0.80], "scores": [5, 4, 3, 2, 1], "higher_is_better": True},

    # ── Species Population Size ──
    "flagship_habitat": {"breaks": [0.20, 0.40, 0.60, 0.80], "scores": [5, 4, 3, 2, 1], "higher_is_better": True},

    # ── Species Extinction Risk ──
    "ceri": {"breaks": [0.10, 0.20, 0.35, 0.50], "scores": [1, 2, 3, 4, 5], "higher_is_better": False},
    "star_t": {"breaks": [1.0, 3.0, 6.0, 9.0], "scores": [1, 2, 3, 4, 5], "higher_is_better": False},
    "kba_overlap": {"breaks": [1.0, 25.0, 75.0, 99.9], "scores": [1, 2, 3, 4, 5], "higher_is_better": False},
    
    # ── Threats & Pressure ──
    "lst_day": {"breaks": [32.0, 36.0, 40.0, 44.0], "scores": [1, 2, 3, 4, 5], "higher_is_better": False},
    "lst_night": {"breaks": [22.0, 26.0, 30.0, 34.0], "scores": [1, 2, 3, 4, 5], "higher_is_better": False},
    "ghm": {"breaks": [0.1, 0.3, 0.6, 0.9], "scores": [1, 2, 3, 4, 5], "higher_is_better": False},
    "hdi": {"breaks": [0.5, 0.6, 0.7, 0.8], "scores": [1, 2, 3, 4, 5], "higher_is_better": False},
    "light_pollution": {"breaks": [1.0, 5.0, 30.0, 100.0], "scores": [1, 2, 3, 4, 5], "higher_is_better": False},
}

PROTOCOL_A_INDICATORS = set(PROTOCOL_A.keys())

# Protocol B v1.0 -- FIXED thresholds (applied to Tier 2 intactness %, or Tier 1 where T2 unavailable)
PROTOCOL_B_BREAKS = [30, 50, 70, 85]
PROTOCOL_B_SCORES = [5,  4,  3,  2, 1]

# Protocol C: Tier 1 regional comparison
PROTOCOL_C_INDICATORS = {"cpland", "endemic_richness", "threatened_richness"}

# TNFD Annex 2 dimension membership
DIM_MAP = {
    1: ["natural_habitat", "natural_landcover", "cpland", "forest_loss_rate", "kba_overlap"],
    2: ["ndvi", "habitat_health", "flii", "eii", "eii_structural", "eii_compositional", "eii_functional", "bii", "pdf", "aridity_index"],
    3: ["endemic_richness", "flagship_habitat"],
    4: ["threatened_richness", "ceri", "star_t"]
}

THREATS = ["ghm", "light_pollution", "hdi", "lst_day", "lst_night"]

DIM_NAMES = {
    1: "Ecosystem Extent",
    2: "Ecosystem Condition",
    3: "Species Population Size",
    4: "Species Extinction Risk",
}

def _is_valid(v):
    if v is None: return False
    try: return np.isfinite(float(v))
    except: return False

def apply_protocol_a(indicator_name, site_value):
    if not _is_valid(site_value): return None
    spec = PROTOCOL_A[indicator_name]
    val = float(site_value)
    for i, b in enumerate(spec["breaks"]):
        if val < b: return spec["scores"][i]
    return spec["scores"][-1]

def apply_protocol_b(intactness_ratio):
    if not _is_valid(intactness_ratio): return None
    pct = float(intactness_ratio) * 100
    for i, b in enumerate(PROTOCOL_B_BREAKS):
        if pct < b: return PROTOCOL_B_SCORES[i]
    return PROTOCOL_B_SCORES[-1]

def concern_label(numeric):
    if numeric is None: return "—"
    return {1: "VL", 2: "L", 3: "M", 4: "H", 5: "VH"}.get(round(numeric), "—")

def dim_label(score):
    if score is None: return "—"
    s = round(score * 2) / 2
    if s <= 1.5: return "Very Low"
    if s <= 2.5: return "Low"
    if s <= 3.5: return "Moderate"
    if s <= 4.5: return "High"
    return "Very High"

def son_concern_label(score):
    if score is None: return "Insufficient data"
    if score < 4: return "Very Low"
    if score < 5: return "Low"
    if score < 7: return "Moderate"
    if score < 8: return "High"
    return "Very High"

def calculate_scorecard(scorecard_data, registry):
    # scorecard_data is report["scorecard"] (list of dicts)
    df = pd.DataFrame(scorecard_data)
    
    results_lookup = {}
    for _, row in df.iterrows():
        # Try to find slug from name or display_name
        name = (row.get("indicator") or row.get("indicator_name") or row.get("name") or "").strip().lower()
        display_name = (row.get("display_name") or "").strip().lower()
        slug = None
        
        for spec in registry.all():
            s_name = spec.name.lower()
            s_display = spec.display_name.lower()
            if (name and s_name == name) or (display_name and s_display == display_name) or (name and s_display == name):
                slug = spec.name; break
        
        lookup_key = slug or name or display_name
        if lookup_key:
            results_lookup[lookup_key] = row.to_dict()

    metric_concerns = {}

    for name, row in results_lookup.items():
        site_val = row.get("site_value")
        t2       = row.get("tier2_intactness")
        t1       = row.get("tier1_intactness")

        if not _is_valid(site_val): site_val = None
        if not _is_valid(t2):       t2 = None
        if not _is_valid(t1):       t1 = None

        if name in PROTOCOL_A_INDICATORS and site_val is not None:
            cn = apply_protocol_a(name, site_val)
            protocol = "A (published absolute threshold)"
            intactness_used = None
            t_ref = None
        elif t2 is not None:
            cn = apply_protocol_b(t2)
            protocol = "B v1.0 (Tier 2 intactness)"
            intactness_used = t2
            t_ref = row.get("tier2_reference")
        elif t1 is not None:
            cn = apply_protocol_b(t1)
            if name in PROTOCOL_C_INDICATORS:
                protocol = "C (Tier 1 regional — designed ref for this indicator)"
            else:
                protocol = "B v1.0 (Tier 1 fallback — T2 unavailable)"
            intactness_used = t1
            t_ref = row.get("tier1_reference")
        else:
            cn = None
            protocol = "— (no reference computable)"
            intactness_used = None
            t_ref = None

        print(f"[DEBUG] Indicator: {name}, Value: {site_val}, CN: {cn}, Label: {concern_label(cn)}")
        metric_concerns[name] = {
            "concern_numeric":  cn,
            "concern_label":    concern_label(cn),
            "protocol":         protocol,
            "intactness_used":  intactness_used,
            "site_value":       site_val,
            "display_name":     row.get("display_name", name),
        }

    dim_scores   = {}
    dim_populated = {}

    for dim_num, indicators in DIM_MAP.items():
        values, populated_names = [], []
        for name in indicators:
            mc = metric_concerns.get(name)
            if mc and mc["concern_numeric"] is not None:
                values.append(mc["concern_numeric"])
                populated_names.append(name)
        dim_populated[dim_num] = populated_names
        dim_scores[dim_num] = sum(values) / len(values) if values else None

    valid_dims = {str(d): s for d, s in dim_scores.items() if s is not None}
    n_valid    = len(valid_dims)

    if n_valid >= 1:
        total     = sum(valid_dims.values())
        son_score = (total - n_valid) / (n_valid * 4) * 10
        partial   = n_valid < 4
    else:
        son_score = None
        partial   = True
        
    # ── Final Schema Mapping for Frontend ───────────────────────────────────────────
    
    # Pillar mapping for metrics object
    pillar_metrics = {
        "Pillar-1: Ecosystem Extent": {},
        "Pillar-2: Ecosystem Condition": {},
        "Pillar-3: Population": {},
        "Pillar-4: Extinction Risk": {},
        "Pillar-5: Pressure": {}
    }

    # Helper to get normalized value (0-1) for a metric
    def get_norm(name):
        mc = metric_concerns.get(name)
        if not mc: return "Coming soon"
        
        # If Protocol A, we need to map the absolute value to 0-1
        if mc["protocol"].startswith("A"):
            val = mc["site_value"]
            if val is None: return 0
            if name == "flii": return val / 10.0
            if name == "kba_overlap": return val / 100.0
            if name == "bii": return val # BII is already 0-1
            if name == "ceri": return 1.0 - val # CERI 0 is best, 1 is worst
            if name == "star_t": return 1.0 - min(val / 10.0, 1.0) # STAR_T 0 is best
            if name == "flagship_habitat": return val # already 0-1
            return val
            
        # If Protocol B/C, use intactness_used
        return mc["intactness_used"] if mc["intactness_used"] is not None else 0

    # Pillar 1
    pillar_metrics["Pillar-1: Ecosystem Extent"] = {
        "Natural Habitat Extent": get_norm("natural_habitat"),
        "Natural Land Cover %": get_norm("natural_landcover"),
        "Habitat Loss Rate": get_norm("forest_loss_rate"),
        "Connectivity (CPLAND)": get_norm("cpland"),
        "KBA Overlap": get_norm("kba_overlap")
    }

    # Pillar 2
    pillar_metrics["Pillar-2: Ecosystem Condition"] = {
        "NDVI": get_norm("ndvi"),
        "Habitat Health Index": get_norm("habitat_health"),
        "FLII": get_norm("flii"),
        "EII Overall": get_norm("eii"),
        "EII Structural": get_norm("eii_structural"),
        "EII Compositional": get_norm("eii_compositional"),
        "EII Functional": get_norm("eii_functional"),
        "BII": get_norm("bii"),
        "PDF": get_norm("pdf"),
        "Aridity Index": get_norm("aridity_index")
    }

    # Pillar 3
    pillar_metrics["Pillar-3: Population"] = {
        "Endemic / Small Range": get_norm("endemic_richness"),
        "Habitat Viability Index": get_norm("flagship_habitat")
    }

    # Pillar 4
    pillar_metrics["Pillar-4: Extinction Risk"] = {
        "Threatened Species": get_norm("threatened_richness"),
        "CERI": get_norm("ceri"),
        "STAR_T": get_norm("star_t")
    }

    # Pillar 5 (Pressure)
    res_lookup = results_lookup
    pillar_metrics["Pillar-5: Pressure"] = {
        "GHM": res_lookup.get("ghm", {}).get("site_value", 0),
        "Light Pollution": res_lookup.get("light_pollution", {}).get("site_value", 0),
        "HDI": res_lookup.get("hdi", {}).get("site_value", 0),
        "Day LST": res_lookup.get("lst_day", {}).get("site_value", 0),
        "Night LST": res_lookup.get("lst_night", {}).get("site_value", 0)
    }

    # Calculate Pressure Score (0-10 scale, Higher = Worse)
    pressure_vals = [
        res_lookup.get("ghm", {}).get("site_value", 0),
        res_lookup.get("light_pollution", {}).get("site_value", 0) / 100.0, # Normalizing VIIRS for avg
        res_lookup.get("hdi", {}).get("site_value", 0)
    ]
    pressure_score = (sum(pressure_vals) / len(pressure_vals)) * 10 if pressure_vals else 0

    # Collect Raw Site Values for Display
    raw_pillar_metrics = {
        "Pillar-1: Ecosystem Extent": {},
        "Pillar-2: Ecosystem Condition": {},
        "Pillar-3: Population": {},
        "Pillar-4: Extinction Risk": {},
        "Pillar-5: Pressure": {}
    }

    def get_raw(name):
        mc = metric_concerns.get(name)
        if mc: return mc["site_value"]
        if name in res_lookup: return res_lookup[name].get("site_value")
        return 0

    # Populate Raw
    raw_pillar_metrics["Pillar-1: Ecosystem Extent"] = {
        "Natural Habitat Extent": get_raw("natural_habitat"),
        "Natural Land Cover %": get_raw("natural_landcover"),
        "Habitat Loss Rate": get_raw("forest_loss_rate"),
        "Connectivity (CPLAND)": get_raw("cpland"),
        "KBA Overlap": get_raw("kba_overlap")
    }
    raw_pillar_metrics["Pillar-2: Ecosystem Condition"] = {
        "NDVI": get_raw("ndvi"),
        "Habitat Health Index": get_raw("habitat_health"),
        "FLII": get_raw("flii"),
        "EII Overall": get_raw("eii"),
        "EII Structural": get_raw("eii_structural"),
        "EII Compositional": get_raw("eii_compositional"),
        "EII Functional": get_raw("eii_functional"),
        "BII": get_raw("bii"),
        "PDF": get_raw("pdf"),
        "Aridity Index": get_raw("aridity_index")
    }
    raw_pillar_metrics["Pillar-3: Population"] = {
        "Endemic / Small Range": get_raw("endemic_richness"),
        "Habitat Viability Index": get_raw("flagship_habitat")
    }
    raw_pillar_metrics["Pillar-4: Extinction Risk"] = {
        "Threatened Species": get_raw("threatened_richness"),
        "CERI": get_raw("ceri"),
        "STAR_T": get_raw("star_t")
    }
    raw_pillar_metrics["Pillar-5: Pressure"] = pillar_metrics["Pillar-5: Pressure"]

    # Pillar mapping for concern levels (1-5)
    pillar_concerns = {
        "Pillar-1: Ecosystem Extent": {},
        "Pillar-2: Ecosystem Condition": {},
        "Pillar-3: Population": {},
        "Pillar-4: Extinction Risk": {},
        "Pillar-5: Pressure": {}
    }

    def get_cn(name):
        mc = metric_concerns.get(name)
        return mc["concern_numeric"] if mc else None

    # Pillar Concerns
    pillar_concerns["Pillar-1: Ecosystem Extent"] = {
        "Natural Habitat Extent": get_cn("natural_habitat"),
        "Natural Land Cover %": get_cn("natural_landcover"),
        "Habitat Loss Rate": get_cn("forest_loss_rate"),
        "Connectivity (CPLAND)": get_cn("cpland"),
        "KBA Overlap": get_cn("kba_overlap")
    }
    pillar_concerns["Pillar-2: Ecosystem Condition"] = {
        "NDVI": get_cn("ndvi"),
        "Habitat Health Index": get_cn("habitat_health"),
        "FLII": get_cn("flii"),
        "EII Overall": get_cn("eii"),
        "EII Structural": get_cn("eii_structural"),
        "EII Compositional": get_cn("eii_compositional"),
        "EII Functional": get_cn("eii_functional"),
        "BII": get_cn("bii"),
        "PDF": get_cn("pdf"),
        "Aridity Index": get_cn("aridity_index")
    }
    pillar_concerns["Pillar-3: Population"] = {
        "Endemic / Small Range": get_cn("endemic_richness"),
        "Habitat Viability Index": get_cn("flagship_habitat")
    }
    pillar_concerns["Pillar-4: Extinction Risk"] = {
        "Threatened Species": get_cn("threatened_richness"),
        "CERI": get_cn("ceri"),
        "STAR_T": get_cn("star_t")
    }
    pillar_concerns["Pillar-5: Pressure"] = {
        "GHM": get_cn("ghm"),
        "Light Pollution": get_cn("light_pollution"),
        "HDI": get_cn("hdi"),
        "Day LST": get_cn("lst_day"),
        "Night LST": get_cn("lst_night")
    }

    return {
        "SoN Score": round(son_score, 1) if son_score is not None else None,
        "n_valid": n_valid,
        "partial": partial,
        "Extent": round(dim_scores.get(1), 2) if dim_scores.get(1) else None,
        "Condition": round(dim_scores.get(2), 2) if dim_scores.get(2) else None,
        "Population": round(dim_scores.get(3), 2) if dim_scores.get(3) else None,
        "Extinction": round(dim_scores.get(4), 2) if dim_scores.get(4) else None,
        "Pressure Score": round(pressure_score, 2),
        "metrics": pillar_metrics,
        "raw_metrics": raw_pillar_metrics,
        "pillar_concerns": pillar_concerns,
        "metric_concerns": metric_concerns
    }

