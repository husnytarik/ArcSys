# core/services/finds_service.py

from __future__ import annotations

from typing import Any, Dict, List

from pyproj import Transformer

from core.db import get_connection


def load_finds_for_project(
    project_id: int,
    transformer: Transformer,
) -> List[Dict[str, Any]]:
    """
    Verilen proje için buluntuları (WGS84'e çevrilmiş) döner.

    Dönüş formatı:
    [
      {
        "id": ...,
        "trench_id": ...,
        "trench_code": ...,
        "trench_name": ...,
        "code": ...,
        "description": ...,
        "lat": ...,
        "lon": ...,
        "z": ...,
        "level_id": ...,
        "level_name": ...,
        "found_at": ...,
      },
      ...
    ]
    """
    finds_data: List[Dict[str, Any]] = []

    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute(
            """
            SELECT
              f.id,
              f.trench_id,
              f.code,
              f.description,
              f.found_at,
              f.x_global,
              f.y_global,
              f.z_global,
              f.level_id,
              l.name AS level_name,
              t.code AS trench_code,
              t.name AS trench_name
            FROM finds f
            JOIN trenches t ON f.trench_id = t.id
            LEFT JOIN levels l ON f.level_id = l.id
            WHERE t.project_id = ?
            ORDER BY f.id
            """,
            (project_id,),
        )
        rows = cur.fetchall()

        for (
            fid,
            trench_id,
            code,
            desc,
            found_at,
            xg,
            yg,
            zg,
            level_id,
            level_name,
            trench_code,
            trench_name,
        ) in rows:
            if xg is None or yg is None:
                continue

            lon, lat = transformer.transform(xg, yg)

            finds_data.append(
                {
                    "id": fid,
                    "trench_id": trench_id,
                    "trench_code": trench_code,
                    "trench_name": trench_name,
                    "code": code,
                    "description": desc,
                    "lat": lat,
                    "lon": lon,
                    "z": zg,
                    "level_id": level_id,
                    "level_name": level_name,
                    "found_at": found_at,
                }
            )
    finally:
        con.close()

    return finds_data
