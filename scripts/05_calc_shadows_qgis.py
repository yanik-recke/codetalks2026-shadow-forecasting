"""
Calculates shadows for a digital surface model (DSM) and turns them into map
tiles, all inside QGIS. Good for trying things out with one or a few points in
time. For a lot of days/times use 05_calc_shadows.sh + 06_make_tiles.py
instead, it's way faster.

For every day/time this runs:
  r.sun.incidout  -> solar incidence angle map, shadows are 'No data'
  r.null          -> shadows become 1, everything else 'No data'
  polygonize      -> shadow polygons
  simplify        -> smoother, smaller polygons
  XYZ tiles       -> <OUTPUT_DIR>/<day>/<time>/<z>/<x>/<y>.png

Run it from the QGIS Python console (Plugins -> Python Console -> Show Editor,
open this file and press Run).
"""

import os
import time as t

from qgis.core import QgsFillSymbol, QgsProcessingUtils, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtGui import QColor
import processing

# ---- Settings, change these -------------------------------------------------

# Your DSM (terrain + buildings, see the "Digital surface model" steps)
DSM = "/path/to/dsm.tif"

# Optional aspect and slope layers. The GRASS tool r.slope.aspect computes both
# from your DSM. Leave as None and r.sun uses ASPECT_VALUE / SLOPE_VALUE
# everywhere instead.
ASPECT = None
ASPECT_VALUE = 270
SLOPE = None
SLOPE_VALUE = 0

# Optional pre-computed horizon rasters from the GRASS tool r.horizon (use the
# same step as horizon_step below), e.g. "/path/horizon/horizon_*.tif".
# Computing them takes a while, but it speeds up every r.sun run afterwards.
HORIZON = None

# Day of the year (1 - 365) and local solar time in decimal hours (14.5 = 14:30)
DAYS = [164]
TIMES = [10, 12, 14, 16, 18, 20]

OUTPUT_DIR = "/path/to/tiles"
ZOOM_MIN = 10
ZOOM_MAX = 18

# -----------------------------------------------------------------------------

CRS = "EPSG:25832"

dsm_layer = QgsRasterLayer(DSM, "dsm")
e = dsm_layer.extent()
EXTENT = f"{e.xMinimum()},{e.xMaximum()},{e.yMinimum()},{e.yMaximum()} [{CRS}]"

# Simple black fill for the shadows
symbol = QgsFillSymbol.createSimple({
    "color": "0,0,0,255",
    "outline_color": "0,0,0,255",
    "outline_width": "0.1",
})

for day in DAYS:
    for time in TIMES:
        start_time = t.time()

        shadow_output = processing.run("grass:r.sun.incidout", {
            "elevation": DSM,
            "aspect": ASPECT,
            "aspect_value": ASPECT_VALUE,
            "slope": SLOPE,
            "slope_value": SLOPE_VALUE,
            "linke": None,
            "albedo": None,
            "albedo_value": 0.2,
            "lat": None,
            "long": None,
            "coeff_bh": None,
            "coeff_dh": None,
            "horizon_basemap": HORIZON,
            "horizon_step": 5.0,
            "day": day,
            "step": 0.5,
            "declination": None,
            "distance_step": 1,
            "npartitions": 1,
            "civil_time": None,
            "time": time,
            "-p": False,
            "-m": False,
            "incidout": "TEMPORARY_OUTPUT",
            "beam_rad": "TEMPORARY_OUTPUT",
            "diff_rad": "TEMPORARY_OUTPUT",
            "refl_rad": "TEMPORARY_OUTPUT",
            "glob_rad": "TEMPORARY_OUTPUT",
            "GRASS_REGION_PARAMETER": EXTENT,
            "GRASS_REGION_CELLSIZE_PARAMETER": 0,
            "GRASS_RASTER_FORMAT_OPT": "",
            "GRASS_RASTER_FORMAT_META": "",
        })
        print(f"{day} {time}: sun calculation took {t.time() - start_time:.1f}s")
        start_time = t.time()

        # Every value that is not null (0 - 999) becomes 'No data', every 'No data' becomes 1
        # -> all shadows have the value 1
        replaced = processing.run("grass:r.null", {
            "map": shadow_output["incidout"],
            "setnull": "0-999",
            "null": "1",
            "-f": False,
            "-i": False,
            "-n": False,
            "-c": False,
            "-r": False,
            "output": QgsProcessingUtils.generateTempFilename("null_output.tif"),
            "GRASS_REGION_PARAMETER": EXTENT,
            "GRASS_REGION_CELLSIZE_PARAMETER": 0,
            "GRASS_RASTER_FORMAT_OPT": "",
            "GRASS_RASTER_FORMAT_META": "",
        })
        print(f"{day} {time}: r.null took {t.time() - start_time:.1f}s")
        start_time = t.time()

        polygons = processing.run("gdal:polygonize", {
            "INPUT": replaced["output"],
            "BAND": 1,
            "FIELD": "DN",
            "EIGHT_CONNECTEDNESS": False,
            "EXTRA": "",
            "OUTPUT": "TEMPORARY_OUTPUT",
        })["OUTPUT"]

        simple = processing.run("native:simplifygeometries", {
            "INPUT": polygons,
            "METHOD": 0,
            "TOLERANCE": 1,
            "OUTPUT": "TEMPORARY_OUTPUT",
        })["OUTPUT"]
        print(f"{day} {time}: polygonize + simplify took {t.time() - start_time:.1f}s")
        start_time = t.time()

        simple.setName(f"shadows {day} {time}")
        simple.renderer().setSymbol(symbol)
        added_layer = QgsProject.instance().addMapLayer(simple)

        processing.run("native:tilesxyzdirectory", {
            "EXTENT": EXTENT,
            "ZOOM_MIN": ZOOM_MIN,
            "ZOOM_MAX": ZOOM_MAX,
            "DPI": 96,
            "BACKGROUND_COLOR": QColor(0, 0, 0, 0),
            "ANTIALIAS": True,
            "TILE_FORMAT": 0,
            "QUALITY": 75,
            "METATILESIZE": 4,
            "TILE_WIDTH": 512,
            "TILE_HEIGHT": 512,
            "TMS_CONVENTION": False,
            "HTML_TITLE": "",
            "HTML_ATTRIBUTION": "",
            "HTML_OSM": False,
            "OUTPUT_DIRECTORY": os.path.join(OUTPUT_DIR, str(day), str(time)),
            "OUTPUT_HTML": "TEMPORARY_OUTPUT",
        })

        # Hide the layer again, otherwise the next tiles contain these shadows as well
        QgsProject.instance().layerTreeRoot().findLayer(added_layer.id()).setItemVisibilityChecked(False)
        print(f"{day} {time}: tile creation took {t.time() - start_time:.1f}s")
