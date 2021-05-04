from typing import List, Optional
from PySide6.QtGui import QPageSize, QTextDocument, QFont, Qt, QPainter, QPixmap, QFontMetrics, QPen, QColor
from PySide6.QtCore import QSize, QRectF, QRect, QLine

from .style import Border, Fill
from .runtime import PreparedText, PreparedPage, PreparedBand, PreparedImage


TAG_REGISTRY = {}


class PreparedWidget:
    pass


class DocumentRenderer:
    def __init__(self, info):
        self.pages = []
        for page in info['pages']:
            PageRenderer(self, page)


class PageRenderer:
    x = 0
    y = 0
    bottom = 0

    def __init__(self, doc: DocumentRenderer, info=None):
        self.doc = doc
        self.height = info.height
        self.width = info.width
        self.margin = info.margin
        self.bands = []
        page = self
        self.init()
        doc.pages.append(self)
        for band in info.bands:
            b = BandRenderer(page, band)
            # if b.bottom > self.bottom:
            #     page = self.new_page()
            #     b.move_to(page.x, page.y)
            #     page.y += b.height
            page.bands.append(b)

    def new_page(self,):
        page = PageRenderer.__new__(PageRenderer)
        page.bands = []
        page.margin = self.margin
        self.doc.pages.append(page)
        page.doc = self.doc
        page.height = self.height
        page.width = self.width
        page.init()
        return page

    def init(self):
        self.bottom = self.height
        if self.margin:
            self.y = self.margin.top
            self.x = self.margin.left
            self.bottom -= self.margin.bottom


class BandRenderer:
    fill = None

    def __init__(self, page: PreparedPage, info):
        self.height = info.height
        self.width = info.width
        self.left = (info.left or 0) + page.x
        self.top = page.y
        self.objects = [type_map[obj['type']](self, page, obj) for obj in info.objects]
        page.y += self.height

    def move_to(self, x, y):
        self.top = y
        self.left = x
        for obj in self.objects:
            obj.move_to(x, y)

    @property
    def bottom(self):
        return self.top + self.height

    @classmethod
    def draw(cls, self: PreparedBand, painter: QPainter):
        if self.fill:
            r = QRectF(self.left, self.top, self.width, self.height)
            painter.fillRect(r, self.fill.color_1)


h_align_map = {
    'right': Qt.AlignRight,
    'center': Qt.AlignHCenter,
}

v_align_map = {
    'top': Qt.AlignTop,
    'center': Qt.AlignVCenter,
    'bottom': Qt.AlignBottom,
}


class TextRenderer:
    can_grow = False
    border = None
    can_shrink = False
    auto_width = None
    paddingX = 2
    paddingY = 1
    allow_tags = False
    _doc = None
    y = 0
    h_align = 0
    v_align = 0

    def __init__(self, band, page, info: PreparedText):
        self.height = info.height
        self.width = info.width
        self.top = info.top
        self.text: str = info.text
        self._text_word_wrap = 0
        self.left = info.left + page.x
        self.y = self.top + band.top
        self.font = QFont(info.fontName)
        if info.fontBold:
            self.font.setBold(info.fontBold)
        if info.fontItalic:
            self.font.setItalic(info.fontItalic)
        self.font.setPointSize(info.fontSize)
        self.v_align = v_align_map.get(info.vAlign)
        self.h_align = h_align_map.get(info.hAlign)
        self.backColor = info.backColor
        self.brushStyle = info.brushStyle or Qt.BrushStyle.SolidPattern
        self.border = info.border

    def move_to(self, x, y):
        self.y = y

    def calc_size(self):
        if self.can_grow or self.can_shrink or self.auto_width:
            rect = QRect(0, self.top, self.width - self.paddingX * 2 - self.border.width * 2, self.height)
            fm = QFontMetrics(self.font)
            flags = self._text_flags()
            r = fm.boundingRect(0, 0, rect.width(), 0, flags, self.text)
            if (self.can_shrink and self.height > r.height()) or (self.can_grow and self.height < r.height()):
                rect.setHeight(r.height())
            if self.auto_width:
                rect.setWidth(r.width() + self.border.width * 2)
            return QSize(rect.width() + self.paddingX * 2 + self.border.width * 2, rect.height() + self.border.width * 2)
        return QSize(self.width, self.height)

    @property
    def word_wrap(self) -> bool:
        return self._word_wrap

    @word_wrap.setter
    def word_wrap(self, value: bool):
        self._word_wrap = value
        if value:
            self._text_word_wrap = Qt.TextWordWrap

    @classmethod
    def textFlags(cls, self: PreparedText):
        ww = Qt.TextWordWrap if self.wordWrap else 0
        return h_align_map.get(self.hAlign, 0) | v_align_map.get(self.vAlign, 0) | ww

    @classmethod
    def draw(cls, x, y, self: PreparedText, painter: QPainter):
        font = QFont(self.fontName)
        if self.fontSize:
            font.setPointSizeF(self.fontSize)
        if self.fontBold:
            font.setBold(True)
        if self.fontItalic:
            font.setItalic(True)
        brushStyle = self.brushStyle or Qt.BrushStyle.SolidPattern
        w = self.width
        h = self.height
        tx = self.left + x
        ty = self.top + y
        if self.border:
            w -= self.border.width
            h -= self.border.width * 2
            tx += self.border.width
            ty += self.border.width
        rect = QRectF(tx, ty, w, h)

        if self.backColor:
            painter.setBrush(brush_style_map[brushStyle])
            painter.fillRect(rect, QColor('#' + hex(self.backColor)[2:]))
        if self.allowTags:
            doc = self._doc
            doc.setTextWidth(self.width)
            opt = doc.defaultTextOption()
            if self.hAlign:
                opt.setAlignment(self.hAlign)
            doc.setDefaultTextOption(opt)
            doc.setHtml(self.text)
            doc.setDocumentMargin(0)
            painter.save()
            painter.translate(0, ty)
            ty = self.top + self.border.width * 2
            doc.setDefaultFont(font)
            doc.drawContents(painter, QRectF(x, y, w, h))
            painter.restore()
        else:
            painter.save()
            painter.setFont(font)
            flags = cls.textFlags(self)
            rect.setX(rect.x() + 2)
            rect.setY(rect.y() + 1)
            painter.drawText(rect, flags, self.text)
            painter.restore()
        if self.border and self.border.color is not None:
            old_pen = painter.pen()
            pen = QPen(QColor(self.border.color), self.border.width)
            painter.setPen(pen)
            painter.drawLines(cls.getLines(self, self.left + x, self.top + y, self.left + self.width + x, self.top + y + self.height))
            painter.setPen(old_pen)

    @classmethod
    def getLines(cls, self, x1, y1, x2, y2):
        r = []
        if self.border.left:
            r.append(QLine(x1, y1, x1, y2))
        if self.border.top:
            r.append(QLine(x1, y1, x2, y1))
        if self.border.right:
            r.append(QLine(x2, y1, x2, y2))
        if self.border.bottom:
            r.append(QLine(x1, y2, x2, y2))
        return r


class ImageRenderer:
    @classmethod
    def draw(cls, x, y, self: PreparedImage, painter: QPainter):
        img = QPixmap()
        img.loadFromData(self.picture)
        painter.drawPixmap(x + self.left, y + self.top, self.width, self.height, img)


type_map = {
    'text': TextRenderer,
}

brush_style_map = {
    0: Qt.BrushStyle.NoBrush,
    1: Qt.BrushStyle.SolidPattern,
}
