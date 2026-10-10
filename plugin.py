"""QGIS menu, toolbar and drawing dock lifecycle."""
from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtGui import QAction, QIcon

from .main import Main


class RingyoZumenMakerPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dock = None

    @staticmethod
    def tr(message):
        return QCoreApplication.translate("RingyoZumenMaker", message)

    def initGui(self):
        self.action = QAction(QIcon(str(Path(__file__).parent / "icon.png")),
                              self.tr("RingyoZumenMaker"), self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.tr("&RingyoZumenMaker"), self.action)

    def run(self, checked=True):
        if self.dock is None:
            self.dock = Main(self.iface.mainWindow(), iface=self.iface)
            self.dock.visibilityChanged.connect(self.action.setChecked)
            self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.setVisible(checked)
        if checked:
            self.dock.raise_()

    def unload(self):
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        if self.action is not None:
            self.iface.removePluginMenu(self.tr("&RingyoZumenMaker"), self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None
