# app/dialogs/project_edit_dialog.py

from __future__ import annotations

from typing import Optional, Tuple, List

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QComboBox,
)


class ProjectEditDialog(QDialog):
    """
    Proje ekleme / düzenleme için diyalog.

    Parametreler:
        crs_options: [(id, label), ...]
        selected_crs_id: başlangıçta seçili olacak koordinat sistemi ID'si

    get_data() çıktısı:
        (name, code, desc, start, end, center_x, center_y, center_z, crs_id)
    """

    def __init__(
        self,
        parent=None,
        *,
        name: Optional[str] = None,
        code: Optional[str] = None,
        desc: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        center_x: Optional[float] = None,
        center_y: Optional[float] = None,
        center_z: Optional[float] = None,
        crs_options: Optional[List[tuple[int, str]]] = None,
        selected_crs_id: Optional[int] = None,
    ):
        super().__init__(parent)

        self.setWindowTitle("Proje Düzenle" if name else "Yeni Proje")
        self.setModal(True)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # -----------------------------------
        # Ad
        # -----------------------------------
        name_row = QHBoxLayout()
        name_label = QLabel("Ad:")
        self.name_edit = QLineEdit()
        if name:
            self.name_edit.setText(name)
        name_row.addWidget(name_label)
        name_row.addWidget(self.name_edit)
        main_layout.addLayout(name_row)

        # -----------------------------------
        # Kod
        # -----------------------------------
        code_row = QHBoxLayout()
        code_label = QLabel("Kod:")
        self.code_edit = QLineEdit()
        if code:
            self.code_edit.setText(code)
        code_row.addWidget(code_label)
        code_row.addWidget(self.code_edit)
        main_layout.addLayout(code_row)

        # -----------------------------------
        # Başlangıç / Bitiş
        # -----------------------------------
        dates_row = QHBoxLayout()

        start_label = QLabel("Başlangıç:")
        self.start_edit = QLineEdit()
        self.start_edit.setPlaceholderText("YYYY-MM-DD")
        if start:
            self.start_edit.setText(start)

        end_label = QLabel("Bitiş:")
        self.end_edit = QLineEdit()
        self.end_edit.setPlaceholderText("YYYY-MM-DD")
        if end:
            self.end_edit.setText(end)

        dates_row.addWidget(start_label)
        dates_row.addWidget(self.start_edit)
        dates_row.addWidget(end_label)
        dates_row.addWidget(self.end_edit)

        main_layout.addLayout(dates_row)

        # -----------------------------------
        # Merkez koordinatlar (X, Y, Z)
        # -----------------------------------
        center_row = QHBoxLayout()

        cx_label = QLabel("Merkez X:")
        self.center_x_edit = QLineEdit()
        if center_x is not None:
            self.center_x_edit.setText(str(center_x))

        cy_label = QLabel("Y:")
        self.center_y_edit = QLineEdit()
        if center_y is not None:
            self.center_y_edit.setText(str(center_y))

        cz_label = QLabel("Z:")
        self.center_z_edit = QLineEdit()
        if center_z is not None:
            self.center_z_edit.setText(str(center_z))

        center_row.addWidget(cx_label)
        center_row.addWidget(self.center_x_edit)
        center_row.addWidget(cy_label)
        center_row.addWidget(self.center_y_edit)
        center_row.addWidget(cz_label)
        center_row.addWidget(self.center_z_edit)

        main_layout.addLayout(center_row)

        # -----------------------------------
        # Koordinat Sistemi (ComboBox)
        # -----------------------------------
        crs_row = QHBoxLayout()
        crs_label = QLabel("Koordinat Sistemi:")
        self.crs_combo = QComboBox()

        # Varsayılan seçenek
        self.crs_combo.addItem("— Seçilmedi —", None)

        self._crs_options: list[tuple[int, str]] = crs_options or []
        for cid, label in self._crs_options:
            self.crs_combo.addItem(label, cid)

        if selected_crs_id is not None:
            idx = self.crs_combo.findData(selected_crs_id)
            if idx >= 0:
                self.crs_combo.setCurrentIndex(idx)

        crs_row.addWidget(crs_label)
        crs_row.addWidget(self.crs_combo)
        main_layout.addLayout(crs_row)

        # -----------------------------------
        # Açıklama
        # -----------------------------------
        desc_label = QLabel("Açıklama:")
        self.desc_edit = QTextEdit()
        if desc:
            self.desc_edit.setPlainText(desc)

        main_layout.addWidget(desc_label)
        main_layout.addWidget(self.desc_edit)

        # -----------------------------------
        # Butonlar
        # -----------------------------------
        btn_row = QHBoxLayout()
        btn_row.addItem(
            QSpacerItem(
                40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )

        self.btn_cancel = QPushButton("Vazgeç")
        self.btn_ok = QPushButton("Kaydet")

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._on_accept)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)

        main_layout.addLayout(btn_row)

        self.setLayout(main_layout)
        self.resize(500, 380)

    # -----------------------------------
    # İç veri erişimi
    # -----------------------------------
    def get_data(self) -> Tuple[str, str, str, str, str, str, str, str, int | None]:
        """
        Formdan verileri döner:
        (name, code, desc, start, end, center_x, center_y, center_z, crs_id)
        """
        name = self.name_edit.text().strip()
        code = self.code_edit.text().strip()
        desc = self.desc_edit.toPlainText().strip()
        start = self.start_edit.text().strip()
        end = self.end_edit.text().strip()
        cx = self.center_x_edit.text().strip()
        cy = self.center_y_edit.text().strip()
        cz = self.center_z_edit.text().strip()
        crs_id = self.crs_combo.currentData()
        return name, code, desc, start, end, cx, cy, cz, crs_id

    # -----------------------------------
    # Onaylama
    # -----------------------------------
    def _on_accept(self):
        """
        Basit doğrulama: Proje adı boş olamaz.
        İstersen burada ekstra kontroller ekleyebilirsin.
        """
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus()
            self.name_edit.selectAll()
            return

        self.accept()
