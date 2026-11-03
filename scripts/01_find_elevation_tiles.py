"""
Finds all elevation tiles (GeoTIFF) that intersect an area and copies them
into a separate folder. Merge them afterwards, e.g. with:

    gdal_merge.py -o terrain.tif <output-dir>/*.tif

Usage:
    python 01_find_elevation_tiles.py <tiles-dir> <output-dir> MIN_X MIN_Y MAX_X MAX_Y

Coordinates are in EPSG:25832 (same as Hamburg's data).
"""

import argparse
import glob
import os
import shutil

import rasterio
from shapely.geometry import box


def get_tiff_bounds(tiff_path):
    """Returns the bounding box of a GeoTIFF or None if it can't be opened."""
    try:
        with rasterio.open(tiff_path) as src:
            return src.bounds
    except rasterio.errors.RasterioIOError:
        print(f"Warning: Could not open {tiff_path}. Skipping.")
        return None


def find_intersecting_tiffs(data_dir, area):
    """Finds all GeoTIFFs in data_dir (recursively) that intersect the area."""
    tif_files = glob.glob(os.path.join(data_dir, "**", "*.tif"), recursive=True)
    print(f"Found {len(tif_files)} TIFF files in total.")

    intersecting_files = []
    for tif_file in tif_files:
        bounds = get_tiff_bounds(tif_file)
        if not bounds:
            continue
        tile = box(bounds.left, bounds.bottom, bounds.right, bounds.top)
        # Tiles that only touch the edge of the area are not needed
        if tile.intersects(area) and not tile.touches(area):
            intersecting_files.append(tif_file)
    return intersecting_files


def copy_files_to_directory(file_paths, destination_directory):
    os.makedirs(destination_directory, exist_ok=True)
    for file_path in file_paths:
        shutil.copy2(file_path, destination_directory)
        print(f"Copied {os.path.basename(file_path)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tiles_dir", help="Folder containing the elevation .tif tiles")
    parser.add_argument("output_dir", help="Folder the relevant tiles are copied to")
    parser.add_argument("bbox", nargs=4, type=float, metavar=("MIN_X", "MIN_Y", "MAX_X", "MAX_Y"))
    args = parser.parse_args()

    relevant_tiffs = find_intersecting_tiffs(args.tiles_dir, box(*args.bbox))
    print(f"Found {len(relevant_tiffs)} TIFF files intersecting your area.")
    copy_files_to_directory(relevant_tiffs, args.output_dir)
