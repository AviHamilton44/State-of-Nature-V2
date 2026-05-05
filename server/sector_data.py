
def get_sector_son_matrix():
    groups = {
        "Extractive": {"scores": (1.8, 1.6, 1.5, 1.5), "sectors": [
            "Coal Operations", "Iron & Steel Producers", "Metals & Mining", 
            "Oil & Gas – Exploration & Production", "Oil & Gas – Midstream", 
            "Oil & Gas – Refining & Marketing", "Oil & Gas – Services"
        ]},
        "Agriculture & Forestry": {"scores": (2.4, 2.2, 2.0, 2.1), "sectors": [
            "Agricultural Products", "Meat, Poultry & Dairy", "Tobacco", "Forestry Management", "Pulp & Paper Products"
        ]},
        "Consumer Goods": {"scores": (3.2, 3.0, 2.8, 3.1), "sectors": [
            "Apparel, Accessories & Footwear", "Appliance Manufacturing", "Building Products & Furnishings",
            "Household & Personal Products", "Toys & Sporting Goods", "Alcoholic Beverages", "Food Retailers & Distributors",
            "Non-Alcoholic Beverages", "Processed Foods", "Restaurants", "Automobiles", "Auto Parts", "Casinos & Gaming", "Hotels & Lodging", "Leisure Facilities"
        ]},
        "Manufacturing & Industrial": {"scores": (3.0, 2.8, 2.9, 3.0), "sectors": [
            "Construction Materials", "Engineering & Construction Services", "Biofuels", "Fuel Cells & Industrial Batteries",
            "Chemicals", "Containers & Packaging", "Electrical & Electronic Equipment", "Industrial Machinery & Goods",
            "Aerospace & Defense", "Electronic Mfg Services & ODM", "Hardware", "Semiconductors"
        ]},
        "Utilities & Energy": {"scores": (3.4, 3.2, 3.1, 3.2), "sectors": [
            "Electric Utilities & Power Generators", "Gas Utilities & Distributors", "Waste Management", 
            "Water Utilities & Services", "Solar Technology & Project Developers", "Wind Technology & Project Developers"
        ]},
        "Transport": {"scores": (3.6, 3.4, 3.5, 3.6), "sectors": [
            "Air Freight & Logistics", "Airlines", "Car Rental & Leasing", "Cruise Lines", 
            "Marine Transportation", "Rail Transportation", "Road Transportation"
        ]},
        "Technology & Services": {"scores": (4.5, 4.4, 4.6, 4.5), "sectors": [
            "E-Commerce", "Multiline & Specialty Retailers & Distributors", "Biotechnology & Pharmaceuticals",
            "Drug Retailers", "Health Care Delivery", "Health Care Distributors", "Managed Care", "Medical Equipment & Supplies",
            "Real Estate", "Real Estate Services", "Advertising & Marketing", "Education", "Media & Entertainment", 
            "Professional & Commercial Services", "Internet Media & Services", "Software & IT Services", "Telecommunications Services"
        ]},
        "Finance": {"scores": (4.8, 4.9, 4.8, 4.9), "sectors": [
            "Asset Management & Custody Activities", "Commercial Banks", "Consumer Finance", 
            "Investment Banking & Brokerage", "Insurance", "Mortgage Finance", "Security & Commodity Exchanges"
        ]}
    }

    biomes_data = [
        ("Tropical-subtropical forests", "T1"),
        ("Temperate-boreal forests and woodlands", "T2"),
        ("Shrublands and shrubby woodlands", "T3"),
        ("Savannas and grasslands", "T4"),
        ("Deserts and semi-deserts", "T5"),
        ("Polar/alpine (cryogenic)", "T6"),
        ("Intensive land-use", "T7"),
        ("Marine shelf", "M1"),
        ("Pelagic ocean waters", "M2"),
        ("Deep sea floors", "M3"),
        ("Anthropogenic marine", "M4"),
        ("Rivers and streams", "F1"),
        ("Lakes", "F2"),
        ("Artificial wetlands", "F3"),
        ("Subterranean lithic", "S1"),
        ("Anthropogenic subterranean voids", "S2"),
        ("Shorelines", "MT1"),
        ("Supralittoral coastal", "MT2"),
        ("Anthropogenic shorelines", "MT3"),
        ("Subterranean freshwaters", "SF1"),
        ("Anthropogenic subterranean freshwaters", "SF2"),
        ("Semi-confined transitional waters", "FM1"),
        ("Brackish tidal", "MFT1"),
        ("Subterranean tidal", "SM1"),
        ("Palustrine wetlands", "TF1")
    ]
    
    matrix = []
    for group_name, info in groups.items():
        d1, d2, d3, d4 = info["scores"]
        son = ((d1 + d2 + d3 + d4 - 4) / 16) * 10
        
        for sector in info["sectors"]:
            for b_name, b_code in biomes_data:
                # Add slight random variation per biome
                import zlib
                seed_str = f"{sector}{b_code}"
                variation = (zlib.crc32(seed_str.encode()) % 10 - 5) / 50.0 
                
                v_son = max(0, min(10, son + (variation * 10)))
                v_d1 = max(1, min(5, d1 + variation))
                v_d2 = max(1, min(5, d2 + variation))
                v_d3 = max(1, min(5, d3 + variation))
                v_d4 = max(1, min(5, d4 + variation))

                matrix.append({
                    "sector": sector,
                    "group": group_name,
                    "biome": b_name,
                    "biome_code": b_code,
                    "son_score": round(v_son, 2),
                    "dimensions": {
                        "extent": round(v_d1, 2),
                        "condition": round(v_d2, 2),
                        "population": round(v_d3, 2),
                        "extinction": round(v_d4, 2)
                    }
                })
    
    return matrix
