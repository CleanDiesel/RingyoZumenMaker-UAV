"""Labeled external layers need not have a fid column to export a QGZ."""
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
base = Path(r"C:\Users\m48c7\AppData\Local\Programs\OSGeo4W")
dll_handles = [os.add_dll_directory(str(base / part))
               for part in ("bin", "apps/Qt6/bin", "apps/qgis/bin")]
sys.path[:0] = [str(base / "apps/qgis/python")]
from qgis.core import (QgsApplication, QgsProject, QgsVectorLayer,
                       QgsPalLayerSettings, QgsVectorLayerSimpleLabeling)
from RingyoZumenMaker.unified_project import UnifiedProjects, UID

app = QgsApplication([], False)
app.initQgis()
exporter = UnifiedProjects.__new__(UnifiedProjects)
exporter.project = QgsProject()

def labeled_layer(key=None):
    uri = "Point?crs=EPSG:6678&field=name:string"
    if key:
        uri += "&field=" + key + (":string" if key == UID else ":integer")
    layer = QgsVectorLayer(uri, "背景ラベル", "memory")
    settings = QgsPalLayerSettings()
    settings.fieldName = "name"
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)
    exporter.project.addMapLayer(layer)
    return layer

background = labeled_layer()
settings = background.labeling().settings()
before = settings.dataDefinedProperties().toVariant({})
try:
    background.fields().field("fid")
except KeyError as error:
    assert str(error) == "'fid'"
else:
    raise AssertionError("Expected the original missing-field failure")
exporter._auxiliary(background)
assert background.auxiliaryLayer() is None
assert background.labelsEnabled()
settings = background.labeling().settings()
assert settings.dataDefinedProperties().toVariant({}) == before
for key in (UID, "fid"):
    layer = labeled_layer(key)
    exporter._auxiliary(layer)
    assert layer.auxiliaryLayer() is not None
    exporter._auxiliary(layer)
    settings = layer.labeling().settings()
    properties = settings.dataDefinedProperties()
    assert properties.property(QgsPalLayerSettings.PositionX).isActive()
    assert properties.property(QgsPalLayerSettings.PositionY).isActive()
exporter.project.clear()
print("PASS: background without fid and managed label positions")
