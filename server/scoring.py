import numpy as np
import math

# ── Threshold Tables ─────────────────────────────────────────────────────
# Numeric encoding: VL=1, L=2, M=3, H=4, VH=5

PROTOCOL_A = {
    "bii":  {"breaks": [0.20, 0.40, 0.60, 0.80], "scores": [5, 4, 3, 2, 1], "higher_is_better": True},
    "flii": {"breaks": [2.0,  4.0,  6.0,  8.0],  "scores": [5, 4, 3, 2, 1], "higher_is_better": True},
    "msa":  {"breaks": [0.20, 0.40, 0.60, 0.80], "scores": [5, 4, 3, 2, 1], "higher_is_better": True},
    "flagship_habitat": {"breaks": [0.20, 0.40, 0.60, 0.80], "scores": [5, 4, 3, 2, 1], "higher_is_better": True},
    "ceri": {"breaks": [0.10, 0.20, 0.35, 0.50], "scores": [1, 2, 3, 4, 5], "higher_is_better": False},
    "star_t": {"breaks": [1.0, 3.0, 6.0, 9.0], "scores": [1, 2, 3, 4, 5], "higher_is_better": False},
    "kba_overlap": {"breaks": [1.0, 25.0, 75.0, 99.9], "scores": [1, 2, 3, 4, 5], "higher_is_better": False},
}

PROTOCOL_B_BREAKS = [30, 50, 70, 85]
PROTOCOL_B_SCORES = [5,  4,  3,  2, 1]
PROTOCOL_C_INDICATORS = {"cpland", "endemic_richness", "threatened_richness"}

DIM_MAP = {
    1: ["natural_habitat", "natural_landcover", "cpland", "forest_loss_rate", "kba_overlap"],
    2: ["ndvi", "habitat_health", "flii", "eii", "eii_structural", "eii_compositional", "eii_functional", "bii", "pdf", "aridity_index"],
    3: ["endemic_richness", "flagship_habitat"],
    4: ["threatened_richness", "ceri", "star_t"],
}

DIM_NAMES = {
    1: "Ecosystem Extent",
    2: "Ecosystem Condition",
    3: "Population",
    4: "Extinction Risk",
}

THREATS = ["ghm", "light_pollution", "hdi", "lst_day", "lst_night"]

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

def son_concern_label(score):
    if score is None: return "Insufficient data"
    if score < 4: return "Very Low"
    if score < 5: return "Low"
    if score < 7: return "Moderate"
    if score < 8: return "High"
    return "Very High"

def calculate_scorecard(scorecard_data, registry):
    # 1. Build results lookup from raw scorecard data
    results_lookup = {}
    for row in scorecard_data:
        # Match by name or display_name
        name = row.get("name") or row.get("indicator_name")
        if not name:
            disp = row.get("display_name", "").lower()
            for spec in registry.all():
                if spec.display_name.lower() == disp:
                    name = spec.name; break
        if name:
            results_lookup[name] = row

    # 2. Per-metric concern assignment (Notebook Logic)
    metric_concerns = {}
    for name, row in results_lookup.items():
        if name in THREATS: continue
        
        site_val = row.get("site_value")
        t2 = row.get("tier2_intactness")
        t1 = row.get("tier1_intactness")
        
        if not _is_valid(site_val): site_val = None
        if not _is_valid(t2): t2 = None
        if not _is_valid(t1): t1 = None
        
        cn, protocol, intact_used = None, "no ref", None
        
        if name in PROTOCOL_A and site_val is not None:
            cn = apply_protocol_a(name, site_val)
            protocol = "A"
        elif t2 is not None:
            cn = apply_protocol_b(t2)
            protocol = "B"
            intact_used = t2
        elif t1 is not None:
            cn = apply_protocol_b(t1)
            protocol = "C" if name in PROTOCOL_C_INDICATORS else "B-T1"
            intact_used = t1
            
        metric_concerns[name] = {
            "concern_numeric": cn,
            "concern_label": concern_label(cn),
            "protocol": protocol,
            "site_value": site_val,
            "intactness_used": intact_used,
            "display_name": row.get("display_name", name)
        }

    # 3. Dimension Scores
    dim_scores = {}
    for dim_num, indicators in DIM_MAP.items():
        vals = [mc["concern_numeric"] for n in indicators if (mc := metric_concerns.get(n)) and mc["concern_numeric"] is not None]
        dim_scores[dim_num] = sum(vals) / len(vals) if vals else None

    # 4. SoN Score
    valid_dims = {d: s for d, s in dim_scores.items() if s is not None}
    n_valid = len(valid_dims)
    son_score = None
    if n_valid >= 1:
        total = sum(valid_dims.values())
        son_score = (total - n_valid) / (n_valid * 4) * 10

    # 5. Dashboard Aggregation (Mapped to UI Keys)
    pillar_metrics = {f"Pillar-{i}: {DIM_NAMES.get(i, 'Indicator')}": {} for i in range(1, 5)}
    pillar_metrics["Pillar-5: Pressure"] = {}
    pillar_concerns = {k: {} for k in pillar_metrics}
    
    # UI Mapping to match Notebook Display Names exactly
    UI_MAP = {
        # Pillar 1
        "natural_habitat": "Natural Habitat Extent",
        "natural_landcover": "Natural Land Cover Proportion",
        "cpland": "Landscape Connectivity (CPLAND)",
        "forest_loss_rate": "Habitat Loss Rate",
        "kba_overlap": "KBA/IBA Overlap",
        # Pillar 2
        "ndvi": "Vegetation Structure (NDVI)",
        "habitat_health": "Habitat Health Index (HHI)",
        "flii": "Forest Landscape Integrity Index",
        "eii": "Ecosystem Integrity Index",
        "eii_structural": "EII: Structural Integrity",
        "eii_compositional": "EII: Compositional Integrity",
        "eii_functional": "EII: Functional Integrity",
        "bii": "Biodiversity Intactness Index",
        "pdf": "Potentially Disappeared Fraction",
        "aridity_index": "Aridity Index",
        # Pillar 3
        "endemic_richness": "Endemic Species Richness",
        "flagship_habitat": "Flagship Habitat Viability",
        # Pillar 4
        "threatened_richness": "Threatened Species Richness",
        "ceri": "Composite Extinction-Risk Index",
        "star_t": "STAR_T (Threat Abatement)",
        # Pillar 5 (Threats)
        "ghm": "GHM",
        "hdi": "HDI",
        "light_pollution": "Light Pollution",
        "lst_day": "Daytime Surface Temperature",
        "lst_night": "Nighttime Surface Temperature"
    }

    for name, mc in metric_concerns.items():
        spec = registry.get(name)
        if not spec: continue
        p_num = spec.pillar
        p_key = f"Pillar-{p_num}: {DIM_NAMES.get(p_num, 'Pressure' if p_num==5 else 'Indicator')}"
        ui_name = UI_MAP.get(name, mc["display_name"])
        
        # Dashboard expects 0-1 for most metrics in the bar charts
        val = mc["intactness_used"] if mc["intactness_used"] is not None else mc["site_value"]
        if name == "kba_overlap": val = mc["site_value"] / 100.0
        if p_num == 5: val = mc["site_value"]
        
        pillar_metrics[p_key][ui_name] = val
        pillar_concerns[p_key][ui_name] = mc["concern_numeric"]

    # Threats (Contextual - Pillar 5)
    p5_key = "Pillar-5: Pressure"
    for tname in THREATS:
        if tname in results_lookup:
            row = results_lookup[tname]
            ui_name = UI_MAP.get(tname, tname)
            val = row.get("site_value")
            
            # Ensure value is normalized for widgets if needed (Light is nW/cm2/sr)
            norm_val = val
            if tname == "light_pollution" and val is not None and val > 100:
                norm_val = val / 500.0 # scale to 0-1 for indicator bars if raw is high
            
            pillar_metrics[p5_key][ui_name] = norm_val
            pillar_concerns[p5_key][ui_name] = 1.0 # Default VL for threats (contextual)

    p5 = pillar_metrics[p5_key]
    p_vals = [p5.get("GHM", 0), p5.get("HDI", 0), (p5.get("Light Pollution", 0)/100.0 if p5.get("Light Pollution",0)>1 else p5.get("Light Pollution",0))]
    pressure_score = (sum(p_vals)/3)*10 if p_vals else 0

    return {
        "SoN Score": round(son_score, 1) if son_score is not None else None,
        "Extent": round(dim_scores.get(1), 2) if dim_scores.get(1) is not None else None,
        "Condition": round(dim_scores.get(2), 2) if dim_scores.get(2) is not None else None,
        "Population": round(dim_scores.get(3), 2) if dim_scores.get(3) is not None else None,
        "Extinction": round(dim_scores.get(4), 2) if dim_scores.get(4) is not None else None,
        "Pressure Score": round(pressure_score, 2),
        "metrics": pillar_metrics,
        "pillar_concerns": pillar_concerns,
        "n_valid": n_valid
    }
