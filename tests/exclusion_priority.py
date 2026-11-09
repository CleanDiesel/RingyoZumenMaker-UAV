"""UAV overlap membership, natural-number priorities and retained line dimensions."""
import os, tempfile
from pathlib import Path
from lxml import etree as ET
from qgis.core import (QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry,
                       QgsCoordinateReferenceSystem, QgsProperty, QgsApplication)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QMessageBox
from RingyoZumenMaker.main import Main

project = QgsProject.instance()
root = Path(tempfile.mkdtemp(prefix='uav-overlap-qa-', dir=os.environ['QGIS_TEST_OUTPUT_DIR']))
print('OUTPUT', root, flush=True)
messages = []
QMessageBox.warning = lambda parent, title, message: messages.append(message)

def layer(name, kind, records):
    result = QgsVectorLayer(f'{kind}?crs=EPSG:6678', name, 'memory')
    result.dataProvider().addAttributes([QgsField('name', QVariant.String), QgsField('priority', QVariant.Double)])
    result.updateFields()
    for name_, priority, wkt in records:
        feature = QgsFeature(result.fields())
        feature.setAttributes([name_, priority]); feature.setGeometry(QgsGeometry.fromWkt(wkt))
        assert result.dataProvider().addFeature(feature)
    result.updateExtents(); project.addMapLayer(result)
    return result

work = layer('施行地', 'Polygon', [('施行地', None, 'POLYGON((0 0,100 0,100 100,0 100,0 0))')])
polygons = layer('除地', 'Polygon', [
    ('A', 2, 'POLYGON((10 10,30 10,30 20,10 20,10 10))'),
    ('B', 1, 'POLYGON((20 10,40 10,40 20,20 20,20 10))'),
    ('C', None, 'POLYGON((50 10,55 10,55 20,50 20,50 10))')])
widget = Main(); widget.crs.setCrs(QgsCoordinateReferenceSystem('EPSG:6678'))
widget.fileName.setFilePath(str(root)); widget.scale.setScale(1000)
widget.polygon.setLayer(work); widget.jochiPolygon.setLayer(polygons)
widget.jochiNameOverride.setToProperty(QgsProperty.fromField('name'))
widget.jochiPriority.setExpression('"priority"'); widget.minJochi.setValue(0)
widget.isJochikeisan.setChecked(True); widget.outputMode.setCurrentIndex(1)
widget.calculate_uav()
assert widget.exclusionOverlap.currentText() == '統合'
assert abs(widget.exclusion_area - 350) < 1e-8
assert widget.exclusion_terms == [('B', 100.0), ('A', 100.0), ('B・A', 100.0), ('C', 50.0)], widget.exclusion_terms
assert not widget.exclusion_adjustments
features = list(widget.exclusion_layer.getFeatures())
for i, first in enumerate(features):
    for second in features[i+1:]:
        assert first.geometry().intersection(second.geometry()).area() < 1e-8

# The minimum area still applies to the connected union (300), rather than
# dropping its individual 100 m2 formula pieces after partitioning.
widget.minJochi.setValue(2.5); widget.calculate_uav()
assert widget.exclusion_area == 300 and len(widget.exclusion_terms) == 3
widget.minJochi.setValue(0); widget.exclusionOverlap.setCurrentIndex(1); widget.calculate_uav()
assert widget.exclusion_terms == [('B', 200.0), ('A・重複部分除去済み', 100.0), ('C', 50.0)]
assert widget.exclusion_adjustments == [('A', 200.0, 100.0, 100.0)]
sheet = widget.build_uav_html_sheet(1, 'unused.png')
assert '重複部分除去済み' in ET.tostring(sheet, encoding='unicode')
assert not sheet.xpath('.//div[contains(@class,"deduction-overlap-adjustment")]')
# Complete coverage leaves a zero-area overlap note, even without a term.
widget.jochiFilter.setExpression('"name" IN (\'A\',\'B\')')
full = layer('完全重複', 'Polygon', [('先', 1, 'POLYGON((10 10,30 10,30 20,10 20,10 10))'),
                                      ('後', 2, 'POLYGON((10 10,30 10,30 20,10 20,10 10))')])
widget.jochiPolygon.setLayer(full); widget.jochiFilter.setExpression(''); widget.calculate_uav()
assert widget.exclusion_terms == [('先', 200.0), ('後・重複部分除去済み', 0.0)]
assert widget.exclusion_adjustments == [('後', 200.0, 200.0, 0.0)]
widget.jochiPolygon.setLayer(polygons)

for expression in ('0', '-1', '1.5', "'abc'"):
    widget.jochiPriority.setExpression(expression)
    try: widget.calculate_uav(); raise AssertionError(expression)
    except ValueError as error: assert '自然数' in str(error), str(error)
widget.jochiPriority.setExpression('1')
try: widget.calculate_uav(); raise AssertionError('duplicate priority')
except ValueError as error: assert '重複' in str(error)
widget.jochiPriority.setExpression('')
widget.calculate_uav()
assert widget.exclusion_terms == [('A', 200.0), ('B・重複部分除去済み', 100.0), ('C', 50.0)]

lines = layer('除地ライン', 'LineString', [('道路', 1, 'LINESTRING(0 15,50 15)')])
widget.sagyodoLine.setLayer(lines); widget.hukuin.setValue(4)
widget.jochiNameSagyodoOverride.setToProperty(QgsProperty.fromField('name'))
widget.sagyodoPriority.setExpression('"priority"'); widget.jochiPriority.setExpression('"priority"')
try: widget.calculate_uav(); raise AssertionError('polygon/line duplicate priority')
except ValueError as error: assert '重複' in str(error)
# All polygon values unspecified; the line now has precedence.
widget.jochiPriority.setExpression(''); widget.calculate_uav()
assert widget.exclusion_terms[0] == ('道路・延長50m × 幅4m', 200.0)
# Line last: retained parts keep the original length and width in the formula.
widget.sagyodoPriority.setExpression('3'); widget.jochiPriority.setExpression('"priority"')
widget.calculate_uav()
road_terms = [term for term in widget.exclusion_terms if term[0].startswith('道路')]
assert road_terms and all('延長50m × 幅4m' in name for name, _ in road_terms), road_terms
assert any(name == '道路' and removed > 0 for name, _, removed, _ in widget.exclusion_adjustments)
widget.exclusionOverlap.setCurrentIndex(0); widget.calculate_uav()
shared = [(name, area) for name, area in widget.exclusion_terms if '道路' in name and ('A' in name or 'B' in name)]
assert shared and all('延長' not in name and '幅' not in name for name, _ in shared), shared
config = widget.configuration_data(); widget.apply_configuration(config)
assert widget.configuration_data() == config
assert widget.jochiPriority.expression() == '"priority"' and widget.sagyodoPriority.expression() == '3'
print('UNION PARTITION, EXCLUSIVE PRIORITY, NULLS, VALIDATION AND LINE DIMENSIONS OK', flush=True)

for index, mode in enumerate(('union', 'exclusive')):
    target = root / mode; target.mkdir(); widget.fileName.setFilePath(str(target))
    widget.exclusionOverlap.setCurrentIndex(index); widget.on_submit()
    assert widget.progressBar.value() == 100, (messages, widget.outputlog.toPlainText())
    assert not messages, messages
    html = ET.parse(str(target/'index.html'), ET.HTMLParser())
    assert not html.xpath('//div[contains(@class,"deduction-overlap-adjustment")]')
    assert ('重複部分除去済み' in ET.tostring(html, encoding='unicode')) == bool(index)
    if index:
        widget.outputMode.setCurrentIndex(0); widget.on_submit()
        assert widget.progressBar.value() == 100, messages
        assert project.read(str(next((target/'qgz').glob('*.qgz'))))
        assert widget.exclusionOverlap.currentText() == '排他'
        assert widget.jochiPriority.expression() == '"priority"' and widget.sagyodoPriority.expression() == '3'
        widget.calculate_uav(); assert widget.exclusion_adjustments
widget.tabWidget.setCurrentWidget(widget.tab_2); widget.resize(760, 950); widget.show()
QgsApplication.instance().processEvents(); widget.grab().save(str(root/'exclusion-settings.png'))
widget.close(); project.clear()
print('HTML AND QGZ SAVE/RESTORE OK; PASS', flush=True)
