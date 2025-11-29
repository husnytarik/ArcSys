# run.py
import os

# Güvenli değil ama şimdilik OSM / file:/// erişimi için gerekli
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-web-security"

from app.main_window import create_app


def main() -> None:
    """ArcSys uygulamasını başlatır.

    - Qt için yazılımsal OpenGL ve benzeri ayarları `create_app` içinde yapar
    - Veritabanı (data/ArcSys.db) yoksa, kullanıcıya hata mesajı gösterip çıkılır
    """
    app, _window = create_app()
    if app is None:
        # create_app zaten kullanıcıya mesaj göstermiş oluyor
        return

    app.exec()


if __name__ == "__main__":
    main()
