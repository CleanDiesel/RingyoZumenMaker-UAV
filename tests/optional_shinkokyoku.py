"""Optional regional attribute, inheritance, configuration and exported schema."""
from pathlib import Path

fixture = Path(__file__).with_name('uav_multidrawing.py')
exec(compile(fixture.read_text(encoding='utf-8').split('polygons = vector(')[0], str(fixture), 'exec'))
from qgis.core import QgsVectorFileWriter

widget = Main()
widget.crs.setCrs(QgsCoordinateReferenceSystem('EPSG:6678'))
source = vector('区域', 'MultiPolygon', [('A', 'MULTIPOLYGON(((0 0,10 0,10 10,0 10,0 0)))', 1)])
widget.polygon.setLayer(source)
feature = next(source.getFeatures())
assert widget.shinkokyoku.currentText() == '石狩'
assert widget.singleLineShinkokyoku.currentText() == '石狩'
widget.shinkokyoku.setCurrentText('なし')
assert not widget.shinkokyoku_enabled()
assert widget.shinkokyoku_enabled('singleLine')
widget.set_attribute_inheritance('singleLineShinkokyoku', 'shinkokyoku', True)
assert not widget.shinkokyoku_enabled('singleLine')
assert '振興局' not in widget.polygon_attributes(source, feature, 'A')
assert '振興局' not in widget.polygon_attributes(source, feature, 'A', 'singleLine')
configuration = widget.configuration_data()
widget.shinkokyoku.setCurrentText('石狩')
widget.apply_configuration(configuration)
assert widget.shinkokyoku.currentText() == 'なし'
assert not widget.shinkokyoku_enabled('singleLine')
attributes = widget.polygon_attributes(source, feature, 'A')
attributes.update({'面積ha': 0.01, '申請ha': 0.01, '更新ha': 0.01})
widget.application_layer = widget.memory_polygon_layer('申請区域', [(feature.geometry(), attributes)], widget.application_field_definitions())
assert widget.application_layer.fields().indexFromName('振興局') == -1
widget._current_drawing = {'title': '確認', 'kind': '申請区域'}
widget.drawing_output_dir = lambda: output_root
widget.displayed_output_path = lambda path: str(path)
widget.export_shapefile()
exported = QgsVectorLayer(str(next(output_root.glob('*.shp'))), 'exported', 'ogr')
assert exported.isValid() and exported.fields().indexFromName('振興局') == -1
options = QgsVectorFileWriter.SaveVectorOptions()
options.driverName = 'GPKG'
assert QgsVectorFileWriter.writeAsVectorFormatV3(widget.application_layer, str(output_root / 'optional.gpkg'), QgsProject.instance().transformContext(), options)[0] == QgsVectorFileWriter.NoError
saved = QgsVectorLayer(str(output_root / 'optional.gpkg'), 'saved', 'ogr')
assert saved.isValid() and saved.fields().indexFromName('振興局') == -1
widget.shinkokyokuOverride.setToProperty(QgsProperty.fromExpression("'上川'"))
assert widget.shinkokyoku_enabled() and widget.shinkokyoku_enabled('singleLine')
assert widget.polygon_attributes(source, feature, 'A')['振興局'] == '上川'
assert widget.polygon_attributes(source, feature, 'A', 'singleLine')['振興局'] == '上川'
widget.set_attribute_inheritance('singleLineShinkokyoku', 'shinkokyoku', False)
widget.singleLineShinkokyoku.setCurrentText('なし')
assert not widget.shinkokyoku_enabled('singleLine')
assert '振興局' not in [item[0] for item in widget.application_field_definitions(True)]
print('Optional regional attribute: PASS', flush=True)
