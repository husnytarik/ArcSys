# app/layer_tree.py

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt


class LayerTreeWidget(QtWidgets.QTreeWidget):
    """
    Soldaki 'Katmanlar' paneli için özel ağaç:
    - 0. kolon: katman adı
    - 1. kolon: göz ikonu ([●] / [ ])
    - Göz ikonuna tıklayınca görünürlük toggle
    - Parent gizlenirse tüm child'lar da gizlenir (Photoshop mantığı)
    """

    # layer_key, visible
    layerVisibilityChanged = QtCore.pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 2 kolon: 0 = label, 1 = göz
        self.setColumnCount(2)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(True)
        self.setIndentation(16)
        self.setUniformRowHeights(True)

        header = self.header()
        header.setStretchLastSection(False)
        # PyQt6'daki yeni enum ismini kullan, eski sürümler için fallback bırak
        try:
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(
                1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
            )
        except AttributeError:
            # Daha eski bir Qt/PyQt sürümü kullanılıyorsa
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)

    # ---- Dışarıdan item eklemek için yardımcı ----
    def add_layer_item(
        self,
        parent_item: QtWidgets.QTreeWidgetItem | None,
        label: str,
        layer_key: str,
        visible: bool = True,
    ) -> QtWidgets.QTreeWidgetItem:
        """
        parent_item None ise root'a ekler.
        layer_key: harita tarafında bu grubu/layer'ı tanımak için string.
        """
        if parent_item is None:
            item = QtWidgets.QTreeWidgetItem(self)
        else:
            item = QtWidgets.QTreeWidgetItem(parent_item)

        # 0. kolon label
        item.setText(0, label)

        # 0. kolon UserRole: layer_key
        item.setData(0, Qt.ItemDataRole.UserRole, layer_key)
        # 1. kolon UserRole: visible bilgisi
        item.setData(1, Qt.ItemDataRole.UserRole, visible)

        # Mouse ile seçilebilsin ama edit edilemesin
        flags = item.flags()
        flags &= ~QtCore.Qt.ItemFlag.ItemIsEditable
        flags |= QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled
        item.setFlags(flags)

        self._update_eye_icon(item)
        return item

    # ---- Göz kolonuna tıklandığını yakala ----
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        pos = event.position().toPoint()
        index = self.indexAt(pos)

        if not index.isValid():
            return super().mousePressEvent(event)

        # SADECE 1. KOLON (göz kolonu) toggle yapsın
        if index.column() == 1:
            item = self.itemFromIndex(index)
            self.toggle_item_visibility(item)
            return

        # Diğer kolonlar normal davranır (expand/collapse + selection)
        super().mousePressEvent(event)

    def toggle_item_visibility(self, item: QtWidgets.QTreeWidgetItem):
        """Tek bir item'in görünürlüğünü tersine çevir ve çocuklara uygula."""
        current_visible = bool(item.data(1, Qt.ItemDataRole.UserRole))
        new_visible = not current_visible
        self._set_item_visible_recursive(item, new_visible)

    def _set_item_visible_recursive(
        self, item: QtWidgets.QTreeWidgetItem, visible: bool
    ):
        # Bu item
        item.setData(1, Qt.ItemDataRole.UserRole, visible)
        self._update_eye_icon(item)

        layer_key = item.data(0, Qt.ItemDataRole.UserRole)
        if layer_key:
            # Harita tarafına haber ver
            self.layerVisibilityChanged.emit(str(layer_key), visible)

        # Çocukları da aynı moda geçir
        for i in range(item.childCount()):
            child = item.child(i)
            self._set_item_visible_recursive(child, visible)

    def _update_eye_icon(self, item: QtWidgets.QTreeWidgetItem):
        visible = bool(item.data(1, Qt.ItemDataRole.UserRole))

        # Renkli emoji yok; sade metin simgesi:
        # görünür: [●]  gizli: [ ]
        item.setText(1, "[●]" if visible else "[ ]")

        # Gizliyken label rengini biraz açalım (gri)
        from core.theme import THEME

        color = QtGui.QColor(
            THEME["tree_text"] if visible else THEME["tree_text_hidden"]
        )
        brush = QtGui.QBrush(color)
        item.setForeground(0, brush)
