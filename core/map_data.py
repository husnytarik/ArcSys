# core/map_data.py

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pyproj import Transformer

from core.db import get_connection, get_active_project_id
from core.services import (
    load_trenches_for_project,
    load_finds_for_project,
    load_map_layers_for_project,
)


@dataclass
class MapData:
    """
    Leaflet haritasının ihtiyaç duyduğu tüm verileri temsil eder.

    layers listesi içinde:
      - kind: "tile"   → URL template tile layer
      - kind: "image"  → GeoTIFF / worldfile image overlay
      - kind: "vector" → GeoJSON vektör katman
    """

    trenches: List[Dict[str, Any]]
    finds: List[Dict[str, Any]]
    layers: List[Dict[str, Any]]
    center_lat: float
    center_lon: float
    error_message: str  # Boş string ise hata yok.


def load_map_data(project_id: Optional[int] = None) -> MapData:
    """
    Veritabanından:
      - Açmalar (trenches + vertices)
      - Buluntular (finds)
      - map_layers (tile + image + vector)
    okuyup Leaflet için hazır hale getirir.

    Parametreler:
        project_id: İsteğe bağlı proje ID'si.
                    Verilmezse aktif proje (get_active_project_id) kullanılır.

    Dönüş:
        MapData dataclass örneği.
    """
    center_lat = 37.0
    center_lon = 32.0
    trenches_data: List[Dict[str, Any]] = []
    finds_data: List[Dict[str, Any]] = []
    layers_data: List[Dict[str, Any]] = []
    error_message = ""

    con = None
    try:
        con = get_connection()
        cur = con.cursor()

        # Proje ID verilmemişse aktif projeyi bul
        if project_id is None:
            project_id = get_active_project_id(con)

        if not project_id:
            raise RuntimeError("Aktif proje bulunamadı.")

        # Proje + EPSG
        cur.execute(
            """
            SELECT p.id, p.name, cs.epsg_code
            FROM projects p
            LEFT JOIN coordinate_systems cs
              ON p.coordinate_system_id = cs.id
            WHERE p.id = ?
            """,
            (project_id,),
        )
        proj_row = cur.fetchone()
        if not proj_row:
            raise RuntimeError("Veritabanında proje bulunamadı.")

        project_id, project_name, epsg_code = proj_row
        if not epsg_code:
            raise RuntimeError(f"Proje '{project_name}' için EPSG kodu tanımlı değil.")

        src_crs = f"EPSG:{epsg_code}"
        transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)

        # Servislerden veriyi çek
        trenches_data = load_trenches_for_project(project_id, transformer)
        finds_data = load_finds_for_project(project_id, transformer)
        layers_data = load_map_layers_for_project(project_id, transformer)

        # Harita merkezini belirle (öncelik: açma → buluntu)
        if trenches_data and trenches_data[0].get("vertices"):
            center_lat = trenches_data[0]["vertices"][0]["lat"]
            center_lon = trenches_data[0]["vertices"][0]["lon"]
        elif finds_data:
            center_lat = finds_data[0]["lat"]
            center_lon = finds_data[0]["lon"]

    except Exception as e:
        error_message = str(e)
    finally:
        if con is not None:
            con.close()

    return MapData(
        trenches=trenches_data,
        finds=finds_data,
        layers=layers_data,
        center_lat=center_lat,
        center_lon=center_lon,
        error_message=error_message,
    )
