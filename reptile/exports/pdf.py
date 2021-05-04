from PySide6.QtGui import QPainter, QFont, QGuiApplication
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtCore import QMarginsF, QSizeF, QSize
from reptile.runtime import PreparedBand
from reptile.qt import BandRenderer, TextRenderer
from reptile.units import mm


class QReportEngine:
    app = None


class PDF:
    def __init__(self, document):
        if not QReportEngine.app:
            QReportEngine.app = QGuiApplication([])
        self.document = document
        self.printer = None
        self.painter = None
        self._isFirstPage = False

    def export(self, filename):
        self.printer = QPrinter()
        self.printer.setOutputFileName(filename)
        self.printer.setPageMargins(QMarginsF(0, 0, 0, 0))
        self.printer.setResolution(72)
        pages = self.document['pages']
        if pages:
            page = pages[0]
            self.printer.setPageSize(QSize(page.width, page.height))
        self.painter = QPainter()
        self.painter.begin(self.printer)
        self._isFirstPage = True
        for page in pages:
            self.exportPage(page)
            self._isFirstPage = False
        self.painter.end()

    def exportPage(self, page):
        if not self._isFirstPage:
            self.printer.newPage()
        for band in page.bands:
            self.exportBand(band)

    def exportBand(self, band: PreparedBand):
        BandRenderer.draw(band, self.painter)
        for obj in band.objects:
            TextRenderer.draw(band.left, band.top, obj, self.painter)

