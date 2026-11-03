"""
Merges all CityGML layers that are loaded in the current QGIS project into one
layer.

Merging them directly in QGIS fails because some layers have values in fields
that are too long. This script first refactors every layer so text fields have
a length of at least 256, then merges them.

Run it from the QGIS Python console (Plugins -> Python Console -> Show Editor,
open this file and press Run) after drag and dropping your CityGML files into
QGIS.
"""

from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant
import processing

CRS = "EPSG:25832"


def get_all_citygml_layers():
    """Get all loaded vector layers that are likely CityGML files"""
    layers = []
    for layer in QgsProject.instance().mapLayers().values():
        if isinstance(layer, QgsVectorLayer) and layer.dataProvider().name() == "ogr":
            # MultiLineStringZ or MultiSurfaceZ, the typical CityGML geometry types
            if layer.wkbType() in [1002, 1005]:
                layers.append(layer)
    return layers


def refactor_layer(layer):
    """Refactor fields to ensure sufficient field lengths"""
    fields_mapping = []
    for field in layer.fields():
        fields_mapping.append({
            "expression": f'"{field.name()}"',
            "length": max(field.length(), 256) if field.type() == QVariant.String else field.length(),
            "name": field.name(),
            "precision": field.precision(),
            "type": field.type(),
        })

    return processing.run("qgis:refactorfields", {
        "INPUT": layer,
        "FIELDS_MAPPING": fields_mapping,
        "OUTPUT": "TEMPORARY_OUTPUT",
    })["OUTPUT"]


def merge_citygml_layers():
    layers = get_all_citygml_layers()
    if not layers:
        print("No CityGML layers found in project")
        return

    print(f"Found {len(layers)} CityGML layers to merge")
    refactored_layers = []
    for layer in layers:
        print(f"Processing layer: {layer.name()}")
        refactored_layers.append(refactor_layer(layer))

    result = processing.run("native:mergevectorlayers", {
        "LAYERS": refactored_layers,
        "CRS": QgsCoordinateReferenceSystem(CRS),
        "OUTPUT": "TEMPORARY_OUTPUT",
    })
    merged = result["OUTPUT"]
    merged.setName("Merged_CityGML")
    QgsProject.instance().addMapLayer(merged)
    print("Done. Added layer 'Merged_CityGML'")


merge_citygml_layers()
