"""Disjoint deduction pieces and stable priority ordering."""
from qgis.core import QgsGeometry


def exclusion_parts(owner, application, sources, minimum):
    """Return (geometry, source indices) pieces, skipped parts and overlap notes."""
    check = owner.checked_operation
    exclusive = owner.exclusionOverlap.currentIndex() == 1
    skipped, notes, pieces = [], [], []
    if not sources:
        return pieces, skipped, notes
    if exclusive:
        claimed = QgsGeometry()
        for index, source in enumerate(sources):
            original = check(application.intersection(source[0]), "除地の切り出し")
            remaining = check(original.difference(claimed), "優先順位による重複除去") if not claimed.isEmpty() else original
            removed = original.area() - remaining.area()
            if removed > 1e-8:
                notes.append((source[1] or f"除地{index + 1}", original.area(), removed, remaining.area(), index))
            for part in owner.polygon_parts(remaining):
                if part.area() < minimum:
                    skipped.append((source[1], part.area()))
                else:
                    pieces.append((part, (index,)))
            claimed = check(QgsGeometry.unaryUnion([claimed, original]) if not claimed.isEmpty() else QgsGeometry(original), "優先除地の統合")
    else:
        union = check(QgsGeometry.unaryUnion([source[0] for source in sources]), "除地の重複統合")
        clipped = check(application.intersection(union), "除地との重なり")
        # Keep the original minimum-area rule: test connected union parts before
        # splitting their formula labels into exclusive membership regions.
        accepted = []
        for part in owner.polygon_parts(clipped):
            if part.area() < minimum:
                names = [s[1] for s in sources if s[1] and part.intersection(s[0]).area() > 1e-8]
                skipped.append(("・".join(dict.fromkeys(names)), part.area()))
            else:
                accepted.append(part)
        if not accepted:
            return pieces, skipped, notes
        accepted_union = check(QgsGeometry.unaryUnion(accepted), "採用除地の統合")
        cells = []
        for index, source in enumerate(sources):
            incoming = check(accepted_union.intersection(source[0]), "除地の所属分割")
            updated = []
            remainder = QgsGeometry(incoming)
            for cell, members in cells:
                common = check(cell.intersection(incoming), "除地重複部分の分割")
                difference = check(cell.difference(incoming), "除地単独部分の分割")
                if difference.area() > 1e-8:
                    updated.append((difference, members))
                if common.area() > 1e-8:
                    updated.append((common, members + (index,)))
                remainder = check(remainder.difference(cell), "除地の残り部分")
            if remainder.area() > 1e-8:
                updated.append((remainder, (index,)))
            cells = updated
        for cell, members in cells:
            pieces.extend((part, members) for part in owner.polygon_parts(cell))
    return pieces, skipped, notes
