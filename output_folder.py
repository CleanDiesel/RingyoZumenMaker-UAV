"""Optional output subfolder, with a single data-defined name per run."""
from pathlib import Path

from qgis.PyQt.QtWidgets import QLineEdit, QWidget, QHBoxLayout
from qgis.core import (QgsExpressionContext, QgsExpressionContextGenerator,
                       QgsExpressionContextUtils, QgsProperty, QgsPropertyDefinition,
                       QgsVariantUtils)
from qgis.gui import QgsPropertyOverrideButton


class FolderContext(QgsExpressionContextGenerator):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def createExpressionContext(self):
        layer = self.owner.output_attribute_layer()
        context = QgsExpressionContext()
        context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        if layer is not None:
            context.setFields(layer.fields())
        return context


class OutputFolder:
    def output_attribute_layer(self):
        return self.polygon.currentLayer() or self.singleLine.currentLayer()

    def setup_output_folder(self):
        self.output_name = QLineEdit()
        self.output_name.setPlaceholderText("空欄なら保存先へ直接出力")
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        button = self.output_name_override = QgsPropertyOverrideButton(row)
        button.init(0, QgsProperty(), QgsPropertyDefinition(
            "output_folder_name", "出力フォルダ名", QgsPropertyDefinition.StandardPropertyTemplate.String),
            self.output_attribute_layer(), False)
        self._folder_context = FolderContext(self)
        button.registerExpressionContextGenerator(self._folder_context)
        button.setUsageInfo("施行地の対象地物の属性・式から、一つの出力フォルダ名を指定します。施行地がなければ付帯作工物を使います。")
        button.menu().aboutToShow.connect(self.label_folder_expression_menu)
        button.changed.connect(lambda: self.output_name.setEnabled(not button.isActive()))
        button.activated.connect(lambda *_: self.output_name.setEnabled(not button.isActive()))
        for combo in (self.polygon, self.singleLine):
            combo.layerChanged.connect(lambda *_: button.setVectorLayer(self.output_attribute_layer()))
        layout.addWidget(self.output_name, 1)
        layout.addWidget(button)
        # Keep the destination and its optional name together at the top.
        self.formLayout_3.insertRow(1, "出力フォルダ名（任意）", row)

    def label_folder_expression_menu(self):
        from qgis.PyQt.QtCore import QCoreApplication
        edit = QCoreApplication.translate("QgsPropertyOverrideButton", "Edit…")
        for action in self.output_name_override.menu().actions():
            if action.text() in (edit, "Edit…", "編集…"):
                action.setText("式を入力・編集…")

    def saved_output_folder(self):
        prop = self.output_name_override.toProperty()
        return {"value": self.output_name.text(), "property": prop.toVariant()} if prop.asExpression() else self.output_name.text()

    def restore_output_folder(self, saved):
        prop = QgsProperty()
        if isinstance(saved, dict):
            if not prop.loadVariant(saved.get("property", {})):
                raise ValueError("出力フォルダ名の上書き設定を読み込めません")
            saved = saved.get("value", "")
        self.output_name.setText(str(saved or ""))
        self.output_name_override.setToProperty(prop)
        self.output_name.setEnabled(not prop.isActive())

    def resolved_output_directory(self):
        base = Path(self.fileName.filePath())
        if not self.fileName.filePath().strip() or not base.is_dir():
            raise ValueError("出力先には存在するフォルダを指定してください")
        prop = self.output_name_override.toProperty()
        if prop.isActive():
            layer = self.output_attribute_layer()
            combo = "polygon" if self.polygon.currentLayer() is not None else "singleLine"
            features = self.selected_features(combo, combo + "Filter") if layer is not None else [None]
            context = self._folder_context.createExpressionContext()
            names = []
            for feature in features:
                if feature is not None:
                    context.setFeature(feature)
                value, ok = prop.value(context)
                if not ok:
                    raise ValueError("出力フォルダ名の式を評価できません")
                name = "" if QgsVariantUtils.isNull(value) else str(value).strip()
                if name and name not in names:
                    names.append(name)
            if not names:
                raise ValueError("出力フォルダ名の式から名前を取得できませんでした")
            if len(names) != 1:
                raise ValueError("出力フォルダ名が複数あります。抽出条件や式で一つの名前に絞ってください。")
            name = names[0]
        else:
            name = self.output_name.text().strip()
        reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{p}{i}" for p in ("COM", "LPT") for i in range(1, 10)}
        if name and (name in (".", "..") or name.endswith((".", " ")) or len(name) > 255
                     or any(c in '\\/:*?"<>|' or ord(c) < 32 for c in name)
                     or name.split(".")[0].upper() in reserved):
            raise ValueError("出力フォルダ名にはパスではなく、使用可能なフォルダ名を一つ指定してください：" + name)
        return base / name if name else base
