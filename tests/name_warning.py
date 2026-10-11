"""Warn only when a changed name will inherit disabled drawing labels."""
import runpy
from pathlib import Path
from unittest.mock import patch

fixture = runpy.run_path(str(Path(__file__).with_name("auxiliary_background.py")))
globals().update({key: value for key, value in fixture.items() if not key.startswith("__")})
from qgis.core import QgsFeature, QgsMapLayerStyle
from qgis.PyQt.QtWidgets import QWidget

def named_layer(name, enabled):
    layer = QgsVectorLayer(f"Point?crs=EPSG:6678&field=label:string&field={UID}:string", name, "memory")
    feature = QgsFeature(layer.fields())
    feature.setAttributes([name, "stable-id"])
    assert layer.dataProvider().addFeature(feature)
    settings = QgsPalLayerSettings()
    settings.fieldName = "label"
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(enabled)
    style = QgsMapLayerStyle()
    style.readFromLayer(layer)
    layer.styleManager().addStyle("図面:aggregate", style)
    return layer

old = named_layer("旧名称", False)
new = named_layer("新名称", True)
exporter = UnifiedProjects.__new__(UnifiedProjects)
exporter.captures = [{"key": "aggregate", "title": "申請区域 - 全体",
                      "layers": [("unused", "output:aggregate", None)]}]
exporter.datasets = {"output:aggregate": new}
exporter.aliases = {"output:aggregate": "output:aggregate"}
exporter.old_layers = {"output:aggregate": old}
assert exporter.label_visibility_warnings() == ["申請区域 - 全体"]
exporter.datasets["output:aggregate"] = named_layer("旧名称", True)
assert not exporter.label_visibility_warnings()
exporter.datasets["output:aggregate"] = named_layer("", False)
assert not exporter.label_visibility_warnings()
exporter.datasets["output:aggregate"] = new
exporter.old_layers["output:aggregate"] = named_layer("旧名称", True)
assert not exporter.label_visibility_warnings()
exporter.old_layers = {}
assert not exporter.label_visibility_warnings()
exporter.old_layers["output:aggregate"] = old
# An enabled canvas style must not hide the disabled drawing theme.
old.setLabelsEnabled(True)
assert exporter.label_visibility_warnings() == ["申請区域 - 全体"]
exporter.owner = QWidget()
logs, alerts = [], []
exporter.owner.append_output_log = logs.append
exporter.prepare_inputs = lambda: None
with patch("RingyoZumenMaker.unified_project.QMessageBox.warning",
           side_effect=lambda parent, title, message: alerts.append((title, message))), \
        patch.object(exporter, "_write_data", side_effect=OSError("stop after alert")):
    try:
        exporter.save()
    except OSError:
        pass
assert len(alerts) == 1 and alerts[0][0] == "名称変更時のラベル確認"
assert "申請区域 - 全体" in alerts[0][1]
assert len(logs) == 1
assert old.labelsEnabled(), "Checking the saved theme must not alter the canvas style"
print("PASS: renamed/unchanged/cleared names, enabled/disabled drawing styles and actual alert")
