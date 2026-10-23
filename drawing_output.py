"""Drawing options and submission archive output."""
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path

from lxml import etree as ET
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout,
)

from .unified_project import feature_uid


@contextmanager
def browser_workspace(directory):
    directory = Path(directory).resolve()
    work = Path(tempfile.mkdtemp(prefix=".ringyo_zip_work_", dir=directory)).resolve()
    if work.parent != directory or not work.name.startswith(".ringyo_zip_work_"):
        raise OSError("ブラウザーの作業フォルダを確認できません")
    try:
        yield work
    finally:
        # Chromium's crash reporter may hold its profile briefly after PDF completion.
        for _ in range(40):
            shutil.rmtree(work, ignore_errors=True)
            if not work.exists():
                break
            time.sleep(.05)


class DrawingOutput:
    def setup_drawing_output(self):
        self._drawing_tables = {}
        self.attributeTables = QPushButton("図面ごとの属性表…")
        self.attributeTables.clicked.connect(self.edit_drawing_tables)
        self.formLayout_3.addRow("属性表", self.attributeTables)
        self.createZip = QCheckBox("ZIPを作成する")
        self.formLayout_3.addRow("ZIP", self.createZip)
        row = QHBoxLayout()
        self.zipDirectory = QLineEdit()
        self.zipDirectory.setPlaceholderText("出力フォルダに保存")
        self.zipBrowse = QPushButton("参照…")
        self.zipBrowse.clicked.connect(self.choose_zip_directory)
        row.addWidget(self.zipDirectory, 1)
        row.addWidget(self.zipBrowse)
        self.formLayout_3.addRow("ZIP保存先", row)
        self.createZip.toggled.connect(self.zipDirectory.setEnabled)
        self.createZip.toggled.connect(self.zipBrowse.setEnabled)
        self.zipDirectory.setEnabled(False)
        self.zipBrowse.setEnabled(False)

    def choose_zip_directory(self):
        path = QFileDialog.getExistingDirectory(
            self, "ZIPの保存先", self.zipDirectory.text() or self.fileName.filePath())
        if path:
            self.zipDirectory.setText(path)

    def edit_drawing_tables(self):
        try:
            candidates = []
            if self.polygon.currentLayer() is not None and self.selected_features("polygon", "polygonFilter"):
                candidates.append(("aggregate", "申請区域図（全体）"))
            source = self.singleLine.currentLayer()
            if source is not None:
                for index, feature in enumerate(self.selected_features("singleLine", "singleLineFilter"), 1):
                    name = self.clean_html_text(self.evaluate_attribute("singleLineName", source, feature)).strip()
                    candidates.append(("line:" + feature_uid(source, feature),
                                       f"付帯作工物図 No.{index} {name}"))
            if not candidates:
                raise ValueError("施行地または付帯作工物の対象地物を指定してください")
        except Exception as error:
            QMessageBox.warning(self, "属性表", str(error))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("図面ごとの属性表")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("チェックした図面の写真下に属性表を表示します。"))
        listing = QListWidget()
        for key, name in candidates:
            item = QListWidgetItem(name, listing)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if self._drawing_tables.get(key, True)
                               else Qt.CheckState.Unchecked)
        layout.addWidget(listing)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.resize(520, 360)
        if dialog.exec():
            for index in range(listing.count()):
                item = listing.item(index)
                self._drawing_tables[item.data(Qt.ItemDataRole.UserRole)] = item.checkState() == Qt.CheckState.Checked

    def drawing_has_table(self):
        return self._drawing_tables.get(self._current_drawing["key"], True)

    @staticmethod
    def pdf_browser():
        candidates = [shutil.which("msedge"), shutil.which("google-chrome"),
                      shutil.which("chromium"), shutil.which("chromium-browser")]
        for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
            base = os.environ.get(variable)
            if base:
                candidates.extend(str(Path(base) / suffix) for suffix in (
                    "Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe"))
        return next((path for path in candidates if path and Path(path).is_file()), None)

    def build_drawing_zip(self):
        """Build from this run only; atomically replace ZIP without making a backup."""
        browser = self.pdf_browser()
        if not browser:
            raise ValueError("HTML図面のPDF化にはMicrosoft EdgeまたはGoogle Chromeが必要です")
        output = self.output_dir()
        if not (output / "位置図/位置図.pdf").is_file():
            raise ValueError("ZIPに収録する位置図がありません。「位置図の生成」を有効にしてください")
        ortho = self._zip_ortho
        if ortho is None or not Path(ortho).is_file():
            raise ValueError("ZIPに収録するオルソ画像を指定してください")
        final = Path(self._final_output_dir)
        directory = Path(self.zipDirectory.text().strip() or final)
        if not directory.is_dir():
            raise ValueError("ZIP保存先には存在するフォルダを指定してください")
        filename = (self.compartment_file_stem() or "図面") + ".zip"
        # Keep the pending archive outside the staged tree/backup inventory.
        with browser_workspace(final) as temp:
            pdfs = []
            for index, drawing in enumerate(self.drawings, 1):
                root = ET.parse(str(output / "index.html"), ET.HTMLParser()).getroot()
                root.find("body").set("data-print-all", "1")
                for sheet in root.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' drawing-sheet ')]"):
                    if sheet.get("data-drawing") != str(index):
                        sheet.getparent().remove(sheet)
                root.find("head").insert(0, ET.Element("base", href=output.as_uri() + "/"))
                html = temp / f"drawing_{index}.html"
                html.write_text("<!DOCTYPE html>\n" + ET.tostring(root, encoding="unicode", method="html"), encoding="utf-8")
                pdf = temp / f"drawing_{index}.pdf"
                command = [browser, "--headless", "--disable-gpu", "--no-first-run",
                           "--no-pdf-header-footer", "--allow-file-access-from-files", "--disable-crash-reporter",
                           "--disable-breakpad", "--disable-background-mode",
                           "--virtual-time-budget=5000", f"--user-data-dir={temp / ('browser_' + str(index))}",
                           f"--print-to-pdf={pdf}", html.as_uri()]
                with subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)) as process:
                    deadline = time.monotonic() + 90
                    while True:
                        QApplication.processEvents()
                        # On Windows Edge's launcher can exit before its worker writes the PDF.
                        if pdf.is_file():
                            with pdf.open("rb") as stream:
                                stream.seek(max(0, pdf.stat().st_size - 32))
                                if b"%%EOF" in stream.read():
                                    break
                        if process.poll() not in (None, 0):
                            raise OSError(f"HTML図面のPDF化に失敗しました: {drawing['folder']}")
                        if time.monotonic() > deadline:
                            if process.poll() is None:
                                process.kill()
                            raise OSError("HTML図面のPDF化がタイムアウトしました")
                        time.sleep(.05)
                    if not pdf.is_file() or pdf.stat().st_size < 100:
                        raise OSError(f"HTML図面のPDF化に失敗しました: {drawing['folder']}")
                pdfs.append((pdf, "図面/" + self.safe_file_name(drawing["folder"].replace("/", "_")) + ".pdf"))
            pending = temp / filename
            with zipfile.ZipFile(pending, "w", zipfile.ZIP_DEFLATED) as archive:
                for pdf, name in pdfs:
                    archive.write(pdf, name)
                archive.write(output / "位置図/位置図.pdf", "位置図/位置図.pdf")
                for path in sorted(Path(ortho).parent.glob(Path(ortho).stem + ".*")):
                    if path.is_file():
                        archive.write(path, "オルソ/" + path.name)
                for drawing in self.drawings:
                    source = output / "シェープファイル" / Path(drawing["folder"]).name
                    folder = ("申請区域" if drawing["kind"] == "申請区域" else
                              "付帯作工物/" + Path(drawing["folder"]).name)
                    for path in sorted(source.iterdir()):
                        if path.is_file() and path.suffix.lower() in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
                            archive.write(path, "シェープファイル/" + folder + "/" + path.name)
            with zipfile.ZipFile(pending) as archive:
                if archive.testzip() is not None:
                    raise OSError("ZIPの検証に失敗しました")
            handle, name = tempfile.mkstemp(prefix=".ringyo_zip_", suffix=".tmp", dir=directory)
            os.close(handle)
            try:
                shutil.copyfile(pending, name)
            except Exception:
                Path(name).unlink(missing_ok=True)
                raise
            self._pending_zip = (Path(name), directory / filename)

    def save_drawing_zip(self):
        pending, target = self._pending_zip
        try:
            os.replace(pending, target)
        finally:
            pending.unlink(missing_ok=True)
            del self._pending_zip
        self.append_output_log(f"ZIP: {target}")
