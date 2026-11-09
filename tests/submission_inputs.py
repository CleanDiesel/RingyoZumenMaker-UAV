"""Manual No values, reference distance, raster defaults and submission ZIP routing."""
from pathlib import Path
import os,sys,json,zipfile,hashlib,copy
from lxml import etree as ET
from qgis.core import (QgsApplication,QgsProject,QgsCoordinateReferenceSystem,QgsVectorLayer,QgsFeature,QgsField,QgsGeometry,QgsProperty,QgsRasterLayer)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QMessageBox,QSpinBox
from osgeo import gdal
from RingyoZumenMaker.main import Main
project=QgsProject.instance()
out=Path(__import__('tempfile').mkdtemp(prefix='uav-submission-qa-',dir=os.environ['QGIS_TEST_OUTPUT_DIR']))
print('OUTPUT',out,flush=True)
messages=[]
QMessageBox.warning=lambda parent,title,message:messages.append(message)
def vector(name,kind,items):
    layer=QgsVectorLayer(f'{kind}?crs=EPSG:6678',name,'memory')
    layer.dataProvider().addAttributes([QgsField('number',QVariant.Int),QgsField('application',QVariant.String)])
    layer.updateFields()
    for number,application,wkt in items:
        f=QgsFeature(layer.fields());f.setAttributes([number,application]);f.setGeometry(QgsGeometry.fromWkt(wkt));layer.dataProvider().addFeature(f)
    layer.updateExtents();project.addMapLayer(layer);return layer
polygons=vector('施行地','MultiPolygon',[(31,'7006-01','MULTIPOLYGON(((0 0,40 0,40 40,0 40,0 0)))'),
    (54,'7006-02','MULTIPOLYGON(((60 0,100 0,100 40,60 40,60 0)))'),
    (88,'','MULTIPOLYGON(((120 0,160 0,160 40,120 40,120 0)))')])
lines=vector('工作物','MultiLineString',[(81,'7006-01','MULTILINESTRING((0 10,30 10))'),
    (93,'7006-02','MULTILINESTRING((60 10,90 10))'),(107,'','MULTILINESTRING((120 10,150 10))')])
refs=vector('基準点','Point',[(1,'','POINT(0 0)'),(2,'','POINT(20 20)')])
widget=Main();widget.crs.setCrs(QgsCoordinateReferenceSystem('EPSG:6678'));widget.scale.setScale(5000)
widget.polygon.setLayer(polygons);widget.singleLine.setLayer(lines);widget.singleLineWidth.setValue(1)
widget.singleLineName.setText('工作物');widget.polygonName.setText('施行地')
assert isinstance(widget.edaban,QSpinBox) and isinstance(widget.singleLineEdaban,QSpinBox)
assert widget.edaban.isEnabled() and widget.singleLineEdaban.isEnabled()
assert widget.edaban.value()==1 and widget.singleLineEdaban.value()==1
widget.edaban.setValue(12);widget.singleLineEdaban.setValue(34);widget.calculate_uav()
assert [f['No'] for f in widget.drawings[0]['application_layer'].getFeatures()]==[12,12,12]
assert [d['attributes']['No'] for d in widget.drawings[1:]]==[34,34,34]
widget.edabanOverride.setToProperty(QgsProperty.fromField('number'))
widget.singleLineEdabanOverride.setToProperty(QgsProperty.fromField('number'))
widget.calculate_uav()
assert [f['No'] for f in widget.drawings[0]['application_layer'].getFeatures()]==[31,54,88]
assert [d['attributes']['No'] for d in widget.drawings[1:]]==[81,93,107]
widget.edabanOverride.setToProperty(QgsProperty.fromExpression('1.5'))
try:widget.calculate_uav();raise AssertionError('No must be an integer')
except ValueError as error:assert 'No' in str(error)
widget.edabanOverride.setToProperty(QgsProperty.fromField('number'))
print('MANUAL NO AND PER-FEATURE NUMERIC VALUES OK',flush=True)

assert widget.distanceDecimals.value()==2
widget.kijunten.setLayer(refs)
for checked in (False,True):
    widget.isJochikeisan.setChecked(checked);widget.calculate_uav()
    for drawing in widget.drawings:
        widget.activate_drawing(drawing)
        sheet=widget.build_uav_html_sheet(1,'unused.png')
        row=sheet.xpath('.//div[@class="reference-distance"]')
        assert len(row)==1
        assert 'scale_' in row[0].getprevious().get('class','')
        assert '28.28' in ET.tostring(row[0],encoding='unicode')
widget.distanceDecimals.setValue(4);widget.calculate_uav()
assert '28.2843' in ET.tostring(widget.build_uav_html_sheet(1,'unused.png'),encoding='unicode')
widget.kijunten.setLayer(None);widget.calculate_uav()
assert not widget.build_uav_html_sheet(1,'unused.png').xpath('.//div[@class="reference-distance"]')
print('DISTANCE UNDER SCALE, CHECKBOX-INDEPENDENT DISPLAY AND PRECISION OK',flush=True)

def raster(name):
    path=out/name
    ds=gdal.GetDriverByName('GTiff').Create(str(path),20,20,1,gdal.GDT_Byte)
    ds.SetGeoTransform((0,1,0,20,0,-1));ds.SetProjection(QgsCoordinateReferenceSystem('EPSG:6678').toWkt());ds.GetRasterBand(1).Fill(240);ds=None
    layer=QgsRasterLayer(str(path),name);project.addMapLayer(layer);return path,layer
image,image_layer=raster('元画像 日本語.tif');other,other_layer=raster('別画像.tif')
image.with_suffix('.tfw').write_text('1\n0\n0\n-1\n0.5\n19.5\n')
widget.olso.setLayer(image_layer);assert Path(widget.assignmentOlso.filePath())==image.resolve()
widget.assignmentOlso.setFilePath(str(other));widget.olso.setLayer(other_layer)
assert Path(widget.assignmentOlso.filePath())==other.resolve()
widget.olso.setLayer(image_layer)
settings=widget.configuration_data();settings['output']['assignment_ortho']=''
widget.apply_configuration(settings);assert widget.assignmentOlso.filePath()==''
settings['output'].pop('assignment_ortho');widget.apply_configuration(settings)
assert Path(widget.assignmentOlso.filePath())==image.resolve()
widget.olso.setLayer(None);assert widget.assignmentOlso.filePath()==''
widget.assignmentOlso.setFilePath(str(image))
print('LOCAL ORTHO DEFAULT, LAYER CHANGE AND EXPLICIT SAVED CHOICE OK',flush=True)

widget.shinseibangoOverride.setToProperty(QgsProperty.fromField('application'))
widget.singleLineShinseibangoOverride.setToProperty(QgsProperty.fromField('application'))
widget.kijunten.setLayer(refs);widget.distanceDecimals.setValue(4);widget.isJochikeisan.setChecked(False)
widget.rinpan.setValue(12);widget.shohan.setValue(60);widget.isIchizu.setChecked(True)
widget.locationScale.setScale(5000);widget.createZip.setChecked(True);widget.outputMode.setCurrentIndex(1)
assert widget.formLayout_3.labelForField(widget.createZip).text()=='提出用ZIP'
widget.fileName.setFilePath(str(out))
assert widget.resolved_output_directory()==out
for invalid in ('../escape','CON','a/b','a.'):
    widget.output_name.setText(invalid)
    try:widget.resolved_output_directory();raise AssertionError(invalid)
    except ValueError:pass
widget.output_name.setText('現場A')
assert widget.resolved_output_directory()==out/'現場A'
widget.output_name_override.setToProperty(QgsProperty.fromExpression("'属性から指定'"))
assert widget.resolved_output_directory()==out/'属性から指定'
widget.output_name_override.setToProperty(QgsProperty.fromField('application'))
try:widget.resolved_output_directory();raise AssertionError('multiple folder names must fail')
except ValueError:pass
widget.output_name_override.setToProperty(QgsProperty())
widget.output_name.setText('現場A');target=out/'現場A'
config=widget.configuration_data();widget.apply_configuration(config)
assert widget.configuration_data()==config
widget.on_submit();assert widget.progressBar.value()==100,(messages,widget.outputlog.toPlainText());assert not messages,messages
assert not (out/'index.html').exists()
print('OPTIONAL OUTPUT FOLDER, EXPRESSIONS, NAME VALIDATION AND CONFIG ROUNDTRIP OK',flush=True)
archive=next(target.glob('*.zip'))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert len([n for n in names if n.startswith('図面/') and n.endswith('.pdf')])==4
    assert '位置図/位置図.pdf' in names
    assert not any(n.startswith('オルソ/') or n.startswith('シェープファイル/') for n in names)
    for application in ('7006-01','7006-02','申請番号未指定'):
        assert any(n.startswith(application+'/オルソ/') and n.endswith('.tif') for n in names)
        assert any(n.startswith(application+'/オルソ/') and n.endswith('.tfw') for n in names)
        shapes=[n for n in names if n.startswith(application+'/シェープファイル/') and n.endswith('.shp')]
        assert len(shapes)==2,(application,shapes)
        aggregate=next(n for n in shapes if '/申請区域/' in n)
        original=target/'シェープファイル/申請区域/申請区域.shp'
        for suffix in ('.shp','.shx','.dbf','.prj','.cpg'):
            assert z.read(str(Path(aggregate).with_suffix(suffix)).replace('\\','/'))==original.with_suffix(suffix).read_bytes()
    assert len([n for n in names if n.endswith('.shp')])==6
print('SUBMISSION ZIP: COMPLETE DRAWINGS DUPLICATED PER APPLICATION, INCLUDING MISSING NUMBER OK',flush=True)
html=ET.parse(str(target/'index.html'),ET.HTMLParser())
assert html.xpath('//h1')[0].text=='申請区域'
assert html.xpath('//div[@data-title="申請区域"]')
assert not (target/'シェープファイル/申請区域 - 全体').exists()
with zipfile.ZipFile(archive) as z:
    assert '図面/申請区域図.pdf' in z.namelist()
    assert '図面/付帯作工物図 - 工作物.pdf' in z.namelist()
    assert '図面/付帯作工物図 - 工作物 (2).pdf' in z.namelist()
    assert not any('/シェープファイル/付帯作工物/' in name for name in z.namelist())
    assert '7006-01/シェープファイル/付帯作工物 - 工作物/工作物 - 付帯作工物.shp' in z.namelist()
    assert '7006-01/シェープファイル/申請区域/申請区域.shp' in z.namelist()
assert len(html.xpath('//div[@class="reference-distance"]'))==4
assert all('28.2843' in ET.tostring(r,encoding='unicode') for r in html.xpath('//div[@class="reference-distance"]'))

widget.createZip.setChecked(False);widget.outputMode.setCurrentIndex(0);widget.on_submit()
assert widget.progressBar.value()==100,messages
qgz=next((target/'qgz').glob('*.qgz'));assert project.read(str(qgz))
assert widget.edaban.value()==12 and widget.singleLineEdaban.value()==34
assert widget.distanceDecimals.value()==4
assert Path(widget.fileName.filePath())==target and widget.output_name.text()==''
widget.calculate_uav()
assert [f['No'] for f in widget.drawings[0]['application_layer'].getFeatures()]==[31,54,88]
assert [d['attributes']['No'] for d in widget.drawings[1:]]==[81,93,107]
print('QGZ RESTORATION OF MANUAL NO, OVERRIDES AND DISTANCE PRECISION OK',flush=True)
widget.tabWidget.setCurrentIndex(0);widget.resize(760,950);widget.show();app=QgsApplication.instance();app.processEvents()
widget.grab().save(str(out/'basic-settings.png'))
widget.tabWidget.setCurrentWidget(widget.tab_5);app.processEvents();widget.grab().save(str(out/'submission-settings.png'))
widget.tabWidget.setCurrentIndex(1);app.processEvents();widget.grab().save(str(out/'manual-number-settings.png'))
widget.close();project.clear();print('PASS',flush=True)
