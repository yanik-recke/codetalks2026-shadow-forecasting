"""
Finds all CityGML files (LoD1/LoD2/LoD3) whose bounding box intersects an area
and copies them into a separate folder, so you only have to import those into
QGIS.

Usage:
    python 02_find_buildings.py <citygml-dir> <output-dir> MIN_X MIN_Y MAX_X MAX_Y

Coordinates are in EPSG:25832 (same as Hamburg's data).

Alternatively, if you just want the buildings of one postal code:

    grep -rlE 'PostalCodeNumber>(22763)</' <citygml-dir> | xargs -I {} cp {} <output-dir>
"""

import argparse
import os
import shutil
import sys
import xml.etree.ElementTree as ET

NS = {"gml": "http://www.opengis.net/gml"}


def is_in_area(lower_corner, upper_corner, area):
    """Checks whether the bounding box intersects the area (min_x, min_y, max_x, max_y)."""
    min_x, min_y, max_x, max_y = area
    try:
        lx, ly = map(float, lower_corner.split()[:2])
        ux, uy = map(float, upper_corner.split()[:2])
    except ValueError:
        return False
    # Files that only touch the edge of the area are not needed
    return not (ux <= min_x or lx >= max_x or uy <= min_y or ly >= max_y)


def is_citygml_file_in_area(file_path, area):
    try:
        root = ET.parse(file_path).getroot()
    except ET.ParseError as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return False

    for envelope in root.iterfind(".//gml:boundedBy/gml:Envelope", NS):
        lower = envelope.find("gml:lowerCorner", NS)
        upper = envelope.find("gml:upperCorner", NS)
        if lower is not None and upper is not None and is_in_area(lower.text, upper.text, area):
            return True
    return False


def copy_files_in_area(directory, area, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    copied = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith((".gml", ".xml")):
                file_path = os.path.join(root, file)
                if is_citygml_file_in_area(file_path, area):
                    shutil.copy2(file_path, output_dir)
                    copied += 1
                    print(f"Copied: {file_path}")
    print(f"Copied {copied} files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("citygml_dir", help="Folder containing the CityGML .xml/.gml files")
    parser.add_argument("output_dir", help="Folder the relevant files are copied to")
    parser.add_argument("bbox", nargs=4, type=float, metavar=("MIN_X", "MIN_Y", "MAX_X", "MAX_Y"))
    args = parser.parse_args()

    copy_files_in_area(args.citygml_dir, args.bbox, args.output_dir)
