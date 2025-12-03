# app/loading_bar.py

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar


class LoadingBarWidget(QWidget):
    """
    StatusBar içinde kullanılacak basit loading bar.
    - solda mesaj
    - sağda progress bar
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.label = QLabel("")
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(160)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)

    def set_message(self, text: str) -> None:
        self.label.setText(text)

    def set_range(self, minimum: int, maximum: int) -> None:
        self.progress.setMinimum(minimum)
        self.progress.setMaximum(maximum)

    def set_value(self, value: int) -> None:
        self.progress.setValue(value)
