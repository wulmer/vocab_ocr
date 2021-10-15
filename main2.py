import cv2
import pytesseract
from PySide6 import QtCore, QtGui, QtWidgets
import sys


class PhotoViewer(QtWidgets.QGraphicsView):
    photoClicked = QtCore.Signal(QtCore.QPoint)

    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        self._zoom = 0
        self._empty = True
        self._scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

    def hasPhoto(self):
        return not self._empty

    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0

    def setPhoto(self, pixmap=None):
        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self._photo.setPixmap(QtGui.QPixmap())
        self._scene = QtWidgets.QGraphicsScene(self)
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.fitInView()

    def wheelEvent(self, event):
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            elif self._zoom == 0:
                self.fitInView()
            else:
                self._zoom = 0

    def toggleDragMode(self):
        if self.dragMode() == QtWidgets.QGraphicsView.ScrollHandDrag:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        elif not self._photo.pixmap().isNull():
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def mousePressEvent(self, event):
        if self._photo.isUnderMouse():
            self.photoClicked.emit(self.mapToScene(event.pos()).toPoint())
        super(PhotoViewer, self).mousePressEvent(event)


class Example(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.pixmap = QtGui.QPixmap(0, 0)
        self.rotation = 0
        self.add_new_line = False
        self.boxes = []
        self.initUI()

    def refreshPixmap(self):
        frame = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        image =  QtGui.QImage(frame,frame.shape[1],frame.shape[0],frame.strides[0],QtGui.QImage.Format_RGB888)
        self.viewer.setPhoto(QtGui.QPixmap.fromImage(image))
        for box in self.boxes:
            self.viewer._scene.addRect(box[0])

    def initUI(self):
        vbox = QtWidgets.QVBoxLayout(self)
        hbox = QtWidgets.QHBoxLayout(self)
        
        # self.lbl = QtWidgets.QLabel(self)
        self.viewer = PhotoViewer(self)
        self.viewer.photoClicked.connect(self.onPhotoClicked)

        self.text = QtWidgets.QPlainTextEdit(self)
        self.text.setCursorWidth(2)
        tb = QtWidgets.QToolBar(self)

        load_action = tb.addAction("load")
        load_action.triggered.connect(self.loadImage)
        rotate_left_action = tb.addAction("rotate left")
        rotate_left_action.triggered.connect(self.onRotateLeft)
        rotate_right_action = tb.addAction("rotate right")
        rotate_right_action.triggered.connect(self.onRotateRight)
        tb.addSeparator()
        scan_action = tb.addAction("scan text")
        scan_action.triggered.connect(self.onScanText)
        tb.addSeparator()
        save_action = tb.addAction("save as textfile")
        save_action.triggered.connect(self.onSaveFile)

        # hbox.addWidget(self.lbl)
        hbox.addWidget(self.viewer)
        hbox.addWidget(self.text)

        vbox.addWidget(tb)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

        self.move(300, 200)
        self.setWindowTitle('Image with PyQt')
        self.show()

    def loadImage(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self,'Select File')
        self.original_image = cv2.imread(str(filename[0]))
        self.image = self.original_image.copy()
        self.boxes = []
        self.refreshPixmap()

    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_F1:
            self.text.moveCursor(QtGui.QTextCursor.End)
            if self.add_new_line:
                self.text.insertPlainText('\n')
            else:
                self.text.insertPlainText(';')
            self.add_new_line = not self.add_new_line
        else:
            super().keyPressEvent(ev)

    def onPhotoClicked(self, pos):
        for box, text in self.boxes:
            if box.contains(pos.x(), pos.y()):
                #self.boxes.remove(box)
                self.text.moveCursor(QtGui.QTextCursor.End)
                self.text.insertPlainText(text.replace(';', ',') + ' ')
                break

    def onRotateLeft(self):
        self.image = cv2.rotate(self.image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        self.rotation -= 90
        self.boxes = []
        self.refreshPixmap()

    def onRotateRight(self):
        self.image = cv2.rotate(self.image, cv2.ROTATE_90_CLOCKWISE)
        self.rotation += 90
        self.boxes = []
        self.refreshPixmap()

    def onScanText(self):
        self.boxes = []
        d = pytesseract.image_to_data(self.image, lang='eng+fra+deu', output_type=pytesseract.Output.DICT)
        n_boxes = len(d['level'])
        for i in range(n_boxes):
            if d['word_num'][i] > 0:
                found_text = d['text'][i].strip()
                if found_text:
                    (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])
                    rect = QtCore.QRectF(x, y, w, h)
                    self.boxes.append((rect, found_text))
        self.refreshPixmap()

    def onSaveFile(self):
        file_extension = '.csv'
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self,'Select File', filter='*' + file_extension)
        if filename:
            if not filename.endswith(file_extension):
                filename += file_extension
            with open(str(filename), 'w', encoding='utf8') as f:
                f.write(self.text.toPlainText())


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec())