"""
Turns the shadow rasters from 05_calc_shadows.sh into map tiles.

It watches INPUT_DIR and processes every new <day>_<time>.tif:
  polygonize   -> shadow polygons
  simplify     -> smoother, smaller polygons
  clean up     -> removes tiny polygons (< MIN_AREA m²)
  XYZ tiles    -> <OUTPUT_DIR>/<day>/<time>/<z>/<x>/<y>.png

So you can run it at the same time as 05_calc_shadows.sh and tiles are created
as soon as a shadow raster is done. To stop it, create an (empty) file called
"stop" in INPUT_DIR.

Run it from the QGIS Python console (Plugins -> Python Console -> Show Editor,
open this file and press Run). QGIS is blocked while it runs.
"""

import os
import time as t

from qgis.core import QgsFillSymbol, QgsProject, QgsRasterLayer
from qgis.PyQt.QtGui import QColor
import processing

# ---- Settings, change these -------------------------------------------------

INPUT_DIR = "/path/to/shadows"   # where 05_calc_shadows.sh writes its .tif files
OUTPUT_DIR = "/path/to/tiles"
ZOOM_MIN = 15
ZOOM_MAX = 18
MIN_AREA = 5                     # polygons smaller than this (m²) are removed
DELETE_PROCESSED = True          # delete each .tif once its tiles are done

# -----------------------------------------------------------------------------

CRS = "EPSG:25832"

# Simple black fill for the shadows
symbol = QgsFillSymbol.createSimple({
    "color": "0,0,0,255",
    "outline_color": "0,0,0,255",
    "outline_width": "0.1",
})


def process_file(file_path, day, time):
    start_time = t.time()
    e = QgsRasterLayer(file_path, "shadow").extent()
    extent = f"{e.xMinimum()},{e.xMaximum()},{e.yMinimum()},{e.yMaximum()} [{CRS}]"

    polygons = processing.run("gdal:polygonize", {
        "INPUT": file_path,
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

    # Remove tiny polygons, they are mostly noise
    simple.startEditing()
    tiny = [f.id() for f in simple.getFeatures() if f.geometry().area() < MIN_AREA]
    simple.deleteFeatures(tiny)
    simple.commitChanges()
    print(f"{day} {time}: removed {len(tiny)} polygons smaller than {MIN_AREA} m²")

    simple.renderer().setSymbol(symbol)
    added_layer = QgsProject.instance().addMapLayer(simple)

    processing.run("native:tilesxyzdirectory", {
        "EXTENT": extent,
        "ZOOM_MIN": ZOOM_MIN,
        "ZOOM_MAX": ZOOM_MAX,
        "DPI": 96,
        "BACKGROUND_COLOR": QColor(0, 0, 0, 0),
        "ANTIALIAS": True,
        "TILE_FORMAT": 0,
        "QUALITY": 75,
        "METATILESIZE": 4,
        "TILE_WIDTH": 256,
        "TILE_HEIGHT": 256,
        "TMS_CONVENTION": False,
        "HTML_TITLE": "",
        "HTML_ATTRIBUTION": "",
        "HTML_OSM": False,
        "OUTPUT_DIRECTORY": os.path.join(OUTPUT_DIR, day, time),
        "OUTPUT_HTML": "TEMPORARY_OUTPUT",
    })

    # Remove the layer again, otherwise the next tiles contain these shadows as well
    QgsProject.instance().removeMapLayer(added_layer.id())
    print(f"{day} {time}: tile creation took {t.time() - start_time:.1f}s")

    if DELETE_PROCESSED:
        os.remove(file_path)


processed_files = set()
print(f"Watching {INPUT_DIR} ...")
while not os.path.exists(os.path.join(INPUT_DIR, "stop")):
    files = {f for f in os.listdir(INPUT_DIR) if f.endswith(".tif")}
    for file_name in sorted(files - processed_files):
        day, time = file_name[:-4].split("_")[:2]
        start_time = t.time()
        process_file(os.path.join(INPUT_DIR, file_name), day, time)
        print(f"{day} {time}: total {t.time() - start_time:.1f}s")
    processed_files |= files
    t.sleep(2)
print("Found 'stop' file, done.")
