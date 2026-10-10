"""Exercise the real QGIS plugin entry point and dock actions."""
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
base = Path(r"C:\Users\m48c7\AppData\Local\Programs\OSGeo4W")
dll_handles = [os.add_dll_directory(str(base / part))
               for part in ("bin", "apps/Qt6/bin", "apps/qgis/bin")]
sys.path[:0] = [str(base / "apps/qgis/python"), str(base / "apps/qgis/python/plugins")]

from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QMainWindow
from RingyoZumenMaker import classFactory
from RingyoZumenMaker import plugin as plugin_module

assert Path(plugin_module.__file__).resolve().parent == Path(__file__).resolve().parents[1]
app = QgsApplication([], False)
app.initQgis()


class Interface:
    def __init__(self):
        self.window = QMainWindow()
        self.toolbar, self.menu = [], []

    def mainWindow(self):
        return self.window

    def addToolBarIcon(self, action):
        self.toolbar.append(action)

    def removeToolBarIcon(self, action):
        self.toolbar.remove(action)

    def addPluginToMenu(self, name, action):
        self.menu.append((name, action))

    def removePluginMenu(self, name, action):
        self.menu.remove((name, action))

    def addDockWidget(self, area, dock):
        self.window.addDockWidget(area, dock)

    def removeDockWidget(self, dock):
        self.window.removeDockWidget(dock)


iface = Interface()
iface.window.show()
plugin = classFactory(iface)
plugin.initGui()
assert plugin.action.text() == "RingyoZumenMaker"
assert len(iface.toolbar) == len(iface.menu) == 1
plugin.action.trigger()
app.processEvents()
dock = plugin.dock
assert dock.isVisible() and plugin.action.isChecked()
assert dock.tabWidget.count() == 5
plugin.action.trigger()
app.processEvents()
assert dock.isHidden() and not plugin.action.isChecked()
plugin.action.trigger()
app.processEvents()
assert plugin.dock is dock and dock.isVisible()
dock.hide()
app.processEvents()
assert not plugin.action.isChecked()
plugin.unload()
assert plugin.dock is None and plugin.action is None
assert not iface.toolbar and not iface.menu
iface.window.close()
print("new repository: plugin entry point, menu/toolbar, dock open/close/reuse and unload OK", flush=True)
