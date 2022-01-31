import os
import fiona
import rtree
from shapely.geometry import shape
from shapely.errors import TopologicalError


# TODO Suggestion from Simon was might be worth buffering the reference and predicted polygons to filter out the small
#  noise along the boundaries
def compare_reference_and_predicted_polygons(ref_polys_shp_fname, ref_polys_geoid_fldname, pred_polys_shp_fname, pred_polys_geoid_fldname, debug=True):
    """
    perform accuracy assessment between a set of reference and predicted polygons held in 2 shapefiles
    uses rtree spatialindex to avoid doing bruteforce search for predicted polygons that intersect with
    reference polygons and calculates measures like IOU

    use of rtree based on https://maptiks.com/blog/spatial-queries-in-python/

    :param ref_polys_shp_fname:
    :param pred_polys_shp_fname:
    :param debug:
    :return:
    """
    have_ref_polys = False
    have_pred_polys = False
    if os.path.exists(ref_polys_shp_fname):
        have_ref_polys = True
    if os.path.exists(pred_polys_shp_fname):
        have_pred_polys = True

    if have_ref_polys and have_pred_polys:
        measure_total = 0
        measure_occurences = 0
        measure_avg = 0
        ref_poly_counter = 1

        with fiona.open(ref_polys_shp_fname, "r") as ref_polys_src:
            num_ref_polys = len(ref_polys_src)
            with fiona.open(pred_polys_shp_fname, "r") as pred_polys_src:
                idx_fname, _ = os.path.splitext(pred_polys_shp_fname)
                if os.path.exists(idx_fname + '.dat') and os.path.exists(idx_fname + '.idx'):
                    print('Loading existing spatial index from file...\n')
                    pred_polys_idx = rtree.index.Index(idx_fname)
                else:
                    print('Generating new spatial index for {0}...\n'.format(pred_polys_shp_fname))
                    pred_polys_idx = generate_spatial_index(pred_polys_src, idx_fname)

                for ref_poly in ref_polys_src:
                    ref_poly_geom = None
                    pred_poly_geoms = []
                    ref_poly_geoid = ref_poly["properties"][ref_polys_geoid_fldname]
                    ref_poly_geom = shape(ref_poly["geometry"])

                    print('Comparing reference poly {0} of {1} against predicted polygons'.format(ref_poly_counter, num_ref_polys))
                    # do bounds query against the spatial index
                    for fid in pred_polys_idx.intersection(ref_poly_geom.bounds):
                        # then check which of the polygons returned by the bounds more precisely intersect
                        pred_poly_geom = shape(pred_polys_src[fid]["geometry"])
                        if ref_poly_geom.intersects(pred_poly_geom):
                            pred_poly_geoid = pred_polys_src[fid]["properties"][pred_polys_geoid_fldname]
                            if debug:
                                print('Ref(erence) poly geoid: {0} isects with Pred(icted) poly geoid: {1}'.format(ref_poly_geoid, pred_poly_geoid))
                            pred_poly_geoms.append(pred_poly_geom)

                    # only compute measure if at least 1 predicted polygon that intersects with the reference polygon
                    if len(pred_poly_geoms) > 0:
                        measure_to_compute = 'intersection_over_union'
                        measure = compute_measure(
                            ref_poly_geom=ref_poly_geom,
                            ext_poly_geoms=pred_poly_geoms,
                            measure_to_compute=measure_to_compute
                        )

                        if measure is not None:
                            if debug:
                                print("\tHighest {0} Calc Result: {1} (0 = worst accuracy; 1 = best accuracy)".format(
                                    measure_to_compute, round(measure,4))
                                )
                            measure_total += measure
                            measure_occurences += 1
                        else:
                            if debug:
                                print("\t{0} could not be calculated".format(measure_to_compute))
                            else:
                                pass
                    else:
                        if debug:
                            print('Ref(erence) poly geoid: {0} isects zero Pred(icted) polys, so excluded from consideration.'.format(ref_poly_geoid))
                    ref_poly_counter += 1

        measure_avg = measure_total / measure_occurences
        print("\nAcross dataset: {0} averaged is: {1} (0 = worst accuracy; 1 = best accuracy), based on IOU total: {2} for {3} occurences.".format(
            measure_to_compute, round(measure_avg, 4), round(measure_total,4), measure_occurences)
        )


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

            # in many cases there will be multiple predicted polygons that intersect with the reference polygon
            # especially where there has been oversegmentation. So return the maximum value of iou. Possibly we
            # should be applying something like non-maximum-suppression
            # https://learnopencv.com/non-maximum-suppression-theory-and-implementation-in-pytorch/
            max_iou = 0
            for p2 in ext_poly_geoms:
                # use shapely to compute intersection over union
                try:
                    iou = p1.intersection(p2).area / p1.union(p2).area
                    if iou > max_iou:
                        max_iou = iou
                except TopologicalError as ex:
                    # shapely will raise a TopologicalError when doing geometry operations like intersection or union
                    # if any of the geometries involved are invalid e.g. contain self-intersections etc
                    print(ex)
            computed_measure = max_iou

    return computed_measure


def generate_spatial_index(records, index_path=None):
    """
    Create in-memory or file-based r-tree index
    from https://maptiks.com/blog/spatial-queries-in-python/

    :param records:
    :param index_path:
    :return:
    """
    prop = rtree.index.Property()
    if index_path is not None:
        prop.storage = rtree.index.RT_Disk
        prop.overwrite = index_path

    sp_index = rtree.index.Index(index_path, properties=prop)
    for n, ft in enumerate(records):
        if ft['geometry'] is not None:
            sp_index.insert(n, shape(ft['geometry']).bounds)
    return sp_index


def main():
    # this is a tiny set of reference and predicted polygons for dev purposes
    # compare_reference_and_predicted_polygons(
    #     ref_polys_shp_fname="data/simple_reference_polygons.shp",
    #     ref_polys_geoid_fldname="id",
    #     pred_polys_shp_fname="data/simple_extracted_polygons.shp",
    #     pred_polys_geoid_fldname="id",
    #     debug=False
    # )

    # this is the complete set of SGov Kelso reference polygons compared to the
    # set of polygons that we used OTB meanshift segmentation to extract from a
    # single scene of Sentinel-2 data
    compare_reference_and_predicted_polygons(
        ref_polys_shp_fname="data/reference_polygons.shp",
        ref_polys_geoid_fldname="geoid",
        pred_polys_shp_fname="data/otb_extracted_polygons.shp",
        pred_polys_geoid_fldname="geoid",
        debug=False
    )


if __name__ == "__main__":
    main()


