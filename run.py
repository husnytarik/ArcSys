# run.py
"""
ArcSys uygulamasının giriş noktası.

Bu dosya sadece:
- QtWebEngine için gerekli ortam değişkenini ayarlar
- app.app_factory içindeki create_app() fonksiyonunu çağırır
- Qt event loop'unu (app.exec()) başlatır
"""

import os

# UYARI:
# Bu bayrak, QtWebEngine içinden hem HTTP(S) hem de file:/// yoluyla
# içerik yükleyebilmek için kullanılıyor. Web güvenlik kısıtlarını gevşetir.
# Geliştirme / saha ortamı için uygundur; genel amaçlı bir tarayıcı gibi
# kullanılmamalıdır.
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-web-security")

from app.app_factory import create_app


def main() -> None:
    """
    ArcSys masaüstü uygulamasını başlat.

    create_app:
      - QApplication örneğini oluşturur
      - ana pencereyi (MainWindow) hazırlar ve gösterir
      - veritabanı vb. kontrolleri içerir;
        kritik bir hata durumunda kullanıcıya mesaj gösterip
        uygulamayı başlatmamak için app = None döndürebilir.
    """
    app, _window = create_app()

    # create_app kritik bir durumda uygulamayı başlatmama kararı verebilir.
    if app is None:
        return

    # Qt event loop'unu başlat.
    app.exec()


if __name__ == "__main__":
    main()
