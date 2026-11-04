"""QGIS export fixtures for table placement, strict frames and physical scales."""
from pathlib import Path
import os, sys, tempfile, json, hashlib, importlib.util
NORMAL=Path(r'C:\Users\m48c7\AppData\Roaming\QGIS\QGIS4\profiles\default\python\plugins\RingyoZumenMaker')
UAV=NORMAL.with_name('RingyoZumenMaker-UAV')
bootstrap=(NORMAL/'tests/measurement_integration.py').read_text(encoding='utf-8').split('from RingyoZumenMaker.main import Main')[0]
exec(bootstrap)
spec=importlib.util.spec_from_file_location('uav_fixture_plugin',UAV/'__init__.py',submodule_search_locations=[str(UAV)])
package=importlib.util.module_from_spec(spec);sys.modules[spec.name]=package;spec.loader.exec_module(package)
from uav_fixture_plugin.main import Main as UavMain
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtGui import QImage, QColor
messages=[]
QMessageBox.warning=lambda parent,title,message:messages.append(message)
project=QgsProject.instance()
root=Path(tempfile.mkdtemp(prefix='map-frame-qa-',dir=QA_ROOT))
print('OUTPUT',root,flush=True)
records=[]
def line_layer(name,wkt):
    layer=QgsVectorLayer('MultiLineString?crs=EPSG:6678',name,'memory')
    f=QgsFeature(layer.fields());f.setGeometry(QgsGeometry.fromWkt(wkt));layer.dataProvider().addFeature(f)
    layer.updateExtents();project.addMapLayer(layer);return layer
short=line_layer('100m検尺線','MULTILINESTRING((0 0,100 0))')
tall_a4=line_layer('縦140m','MULTILINESTRING((0 -70,0 70))')
tall_a3=line_layer('縦200m','MULTILINESTRING((0 -100,0 100))')
overflow=line_layer('縦160m','MULTILINESTRING((0 -80,0 80))')
widget=UavMain();widget.crs.setCrs(QgsCoordinateReferenceSystem('EPSG:6678'))
widget.scale.setScale(1000);widget.singleLineWidth.setValue(1);widget.singleLineName.setText('検尺線')
widget.outputMode.setCurrentIndex(1);widget.isIchizu.setChecked(False)
for paper in ('A4','A3'):
    widget.paper.setCurrentText(paper)
    for title,layer in (('short',short),('tall',tall_a4 if paper=='A4' else tall_a3)):
        widget.singleLine.setLayer(layer)
        widget.calculate_uav();key=widget.drawings[0]['key']
        image_shapes=[];image_hashes=[]
        for table in (True,False):
            out=root/f'uav-{paper}-{title}-table-{int(table)}';out.mkdir()
            widget.fileName.setFilePath(str(out));widget._drawing_tables[key]=table
            widget.on_submit()
            assert widget.progressBar.value()==100,(messages,widget.outputlog.toPlainText())
            assert not messages,messages
            image=QImage(str(out/'asset/drawing_1_map.png'))
            image_shapes.append((image.width(),image.height()))
            image_hashes.append(hashlib.sha256((out/'asset/drawing_1_map.png').read_bytes()).hexdigest())
            records.append({'plugin':'uav','paper':paper,'kind':title,'table':table,'html':str(out/'index.html')})
        assert image_shapes[0]==image_shapes[1],image_shapes
        assert image_hashes[0]==image_hashes[1],'Table must never change map raster or scale'
    print(paper,'same map dimensions/pixels with and without table: PASS',flush=True)
widget.paper.setCurrentText('A4');widget.singleLine.setLayer(overflow)
bad=root/'uav-overflow';bad.mkdir();widget.fileName.setFilePath(str(bad));widget.on_submit()
assert widget.progressBar.value()==0 and messages and '大枠を超え' in messages[-1],messages
assert not (bad/'index.html').exists()
messages.clear()
print('OVERSIZED DIAGRAM REJECTED BEFORE COMMIT: PASS',flush=True)
# The final saved layout also receives the check, after preserving edits.
widget.singleLine.setLayer(short);widget.outputMode.setCurrentIndex(0)
qgz_dir=root/'uav-saved-layout';qgz_dir.mkdir();widget.fileName.setFilePath(str(qgz_dir));widget.on_submit()
assert not messages,messages
qgz=next((qgz_dir/'qgz').glob('*.qgz'));assert project.read(str(qgz))
from uav_fixture_plugin.unified_project import metadata
info=metadata(project);layout=project.layoutManager().layoutByName(info['layouts'][0]['layout'])
main_map=next(i for i in layout.items() if isinstance(i,QgsLayoutItemMap))
main_map.setScale(400)
old_hash=hashlib.sha256((qgz_dir/'index.html').read_bytes()).hexdigest()
widget.on_submit()
assert messages and '大枠を超え' in messages[-1],messages
assert hashlib.sha256((qgz_dir/'index.html').read_bytes()).hexdigest()==old_hash
messages.clear();project.clear()
print('EDITED QGZ OVERFLOW REJECTED AND OLD OUTPUT KEPT: PASS',flush=True)

from RingyoZumenMaker.drawing_service import DrawingService
from RingyoZumenMaker.drawing_inputs import DrawingRequest
class RulerService(DrawingService):
    def apply_layer_color(self,layer,color,include_labels=False):
        super().apply_layer_color(layer,color,include_labels)
        layer.setLabelsEnabled(False)
        if layer.geometryType()==QgsWkbTypes.PointGeometry:layer.renderer().symbol().setOpacity(0)
    def configure_mix_line_label(self,layer,name,color=None):
        super().configure_mix_line_label(layer,name,QColor('red'));layer.setLabelsEnabled(False)

points=QgsVectorLayer('Point?crs=EPSG:6678','100m測点','memory')
for x in (0,100):
    f=QgsFeature(points.fields());f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x,0)));points.dataProvider().addFeature(f)
points.updateExtents();project.addMapLayer(points)
for paper in ('A4','A3'):
    out=root/f'normal-{paper}';out.mkdir()
    config={'format':'RingyoZumenMaker.config','version':3,'mode':'measurement','workflow':'roles','attribute_input_mode':'literal_per_drawing',
        'map':{'crs':'EPSG:6678','paper':paper,'scale':1000},'output':{'directory':str(out),'create_qgz':False},
        'polygons':{'items':[]},'lines':{'items':[{'drawing_uid':'00000000000000000000000000000001','role':'work','name':'検尺線',
           'point_name_expressions':['$id'],'sort_expression':'$id','has_width':False,'drawing_attributes':{}}]},'drawing_attributes':{'land':{}}}
    service=RulerService(DrawingRequest(config,{'00000000000000000000000000000001':points}));service.run()
    records.append({'plugin':'normal','paper':paper,'kind':'short','table':False,'html':str(out/'index.html')})
(root/'fixtures.json').write_text(json.dumps(records,ensure_ascii=False),encoding='utf-8')
print('FIXTURES',root/'fixtures.json',flush=True)
project.clear();print('PASS',flush=True);os._exit(0)
