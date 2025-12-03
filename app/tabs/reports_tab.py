from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QTextEdit,
    QSplitter,
)


class ReportsTab(QWidget):
    """
    Raporlar sekmesi:
    Şimdilik sadece iskelet.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.group_list = QListWidget()
        self.group_list.addItems(
            [
                "Açma T1 – Günlük Raporlar (dummy)",
                "Açma T2 – Günlük Raporlar (dummy)",
            ]
        )

        self.report_list = QListWidget()
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setPlaceholderText("Rapor içeriği...")

        splitter_main = QSplitter()
        splitter_main.addWidget(self.group_list)
        splitter_main.addWidget(self.report_list)
        splitter_main.addWidget(self.report_view)
        splitter_main.setStretchFactor(0, 1)
        splitter_main.setStretchFactor(1, 1)
        splitter_main.setStretchFactor(2, 3)

        layout = QVBoxLayout()
        layout.addWidget(splitter_main)
        self.setLayout(layout)

        self.group_list.currentTextChanged.connect(self.on_group_selected)
        self.report_list.currentTextChanged.connect(self.on_report_selected)

    def on_group_selected(self, group_name: str) -> None:
        self.report_list.clear()
        if not group_name:
            return

        self.report_list.addItems(
            [
                f"{group_name} – Rapor 1 (dummy)",
                f"{group_name} – Rapor 2 (dummy)",
            ]
        )

    def on_report_selected(self, report_title: str) -> None:
        if not report_title:
            self.report_view.clear()
            return

        self.report_view.setPlainText(
            f"{report_title}\n\n"
            "Bu alan ileride veritabanından çekilen rapor metni ile dolacak.\n"
            "Şu an sadece iskelet hazır."
        )
