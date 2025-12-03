# app/app_factory.py

import os
import sys
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen

from core.db import DB_PATH
from app.main_window import MainWindow


def create_app():
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)

    # DB kontrolü
    if not os.path.exists(DB_PATH):
        QMessageBox.critical(
            None, "Veritabanı Yok", f"ArcSys.db bulunamadı:\n{DB_PATH}"
        )
        return None, None

    app = QApplication(sys.argv)

    # Splash
    base_dir = Path(__file__).resolve().parent.parent
    icon_path = base_dir / "assets" / "logo" / "logo_1024.png"

    splash = None
    if icon_path.exists():
        pixmap = QPixmap(str(icon_path)).scaled(320, 320)
        splash = QSplashScreen(pixmap)
        splash.show()
        app.processEvents()

    # Asıl pencere
    window = MainWindow()

    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))

    window.show()

    if splash:
        time.sleep(0.5)
        splash.finish(window)

    return app, window
