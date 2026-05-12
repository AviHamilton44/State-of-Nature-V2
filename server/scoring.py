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
    
    # ── Threats & Pressure (Contextual, not in SoN score) ──
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
    3: "Population",
    4: "Extinction Risk",
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
    if score <= 4: return "Very Low"
    if score <= 5: return "Low"
    if score <= 7: return "Moderate"
    if score <= 8: return "High"
    return "Very High"

def calculate_scorecard(scorecard_data, registry):
    processed_rows = []
    for row in scorecard_data:
        clean_row = {}
        for k, v in row.items():
            if k in ["site_value", "tier1_intactness", "tier2_intactness"]:
                if v is None: clean_row[k] = None
                elif isinstance(v, (int, float)): clean_row[k] = float(v)
                elif isinstance(v, str):
                    try: 
                        vs = v.replace("%", "").strip()
                        clean_row[k] = float(vs) / 100.0 if "%" in v else float(vs)
                    except: clean_row[k] = None
                else: clean_row[k] = None
            else: clean_row[k] = v
        
        raw_name = str(clean_row.get("display_name") or clean_row.get("indicator") or "").strip()
        clean_row["_search_key"] = raw_name.lower()
        import re
        clean_row["_search_clean"] = re.sub(r"^[0-9A-Z.\s]+", "", clean_row["_search_key"]).strip()
        processed_rows.append(clean_row)

    metric_concerns = {}
    reg_specs = registry.all()
    
    for spec in reg_specs:
        s_slug = spec.name.lower()
        s_disp = spec.display_name.lower()
        
        matched_row = None
        for row in processed_rows:
            rk, rc = row["_search_key"], row["_search_clean"]
            if s_slug == rk or s_disp == rk or s_slug == rc or s_disp == rc:
                matched_row = row; break
            if rc and (rc in s_disp or s_disp in rc):
                matched_row = row; break
                
        if not matched_row: continue

        site_val = matched_row.get("site_value")
        t2 = matched_row.get("tier2_intactness")
        t1 = matched_row.get("tier1_intactness")

        cn, protocol, intactness_used = None, "no ref", None

        if spec.name in PROTOCOL_A_INDICATORS and site_val is not None:
            cn, protocol = apply_protocol_a(spec.name, site_val), "A"
        elif t2 is not None:
            cn, protocol, intactness_used = apply_protocol_b(t2), "B", t2
        elif t1 is not None:
            cn, protocol, intactness_used = apply_protocol_b(t1), "C", t1

        if cn is not None:
            metric_concerns[spec.name] = {
                "concern_numeric": cn, "concern_label": concern_label(cn),
                "protocol": protocol, "site_value": site_val,
                "intactness_used": intactness_used, "display_name": spec.display_name,
                "pillar": spec.pillar
            }

    dim_scores = {}
    dim_metrics = {}
    for dim_num, indicators in DIM_MAP.items():
        vals = [mc["concern_numeric"] for n in indicators if (mc := metric_concerns.get(n)) and mc["concern_numeric"] is not None]
        dim_metrics[dim_num] = [n for n in indicators if n in metric_concerns]
        dim_scores[dim_num] = sum(vals) / len(vals) if vals else None

    valid_dims = {d: s for d, s in dim_scores.items() if s is not None}
    n_valid = len(valid_dims)
    son_score = (sum(valid_dims.values()) - n_valid) / (n_valid * 4) * 10 if n_valid >= 1 else None

    # Aggregation for Frontend
    pillar_metrics = {f"Pillar-{i}: {DIM_NAMES.get(i, 'Pressure' if i==5 else 'Indicator')}": {} for i in range(1, 6)}
    raw_pillar_metrics = {k: {} for k in pillar_metrics}
    pillar_concerns = {k: {} for k in pillar_metrics}

    for name, mc in metric_concerns.items():
        p_num = mc["pillar"]
        p_key = f"Pillar-{p_num}: {DIM_NAMES.get(p_num, 'Pressure' if p_num==5 else 'Indicator')}"
        disp = mc["display_name"]
        
        # Dashboard wants normalized 0-1 for most, but raw for some
        norm = mc["intactness_used"] if mc["intactness_used"] is not None else mc["site_value"]
        if name == "kba_overlap": norm = mc["site_value"] / 100.0
        if p_num == 5: norm = mc["site_value"]
        
        # Specialized keys for Dashboard widgets
        final_disp = disp
        if name == "ghm": final_disp = "GHM"
        elif name == "hdi": final_disp = "HDI"
        elif name == "light_pollution": final_disp = "Light Pollution"
        elif name == "ndvi": final_disp = "NDVI"
        elif name == "habitat_health": final_disp = "Habitat Health Index"
        elif name == "flii": final_disp = "FLII"
        elif name == "eii": final_disp = "EII Overall"
        elif name == "bii": final_disp = "BII"
        elif name == "natural_habitat": final_disp = "Natural Habitat Extent"
        elif name == "natural_landcover": final_disp = "Natural Land Cover %"
        elif name == "forest_loss_rate": final_disp = "Habitat Loss Rate"
        elif name == "cpland": final_disp = "Connectivity (CPLAND)"
        elif name == "kba_overlap": final_disp = "KBA Overlap"
        elif name == "endemic_richness": final_disp = "Endemic / Small Range"
        elif name == "flagship_habitat": final_disp = "Habitat Viability Index"
        elif name == "threatened_richness": final_disp = "Threatened Species"
        elif name == "ceri": final_disp = "CERI"
        elif name == "star_t": final_disp = "STAR_T"
        
        pillar_metrics[p_key][final_disp] = norm
        raw_pillar_metrics[p_key][final_disp] = mc["site_value"]
        pillar_concerns[p_key][final_disp] = mc["concern_numeric"]

    # Calculate overall Pressure Score using aligned keys
    p5 = pillar_metrics.get("Pillar-5: Pressure", {})
    p_vals = [p5.get("GHM", 0), p5.get("HDI", 0), (p5.get("Light Pollution", 0) / 100.0 if p5.get("Light Pollution", 0) > 1 else p5.get("Light Pollution", 0))]
    pressure_score = (sum(p_vals) / 3) * 10

    return {
        "SoN Score": round(son_score, 1) if son_score is not None else None,
        "n_valid": n_valid, "partial": n_valid < 4,
        "Extent": round(dim_scores.get(1), 2) if dim_scores.get(1) is not None else None,
        "Condition": round(dim_scores.get(2), 2) if dim_scores.get(2) is not None else None,
        "Population": round(dim_scores.get(3), 2) if dim_scores.get(3) is not None else None,
        "Extinction": round(dim_scores.get(4), 2) if dim_scores.get(4) is not None else None,
        "Pressure Score": round(pressure_score, 2),
        "metrics": pillar_metrics, "raw_metrics": raw_pillar_metrics, "pillar_concerns": pillar_concerns
    }
