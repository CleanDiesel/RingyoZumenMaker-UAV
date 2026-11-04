"""Validate the actual exported map frame and record occupied image space."""
import numpy as np
from qgis.PyQt.QtGui import QImage
from qgis.core import QgsGeometry, QgsPointXY, QgsCoordinateTransform, QgsProject


def validate_drawing_frame(owner, map_item):
    polygon = list(map_item.visibleExtentPolygon())
    points = [QgsPointXY(point.x(), point.y()) for point in polygon]
    if points and points[0] != points[-1]: points.append(points[0])
    frame = QgsGeometry.fromPolygonXY([points])
    # Leave room for the stroke at the boundary, rather than accepting a line
    # whose centre is inside the frame but whose outer half would be clipped.
    margin = .5 * map_item.scale() / 1000
    safe = frame.buffer(-margin, 8)
    if safe.isEmpty(): raise ValueError('地図枠の大きさを確認してください')
    targets = [owner.original_layer]
    if owner.reference_layer is not None: targets.append(owner.reference_layer)
    for layer in targets:
        transform = QgsCoordinateTransform(layer.crs(), map_item.crs(), QgsProject.instance())
        for feature in layer.getFeatures():
            geometry = QgsGeometry(feature.geometry())
            if geometry.isEmpty(): continue
            geometry.transform(transform)
            if not geometry.difference(safe).isEmpty():
                title = owner._current_drawing['folder']
                raise ValueError(f'{title}: 指定縮尺では生成図が大枠を超えます。'
                                 '縮尺の分母を大きくするか、QGZの地図位置を調整してください。')


def occupied_bottom(image, has_ortho=False):
    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    buffer = rgba.constBits()
    buffer.setsize(rgba.sizeInBytes())
    values = np.frombuffer(buffer, dtype=np.uint8, count=rgba.sizeInBytes()).reshape(rgba.height(), rgba.bytesPerLine())
    pixels = values[:, :rgba.width() * 4].reshape(rgba.height(), rgba.width(), 4)
    visible = (pixels[:, :, 3] > 0) & np.any(pixels[:, :, :3] < 250, axis=2)
    rows = np.flatnonzero(visible.any(axis=1))
    return float(rows[-1] + 1) / rgba.height() if rows.size else 0.0
