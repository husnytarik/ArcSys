# core/webmap_loader.py

from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional

from core.db import get_connection, get_active_project_id
from core.map_data import load_map_data


def load_all_map_data(project_id: Optional[int] = None):
    """
    Harita için gerekli tüm verileri tek seferde döner.

    Dönüş:
      trenches, finds, layers, center_lat, center_lon, error_message
    """
    con = get_connection()
    try:
        if project_id is None:
            project_id = get_active_project_id(con)
        if project_id is None:
            raise RuntimeError("Aktif proje bulunamadı.")

        md = load_map_data(project_id)

        return (
            md.trenches,
            md.finds,
            md.layers,
            md.center_lat,
            md.center_lon,
            md.error_message,
        )
    finally:
        con.close()
