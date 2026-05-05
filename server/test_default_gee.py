import ee

try:
    ee.Initialize(project='gaurav-singh-007')
    print("Successfully initialized with default credentials for gaurav-singh-007")

    g = ee.Geometry.Polygon([[
        [76.0, 20.0], [76.1, 20.0], [76.1, 20.1], [76.0, 20.1], [76.0, 20.0]
    ]])

    pa = "projects/darukaa-earth-product/assets/biodiversity_India_PV_Binary_2025_Full_Mosaic"
    img = ee.Image(pa).select(0)
    sm = img.projection().nominalScale().getInfo()
    print("Scale:", sm)
    import math
    rp=int(math.ceil((10+0.5*sm)/sm))
    core=img.eq(1).unmask(0).rename("b").reduceNeighborhood(reducer=ee.Reducer.min(),kernel=ee.Kernel.circle(rp,units="pixels")).rename("c")
    ca=core.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(),geometry=g,scale=sm,maxPixels=1e13)
    pa_m2=float(g.area().getInfo())
    
    val = max(0,min(100,100*float(ee.Number(ca.get("c")).getInfo())/pa_m2))
    print("CPLAND Value:", val)

except Exception as e:
    print("Error:", e)
