import os
import fiona
import rtree
from shapely.geometry import shape


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
        # TODO use rtree to speed things up rather than nasty brute force approach we have here at the moment
        #  https://maptiks.com/blog/spatial-queries-in-python/

        measure_total = 0
        measure_occurences = 0
        measure_avg = 0

        with fiona.open(ref_polys_shp_fname, "r") as ref_polys_src:
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

                    # do bounds query against the spatial index
                    for fid in pred_polys_idx.intersection(ref_poly_geom.bounds):
                        # then check which of the polygons returned by the bounds more precisely intersect
                        pred_poly_geom = shape(pred_polys_src[fid]["geometry"])
                        if ref_poly_geom.intersects(pred_poly_geom):
                            pred_poly_geoid = pred_polys_src[fid]["properties"][pred_polys_geoid_fldname]
                            if debug:
                                print('Ref(erence) poly geoid: {0} isects with Pred(icted) poly geoid: {1}'.format(ref_poly_geoid, pred_poly_geoid))
                            pred_poly_geoms.append(pred_poly_geom)

                    measure_to_compute = 'intersection_over_union'

                    # TODO calculate the measures for this reference polygon
                    measure = compute_measure(
                        ref_poly_geom=ref_poly_geom,
                        ext_poly_geoms=pred_poly_geoms,
                        measure_to_compute=measure_to_compute
                    )

                    if measure is not None:
                        print("\t{0} Calc Result: {1} (0 = worst accuracy; 1 = best accuracy)".format(
                            measure_to_compute, measure)
                        )
                        measure_total += measure
                        measure_occurences += 1
                    else:
                        print("\t{0} could not be calculated".format(measure_to_compute))

        measure_avg = measure_total / measure_occurences
        print("\nAcross dataset: {0} averaged is: {1} (0 = worst accuracy; 1 = best accuracy), based on IOU total: {2} for {3} occurences.".format(
            measure_to_compute, measure_avg, measure_total, measure_occurences)
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

            # TODO at moment we are only grabbing 1 of the predicted polygons that intersect with the reference polygon
            #  this is likely, mostly not to be the case
            p2 = ext_poly_geoms[0]

            # use shapely to compute intersection over union
            computed_measure = round(p1.intersection(p2).area / p1.union(p2).area, 4)

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
    ref_polys_fname = "data/simple_reference_polygons.shp"
    ext_polys_fname = "data/simple_extracted_polygons.shp"

    # TODO add cli with click
    compare_reference_and_predicted_polygons(
        ref_polys_shp_fname=ref_polys_fname,
        ref_polys_geoid_fldname="id",
        pred_polys_shp_fname=ext_polys_fname,
        pred_polys_geoid_fldname="id",
        debug=True
    )


if __name__ == "__main__":
    main()


