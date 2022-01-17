import fiona

# for the reference and extracted shapefiles rewrite with just unq_geoid and geom column
# since in the sgov data FID_1 is NOT unq

# declare that inputs need to follow this schema

sink_schema = {
    "geometry": "Polygon",
    "properties": {
        "geoid": "int"
    }
}

#in_shp_fname = "/home/james/Work/Rubicon/agrimetrics_041121/JNCC_Test_Data/Kelso_Training_Validation.shp"

in_shp_fname = "/home/james/Work/Rubicon/agrimetrics_041121/JNCC_Test_Data/OTB_extracted_polys/otb_mean_shift_jncc_params_test_aoi_isect_w_training.shp"

with fiona.open(in_shp_fname, "r") as source:
    with fiona.open("/home/james/Desktop/otb_extracted_polygons.shp", "w", crs=source.crs, driver=source.driver, schema=sink_schema) as sink:
        geoid = 1
        for f in source:
            sink.write(
                {
                    "geometry": f["geometry"],
                    "properties": {
                        "geoid": geoid
                    }
                }
            )
            geoid += 1