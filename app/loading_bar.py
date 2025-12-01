# app/loading_bar.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt


class LoadingBarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("LoadingBarWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        # Üstteki yazı
        self.label = QLabel("Hazırlanıyor...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Renk / font temadan gelsin diye sadece boyut veriyoruz
        self.label.setStyleSheet("font-size: 11px;")

        # Alttaki progress bar
        self.progress = QProgressBar()
        self.progress.setObjectName("LoadingProgressBar")  # <-- TEMA BURAYA UYGULANACAK
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)

        # Buradaki sabit renkleri kaldırdık, her şey theme.build_qt_stylesheet'ten gelsin
        # self.progress.setStyleSheet(...)

        layout.addWidget(self.label)
        layout.addWidget(self.progress)

        # Başlangıçta gizli
        self.hide()

    # Dışarıdan kullanmak için küçük yardımcılar
    def set_message(self, text: str):
        self.label.setText(text)

    def set_range(self, minimum: int, maximum: int):
        self.progress.setMinimum(minimum)
        self.progress.setMaximum(maximum)

    def set_value(self, value: int):
        self.progress.setValue(value)
