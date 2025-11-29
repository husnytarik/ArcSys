# core/utils.py
from pathlib import Path


# Proje kökü (ArcSys klasörü)
BASE_DIR = Path(__file__).resolve().parent.parent

# Veritabanı / raster / tile klasörleri
DATA_DIR = BASE_DIR / "data"
RASTERS_DIR = DATA_DIR / "rasters"
TILES_DIR = DATA_DIR / "tiles"

# Web dosyaları (HTML template vb.)
WEB_DIR = BASE_DIR / "web"


def ensure_dir(path: Path) -> None:
    """Klasör yoksa oluştur."""
    path.mkdir(parents=True, exist_ok=True)
