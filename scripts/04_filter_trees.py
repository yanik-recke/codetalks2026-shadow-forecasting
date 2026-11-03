"""
Filters Hamburg's street tree register (Straßenbaumkataster, GeoJSON) down to
the trees inside an area. The result is a GeoJSON file you can drag and drop
into QGIS.

Usage:
    python 04_filter_trees.py <all-trees.json> <output.geojson> MIN_X MIN_Y MAX_X MAX_Y

Coordinates are in EPSG:25832 (same as Hamburg's data).
"""

import argparse
import json


def first_point(geometry):
    """Returns the (x, y) of a Point or the first point of a MultiPoint."""
    coords = geometry["coordinates"]
    return coords[0] if geometry["type"] == "MultiPoint" else coords


def filter_by_coordinates(input_file, output_file, min_x, min_y, max_x, max_y):
    with open(input_file) as f:
        data = json.load(f)

    filtered = []
    for feature in data["features"]:
        x, y = first_point(feature["geometry"])[:2]
        if min_x <= x <= max_x and min_y <= y <= max_y:
            filtered.append(feature)

    # Keep it a FeatureCollection (including the CRS if there is one) so QGIS can read it
    data["features"] = filtered
    with open(output_file, "w") as f:
        json.dump(data, f)

    print(f"Kept {len(filtered)} of the trees.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_file", help="GeoJSON of all trees")
    parser.add_argument("output_file", help="Where the filtered GeoJSON is written")
    parser.add_argument("bbox", nargs=4, type=float, metavar=("MIN_X", "MIN_Y", "MAX_X", "MAX_Y"))
    args = parser.parse_args()

    filter_by_coordinates(args.input_file, args.output_file, *args.bbox)
