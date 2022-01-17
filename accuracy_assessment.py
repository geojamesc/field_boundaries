import fiona
import os
from shapely.geometry import shape


def fetch_polygons_to_compare(ref_polys_shp_fname, ext_polys_shp_fname, ref_geoid):
    """
    for a given ref_geoid return the polygon geometry associated with this
    from the input reference polygons shapefile and the set (list) of polygons
    in a second shapefile e.g. those that were extracted by a segmentation algo

    :param ref_polys_shp_fname:
    :param ext_polys_shp_fname:
    :param ref_geoid:
    :return: shapely.geometry.polygon.Polygon [shapely.geometry.polygon.Polygon..n]
    """
    ref_poly_geom = None
    ext_poly_geoms = []

    have_ref_polys = False
    have_ext_polys = False
    if os.path.exists(ref_polys_shp_fname):
        have_ref_polys = True
    if os.path.exists(ext_polys_shp_fname):
        have_ext_polys = True

    # TODO test that both shapefiles have geoid column

    if have_ref_polys and have_ext_polys:
        # brute force find all polygons in 2nd shapefile that intersect with 1 feature in 1st shapefile
        # TODO use rtree to speed things up as per https://maptiks.com/blog/spatial-queries-in-python/

        with fiona.open(ref_polys_shp_fname, "r") as ref_polys_src:
            with fiona.open(ext_polys_shp_fname, "r") as ext_polys_src:
                for ref_poly  in ref_polys_src:
                    if ref_poly["properties"]["geoid"] == ref_geoid:
                        ref_poly_geoid = ref_poly["properties"]["geoid"]
                        ref_poly_geom = shape(ref_poly["geometry"])
                        for ext_poly in ext_polys_src:
                            ext_poly_geoid = ext_poly["properties"]["geoid"]
                            ext_poly_geom = shape(ext_poly["geometry"])
                            if ext_poly_geom.intersects(ref_poly_geom):
                                ext_poly_geoms.append(ext_poly_geom)

    return ref_poly_geom, ext_poly_geoms


def compute_measure(ref_poly_geom, ext_poly_geoms, measure_to_compute):
    """
       in their paper Waldner have the following metrics to measure accuracy of segmentation

       1. Boundary Similarity
        - compare the boundary of a reference object coincident with that of a classified object

       2. Location Similarity
        - evaluates the similarity between the centroid position of classified and reference objects

       3. Oversegmentation Rate
        - measures incorrect subdivision of larger objects into smaller ones

       4. Undersegmentation Rate
        - measures incorrect consolidation of small adjacent objects into larger ones

       5. Intersection over Union
        - evaluates the overlap between reference and classified objects

       6. Shape similarity
        - compares the geometric form of a reference object with that of the classified objects
         - shape similarity is based on the normalized perimeter index (NPI) and concept of an equal area circle (eac)
          - https://postgis.net/docs/manual-3.2/ST_FrechetDistance.html
          - https://postgis.net/docs/manual-3.2/ST_HausdorffDistance.html

       all 6 metrics are defined to a range between 0 and 1; the closer to 1, the more accurate
       if an extracted field intersected with more that one field, metrics were weighted by the corresponding intersection areas
    """
    if ref_poly_geom is not None and ext_poly_geoms is not None:
        print("Measure to compute: ", measure_to_compute)
        print("Reference Poly Geom: ", type(ref_poly_geom))
        for g in ext_poly_geoms:
            print("Comparison Poly Geom: ", type(g))


def main():
    ref_polys_fname = "data/reference_polygons.shp"
    ext_polys_fname = "data/otb_extracted_polygons.shp"

    # do accuracy assessment for 1 reference polygon
    ref_geoid = 413

    # fetch the reference poly geometry and the other polygons we are comparing against
    ref_poly_geom, ext_poly_geoms = fetch_polygons_to_compare(ref_polys_fname, ext_polys_fname, ref_geoid)

    # compute aa measure for just this polygon
    compute_measure(ref_poly_geom, ext_poly_geoms, measure_to_compute="IOU")


if __name__ == "__main__":
    main()


