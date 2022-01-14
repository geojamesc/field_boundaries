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

   all 6 metrics are defined to a range between 0 and 1; the closer to 1, the more accurate
   if an extracted field intersected with more that one field, metrics were weighted by the corresponding intersection areas
"""

