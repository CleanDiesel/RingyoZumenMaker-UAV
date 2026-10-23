"""Run with QGIS Python via tests/run_integration.py."""
import os
import tempfile
import zipfile
from pathlib import Path

from lxml import etree as ET
from qgis.core import QgsApplication, QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtGui import QFontDatabase, QFont
from osgeo import gdal

app = QgsApplication.instance() or QgsApplication([], False)
app.initQgis()
for path in Path(r"C:\Windows\Fonts").glob("YuGoth*.ttc"):
    QFontDatabase.addApplicationFont(str(path))
app.setFont(QFont("Yu Gothic", 9))
from RingyoZumenMaker.main import Main

messages = []
QMessageBox.warning = lambda parent, title, message: messages.append(message)
root = Path(tempfile.mkdtemp(prefix="drawing-output-", dir=os.environ.get("QGIS_TEST_OUTPUT_DIR")))
project = QgsProject.instance()
polygon = QgsVectorLayer("MultiPolygon?crs=EPSG:6678", "施行地", "memory")
for index in range(16):
    feature = QgsFeature(polygon.fields())
    x = index * 5
    feature.setGeometry(QgsGeometry.fromWkt(f"MULTIPOLYGON((({x} 0,{x+4} 0,{x+4} 4,{x} 4,{x} 0)))"))
    polygon.dataProvider().addFeature(feature)
polygon.updateExtents()
line = QgsVectorLayer("MultiLineString?crs=EPSG:6678", "作業道", "memory")
for index in range(2):
    feature = QgsFeature(line.fields())
    feature.setGeometry(QgsGeometry.fromWkt(f"MULTILINESTRING((0 {index*10},50 {index*10}))"))
    line.dataProvider().addFeature(feature)
line.updateExtents()
project.addMapLayer(polygon)
project.addMapLayer(line)
image = root / "original.tif"
ds = gdal.GetDriverByName("GTiff").Create(str(image), 100, 100, 3, gdal.GDT_Byte)
ds.SetGeoTransform((-10, 1, 0, 80, 0, -1))
ds.SetProjection(QgsCoordinateReferenceSystem("EPSG:6678").toWkt())
for index in range(1, 4):
    ds.GetRasterBand(index).Fill(210)
ds = None
image.with_suffix(".tfw").write_text("1\n0\n0\n-1\n-9.5\n79.5\n")
widget = Main()
assert not widget.createZip.isChecked()
assert widget.zipDirectory.placeholderText() == "出力フォルダに保存"
widget.crs.setCrs(QgsCoordinateReferenceSystem("EPSG:6678"))
widget.scale.setScale(2000)
widget.locationScale.setScale(5000)
widget.polygon.setLayer(polygon)
widget.singleLine.setLayer(line)
widget.singleLineWidth.setValue(2)
widget.shinseibango.setText("7006-01")
widget.rinpan.setValue(12)
widget.shohan.setValue(60)
widget.polygonName.setText("新植区域")
widget.sanrinshoyusha2.setText("長い所有者の名称を途中で省略せず折り返して表示するための試験株式会社")
widget.singleLineName.setText("作業道")
widget.assignmentOlso.setFilePath(str(image))
ortho = QgsRasterLayer(str(image), "オルソ")
project.addMapLayer(ortho)
widget.olso.setLayer(ortho)
widget.isIchizu.setChecked(True)
widget.outputMode.setCurrentIndex(1)
output = root / "output"
output.mkdir()
widget.fileName.setFilePath(str(output))
widget.validate_inputs()
widget.calculate_uav()
assert len(widget.drawings) == 3
assert [f["No"] for f in widget.drawings[0]["application_layer"].getFeatures()] == list(range(1, 17))
assert [d["attributes"]["No"] for d in widget.drawings[1:]] == [1, 2]
assert "枝番" not in widget.drawings[0]["application_layer"].fields().names()
assert widget.application_layer.labeling().settings().isExpression
assert "'No.'" in widget.application_layer.labeling().settings().fieldName
disabled_key = widget.drawings[2]["key"]
widget._drawing_tables[disabled_key] = False
widget.createZip.setChecked(True)
config = widget.configuration_data()
widget.apply_configuration(config)
assert widget.configuration_data() == config
widget.on_submit()
assert widget.progressBar.value() == 100, (messages, widget.outputlog.toPlainText())
assert not messages, messages
html = ET.parse(str(output / "index.html"), ET.HTMLParser())
tables = html.xpath("//table[@class='attribute-table']")
assert len(tables) == 2
assert len(tables[0].xpath("tbody/tr")) == 16
assert len(tables[0].xpath("thead/tr")) == 1
assert "枝番" not in ET.tostring(tables[0], encoding="unicode")
archive = next(output.glob("*.zip"))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len([name for name in z.namelist() if name.startswith("図面/") and name.endswith(".pdf")]) == 3
    assert "位置図/位置図.pdf" in z.namelist()
    assert len([name for name in z.namelist() if name.endswith(".shp")]) == 3
    assert any(name.endswith(".tfw") for name in z.namelist())
    z.extractall(root / "archive")
widget.backupQgz.setChecked(True)
widget.zipDirectory.setText(str(output / "asset"))
widget.on_submit()
assert widget.progressBar.value() == 100, messages
assert not list((output / "backup").rglob("*.zip"))
assert (output / "asset" / archive.name).is_file()
assert not list(output.glob(".ringyo_zip_*"))
widget.outputMode.setCurrentIndex(0)
widget.createZip.setChecked(False)
widget.on_submit()
assert widget.progressBar.value() == 100, messages
widget.on_submit()
assert widget.progressBar.value() == 100, messages
for path in (output / "シェープファイル").rglob("*.shp"):
    layer = QgsVectorLayer(str(path), "output", "ogr")
    assert layer.isValid()
    assert "No" in layer.fields().names() and "枝番" not in layer.fields().names()
    iterator = layer.getFeatures()
    assert all(f["No"] >= 1 for f in iterator)
    iterator.close()
layer = None
print(f"PASS: numbering, table settings, shapefiles, ZIP/PDF, backup and QGZ regeneration: {root}", flush=True)
widget.tabWidget.setCurrentWidget(widget.tab_5)
widget.resize(700, 930)
widget.show()
app.processEvents()
widget.grab().save(str(root / "output-ui.png"))
widget.close()
project.clear()
