import fiona
import os
from shapely.geometry import shape


def fetch_polygons_to_compare(ref_polys_shp_fname, ext_polys_shp_fname, ref_geoid_fld_name, ext_geoid_fld_name, ref_geoid):
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

    if have_ref_polys and have_ext_polys:
        # TODO use rtree to speed things up rather than nasty brute force approach we have here at the moment
        #  https://maptiks.com/blog/spatial-queries-in-python/

        with fiona.open(ref_polys_shp_fname, "r") as ref_polys_src:
            with fiona.open(ext_polys_shp_fname, "r") as ext_polys_src:
                for ref_poly  in ref_polys_src:
                    if ref_poly["properties"][ref_geoid_fld_name] == ref_geoid:
                        ref_poly_geoid = ref_poly["properties"][ref_geoid_fld_name]
                        ref_poly_geom = shape(ref_poly["geometry"])
                        for ext_poly in ext_polys_src:
                            ext_poly_geoid = ext_poly["properties"][ext_geoid_fld_name]
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
         - the area of overlap between the predicted (bounding box) and the target (bounding box), divided
           by the area of their union.

       6. Shape similarity
        - compares the geometric form of a reference object with that of the classified objects
         - shape similarity is based on the normalized perimeter index (NPI) and concept of an equal area circle (eac)
          - https://postgis.net/docs/manual-3.2/ST_FrechetDistance.html
          - https://postgis.net/docs/manual-3.2/ST_HausdorffDistance.html

       all 6 metrics are defined to a range between 0 and 1; the closer to 1, the more accurate
       if an extracted field intersected with more that one field, metrics were weighted by the corresponding intersection areas
    """

    computed_measure = None

    if ref_poly_geom is not None and ext_poly_geoms is not None:
        if measure_to_compute == 'intersection_over_union':

            # the reference polygon
            p1 = ref_poly_geom

            # the predicted polygon
            # sometimes we will have 1:M, for now just grab first other poly
            #for g in ext_poly_geoms:
            #    print("Comparison Poly Geom: ", type(g))
            p2 = ext_poly_geoms[0]

            # use shapely to compute intersection over union
            computed_measure = round(p1.intersection(p2).area / p1.union(p2).area, 4)

    return computed_measure


def main():
    ref_polys_fname = "data/simple_reference_polygons.shp"
    ext_polys_fname = "data/simple_extracted_polygons.shp"

    # names of geoid fieldnames in vector input files
    ref_geoid_fld_name = "id"
    ext_geoid_fld_name = "id"

    # TODO at moment just doing the calc for 1 feature, the id of which, the user has supplied
    #  really we want to do this for all features
    ##################################################################################
    # set this to the id of reference polygon we want to find predicted polygon(s) for
    ref_geoid = 2
    ##################################################################################

    # fetch the reference poly geometry and the intersecting predicted polygons

    # TODO at the moment doing this by brute force by comparing all predicted polygons with the reference polygon
    #  this approach won`t scale beyond a trivial dataset so instead use a file/memory spatial index implemented
    #   using py rtree
    ref_poly_geom, ext_poly_geoms = fetch_polygons_to_compare(ref_polys_fname, ext_polys_fname, ref_geoid_fld_name, ext_geoid_fld_name, ref_geoid)

    # compute iou measure
    iou = compute_measure(
        ref_poly_geom,
        ext_poly_geoms,
        measure_to_compute="intersection_over_union"
    )

    if iou is not None:
        print("IOU Calc Result: {0} (0 = worst accuracy; 1 = best accuracy)".format(iou))
    else:
        print("IOU could not be calculated")


if __name__ == "__main__":
    main()


