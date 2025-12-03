# core/services/trenches_service.py

from __future__ import annotations

from typing import Any, Dict, List

from pyproj import Transformer

from core.db import get_connection


def load_trenches_for_project(
    project_id: int,
    transformer: Transformer,
) -> List[Dict[str, Any]]:
    """
    Verilen proje için açmaları ve köşe noktalarını (WGS84'e çevrilmiş) döner.

    Dönüş formatı:
    [
      {
        "id": ...,
        "code": ...,
        "name": ...,
        "project": ...,
        "vertices": [
          {"order": ..., "lat": ..., "lon": ..., "z": ...},
          ...
        ],
      },
      ...
    ]
    """
    trenches_data: List[Dict[str, Any]] = []

    con = get_connection()
    try:
        cur = con.cursor()

        # Açma temel bilgileri
        cur.execute(
            """
            SELECT t.id, t.code, t.name, p.name
            FROM trenches t
            JOIN projects p ON t.project_id = p.id
            WHERE t.project_id = ?
            ORDER BY t.id
            """,
            (project_id,),
        )
        trench_rows = cur.fetchall()

        for tid, tcode, tname, pname in trench_rows:
            # Köşe noktaları (GLOBAL koordinatlar)
            cur.execute(
                """
                SELECT order_index, x_global, y_global, z_global
                FROM trench_vertices
                WHERE trench_id = ?
                ORDER BY order_index
                """,
                (tid,),
            )
            verts = cur.fetchall()

            vertices_latlon = []
            for order_idx, xg, yg, zg in verts:
                if xg is None or yg is None:
                    continue
                lon, lat = transformer.transform(xg, yg)
                vertices_latlon.append(
                    {"order": order_idx, "lat": lat, "lon": lon, "z": zg}
                )

            if vertices_latlon:
                trenches_data.append(
                    {
                        "id": tid,
                        "code": tcode,
                        "name": tname,
                        "project": pname,
                        "vertices": vertices_latlon,
                    }
                )
    finally:
        con.close()

    return trenches_data
